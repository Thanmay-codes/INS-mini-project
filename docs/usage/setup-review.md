# Setup and Reproduction Review (D02)

Reviewed on 27 November 2026 against `main` commit `a6a0e227ae5b1ec351c1680d4a96ce9a1b774255`.

## Environment Checked

- **OS:** Linux
- **Python:** 3.14.8 (`.venv/bin/python`)
- **Scope limit:** Verified in the existing project `.venv` on Linux; fresh network `pip install` on a clean machine and native Windows lifecycle/ACL checks were not executed here.

## Commands Reproduced and Observed Outcomes

| Command | Outcome | Notes |
| --- | --- | --- |
| `.venv/bin/python docs/contracts/verify-fixtures.py` | **Passed** (exit 0) | Checked AES-GCM, both request MACs, both KDFs, 15 cases, duplicate JSON, and TOML syntax. |
| `.venv/bin/python scripts/init_demo.py --run-dir /tmp/.../demo-001 --password-stdin` | **Passed** (exit 0) | Initialized private run `8cb0ee9b9fae5a059385ec5786ed3fea` without echoing password. |
| `.venv/bin/python experiments/kerberoasting/runner.py --output-dir /tmp/.../b05-smoke --iterations 1000` | **Passed** (exit 0) | Produced `results.jsonl`, `summary.csv`, `environment.json`. |
| `.venv/bin/python experiments/replay/runner.py --scenarios E01,E02 --trials 1 --output-dir /tmp/.../b03-smoke` | **Exit 2** | `replay/runner.py` requires `--output-dir` inside the repository (e.g. `results/raw/...`), unlike `kerberoasting/runner.py`. |
| `.venv/bin/python experiments/replay/runner.py --scenarios E01,E02 --trials 1 --output-dir results/raw/d02-smoke-check` | **Passed** (exit 0) | Completed `6` attempts with `0` failed attempts. |
| `.venv/bin/python experiments/analysis/analyze.py results/raw/d02-smoke-check --output-dir results/figures/d02-smoke-check` | **Passed** (exit 0) | Reconciled 1 source run and generated summary CSVs. |

## Actionable Owner Requests

1. **B (`docs/usage/experiments.md`):**
   - Document that `experiments/replay/runner.py --output-dir` must point inside the repository (such as `results/raw/...`).
   - Add the `python experiments/kerberoasting/runner.py` command and options to `docs/usage/experiments.md`.
2. **A (`README.md`):**
   - Root `README.md` lines 13–20 still describe G2 as pending, whereas G2, G3, B05/A09, B06/A08, and C01–C03 are now merged on `main`.
