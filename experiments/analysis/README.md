# Candidate analysis

`analyze.py` validates B03 JSONL/CSV run bundles, calculates denominator-aware
replay, legitimate-request, operation, restart, time-check, and latency
summaries, then writes candidate tables and an SVG using the Python standard
library. It does not edit or publish reviewed evidence.

Example, from the repository root:

```powershell
python experiments/analysis/analyze.py `
  results/raw/b03-smoke-<run-id> `
  results/raw/b04-performance-<run-id> `
  --output-dir results/figures/b04-analysis-<run-id>
```

Inputs must each include `requests.jsonl`, `summary.csv`, and
`environment.json`. The analyzer rejects mismatched request counts, decisions,
trial counts, or failure counts between JSONL and the runner's CSV/metadata.
The output directory must be new and beneath ignored `results/figures/`.

Request-latency p50/p95 use nearest rank, `sorted_values[ceil(p*n)-1]`, without
interpolation. Run-to-run variation is summarized by each trial's median
latency, then nearest-rank p50/p95 across trial medians. Missing attempts and
failed trials stay visible in output denominators. For
source commands that regenerate data, see `docs/usage/experiments.md`; run
directories are ignored and must be regenerated locally when needed. The SVG
and tables are analysis candidates for review, not approved publication.
