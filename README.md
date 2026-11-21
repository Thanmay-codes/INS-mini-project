# INS mini project: Kerberos-style authentication lab

**Academic title:** Experimental Security Analysis of Kerberos-Style Ticket Authentication.
The longer submitted title is preserved in `docs/planning/original-plan.txt`; no
change to the submitted topic is required.

This college project implements a custom local Python/Flask ticket-authentication
simulator. It compares identical session-key-authenticated requests with replay
tracking disabled and enabled. Persistent atomic replay tracking, concurrent
duplicates, ordinary process restart and controlled clock offsets are the core
study. Bounded synthetic service-password guessing is a later extension.

## Current status

Shared contracts, cryptography, settings/clocks, private setup, persistent stores,
AS/TGS endpoints, the client and protected resource endpoint are implemented.
A05 adds real-process normal/invalid-flow integration and the launcher below.
See [gate status](docs/workflow/status.md): G1 is released; G2 requires A05's merge
and passing checks on merged main. Experiment runners, reviewed measurements,
figures and paper results are still pending. Passing tests are not paper results.

Use [project context](PROJECT_CONTEXT.md), [the implementation plan](docs/implementation-plan.md),
[task prompts](docs/prompts/README.md) and [ownership/workflow](docs/workflow/README.md)
for contributor instructions. Work in separate clones and follow released gates.
The human handles Git commits, pushes and authentication.

## Install and initialize

Python 3.11+ is required. From the repository root on Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m pip install -e '.[dev]'
```

On Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
python -m pip install -e ".[dev]"
```

The lock snapshot was validated locally on Python 3.14; the supported dependency
ranges are in `pyproject.toml`. Revalidate installation on other environments.
B reported that an existing POSIX permission-mode assertion fails on Windows;
Windows ACL protection is not established by that assertion. See the A05 handoff.

Create a **new** private run and choose a synthetic password at the hidden prompt:

```bash
python scripts/init_demo.py --run-dir data/private/demo-001
```

Use this same password for client login. There is no default password. Keys,
password verifier, tickets, captures and SQLite state stay in ignored private
paths. Existing directories are refused. To reset an independent experiment,
stop its servers and choose a new directory, e.g. `data/private/demo-002`.
Preserve the directory for restart tests; never recreate a lost replay database
while continuing that run. See [setup details](docs/contracts/setup-v1.md).

## Start, access and replay

In the activated environment, start both servers:

```bash
python scripts/run_lab.py --run-dir data/private/demo-001
```

Keep that terminal open. Activate the environment in another terminal, then run:

```bash
python -m kerberos_lab.client
python -m kerberos_lab.client run --run-dir data/private/demo-001 --count 2 --capture
```

The first command prints two health responses with `stage: implemented`.
The second prompts for the synthetic password, logs in, obtains a service ticket
and performs two increments with fresh authenticators on that ticket. For a fresh
run, the returned counters are 1 and 2. Output includes each saved relative
capture path, such as `captures/resource-<nonce>.json`.

To replay one, use its actual filename without the `captures/` prefix:

```bash
python -m kerberos_lab.client replay --run-dir data/private/demo-001 --capture resource-<nonce>.json
```

Replace `<nonce>` with the value printed by the client. In the default defended
mode, an already-consumed request returns `replay_detected` with HTTP 409, and the
CLI exits 1. Captures are bearer requests; keep them private.

Press **Ctrl+C in the launcher terminal** to stop both children. The launcher also
stops the sibling if either child exits. On POSIX, SIGTERM is handled as graceful
shutdown. Force-killing the launcher bypasses cleanup; stop surviving children
before restarting on their ports.

For the intentionally incomplete comparison mode, initialize a separate fresh
run, then pass `--defense-mode authenticator_no_cache` to the launcher. It keeps
ticket/MAC/context/time validation and the committed counter but omits duplicate
tracking. The same captured request can therefore increment again while valid.

## Runtime controls

Defaults are KDC `http://127.0.0.1:5000` and resource
`http://127.0.0.1:5001`. Bind addresses are fixed to loopback; debugger and reloader
are off. If you change ports, pass matching URLs to the client:

```bash
python scripts/run_lab.py --run-dir data/private/demo-001 --kdc-port 5100 --resource-port 5101
python -m kerberos_lab.client health --kdc-url http://127.0.0.1:5100 --resource-url http://127.0.0.1:5101
python -m kerberos_lab.client run --run-dir data/private/demo-001 --kdc-url http://127.0.0.1:5100 --resource-url http://127.0.0.1:5101
```

Run the launcher in its own terminal. For independent worker control:

```bash
python -m kerberos_lab.kdc.app --run-dir data/private/demo-001 --port 5000
python -m kerberos_lab.resource_server.app --run-dir data/private/demo-001 --port 5001
```

Each independent process needs its own terminal and stop command. Resource workers
may share one run directory/service key/store on distinct ports. The launcher
also supports `--config configs/replay.example.toml`, role-specific logical clock
offsets/frozen times and resource defense mode. See [runtime controls](docs/contracts/runtime-v1.md).
Clock injection never changes the host clock. The client CLI uses real time, so
use the injectable Python client clock for frozen-time tests.

## Verify

```bash
python -m pytest -q --tb=short
python docs/contracts/verify-fixtures.py
python -m pip check
```

A05 integration tests run the actual launcher, KDC, client and resource processes
over loopback, with temporary private state. Earlier B02 tests retain an explicitly
labeled resource stub; those alone do not establish the full flow. Linux is the
locally verified integration platform. No E01–E10 measurement matrix is claimed
by these correctness checks.

## Workspace and study limits

- `src/kerberos_lab/`: shared helpers, KDC, resource service and client.
- `scripts/`: private setup and local launcher.
- `tests/`: unit, integration and security checks.
- `configs/`: non-secret TOML settings.
- `data/private/`, `logs/`, `results/raw/`: ignored runtime artifacts.
- `experiments/`: planned runners and analysis; `results/published/`: reviewed evidence.
- `docs/`: contracts, plans, handoffs, references, diagrams, paper and presentation.

This is Kerberos-style, not Kerberos wire compatibility or Active Directory.
Local login delivers synthetic credentials/session material over loopback JSON,
an explicit educational simplification. Replay caching is an established defense;
we claim an evaluated student implementation, not a new protocol or vulnerability.
The optional password experiment will be Kerberoasting-inspired, with bounded
synthetic data. A dictionary miss only shows non-recovery within its stated budget.
Ordinary process persistence does not establish power-loss durability, hostile
filesystem rollback resistance or response recovery after a committed operation.
