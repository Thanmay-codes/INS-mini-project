"""Client integration with the real KDC and a contract-only resource stub."""

from contextlib import contextmanager
import json
from threading import Thread

from flask import Flask, jsonify, request
from werkzeug.serving import make_server
import pytest

from kerberos_lab.client import (
    AuthenticationClient,
    CaptureError,
    ClientProtocolError,
    RemoteError,
    check_health,
    load_capture,
    save_capture,
)
from kerberos_lab.client import __main__ as client_cli
from kerberos_lab.common.clock import FrozenClock
from kerberos_lab.common.material import initialize_run
from kerberos_lab.common.models import parse_json_object
from kerberos_lab.common.settings import Settings
from kerberos_lab.kdc.app import create_app as create_kdc_app


PASSWORD = "synthetic client test password"
NOW = 1_700_000_000


@contextmanager
def serve(app):
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def make_resource_contract_stub():
    app = Flask("resource-contract-stub")
    app.config["seen_requests"] = []
    app.config["error_code"] = None
    app.config["http_status"] = None

    @app.get("/health")
    def health():
        return jsonify(status="ok", role="resource_server", stage="scaffold")

    @app.post("/access-resource")
    def access_resource():
        raw = request.get_data(cache=False)
        app.config["seen_requests"].append(raw)
        message = parse_json_object(raw)
        auth = message["authenticator"]
        body = message["body"]
        http_status = app.config["http_status"]
        if http_status is not None:
            return "<html>not implemented</html>", http_status
        error_code = app.config["error_code"]
        if error_code is not None:
            return jsonify(version=1, error=error_code), 409
        return jsonify(
            version=1,
            status="granted",
            client_id=auth["client_id"],
            service_id="files",
            request_nonce=auth["request_nonce"],
            operation=body["operation"],
            counter=len(app.config["seen_requests"]),
        )

    return app


def make_real_kdc(tmp_path):
    run_dir = tmp_path / "run"
    initialize_run(run_dir, password=PASSWORD, run_id="b" * 32)
    settings = Settings(
        run_dir=run_dir,
        role="kdc",
        port=5000,
        frozen_time_seconds=NOW,
    )
    return run_dir, create_kdc_app(settings, clock=FrozenClock(NOW))


def test_real_kdc_client_journey_capture_and_fresh_authenticator(tmp_path):
    run_dir, kdc_app = make_real_kdc(tmp_path)
    resource_app = make_resource_contract_stub()

    with serve(kdc_app) as kdc_url, serve(resource_app) as resource_url:
        client = AuthenticationClient(kdc_url, resource_url, clock=FrozenClock(NOW))
        health = check_health(kdc_url, resource_url)
        assert [item["role"] for item in health] == ["kdc", "resource_server"]
        assert health[0]["stage"] == "implemented"
        assert health[1]["stage"] == "scaffold"

        grant = client.authenticate("alice", PASSWORD)
        first = client.build_resource_request(grant)
        second = client.build_resource_request(grant)
        assert first.message["service_ticket"] == second.message["service_ticket"]
        assert first.request_nonce != second.request_nonce
        assert first.raw_bytes != second.raw_bytes

        saved_name = save_capture(run_dir, first, name="first-resource-request.json")
        assert saved_name == "captures/first-resource-request.json"
        loaded = load_capture(run_dir, "first-resource-request.json")
        assert loaded.raw_bytes == first.raw_bytes

        response = client.send_resource_request(first)
        assert response["status"] == "granted"
        assert response["request_nonce"] == first.request_nonce
        client.send_resource_request(loaded)
        client.send_resource_request(second)
        assert resource_app.config["seen_requests"] == [
            first.raw_bytes, first.raw_bytes, second.raw_bytes,
        ]

        with pytest.raises(CaptureError):
            save_capture(run_dir, first, name="first-resource-request.json")
        with pytest.raises(CaptureError):
            load_capture(run_dir, "../escape.json")
        with pytest.raises(CaptureError):
            type(first).from_bytes(first.raw_bytes + b" ")
        with pytest.raises(CaptureError):
            type(first)(b"{}")


def test_remote_errors_and_endpoint_validation(tmp_path):
    _run_dir, kdc_app = make_real_kdc(tmp_path)
    resource_app = make_resource_contract_stub()

    with serve(kdc_app) as kdc_url, serve(resource_app) as resource_url:
        client = AuthenticationClient(kdc_url, resource_url, clock=FrozenClock(NOW))
        with pytest.raises(RemoteError) as bad_password:
            client.login("alice", "wrong password")
        assert (bad_password.value.status, bad_password.value.code) == (401, "invalid_credentials")

        grant = client.authenticate("alice", PASSWORD)
        captured = client.build_resource_request(grant)
        resource_app.config["error_code"] = "replay_detected"
        with pytest.raises(RemoteError) as replay:
            client.send_resource_request(captured)
        assert (replay.value.status, replay.value.code) == (409, "replay_detected")

        resource_app.config["error_code"] = None
        resource_app.config["http_status"] = 404
        with pytest.raises(RemoteError) as not_implemented:
            client.send_resource_request(captured)
        assert (not_implemented.value.status, not_implemented.value.code) == (404, "http_404")

    with pytest.raises(ClientProtocolError):
        AuthenticationClient("https://example.com", "http://127.0.0.1:5001")


def test_health_command_without_arguments_is_preserved(monkeypatch, capsys):
    expected = [
        {"url": "http://127.0.0.1:5000/health", "status": "ok", "role": "kdc", "stage": "implemented"},
        {"url": "http://127.0.0.1:5001/health", "status": "ok", "role": "resource_server", "stage": "scaffold"},
    ]
    seen = []

    def fake_health(kdc_url, resource_url):
        seen.append((kdc_url, resource_url))
        return expected

    monkeypatch.setattr(client_cli, "check_health", fake_health)
    assert client_cli.main([]) == 0
    assert seen == [("http://127.0.0.1:5000", "http://127.0.0.1:5001")]
    assert capsys.readouterr().out.splitlines() == [
        json.dumps(item) for item in expected
    ]
