# A07 reviewed core evidence

This directory contains A's reviewed, sanitized outputs from the corrected
E01–E10 replay/time/concurrency runner and the E01–E03 repeated local
measurement. It contains no runtime material, request bodies, tickets,
authenticators, keys, passwords or replay databases.

- `primary_metrics.csv` records the duplicate-acceptance, legitimate-rejection
  and restart-replay metrics.
- `scenario_summary.csv` records per-condition denominators, observed counts,
  statuses, operation counts and local timing summaries for the smoke and
  repeated runs.
- `time_categories.csv` records E07/E08 validation categories. These categories
  are runner-derived from declared rules; the service publishes only a stable
  invalid-authentication response.
- `performance_summary.csv` and `request_latency.svg` report local E01–E03
  request timings. They are descriptive local observations, not a production
  performance comparison or a caching speed claim.
- `manifest.json` is the authority for provenance, hashes, commands, approval
  status and limitations.

Regenerate raw inputs and candidate outputs with the commands in
`docs/usage/experiments.md`; use a new ignored output directory for every run.
