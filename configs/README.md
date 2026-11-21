# Experiment configuration

This folder contains `replay.example.toml`, a non-secret example of the planned scenario interface. The scaffold currently uses loopback and fixed ports 5000/5001; it does not load experiment configuration yet. The authoritative configuration/time rules are in `docs/implementation-plan.md`.

When the scenario runner is implemented, centralize ticket lifetime, allowed clock skew, per-role simulated clock offsets, defense mode, KDF parameters, guess budget, and repeat count here. Keep actual keys and passwords in ignored `data/private/` rather than tracked configuration.
