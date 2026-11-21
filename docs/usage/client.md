# Client usage

The client provides a backward-compatible health check, a reusable AS → TGS →
resource API, a CLI for a normal request, and exact resource-request captures.
It uses only loopback HTTP endpoints and the shared v1 ticket/authenticator
helpers. The local login sends the synthetic password and session data as
loopback JSON; this is an educational simplification, not a production Kerberos
exchange.

## Health check

With the KDC and resource server running, either existing no-argument invocation
checks both health endpoints and prints one JSON response per server:

```powershell
python -m kerberos_lab.client
```

The explicit equivalent is:

```powershell
python -m kerberos_lab.client health
```

Optional `--kdc-url` and `--resource-url` flags select alternate ports on
`127.0.0.1`. The client rejects non-loopback hosts. The KDC health response has
`stage: implemented`; the resource server remains a health-only scaffold until
A04 is integrated.

## Normal request CLI

Create a new private run directory first. The setup command prompts for the
synthetic user's password without echoing it:

```powershell
python scripts/init_demo.py --run-dir data/private/demo-001
```

Start the KDC with that initialized directory. The current resource server
starter can be started separately for its health endpoint:

```powershell
python -m kerberos_lab.kdc.app --run-dir data/private/demo-001
python -m kerberos_lab.resource_server.app
```

After A04 provides `POST /access-resource`, perform the complete client flow:

```powershell
python -m kerberos_lab.client run --run-dir data/private/demo-001
```

The client prompts for the password, obtains a TGT and service ticket, signs an
`increment` request with a fresh authenticator, and prints only the public
operation result. `--count N` performs N requests using one service ticket, with
a fresh authenticator for each request. Use `--capture` to save each exact
request body under `data/private/demo-001/captures/`; the output includes each
relative capture path. Captures contain bearer tickets and authenticators, so
keep them in the ignored private run directory and never commit them.

The `run` command is implemented, but a complete run cannot succeed in this
checkout because the resource app still returns only health responses. The B02
client tests use the real KDC endpoints and a clearly labeled contract stub for
resource responses; they do not claim a protected-resource implementation or
full normal-flow integration.

When A04 is integrated, start its resource app with the same initialized run
directory (the released app contract requires `--run-dir`):

```powershell
python -m kerberos_lab.resource_server.app --run-dir data/private/demo-001
```

That resource CLI is not available in the current scaffold yet.

## Replay a saved request

Pass the capture's filename (not the `captures/` prefix); the client reads the
saved bytes and posts them unchanged:

```powershell
python -m kerberos_lab.client replay --run-dir data/private/demo-001 --capture resource-<nonce>.json
```

With A04 integrated, an already-consumed request should produce the contract's
`409 replay_detected` response. Replay sends the same ticket, authenticator,
nonce, and body. It does not create a fresh authenticator.

## Reusable Python API

B03 and other callers can obtain a service grant once, then create fresh
resource requests on the same service ticket:

```python
from pathlib import Path
from getpass import getpass

from kerberos_lab.client import AuthenticationClient, load_capture, save_capture

client = AuthenticationClient()
password = getpass("Password for alice: ")
grant = client.authenticate("alice", password)
first = client.build_resource_request(grant, operation="increment")
second = client.build_resource_request(grant, operation="increment")

assert first.request_nonce != second.request_nonce
capture_path = save_capture(Path("data/private/demo-001"), first)
restored = load_capture(Path("data/private/demo-001"), capture_path.removeprefix("captures/"))
assert restored.raw_bytes == first.raw_bytes

# Send any request byte-for-byte as captured:
# result = client.send_resource_request(restored)
```

`AuthenticationClient` accepts injectable `clock` and `timeout` values for
deterministic tests. `CapturedRequest.raw_bytes` contains the canonical v1 POST
body; `send_resource_request` transmits those bytes without reserializing them.
Capture helpers only create/read `.json` files beneath `<run-dir>/captures/`,
reject path traversal and do not overwrite existing captures. The client API
raises `RemoteError` with the stable HTTP status/error code, or safe
transport/protocol/capture errors without printing credentials, tickets, or
session keys.

## Launcher coordination

The existing `scripts/run_lab.py` launcher and root README have not yet been
updated for the required KDC `--run-dir` argument or the A04 resource settings.
Use the direct process commands above until A05 integrates and documents the
complete launcher. The client does not provide server time-control endpoints;
tests inject the shared logical `Clock` API instead.
