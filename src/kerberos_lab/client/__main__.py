"""Command-line client; no arguments retain the original health check."""

from __future__ import annotations

import argparse
import getpass
import json
from pathlib import Path
import sys

from .api import (
    AuthenticationClient,
    CaptureError,
    ClientError,
    RemoteError,
    check_health,
    load_capture,
    save_capture,
)


_KDC_DEFAULT = "http://127.0.0.1:5000"
_RESOURCE_DEFAULT = "http://127.0.0.1:5001"


def _count(value: str) -> int:
    try:
        result = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError("count must be an integer") from None
    if not 1 <= result <= 10000:
        raise argparse.ArgumentTypeError("count must be between 1 and 10000")
    return result


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Local Kerberos-style lab client")
    commands = parser.add_subparsers(dest="command", required=True)

    health = commands.add_parser("health", help="check both local server health endpoints")
    health.add_argument("--kdc-url", default=_KDC_DEFAULT)
    health.add_argument("--resource-url", default=_RESOURCE_DEFAULT)

    run = commands.add_parser("run", help="perform login, service-ticket and resource access")
    run.add_argument("--run-dir", required=True, type=Path,
                     help="private run directory created by scripts/init_demo.py")
    run.add_argument("--username", default="alice")
    run.add_argument("--kdc-url", default=_KDC_DEFAULT)
    run.add_argument("--resource-url", default=_RESOURCE_DEFAULT)
    run.add_argument("--operation", choices=("increment",), default="increment")
    run.add_argument("--count", type=_count, default=1,
                     help="number of fresh operations using one service ticket")
    run.add_argument("--capture", action="store_true",
                     help="save each exact resource request under <run-dir>/captures/")

    replay = commands.add_parser("replay", help="send an exact saved resource request")
    replay.add_argument("--run-dir", required=True, type=Path)
    replay.add_argument("--capture", required=True,
                        help="capture filename inside <run-dir>/captures/")
    replay.add_argument("--resource-url", default=_RESOURCE_DEFAULT)

    return parser


def _print_health(kdc_url: str = _KDC_DEFAULT,
                  resource_url: str = _RESOURCE_DEFAULT) -> int:
    for response in check_health(kdc_url, resource_url):
        print(json.dumps(response))
    return 0


def _print_grant(result: dict[str, object], *, capture: str | None = None) -> None:
    public = {
        key: result[key]
        for key in ("status", "client_id", "service_id", "request_nonce", "operation", "counter")
    }
    if capture is not None:
        public["capture"] = capture
    print(json.dumps(public))


def _run(args: argparse.Namespace) -> int:
    password = getpass.getpass(f"Password for {args.username}: ")
    client = AuthenticationClient(args.kdc_url, args.resource_url)
    grant = client.authenticate(args.username, password)
    for _index in range(args.count):
        captured = client.build_resource_request(grant, operation=args.operation)
        capture_name = None
        if args.capture:
            capture_name = save_capture(args.run_dir, captured).replace("\\", "/")
        result = client.send_resource_request(captured)
        _print_grant(result, capture=capture_name)
    return 0


def _replay(args: argparse.Namespace) -> int:
    captured = load_capture(args.run_dir, args.capture)
    client = AuthenticationClient(resource_url=args.resource_url)
    result = client.send_resource_request(captured)
    _print_grant(result, capture=f"captures/{args.capture}")
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    # Preserve the original `python -m kerberos_lab.client` health check.
    if not arguments:
        try:
            return _print_health()
        except ClientError as error:
            print(json.dumps({"error": "health_check_failed", "detail": str(error)}), file=sys.stderr)
            return 1

    args = _parser().parse_args(arguments)
    try:
        if args.command == "health":
            return _print_health(args.kdc_url, args.resource_url)
        if args.command == "run":
            return _run(args)
        if args.command == "replay":
            return _replay(args)
        raise AssertionError("unreachable command")
    except RemoteError as error:
        print(json.dumps({"error": error.code, "http_status": error.status}), file=sys.stderr)
        return 1
    except CaptureError as error:
        print(json.dumps({"error": "capture_error", "detail": str(error)}), file=sys.stderr)
        return 1
    except ClientError as error:
        print(json.dumps({"error": "client_error", "detail": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
