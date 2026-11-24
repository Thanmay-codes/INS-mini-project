# Core evidence review — A07

Review date: 24 November 2026. Producing and review base:
`636ba23f066b082eccc1d590e17f62608b2bd626`.

**Status: reviewed evidence prepared for merge.** The selected sanitized outputs
and provenance are in
[`results/published/a07-20261124/`](../../../../results/published/a07-20261124/).
G3 remains unreleased until this A07 work is merged and rechecked on the resulting
`main` commit.

## Reproduced core observations

A fresh E01–E10 run produced 46 expected attempts with zero failed attempts or
transport failures. The review independently traversed every raw JSONL record,
then reconciled it with the corrected analyzer output. The E04 phase-denominator
correction was verified: each of the four mutation phases reports one expected,
one observed and zero missing attempt.

| Scenario | Reviewed local observation |
| --- | --- |
| E01 | Both modes accepted an initial valid request. |
| E02 | The intentionally incomplete no-cache control accepted the original and duplicate; the cache mode accepted the original and rejected the duplicate with 409. |
| E03 | Both modes accepted two fresh authenticated requests on the same valid ticket. |
| E04 | Three modified artifacts returned 401; an unsupported operation returned 400. |
| E05 | Each 2-, 4- and 8-worker condition had exactly one successful response and a maximum protected-operation counter of one. |
| E06 | The initial request succeeded; its replay after an ordinary resource-process restart returned 409. |
| E07 | Offsets −15, 0 and +15 seconds were accepted; −60 and +60 returned 401. |
| E08 | Inclusive ticket-leeway edges at −30 and +330 seconds were accepted; −31 and +331 returned 401. |
| E09 | Missing and corrupt replay stores each returned 503; the defense was not bypassed. |
| E10 | After one accepted request, the exact replay returned 409 after both +15 and −15 second logical-time restarts. |

Time categories in the export are computed by the runner from the declared
validation rules. The public resource-server observation is only its stable
`invalid_authentication` response; this evidence does not claim that an internal
server diagnostic was exposed.

## Repeated E01–E03 comparison

An independent 30-trial run for each selected scenario and mode produced 300
attempts, with all requested trials observed and no failed or transport attempts.
The raw records give the central comparison below.

| Metric | No-cache control | Persistent cache mode |
| --- | ---: | ---: |
| E02 duplicate grants / duplicate attempts | 30 / 30 | 0 / 30 |
| E01 + E03 legitimate rejections / requests | 0 / 90 | 0 / 90 |

The reviewed request-latency summaries (milliseconds, nearest-rank p50 / p95)
are descriptive local measurements:

| Scenario | Cache mode | No-cache control |
| --- | ---: | ---: |
| E01 | 11.8839 / 13.9820 | 12.4544 / 14.5174 |
| E02 | 3.9937 / 14.9442 | 9.1162 / 14.2462 |
| E03 | 9.0404 / 13.8268 | 9.9426 / 14.4951 |

E02 combines an accepted original request with an expected 409 replay response
in the cache mode. Fixed mode order and local process start effects also remain.
The latency values therefore do not support a general cache-speed, throughput or
production-performance claim. The complete denominator-aware tables and figure
are in the [published evidence directory](../../../../results/published/a07-20261124/).

## Comparison controls and evidence limits

For paired E01–E03 conditions, the runner clones equivalent initial state and
uses the same ticket, request bytes, validation settings, logical time and
service key. E03 changes only to a newly authenticated nonce for its legitimate
second operation. Independent trials receive fresh state, while E06/E10 retain
the replay store across the resource-process restart. E05 workers use separate
local processes that share the same service key and SQLite replay state.

This is a custom, single-host educational simulator. It demonstrates behavior
under the stated local process, SQLite and logical-clock model; it does not
establish a new Kerberos flaw, AD interoperability, NTP compromise, distributed
replay coordination, power-loss durability, hostile rollback resistance or
exactly-once response recovery. E04–E10 have one reviewed smoke trial; only
E01–E03 have 30 repeated trials. Optional synthetic password guessing is not
part of this evidence or the G3 core release.
