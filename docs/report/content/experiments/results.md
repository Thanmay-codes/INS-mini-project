# Results

*Draft for lead review. All measurements below come from A07-reviewed, sanitized evidence in `results/published/a07-20261124/`; no local candidate or unreviewed raw value is used.*

## Functional smoke observations

The one-trial E01-E10 smoke run produced **46 attempts**, all with expected outcomes and zero failed or transport attempts. In E04, each of the four mutation phases had one expected and one observed attempt, with none missing. Three modified artifacts were rejected with HTTP 401; the unsupported operation was rejected with HTTP 400.

The defended E05 concurrency conditions each returned exactly one successful response and a maximum operation counter of one at 2, 4, and 8 workers. E06 rejected the replay after an ordinary resource-process restart. E09 returned HTTP 503 for both missing and corrupt replay stores. In E10, after the initial accepted operation, the exact replay was rejected after both +15-second and -15-second logical-time restarts. E07 accepted the -15, 0, and +15-second offsets and rejected -60 and +60 seconds. E08 accepted the inclusive ticket-leeway edges at -30 and +330 seconds and rejected the adjacent outside points at -31 and +331 seconds. Time categories are runner-derived; they are not internal server diagnostics.

## Repeated E01-E03 outcomes

The repeated run contains 30 trials for each scenario and defense mode (300 HTTP attempts total). All requested trials were observed, with no failed trials or transport failures.

| Measure | Cache mode | No-cache control |
| --- | ---: | ---: |
| E01 initial requests accepted | 30/30 | 30/30 |
| E02 exact duplicate requests accepted | 0/30 | 30/30 |
| E03 fresh authenticated requests accepted | 60/60 | 60/60 |
| E01+E03 legitimate requests rejected | 0/90 | 0/90 |

The accepted original E02 request is not included in the duplicate denominator. E03 contributes two legitimate requests per trial, explaining its 60-request count in each mode.

## Request latency

The table reports milliseconds from the approved `performance_summary.csv`. Request p50/p95 are nearest-rank percentiles over request attempts. Trial-median p50/p95 are nearest-rank percentiles over the 30 per-trial median latencies.

| Scenario | Mode | Requests | Request p50 | Request p95 | Trial-median p50 | Trial-median p95 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| E01 | Cache | 30 | 11.8839 | 13.9820 | 11.8839 | 13.9820 |
| E01 | No-cache | 30 | 12.4544 | 14.5174 | 12.4544 | 14.5174 |
| E02 | Cache | 60 | 3.9937 | 14.9442 | 7.8096 | 9.2784 |
| E02 | No-cache | 60 | 9.1162 | 14.2462 | 9.9586 | 11.3091 |
| E03 | Cache | 60 | 9.0404 | 13.8268 | 10.0068 | 11.0278 |
| E03 | No-cache | 60 | 9.9426 | 14.4951 | 9.9624 | 11.4938 |

These are descriptive measurements of this local simulator. Mode order was fixed, each mode used a new resource process, and E02 cache-mode latency combines accepted originals with expected 409 duplicate rejections. The data do not support a general cache-speed, throughput, or production-performance claim.

The approved [primary metrics](../../../../results/published/a07-20261124/primary_metrics.csv), [scenario summary](../../../../results/published/a07-20261124/scenario_summary.csv), [time categories](../../../../results/published/a07-20261124/time_categories.csv), [performance summary](../../../../results/published/a07-20261124/performance_summary.csv), and [request-latency figure](../../../../results/published/a07-20261124/request_latency.svg) are accompanied by their provenance in the [manifest](../../../../results/published/a07-20261124/manifest.json). The outputs report the approved local observations; they do not establish production Kerberos/Active Directory compatibility, power-loss durability, hostile rollback resistance, distributed replay coordination, or exactly-once response recovery. E04-E10 have one reviewed trial; only E01-E03 have 30 repeated trials.

No service-password guessing results are included. That optional extension is future work unless A09 separately reviews and publishes approved evidence.
