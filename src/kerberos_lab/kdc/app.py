"""Authentication Server and Ticket-Granting Server for protocol v1."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from kerberos_lab.common._validation import identifier
from kerberos_lab.common.clock import Clock
from kerberos_lab.common.crypto import (
    encode_b64,
    new_identifier,
    new_key,
    open_ticket,
    seal_ticket,
    verify_authenticator,
    verify_password,
)
from kerberos_lab.common.errors import (
    InvalidCredentials,
    InvalidAuthentication,
    LabError,
    MalformedRequest,
    WrongService,
    to_error_response,
)
from kerberos_lab.common.material import load_material
from kerberos_lab.common.models import ClientSession, Ticket, parse_json_object
from kerberos_lab.common.replay_cache import ReplayStore
from kerberos_lab.common.settings import Settings, load_settings, make_clock


_BODY_LIMIT = 65_536


def _exact_fields(value: object, expected: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or set(value) != expected:
        raise MalformedRequest("invalid_request_fields")
    return value


def _version_one(value: object) -> None:
    if type(value) is not int or value != 1:
        raise MalformedRequest("unsupported_request_version")


def _request_object() -> dict[str, object]:
    if request.query_string:
        raise MalformedRequest("query_string_not_supported")
    if request.mimetype != "application/json":
        raise MalformedRequest("application_json_required")
    return parse_json_object(request.get_data(cache=False), max_bytes=_BODY_LIMIT)


def _session(ticket: Ticket) -> ClientSession:
    return ClientSession(
        client_id=ticket.client_id,
        service_id=ticket.service_id,
        ticket_id=ticket.ticket_id,
        session_key=ticket.session_key,
        expires_at=ticket.expires_at,
    )


def create_app(settings: Settings, *, clock: Clock | None = None) -> Flask:
    """Load validated KDC material and build the loopback HTTP application."""
    if not isinstance(settings, Settings) or settings.role != "kdc":
        raise MalformedRequest("invalid_kdc_settings")

    material = load_material(settings.run_dir, role="kdc")
    if (material.tgs_key is None or material.password_verifier is None
            or material.kdc_store_path is None):
        raise MalformedRequest("incomplete_kdc_material")
    replay_store = ReplayStore.open_existing(
        material.kdc_store_path,
        expected_run_id=material.run_id,
        namespace="tgs",
        capacity=settings.replay_capacity,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )
    app_clock = make_clock(settings) if clock is None else clock

    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = _BODY_LIMIT
    app.config["KDC_SETTINGS"] = settings

    @app.errorhandler(LabError)
    def handle_lab_error(error: LabError):
        payload, status = to_error_response(error)
        return jsonify(payload), status

    @app.errorhandler(RequestEntityTooLarge)
    @app.errorhandler(BadRequest)
    def handle_bad_http_request(_error):
        payload, status = to_error_response(MalformedRequest("malformed_http_request"))
        return jsonify(payload), status

    @app.get("/health")
    def health():
        return jsonify(status="ok", role="kdc", stage="implemented")

    @app.post("/login")
    def login():
        body = _exact_fields(_request_object(), {"username", "password"})
        username = body["username"]
        password = body["password"]
        if not isinstance(username, str) or not isinstance(password, str):
            raise MalformedRequest("invalid_login_fields")
        identifier(username)

        # Verify even for an unknown username so both credential failures do
        # comparable password-KDF work and share one public response.
        password_ok = verify_password(password, material.password_verifier)
        if username != material.client_id or not password_ok:
            raise InvalidCredentials()

        now = app_clock.now()
        expires_at = now + settings.ticket_lifetime_seconds
        session_key = new_key()
        tgt = Ticket(
            version=1,
            kind="tgt",
            ticket_id=new_identifier(),
            client_id=material.client_id,
            service_id="tgs",
            issued_at=now,
            not_before=now,
            expires_at=expires_at,
            session_key=encode_b64(session_key),
        )
        envelope = seal_ticket(tgt, material.tgs_key)
        client_session = _session(tgt)
        return jsonify({
            "version": 1,
            "tgt": envelope,
            "client_session": client_session.to_dict(),
        })

    @app.post("/service-ticket")
    def service_ticket():
        message = _exact_fields(
            _request_object(), {"version", "tgt", "authenticator", "body"}
        )
        _version_one(message["version"])
        body = _exact_fields(message["body"], {"service_id"})
        requested_service = body["service_id"]
        if not isinstance(requested_service, str):
            raise MalformedRequest("invalid_service_id")

        tgt = open_ticket(message["tgt"], material.tgs_key, expected_kind="tgt")
        if tgt.client_id != material.client_id or tgt.service_id != "tgs":
            raise InvalidAuthentication("wrong_tgt_identity_or_audience")

        # One captured logical time is used for all checks and store metadata.
        now = app_clock.now()
        authenticator = verify_authenticator(
            message["authenticator"],
            tgt,
            message["tgt"],
            body,
            purpose="tgs",
            now=now,
            skew=settings.allowed_clock_skew_seconds,
        )
        if requested_service != material.service_id:
            raise WrongService("unsupported_service")

        expires_at = min(now + settings.ticket_lifetime_seconds, tgt.expires_at)
        if expires_at <= now:
            raise InvalidAuthentication("tgt_expiry_leaves_no_service_lifetime")

        # Reserve an accepted authenticator before issuing any ticket. TGS
        # replay protection is independent of resource defense-mode settings.
        replay_store.consume(
            service_id="tgs",
            ticket_id=tgt.ticket_id,
            request_nonce=authenticator["request_nonce"],
            accepted_at=now,
        )

        service_ticket = Ticket(
            version=1,
            kind="service",
            ticket_id=new_identifier(),
            client_id=tgt.client_id,
            service_id=material.service_id,
            issued_at=now,
            not_before=now,
            expires_at=expires_at,
            session_key=encode_b64(new_key()),
        )
        service_envelope = seal_ticket(service_ticket, material.service_key)
        return jsonify({
            "version": 1,
            "service_ticket": service_envelope,
            "client_session": _session(service_ticket).to_dict(),
        })

    return app


def _argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local KDC simulator")
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--config", type=Path)
    parser.add_argument("--port", type=int)
    parser.add_argument("--clock-offset-seconds", type=int, default=0)
    parser.add_argument("--frozen-time-seconds", type=int)
    return parser


def main() -> None:
    args = _argument_parser().parse_args()
    try:
        settings = load_settings(
            args.config,
            run_dir=args.run_dir,
            role="kdc",
            port=args.port,
            clock_offset_seconds=args.clock_offset_seconds,
            frozen_time_seconds=args.frozen_time_seconds,
        )
        app = create_app(settings)
    except LabError as error:
        reason = error.reason or error.code
        print(f"KDC startup failed: {reason}", file=sys.stderr)
        raise SystemExit(2) from None

    app.run(host=settings.host, port=settings.port, debug=False, use_reloader=False)


if __name__ == "__main__":
    main()
