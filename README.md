# Kerberos-Style Authentication & Replay Protection Lab

An educational Python/Flask simulator built for our Information and Network Security (INS) college project and conference paper.

The project implements a local ticket-based authentication flow (AS, TGS, resource server, and CLI client) and evaluates **persistent, atomic replay protection** against an intentionally incomplete **no-cache control** under exact duplicates, concurrent workers, process restarts, and controlled clock offsets. It also includes a small, bounded offline service-password guessing demo (Kerberoasting-inspired).

---

## Architecture

```text
CLI Client
  |  POST /login (synthetic username + password)
  v
KDC Process — AS & TGS (127.0.0.1:5000)
  |  Returns AES-256-GCM TGT + session key
  |  POST /service-ticket (TGT + HMAC-SHA-256 authenticator)
  |  Returns AES-256-GCM service ticket + session key
  v
Resource Server (127.0.0.1:5001)
  |  POST /access-resource (service ticket + fresh nonce + HMAC authenticator)
  |  Validates ticket, audience, context, body digest, and time bounds
  v
SQLite Replay Store & Counter (atomic BEGIN IMMEDIATE transaction)
```

Editable Mermaid architecture, sequence, and comparison diagrams are in [docs/diagrams/](docs/diagrams/README.md).

---

## Summary of Measured Results

All numbers below come from the reviewed, sanitized datasets in [results/published/a07-20261124/](results/published/a07-20261124/manifest.json) and [results/published/extension/](results/published/extension/manifest.json).

| Experiment | What was tested | Observed outcome |
| --- | --- | --- |
| **E01–E03 (30 trials each)** | Exact duplicate replay vs. legitimate fresh requests (300 requests total) | No-cache accepted **30/30** duplicates; persistent cache accepted **0/30** (`409 replay_detected`). Legitimate rejections: **0/90** in both modes. |
| **E04 (smoke)** | Modified ticket, authenticator, body, and service audience | All 4 mutation phases rejected (`401` / `400`), 0 missing attempts. |
| **E05 (smoke)** | 2, 4, and 8 concurrent worker processes sharing one SQLite store | Defended mode committed exactly **1** operation (`counter = 1`) in every worker-count condition. |
| **E06 & E10 (smoke)** | Replay after ordinary process restart and ±15 s logical clock shifts | Previously consumed requests stayed rejected (`409`). |
| **E07 & E08 (smoke)** | Clock offsets (−60 to +60 s) and ticket validity edges (−31 to +331 s) | Matched the inclusive ±30 s skew and leeway rules. |
| **E09 (smoke)** | Missing or corrupt SQLite replay store | Failed closed with `503 replay_state_unavailable`. |
| **E11–E12 (extension)** | Offline PBKDF2-SHA256 + AES-GCM guessing on a 5-word demo list | Weak password in list recovered in **4/5** attempts (`113.99 ms`); random absent password not recovered in **5/5** attempts (`165.01 ms`). |

---

## Quick Start

Python **3.11+** is required (validated locally on Linux / Python 3.14.8).

### 1. Install dependencies

**Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock.txt
python -m pip install -e '.[dev]'
```

**Windows PowerShell:**
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock.txt
python -m pip install -e ".[dev]"
```

### 2. Initialize a private run

Create a fresh run directory and enter a synthetic password at the prompt (there is no default password):

```bash
python scripts/init_demo.py --run-dir data/private/demo-001
```

Keys, password verifiers, captures, and SQLite databases stay inside ignored `data/private/` paths. To reset an experiment, stop the servers and pick a new directory name (for example `data/private/demo-002`).

### 3. Start the servers

```bash
python scripts/run_lab.py --run-dir data/private/demo-001
```

Keep this terminal open (press `Ctrl+C` to stop both servers cleanly).

### 4. Run the client and test a replay

In a second terminal with `.venv` activated:

```bash
# Check both servers
python -m kerberos_lab.client

# Log in, fetch a service ticket, execute 2 fresh requests, and capture them
python -m kerberos_lab.client run --run-dir data/private/demo-001 --count 2 --capture
```

The command prints each saved capture path (for example `captures/resource-<nonce>.json`). Replay that exact request using its filename without the `captures/` prefix:

