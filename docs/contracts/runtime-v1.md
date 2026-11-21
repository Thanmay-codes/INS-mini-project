# Local runtime controls — v1 integration

The launcher runs the released KDC and resource modules as separate child
processes. Invoke it from the repository root using the installed environment:

```bash
python scripts/run_lab.py --run-dir data/private/demo-001
```

Initialize that directory with `scripts/init_demo.py` first. The launcher does
not initialize, reset or repair state. It uses argv arrays with the same Python
interpreter, never shell interpolation. Paths with spaces are supported.

| Launcher option | Default / meaning |
| --- | --- |
| `--run-dir PATH` | Required, existing private run shared by both children |
| `--config PATH` | Optional shared TOML; e.g. `configs/replay.example.toml` |
| `--kdc-port INT` | 5000; must differ from the resource port |
| `--resource-port INT` | 5001 |
| `--kdc-clock-offset-seconds INT` | 0; logical KDC offset |
| `--resource-clock-offset-seconds INT` | 0; logical resource offset |
| `--kdc-frozen-time-seconds INT` | Optional fixed base for KDC clock |
| `--resource-frozen-time-seconds INT` | Optional fixed base for resource clock |
| `--defense-mode MODE` | Override resource TOML mode; default `authenticator_cache` |

The alternative mode is `authenticator_no_cache` and is intentionally incomplete.
Explicit CLI overrides take precedence over TOML. Frozen time plus offset produces
the effective logical time; neither changes the operating-system clock. The
client CLI uses its real clock. Deterministic callers should inject
`FrozenClock` into `AuthenticationClient` as described in its public API.

Child app flags use `--port`, `--clock-offset-seconds` and
`--frozen-time-seconds` without role prefixes. Only the resource receives
`--defense-mode`; the KDC always consumes TGS request identities. Both children
require `--run-dir` and may also be started independently. Multiple resource
workers can use distinct ports with the same directory/key/store. There are no
HTTP clock, reset or defense-mode mutation endpoints.

The startup message means children were spawned, not that they are healthy.
Use `python -m kerberos_lab.client` at default ports or explicit `health` with
`--kdc-url`/`--resource-url` for alternate ports. Health returns
`{"status":"ok","role":"kdc|resource_server","stage":"implemented"}`.
A health response is not a per-operation state-integrity check; accesses still
validate the required store and fail closed.

Ctrl+C stops both children. POSIX SIGTERM is also handled; on Windows the
launcher installs a SIGBREAK handler for console-group interruption. Child exit
or spawn failure stops remaining children and returns nonzero. Termination waits
are bounded, followed by kill/wait if needed. Force-killing the launcher or OS
termination that bypasses Python cannot promise child cleanup. Actual lifecycle
integration was verified on Linux; Windows console behavior needs a native run.

A05's tests exercise real AS/TGS/resource flows, invalid credentials/artifacts,
role/context/time failures, byte-preserving captures/replays, same-ticket fresh
requests and launcher cleanup. See `docs/handoffs/A/A05.md`. G2 can be released
only after A05 is merged and checks rerun at a recorded main SHA. These checks
produce no performance benchmark, E01–E10 evidence or scientific result.

The older B-owned `docs/usage/client.md` was authored before A04 integration and
contains scaffold caveats. Root README and this runtime document describe the
integrated startup commands; B is requested to reconcile its usage page.
