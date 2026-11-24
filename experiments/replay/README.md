# Replay and logical-time runners

`runner.py` drives the released KDC, client, and resource server APIs over loopback. It implements E01–E10 from the experiment plan. It does not add server routes, change the host clock, or contain a second ticket/authenticator implementation.

From the repository root and an installed project environment:

```powershell
python experiments/replay/runner.py
```

The default is a one-trial smoke pass over E01–E10. To select conditions and repeat performance-sensitive scenarios:

```powershell
python experiments/replay/runner.py --scenarios E01,E02,E03,E05 --trials 30
python experiments/replay/runner.py --scenarios E07,E08,E10 --trials 1
```

Each invocation creates a new directory under `results/raw/b03-<UTC-id>/` with `requests.jsonl`, `summary.csv`, and `environment.json`. Runner failures are represented by records with status `0`, an error code, and a failed trial; the command exits nonzero when an expected outcome fails. The denominator is the requested trial count, while `observed_trials` and `failed_trials` expose missing or failed trials. The metadata records scenario/trial ordering and states that no seeded PRNG is used; runtime keys and request nonces come from cryptographic randomness. The raw stream also records each attempt, HTTP code, public error, operation acceptance, counter, worker count, logical offset, startup time, and monotonic request time. It omits passwords, ticket blobs, authenticators, and request bodies. Process logs are transient and removed after the run.

Runtime keys and SQLite stores are initialized using the released `initialize_run` API in temporary per-trial subdirectories beneath `data/private/`. Each trial gets a new run and service grant. Paired defense mode comparisons clone that fresh run before requests are sent, preserving the same run ID, ticket keys, ticket, request bytes, logical time, and initial resource state. The ephemeral synthetic password is never printed or written to the evidence directory. Temporary runtime trees are removed at the end of each trial. E05 starts distinct resource processes bound to separate ports and sharing one resource key and SQLite store. E06/E10 preserve the same store through a stop/restart boundary.

| Scenario | Runner behavior |
| --- | --- |
| E01 | Valid request in each defense mode from equivalent fresh state |
| E02 | Two sends of the exact same captured bytes in each mode |
| E03 | Two fresh authenticator requests on the same service ticket |
| E04 | Mutated ticket, MAC, operation body, and service identity |
| E05 | 2, 4, and 8 simultaneous exact copies across separate workers |
| E06 | Exact replay after restarting the defended resource process |
| E07 | Exact request at resource offsets −60, −15, 0, +15, and +60 seconds |
| E08 | Just-before, at, and just-inside/outside each ticket validity boundary with a fresh authenticator at each logical instant |
| E09 | Missing and corrupted required replay database after healthy startup |
| E10 | Consumed request replayed after +15 then −15 second process restarts |

For time cases, `ticket_time_valid` and `authenticator_time_valid` are computed from the released checks and the captured timestamp. `expected_time_reason` identifies the first failed validation class; the HTTP contract deliberately returns only the stable public `invalid_authentication` code. The runner does not claim the server exposes its internal reason.

`latency_ms` measures one loopback HTTP request using `time.perf_counter_ns`; `startup_ms` measures from immediately after `subprocess.Popen` returns until the first healthy endpoint response; it includes health polling and excludes the process-creation call. Boundary checks use logical timestamps and are not used as elapsed-time measurements. A 30-trial command is an actual local measurement, not a claim that a smoke run has 30 observations. These outputs are unreviewed raw evidence; the lead reviews and publishes sanitized results after B04/A07.

The local B03 smoke command and actual outcomes are recorded in `docs/handoffs/B/B03.md`. The runner intentionally relies on the released private-run initializer; do not replace it with manual runtime-material creation.