```bash
python -m kerberos_lab.client replay --run-dir data/private/demo-001 --capture resource-<nonce>.json
```

In the default defended mode (`authenticator_cache`), the replay returns HTTP `409 replay_detected` and exits with code `1`. To observe the intentionally incomplete control mode, initialize a separate run directory and start the launcher with `--defense-mode authenticator_no_cache`.

For custom ports, TOML configuration, and logical clock offsets, see [docs/contracts/runtime-v1.md](docs/contracts/runtime-v1.md) and [docs/usage/client.md](docs/usage/client.md).

---

## Running Experiments and Tests

**Run the full test suite and contract fixture checks (310 tests):**
```bash
python -m pytest -q --tb=short
python docs/contracts/verify-fixtures.py
python -m pip check
```

**Run the E01–E10 replay experiments and analyzer:**
```bash
# 1-trial smoke run across E01-E10
python experiments/replay/runner.py --trials 1 --output-dir results/raw/smoke-run

# 30-trial comparison across E01-E03
python experiments/replay/runner.py --scenarios E01,E02,E03 --trials 30 --output-dir results/raw/perf-30

# Generate summary tables and latency SVG into an ignored folder
python experiments/analysis/analyze.py results/raw/smoke-run results/raw/perf-30 --output-dir results/figures/review-run
```

**Run the optional E11–E12 offline password-guessing demo:**
```bash
python experiments/kerberoasting/runner.py --output-dir results/raw/kerberoasting-demo
```

Raw outputs stay in ignored `results/raw/` and `results/figures/` directories. See [docs/usage/experiments.md](docs/usage/experiments.md) and [docs/usage/setup-review.md](docs/usage/setup-review.md) for details.

---

## Repository Layout

| Path | Contents |
| --- | --- |
| `src/kerberos_lab/` | Shared crypto, models, clocks, SQLite replay store, KDC (`kdc/`), resource server (`resource_server/`), and CLI client (`client/`). |
| `scripts/` | Private run initializer (`init_demo.py`), dual-server launcher (`run_lab.py`), and workflow scope checker. |
| `experiments/` | Replay/time/concurrency runner (`replay/`), analyzer (`analysis/`), and offline password-guessing demo (`kerberoasting/`). |
| `tests/` | Unit, integration, and adversarial security tests (310 passing tests). |
| `results/published/` | Reviewed, sanitized core (`a07-20261124/`) and extension (`extension/`) CSVs, SVG figure, and SHA-256 provenance manifests. |
| `docs/report/manuscript/` | Assembled neutral paper draft ([paper.md](docs/report/manuscript/paper.md)) and verified bibliography ([references.bib](docs/report/manuscript/references.bib)). |
| `docs/diagrams/` | Editable Mermaid diagrams for architecture, normal flow, and replay comparison. |
| `docs/presentation/` | Slide deck outline, live demo script, and recorded-output fallback. |
| `docs/contracts/` | Protocol v1, Python API v1, setup, and runtime control specifications. |

---

## Scope and Limitations

- **Educational simulator:** Uses a custom JSON/HTTP format over loopback, AES-256-GCM tickets, and PBKDF2-SHA256 service keys. It does not implement Kerberos V5 ASN.1 wire formats, RFC 3962 string-to-key, or Active Directory interoperability.
- **Evaluated implementation of established defenses:** Replay caching and session-key-authenticated nonces are established techniques ([RFC 4120 §3.2.3](https://www.rfc-editor.org/rfc/rfc4120.html#section-3.2.3)). This project evaluates a local implementation rather than claiming a new protocol or vulnerability.
- **Persistence and failure model:** Tests verify ordinary process restarts and shared-store concurrency on one host. Power-loss durability, hostile filesystem rollback, distributed multi-host caches, and exactly-once response recovery after a dropped response are out of scope.
- **Bounded password demo:** E11–E12 use a tiny 5-word list (`data/wordlists/demo.txt`) to illustrate why AES alone does not protect weak passwords; non-recovery means absence from that list within the budget, not uncrackability.
- **Platform note:** Core integration and experiments were verified on Linux (Python 3.14.8). Native Windows ACL and console lifecycle checks remain unverified.
