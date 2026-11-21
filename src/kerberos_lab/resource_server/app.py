"""Protected resource and local counter for the educational v1 protocol."""

import argparse
from pathlib import Path
import sys

from flask import Flask, jsonify, request
from werkzeug.exceptions import BadRequest, RequestEntityTooLarge

from kerberos_lab.common.clock import Clock
from kerberos_lab.common.crypto import open_ticket, verify_authenticator
from kerberos_lab.common.errors import (
    InvalidAuthentication, LabError, MalformedRequest, to_error_response,
)
from kerberos_lab.common.material import load_material
from kerberos_lab.common.models import parse_json_object
from kerberos_lab.common.replay_cache import ReplayStore
from kerberos_lab.common.settings import Settings, load_settings, make_clock


_BODY_LIMIT = 65_536


def create_app(settings: Settings, *, clock: Clock | None = None) -> Flask:
    """Require initialized role-scoped material before serving any requests."""
    if not isinstance(settings, Settings) or settings.role != 'resource':
        raise MalformedRequest('invalid_resource_settings')
    material = load_material(settings.run_dir, role='resource')
    store = ReplayStore.open_existing(
        material.resource_store_path, expected_run_id=material.run_id,
        namespace='resource', capacity=settings.replay_capacity,
        busy_timeout_ms=settings.sqlite_busy_timeout_ms,
    )
    app_clock = make_clock(settings) if clock is None else clock
    app = Flask(__name__)
    app.config['MAX_CONTENT_LENGTH'] = _BODY_LIMIT

    @app.errorhandler(LabError)
    def handle_lab_error(error):
        payload, status = to_error_response(error)
        return jsonify(payload), status

    @app.errorhandler(BadRequest)
    @app.errorhandler(RequestEntityTooLarge)
    def handle_bad_http_request(_error):
        payload, status = to_error_response(MalformedRequest('malformed_http_request'))
        return jsonify(payload), status

    @app.get('/health')
    def health():
        return jsonify(status='ok', role='resource_server', stage='implemented')

    @app.post('/access-resource')
    def access_resource():
        if request.query_string or request.mimetype != 'application/json':
            raise MalformedRequest('invalid_http_context')
        message = parse_json_object(request.get_data(cache=False), max_bytes=_BODY_LIMIT)
        if set(message) != {'version', 'service_ticket', 'authenticator', 'body'}:
            raise MalformedRequest('invalid_request_fields')
        if type(message['version']) is not int or message['version'] != 1:
            raise MalformedRequest('unsupported_request_version')
        ticket = open_ticket(message['service_ticket'], material.service_key, expected_kind='service')
        if ticket.client_id != material.client_id or ticket.service_id != material.service_id:
            raise InvalidAuthentication('wrong_resource_identity_or_audience')
        now = app_clock.now()
        authenticator = verify_authenticator(
            message['authenticator'], ticket, message['service_ticket'], message['body'],
            purpose='resource', now=now, skew=settings.allowed_clock_skew_seconds,
        )
        # Only this transaction choice differs between comparison modes.
        if settings.defense_mode == 'authenticator_cache':
            count = store.consume_and_increment(
                service_id=material.service_id, ticket_id=ticket.ticket_id,
                request_nonce=authenticator['request_nonce'], accepted_at=now,
            )
        else:
            count = store.increment_without_replay_tracking(service_id=material.service_id)
        return jsonify(version=1, status='granted', client_id=ticket.client_id,
                       service_id=material.service_id, request_nonce=authenticator['request_nonce'],
                       operation='increment', counter=count)

    return app


def main() -> None:
    parser = argparse.ArgumentParser(description='Run the local resource simulator')
    parser.add_argument('--run-dir', required=True, type=Path)
    parser.add_argument('--config', type=Path)
    parser.add_argument('--port', type=int)
    parser.add_argument('--clock-offset-seconds', type=int, default=0)
    parser.add_argument('--frozen-time-seconds', type=int)
    parser.add_argument('--defense-mode', choices=('authenticator_cache', 'authenticator_no_cache'))
    args = parser.parse_args()
    try:
        settings = load_settings(
            args.config, run_dir=args.run_dir, role='resource', port=args.port,
            clock_offset_seconds=args.clock_offset_seconds,
            frozen_time_seconds=args.frozen_time_seconds, defense_mode=args.defense_mode,
        )
        app = create_app(settings)
    except LabError as error:
        print(f'Resource startup failed: {error.reason or error.code}', file=sys.stderr)
        raise SystemExit(2) from None
    app.run(host=settings.host, port=settings.port, debug=False, use_reloader=False)


if __name__ == '__main__':
    main()
