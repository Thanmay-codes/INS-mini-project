"""Check the two running server starters using the Python standard library."""

import json
import sys
from urllib.error import URLError
from urllib.request import urlopen


def main() -> None:
    failed = False
    for role, port in (("kdc", 5000), ("resource_server", 5001)):
        url = f"http://127.0.0.1:{port}/health"
        try:
            with urlopen(url, timeout=3) as response:
                payload = json.load(response)
            if payload.get("status") != "ok" or payload.get("role") != role:
                raise ValueError("Unexpected health response")
            print(json.dumps({"url": url, **payload}))
        except (URLError, TimeoutError, ValueError) as error:
            print(f"{role}: {error}", file=sys.stderr)
            failed = True
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
