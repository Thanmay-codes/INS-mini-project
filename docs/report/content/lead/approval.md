# A08 Scientific Approval and Source Manifest

Review date: 24 November 2026. Base commit: `5df55aafac934ced172981c08280bd3498da3d01`.

## B06 Review Outcome

Reviewed [methods.md](../experiments/methods.md), [results.md](../experiments/results.md), and [B06 handoff](../../../handoffs/B/B06.md) against the codebase (`src/kerberos_lab/`, `experiments/replay/runner.py`, `experiments/analysis/analyze.py`) and [a07-20261124/manifest.json](../../../../results/published/a07-20261124/manifest.json).

- **Approved as written:** All protocol details, trial-major ordering, denominator rules (`46` smoke, `300` repeated, E04 `1/1/0`), latency calculations (nearest-rank p50/p95 and 30-trial medians), and table values match the published G3 artifacts exactly.
- **Note on extension wording in B06:** B06 was drafted at `3845f42` before A09 merged (`5df55aa`), so its closing lines state that the password-guessing extension has no published A09 evidence. **D03** should keep B06's core `methods.md` and `results.md` intact and incorporate the approved extension from [extension-findings.md](extension-findings.md) and [`results/published/extension/`](../../../../results/published/extension/).

## Approved Sources for C03 and D03

| Component | Approved source file(s) | Provenance |
| --- | --- | --- |
| Title, Abstract, Objectives, Background | [abstract-and-intro.md](abstract-and-intro.md) | A08 (`work/a08-paper-content`) |
| Threat Model & Security Design | [threat-model-and-design.md](threat-model-and-design.md) | A08 (`work/a08-paper-content`) |
| Methods & Core Results | [methods.md](../experiments/methods.md), [results.md](../experiments/results.md) | B06 (`4de2855` on `main`) |
| Core Evidence Tables & Figure | [`results/published/a07-20261124/`](../../../../results/published/a07-20261124/manifest.json) | A07 / G3 (`3845f42`) |
| Optional Extension Findings & Data | [extension-findings.md](extension-findings.md), [`results/published/extension/`](../../../../results/published/extension/manifest.json) | A09 (`5df55aa` on `main`) |
| Discussion, Limitations, Conclusions | [discussion-and-conclusions.md](discussion-and-conclusions.md) | A08 (`work/a08-paper-content`) |
| Reference Audits | [validity-research.md](../../../references/validity-research.md), [conference-extension-research.md](../../../references/conference-extension-research.md) | Checked 21 Nov 2026 |
