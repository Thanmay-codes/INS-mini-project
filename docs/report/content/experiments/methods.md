# Methods

*Draft for lead review; this section describes the implementation and the approved A07 experiment bundle.*

## System and protocol model

The experiment uses a custom, single-host Kerberos-style simulator implemented in Python. A KDC process provides Authentication Server (AS) and Ticket-Granting Server (TGS) endpoints; a command-line client obtains a ticket-granting ticket (TGT), requests a service ticket for the synthetic `files` service, and sends authenticated requests to a separate resource-server process. The services communicate over loopback HTTP. This is an educational simulator, not an implementation of the Kerberos wire protocol or an Active Directory deployment.

The local initializer creates independent 32-byte TGS and service keys, a salted Scrypt verifier for the synthetic user, and separate SQLite stores for the TGS and resource roles. The login endpoint verifies the password and issues a TGT protected with AES-GCM. The TGS validates the TGT and a request authenticator, consumes the authenticator in its own replay namespace, and issues an AES-GCM-protected service ticket. In this simulator, the client receives its session material in the JSON exchange. The resource server checks the service ticket, audience, request context, body digest, HMAC-SHA-256 authenticator, ticket validity, and authenticator freshness before executing the counter operation. Authenticated messages use canonical JSON and separate TGS/resource domain labels.

Two resource-server modes are compared. `authenticator_no_cache` validates requests but omits resource-request replay tracking; `authenticator_cache` consumes the authenticated request identity and increments the SQLite-backed operation counter in one transaction. The TGS checks and its replay store are unchanged between modes. The comparison therefore concerns this simulator's resource replay-tracking choice; the no-cache mode is an intentionally incomplete control, not a description of standard Kerberos behavior.

## Experimental design

The runner executes E01-E10 in trial-major order: for each trial, it runs the selected scenarios in the declared scenario order. Every independent trial initializes fresh private state. For paired mode conditions, the runner clones equivalent initial state so both modes use the same service ticket, request bytes, keys, logical time, and workload. Mode order is fixed (no-cache followed by cache), not randomized or counterbalanced. E03 uses a newly authenticated nonce for the second legitimate request. E05 starts separate resource processes on distinct loopback ports that share one service key and SQLite store. E06 and E10 retain the store across ordinary resource-process restarts.

The scenarios cover: valid initial access (E01); exact captured-request replay in both modes (E02); fresh authenticated requests on one ticket (E03); four ticket/authenticator/body/service mutations (E04); two, four, and eight concurrent exact copies (E05); replay after restart (E06); resource-clock offsets of -60, -15, 0, +15, and +60 seconds (E07); inclusive ticket-leeway edges and adjacent outside points (E08); missing and corrupt replay stores (E09); and replay after forward/backward logical-time changes of 15 seconds (E10). E04-E10 are functional smoke conditions with one trial each in the approved bundle. E01-E03 have a separate repeated run with 30 independent trials per scenario and mode.

The runner uses a frozen logical base time and role-specific logical offsets. The allowed skew and ticket boundary leeway are 30 seconds. The host clock is not changed. Time-rejection categories in the exported data are runner-derived from the declared validation order; the service exposes only its public authentication error. The runner does not use a seeded PRNG; runtime keys and request nonces use cryptographic randomness. The published manifest records a digest for each source environment file rather than embedding the complete host inventory. The A07 release handoff reports Linux regeneration and Linux/Python 3.14.8 regression validation; this draft makes no claim about unrecorded CPU or hardware details.

## Measurements and calculations

The runner writes one JSONL record per HTTP attempt, a scenario summary CSV, and environment/configuration metadata. It excludes request bodies, tickets, authenticators, passwords, and keys. The smoke run contains 46 attempts. The repeated E01-E03 run contains 300 attempts: E01 has one attempt per trial and mode, while E02 and E03 have two.

Duplicate acceptance is calculated only from the second exact E02 request in each trial. Legitimate-request rejection pools E01 and E03 and counts HTTP 4xx/5xx responses as rejections; transport failures are reported separately. Requested, observed, missing, and failed denominators remain explicit. E04 is summarized per mutation phase, with one expected attempt per trial in each phase. Protected-operation counts and the E05 returned counter are reported separately from HTTP attempts.

Request latency is measured around each loopback HTTP request with a monotonic `perf_counter_ns` timer. Startup timing begins after `subprocess.Popen` returns and ends when the first healthy endpoint response is observed; it includes health polling and excludes the process-creation call. The published latency figure reports request latency, not startup time. Request p50/p95 use nearest rank, `sorted[ceil(p*n)-1]`, without interpolation. For run-to-run variation, the analyzer first calculates each trial's median request latency (averaging the middle two observations for an even-sized trial), then applies nearest rank to the 30 trial medians.

## Provenance and reproduction

The approved evidence is `a07-20261124`. Its [manifest](../../../../results/published/a07-20261124/manifest.json) records the producing source commit (`636ba23f066b082eccc1d590e17f62608b2bd626`), runner and analyzer hashes, source-run identifiers, attempt counts, raw-source hashes, generation commands, published-output hashes, configuration, and interpretation limits. The reviewed summaries and figure are in [`results/published/a07-20261124/`](../../../../results/published/a07-20261124/). G3 is released on merged main; see the [release record](../../../workflow/status.md).

From a fresh clone with the project environment installed, these commands generate new local measurements and candidate analysis:

```powershell
$id = (Get-Date).ToUniversalTime().ToString("yyyyMMddTHHmmssZ")
$smoke = "results/raw/b06-smoke-$id"
$performance = "results/raw/b06-performance-$id"
$candidate = "results/figures/b06-analysis-$id"
python experiments/replay/runner.py --trials 1 --output-dir $smoke
python experiments/replay/runner.py --scenarios E01,E02,E03 --trials 30 --output-dir $performance
python experiments/analysis/analyze.py $smoke $performance --output-dir $candidate
```

These commands reproduce the procedure, not the exact approved raw latency samples. Raw inputs are local and ignored; the manifest preserves their hashes and run metadata, while the approved sanitized outputs are tracked. A new run will naturally have different random material and timing observations.

The synthetic password-guessing extension is outside this methods section: no A09-approved extension evidence is published. It remains future work for this core-results draft.
