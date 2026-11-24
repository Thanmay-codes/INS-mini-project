# Core evidence review — A07 publication withheld

Review date: 24 November 2026. Producing/review base:
`05422d01232607f609983e770f82e86d3333e5b2`.

**Status: preliminary audit, not approved evidence. G3 is NOT RELEASED.**
The actual runner outcomes reproduced, but B-owned reporting/provenance defects
must be corrected and the affected outputs regenerated before publication.
Merging this review note does not complete A07 or release a gate.

## Independently regenerated observations

Ran the tracked runner locally with all E01–E10 and one trial per scenario into
ignored `results/raw/a07-smoke-20261124/`. It produced 46 attempts, zero transport
failures and zero unexpected outcomes. This is a smoke-size correctness run,
not repeated evidence for E04–E10 or performance proof.

| Scenario | Locally observed HTTP outcomes |
| --- | --- |
| E01 | Both modes granted initial access |
| E02 | No-cache granted original and duplicate; cache granted original and rejected duplicate (409) |
| E03 | Both modes granted two fresh authenticated requests on one ticket |
| E04 | Three tamper cases rejected with 401; unsupported operation rejected with 400 |
| E05 | Exactly one grant/counter=1 in each independent 2/4/8-worker condition; other copies returned 409 |
| E06 | Initial grant followed by 409 after resource restart with preserved state |
| E07 | −15/0/+15 s accepted; −60/+60 s rejected with 401 |
| E08 | Inclusive −30/+330 s ticket-leeway edges accepted; points just outside rejected |
| E09 | Missing and corrupt initialized stores each produced 503 |
| E10 | Initial grant followed by 409 after both +15 and −15 s restarts |

Time rejection subcategories are computed by the runner from the declared time
rules; the server observation is only the public `invalid_authentication` code.
No private server rejection diagnostic was exposed or measured.

## Repeated local observations — still unapproved

A separate regenerated E01/E02/E03 run used 30 independent trials per scenario
and produced 300 attempts with no unexpected outcomes or transport failures.
Each scenario/mode has all requested 30 trials. Independently reading the JSONL
and validating each trial's returned counter sequence gave:

| Metric | No-cache | Cache |
| --- | ---: | ---: |
| E02 duplicate grants / duplicate attempts | 30 / 30 | 0 / 30 |
| E01+E03 legitimate rejections / requests | 0 / 90 | 0 / 90 |

Nearest-rank request p50/p95 and p50/p95 across independently computed trial
medians match all six analyzer performance conditions. These local Linux values
are not B's Windows values and are not a causal speedup claim. Full regenerated
raw inputs and candidate tables remain ignored and unapproved.

## Publication blockers

### E04 phase denominators are wrong

`experiments/analysis/analyze.py:scenario_summary` groups records by scenario,
mode, phase, worker count and offset, but uses four expected attempts per E04
trial for **each individual mutation phase**. One trial actually has four phases
with one request each. The regenerated complete smoke data consequently yields:

| E04 phase | Expected attempts reported | Observed | Missing reported | Correct expected / missing |
| --- | ---: | ---: | ---: | ---: |
| mutated_authenticator | 4 | 1 | 3 | 1 / 0 |
| mutated_body | 4 | 1 | 3 | 1 / 0 |
| mutated_service | 4 | 1 | 3 | 1 / 0 |
| mutated_ticket | 4 | 1 | 3 | 1 / 0 |

The CSV therefore reports twelve missing attempts although all four required E04
requests ran. The aggregate scenario total is four, not the per-phase denominator.
This is an analysis bug, not a protocol rejection or missing measurement.

B must correct condition-level denominators and test complete one-/multi-trial
E04 data plus a genuinely absent attempt. Preserve E02/E03 denominators: their
two requests share a phase. Do not solve this by merely changing expected counts
without checking the grouping level.

### Provenance labels need correction

The runner executes the outer trial loop first and the scenario loop inside it,
but emits `trial_order="1..N within each scenario"`. Record the actual trial-major
order and scenario order. This matters when interpreting temporal/load effects.

The startup timer starts **after** `subprocess.Popen` returns, but metadata says
"from process spawn to healthy endpoint". Either start the timer before process
creation, or label the current post-Popen-to-health interval accurately. Do not
silently reinterpret old timing values. Request latency is separately measured
around loopback HTTP and is unaffected by this startup-label issue.

## Comparison fairness and interpretation

Code review confirms paired E01–E03 modes clone untouched equivalent state and
use the same issued ticket/request bytes, frozen logical time, service key and
validation path. E03 legitimately changes the authenticated request nonce.
Restart scenarios retain one run/store; independent trials use fresh state.
Concurrency scenarios share one key/store across distinct loopback processes.

Mode order is fixed (no-cache first, then cache), not randomized/counterbalanced.
Each mode starts a new resource process; initial requests include cold-process
and loopback overhead. E02 pools successful originals with rejected duplicates
in cached-mode latency summaries. A lower measured cached latency would not by
itself establish general caching speedup, throughput or production performance.
Do not compare local Linux latencies numerically with B's Windows handoff as
though the machines/environments were identical.

Operation counts in the current analyzer are derived from successful responses.
For these complete zero-transport-failure runs, validate returned counter values
as well as status counts. That derivation cannot establish absence of committed
operations after a transport failure or lost response; A06 explicitly covers the
response-uncertainty boundary.

## Resume and limits

B owns runner/analyzer corrections; A07 does not edit those files concurrently.
After corrected code is merged, regenerate affected evidence, independently
reconcile phase/trial/attempt denominators, review calculations and selected
figures, scan exports for secrets, and publish selected sanitized results with
hashes/environment/commands. G3 requires that evidence task's merge and recorded
merged-main verification. No evidence has been approved in `results/published/`.

This work evaluates established replay-cache techniques in a custom educational
Kerberos-style simulator. It establishes no new Kerberos vulnerability, AD
interoperability, production effectiveness, NTP attack, power-loss durability or
exactly-once response recovery. Optional password guessing remains outside G3.
