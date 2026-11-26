# Demo script — normal access, exact replay, and recorded evaluation

**Draft run time:** about 3 minutes for the live portion, followed by the reviewed-output fallback if required. Use the installed project environment from the repository root. This is an educational local simulator, not Kerberos wire protocol.

## Before presenting

1. Start from an activated environment with the locked project dependencies installed; the current checkout's global Python may not have the project package installed.
2. Choose two new, unused private run paths. The initializer refuses existing directories. Keep both under ignored `data/private/`; never reset or delete state during a run.
3. Initialize each path and choose the same disposable synthetic password at the hidden prompt. Do not put passwords in command arguments, slides, captures, or notes.

```powershell
python scripts/init_demo.py --run-dir data/private/c02-no-cache
python scripts/init_demo.py --run-dir data/private/c02-cache
```

If either path already exists, choose a new suffix rather than reusing or deleting it. Keep the two lab runs separate so the comparison starts from fresh state.

## Part A — intentionally incomplete no-cache control

**Terminal 1 — start both local server processes in the no-cache resource mode:**

```powershell
python scripts/run_lab.py --run-dir data/private/c02-no-cache --defense-mode authenticator_no_cache
```

Leave the launcher running. The KDC still consumes TGS requests; the mode switch applies only to resource replay tracking.

**Terminal 2 — check health, make one request, and replay its exact saved request:**

```powershell
python -m kerberos_lab.client health
python -m kerberos_lab.client run --run-dir data/private/c02-no-cache --count 1 --capture
python -m kerberos_lab.client replay --run-dir data/private/c02-no-cache --capture resource-<nonce>.json
```

At the hidden password prompt, enter the synthetic password chosen for this run. Copy the capture **filename** printed by `run` into the replay command (omit the `captures/` prefix). On a fresh run, the first increment returns counter `1`; the identical replay is expected to succeed again and return counter `2`.

**Speaking cue:** The repeated request preserves the ticket, authenticator, request nonce, and body. This mode intentionally omits resource request-identity consumption.

Stop the launcher with **Ctrl+C** in Terminal 1 before starting Part B.

## Part B — replay-cache defense

**Terminal 1 — start the separate defended run (default mode is `authenticator_cache`):**

```powershell
python scripts/run_lab.py --run-dir data/private/c02-cache
```

**Terminal 2 — make and replay an exact request:**

```powershell
python -m kerberos_lab.client health
python -m kerberos_lab.client run --run-dir data/private/c02-cache --count 1 --capture
python -m kerberos_lab.client replay --run-dir data/private/c02-cache --capture resource-<nonce>.json
```

The first increment should return counter `1`. The duplicate replay is expected to return HTTP `409` / `replay_detected`; the CLI reports the error and exits with status `1`. That nonzero exit is the expected defended outcome, not a successful request. Stop the launcher with **Ctrl+C**.

**Speaking cue:** The replay cache atomically records the authenticated request identity with the protected increment. This manual demonstration uses separate fresh runs; it is illustrative, not the paired E01/E02 experiment.

## Concurrency, restart, and time evaluation

For a reproducible one-trial smoke run of the actual implemented E05/E06/E07/E08/E10 scenarios, use a fresh terminal after the live demonstration:

```powershell
python experiments/replay/runner.py --scenarios E05,E06,E07,E08,E10 --trials 1
```

The runner creates new raw output under ignored `results/raw/`; do not copy this new output into the presentation as approved evidence. For the stage presentation, prefer the existing reviewed fallback described below. E05 exercises 2/4/8-worker duplicate races; E06 restarts the defended resource process while retaining its SQLite state; E07/E08/E10 use logical offsets and validity boundaries without changing the host clock. The service does not publish internal time-failure reasons.

## Failure fallback — recorded material, not live

If either process fails, do not imply that a recording is live. Switch to these approved sanitized files and label the slide visibly:

> **RECORDED OUTPUT — A07/G3 approved evidence from 2026-11-24; not live.**

- Duplicate and legitimate-request outcomes: [`primary_metrics.csv`](../../results/published/a07-20261124/primary_metrics.csv).
- Concurrent operation counts and post-restart replay: [`scenario_summary.csv`](../../results/published/a07-20261124/scenario_summary.csv).
- Offset and ticket-boundary categories: [`time_categories.csv`](../../results/published/a07-20261124/time_categories.csv).
- Optional descriptive timing visual only: [`request_latency.svg`](../../results/published/a07-20261124/request_latency.svg); do not claim a causal speedup.

These are reviewed summaries, not terminal captures. No approved terminal transcript or screenshot bundle is tracked. Use the C01 diagram for an explanatory view of the flow, clearly identified as a draft diagram rather than a captured run.

## Presenter limits and questions

- The interactive comparison is not a controlled paired measurement. For exact duplicate rates, cite the approved E02 result: 30/30 accepted in no-cache versus 0/30 in cache mode.
- E05–E10 approved evidence is a one-trial smoke run; E01–E03 are the repeated 30-trial scenarios. Avoid generalizing from the smoke run.
- Do not present latency as a performance win. The approved manifest describes local timing limitations.
- Do not show the optional password-guessing extension or claim any password result until A09 approves it.
- If asked about compatibility, production guarantees, power loss, distributed state, or response recovery: these are outside the evidence and are listed in the G3 manifest.

## Remaining presentation inputs

The human should supply the conference template, allotted presentation time, preferred deck format, and any required attribution before these Markdown drafts are converted into final slides.
