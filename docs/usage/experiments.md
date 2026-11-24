# Running the replay and time experiments

The replay runner uses the released KDC, client, resource server, logical clocks,
and SQLite replay store. Start from the repository root in the project
environment. A smoke pass over E01–E10 uses one trial per scenario:

```powershell
python experiments/replay/runner.py
```

For the plan's repeated request-performance observations, repeat selected
conditions across 30 independent trials:

```powershell
python experiments/replay/runner.py --scenarios E01,E02,E03,E05 --trials 30
```

The selection and count are explicit. Each trial creates its own run directory,
ticket, and replay database. E01/E02 compare cache modes by cloning a fresh run
before either mode is exercised; both sides receive the same ticket and exact
request bytes. E03 reuses the service ticket but creates a fresh authenticator
and nonce per legitimate operation. E05 uses separate resource processes on
distinct loopback ports sharing one key and database. E06/E10 restart only the
resource process and retain its database. These are local process restarts,
not simulated machine crashes or power-loss tests.

E07 uses released resource process options to test offsets −60, −15, 0, +15,
and +60 seconds. E08 evaluates both ticket validity leeway boundaries and an
authenticator timestamp generated at each corresponding logical instant. The
host operating-system clock is not changed. The JSONL's predicted reason is
computed from the released validation order; the public API only returns the
stable `invalid_authentication` error. This is a runner-side explanation, not
an internal server diagnostic.

Every successful invocation writes to a new ignored `results/raw/b03-<UTC-id>/`
directory:

- `requests.jsonl`: one record per HTTP attempt, including failed transport or
  server responses; includes exact scenario/trial/phase, status, public code,
  acceptance, operation counter, mode, offset, workers, startup time, and
  monotonic request latency. It contains no request bytes or bearer artifacts.
- `summary.csv`: requested denominator, observed trials/attempts, accepted and
  rejected counts, failed trials, protected-operation count, and p50/p95
  request/startup timings.
- `environment.json`: Git HEAD, Python/platform details, scenario/config
  values, timing definitions, and the interpretation limit for time reasons.

Runtime keys and replay stores exist only in temporary per-trial directories
under ignored `data/private/` and are deleted after the scenario. Do not copy
those files into evidence or commit raw results. Outputs are candidate evidence;
the project lead reviews and publishes sanitized measurements later.

Run the end-to-end integration coverage with:

```powershell
python -m pytest tests/integration/test_b_replay_runner.py -q --tb=short
```

The real-process test exercises all ten scenarios against local KDC and resource
processes. It uses the same released private-run initializer and SQLite stores
as the applications; no test-only runtime-material implementation is used.

See `experiments/replay/README.md` for the E01–E10 map and `docs/handoffs/B/B03.md`
for the exact validation commands and observed run status.
