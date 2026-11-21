# Client usage outline (planned)

This is a B00 planning note. The current CLI only checks the two scaffold health
endpoints; it does not authenticate, obtain tickets, or access the resource. The
AS/TGS/resource journey below follows the released v1 contract and is planned
client behavior, not an implemented end-to-end flow.

## Current scaffold check

After installing the project dependencies, start both local servers from the
repository root:

```powershell
python scripts/run_lab.py
```

In another terminal, run the existing health client:

```powershell
python -m kerberos_lab.client
```

The current client requests `GET /health` at `127.0.0.1:5000` and
`127.0.0.1:5001`. It expects JSON with `status: ok` and the corresponding role;
the scaffold stage is `scaffold`. Stop the launcher with Ctrl+C. This is only a
process/setup check and does not demonstrate authentication.

## Planned normal client journey

Once the KDC, resource server and client tasks are implemented and integrated,
the intended flow is:

1. Initialize a new private run directory using the lead-owned setup command.
   The client will use the synthetic `alice` credential supplied locally; no
   default password is defined.
2. Send `POST /login` with `username` and `password` to the KDC. On success,
   retain the opaque TGT and the separately returned client/TGS session
   material for the next exchange.
3. Send `POST /service-ticket` with the TGT, a TGS-purpose authenticated
   request, and body `{"service_id":"files"}`. The KDC validates and consumes
   the TGS request before returning an opaque service ticket and separate
   client/service session material.
4. Send `POST /access-resource` with the service ticket, a resource-purpose
   authenticated request, and body `{"operation":"increment"}`. A successful
   response reports the demo counter. Replay behavior depends on the resource
   defense mode; TGS replay checking remains enabled in either mode.

The client should use the released shared `ClientSession`, canonical encoding,
and authenticator-signing helpers rather than implementing cryptography or
serialization independently. A replay capture should preserve the structured
resource request (ticket, authenticator and body) so a replay does not silently
create a new authenticator. A legitimate second operation must be signed with a
fresh request nonce.

## Future CLI shape

The exact CLI is pending B02 and lead integration. These examples are proposals,
not commands that work in the current checkout:

```text
python -m kerberos_lab.client login --run-dir data/private/<run>
python -m kerberos_lab.client access --run-dir data/private/<run> --operation increment
python -m kerberos_lab.client capture --run-dir data/private/<run> --output <private-capture>
python -m kerberos_lab.client replay --capture <private-capture>
```

The existing health command `python -m kerberos_lab.client` must remain
available after B02 replaces or extends its current default behavior. Captures
can contain bearer tickets and authenticators; keep them in ignored private
storage and never commit them. The simulator delivers credentials and session
material over loopback JSON and is not a production Kerberos exchange.

## Questions for the lead / contract

- The released v1 API defines the wire messages and signing helpers, but leaves
  exact client subcommands, local secret prompting, and capture file format to
  B02. Confirm the command interface during B02 before treating these examples
  as stable.
- Confirm how the client receives the run directory and synthetic password
  without putting secrets in arguments, logs, or tracked files. The shared
  setup CLI uses hidden prompting or a single line from standard input.
- Keep capture/replay artifacts private and confirm whether B02 should store
  canonical bytes or a validated structured request. In either form replay
  must preserve the original authenticator.

The shared v1 contract already fixes endpoint paths, request/response fields,
error codes, authentication binding, and the client health invocation. Any
incompatible change to these shared fields belongs to the lead and requires a
contract revision; this outline does not propose such a change.
