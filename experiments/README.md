# Experiments

The E01–E10 replay, clock, concurrency, restart and store-failure runners are implemented in `experiments/replay/`. Exact commands, output schema, trial semantics, and current platform constraints are documented in `experiments/replay/README.md` and `docs/usage/experiments.md`.

All generated raw evidence belongs under the ignored `results/raw/` tree. Private runtime keys and replay databases are temporary and excluded from tracked output. Raw runs are evidence candidates only; A reviews and publishes approved sanitized results. `experiments/analysis/` and `results/published/` are reserved for the later analysis and lead review tasks.
