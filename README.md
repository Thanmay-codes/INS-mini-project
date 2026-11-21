# INS mini project: Kerberos-style authentication lab

**Recommended academic title:** Experimental Security Analysis of Kerberos-Style Ticket Authentication.

The longer initial title and original plan are preserved in `docs/planning/original-plan.txt`.

**Current direction:** Keep the submitted topic. The authoritative build specification is [the implementation plan](docs/implementation-plan.md), with [four-person ownership](docs/team-work.md). The user owns security/replay defense and integration; one active contributor owns KDC/client/experiments; two support contributors own diagrams, presentation and document packaging. The shorter title above is optional; a title change is unnecessary.

This is a Python college-project workspace for a simplified protocol simulation. It will compare identical session-key-authenticated requests with replay tracking disabled and enabled, then demonstrate bounded offline guessing against synthetic service tickets. Persistent atomic replay tracking, concurrent duplicates and process restart form the core evaluation.

## Current status

The folder structure, Python package, dependencies, two Flask server starters, and health-check client are ready. Authentication, tickets, attacks, mitigations, and benchmarks are **not implemented yet**. Both servers currently expose only `GET /health`.

## Start your assigned work

Use [the copy-paste prompt index](docs/prompts/README.md) and [the staged workflow](docs/workflow/README.md). There are 22 bounded task prompts, separate file ownership and per-task handoffs. Start A01, B00, C01 and D01 after cloning the preparation commit. B01 KDC implementation waits for the lead's tested shared-core release G1. [Gate status](docs/workflow/status.md) currently marks every implementation gate unreleased.

Everyone creates their own virtual environment; the local `.venv` is not pushed. Only A updates central context/status after integration. Agents leave authenticated Git commands to their human operator.

## Run locally

Python 3.11 or newer is required. The `.venv` in this workspace has been prepared; for a fresh checkout, run:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m pip install -e '.[dev]'
```

`requirements.lock.txt` records the dependency versions verified in this workspace on Python 3.14. The broader supported dependency ranges are in `pyproject.toml`; revalidate the snapshot when using a different Python version.

Start both servers from the project root:

```bash
.venv/bin/python scripts/run_lab.py
```

In another terminal, check them:

```bash
.venv/bin/python -m kerberos_lab.client
```

Expected: two JSON responses with `status: ok` and `stage: scaffold`. Use Ctrl+C in the launcher terminal to stop both servers. Alternatively, run each independently:

```bash
.venv/bin/python -m kerberos_lab.kdc.app
.venv/bin/python -m kerberos_lab.resource_server.app
```

The KDC runs at `http://127.0.0.1:5000`; the resource server runs at `http://127.0.0.1:5001`. The servers bind to loopback, with the Flask debugger and reloader disabled.

## Workspace map

```text
src/kerberos_lab/
  kdc/                 Authentication Server + Ticket-Granting Server roles
  resource_server/     Service-ticket validation and protected resource
  common/              Shared web helpers; future crypto, clock, ticket types
  client/              Health client; future legitimate authentication client
experiments/
  replay/              Replay and simulated clock-skew scenarios
  kerberoasting/       Offline guessing of lab-generated service tickets
configs/               Planned experiment configuration examples
tests/                 Unit, integration, and security test locations
data/
  fixtures/            Synthetic, reproducible sample inputs
  wordlists/           Small demonstration password list
  private/             Ignored generated keys and captured lab tickets
results/
  raw/                 Ignored machine-readable experiment output
  figures/             Ignored generated plots
  summaries/           Reviewed tables and findings
  published/           Tracked, sanitized reproducibility evidence
docs/
  planning/            Original submitted plan
  diagrams/            Editable architecture and flow diagrams
  report/              Outline, future manuscript source and approved assets
  references/          Source list and citation notes
  presentation/        Viva and demonstration outline
scripts/               Local development launcher
logs/                  Ignored runtime logs
.github/               Task and pull-request templates
PROJECT_CONTEXT.md     Persistent context/status for future chats
AGENTS.md              Entry point for agents working in this repository
```

For work in this repository, start with [project context](PROJECT_CONTEXT.md), [the detailed build plan](docs/implementation-plan.md), and [task ownership](docs/team-work.md). The next milestone establishes shared schemas, crypto/time helpers and local fixtures before integrating AS → TGS → resource access. The [reference audit](docs/references/validity-research.md) supports the paper's claims.

See [GitHub handoff instructions](docs/github-setup.md) for the first publication to [Thanmay-codes/INS-mini-project](https://github.com/Thanmay-codes/INS-mini-project). The user handles authentication and credential-requiring commands. No completed protocol tests, experiments, or results are claimed by the scaffold.

The replay demonstration will deliberately omit checks in its baseline. Results from this educational simulation must be described as simulation results, with the differences from Kerberos and Active Directory stated explicitly.
