# Presentation skeleton — Kerberos-style replay study

**Draft:** neutral Markdown outline; conference template, final deck format, and allotted time were not supplied. Suggested delivery is 6–7 minutes. Convert only after the human chooses the publisher/deck format.

The sources are the C01 drafts in [`docs/diagrams/`](../diagrams/). They remain drafts pending A/B label review. This presentation describes a local educational simulator with a custom JSON message format, not Kerberos wire protocol or production deployment.

## Slide 1 — Motivation: authenticated requests can be replayed

**On slide**

- A captured request can be submitted again while its ticket and authenticator remain valid.
- Compare an intentionally incomplete resource-server control with authenticated request-identity consumption.
- Study correctness under duplicate, concurrent, restart, and controlled-time conditions.

**Speaking cue:** This is an evaluation of established replay-cache techniques in a bounded student simulator, not a new protocol or vulnerability claim.

## Slide 2 — Roles and system boundary

**On slide**

- CLI client.
- One KDC process containing the Authentication Service (AS) and Ticket-Granting Service (TGS).
- Separate resource-server process and local SQLite-backed replay state.
- TGT audience: `tgs`. Service-ticket audience: `files`.

**Visual:** [`architecture.mmd`](../diagrams/architecture.mmd).

**Speaking cue:** The resource server receives a service ticket for `files`, never a TGT. Session keys are delivered separately to the client as an explicit local-simulator simplification.

## Slide 3 — Normal authentication flow

**On slide**

1. Client logs in to AS and receives a TGT plus client/TGS session material.
2. Client presents the TGT and a TGS-session-key-authenticated request to TGS.
3. TGS issues a service ticket for `files` and corresponding client/service session material.
4. For each resource request, the client authenticates a fresh request nonce with the service session key.

**Visual:** [`normal-authentication.mmd`](../diagrams/normal-authentication.mmd).

**Speaking cue:** The request nonce is distinct from the ticket-encryption nonce. Fresh requests may reuse a valid service ticket; an exact replay preserves the same nonce and authenticator.

## Slide 4 — Replay control versus defense

**On slide**

- `authenticator_no_cache`: validates the same ticket, MAC, context, and time but omits resource request-identity consumption; intentionally incomplete.
- `authenticator_cache`: atomically consumes `(namespace, service_id, ticket_id, request_nonce)` with the protected increment.
- TGS request consumption remains enabled in both resource modes.

**Visual:** [`replay-cache-comparison.mmd`](../diagrams/replay-cache-comparison.mmd).

**Speaking cue:** The live CLI replay is a short illustration. The controlled E01/E02 comparison uses equivalent cloned state and identical request bytes; the manual demonstration alone is not that paired experiment.

## Slide 5 — Evaluation and reviewed core observations

**RECORDED OUTPUT — A07/G3-approved, sanitized evidence; not a live run.**

| Evaluation | Reviewed observation | Evidence |
| --- | --- | --- |
| E02 exact duplicate, 30 trials | No-cache accepted 30/30 duplicate requests; cache mode accepted 0/30. | [`primary_metrics.csv`](../../results/published/a07-20261124/primary_metrics.csv) |
| E01/E03 legitimate requests, 30 trials | Rejection was 0/90 in each mode. | [`primary_metrics.csv`](../../results/published/a07-20261124/primary_metrics.csv) |
| E05 concurrency smoke | At each of 2, 4, and 8 workers, one protected operation committed; other copies were rejected. | [`scenario_summary.csv`](../../results/published/a07-20261124/scenario_summary.csv) |
| E06 restart smoke | The request accepted before resource-process restart was rejected on replay after restart. | [`scenario_summary.csv`](../../results/published/a07-20261124/scenario_summary.csv) |
| E07/E08 time smoke | Offsets −15/0/+15 were accepted and −60/+60 rejected; inclusive ticket-leeway edges −30/+330 were accepted, just outside −31/+331 rejected. | [`time_categories.csv`](../../results/published/a07-20261124/time_categories.csv) |
| E10 logical-time smoke | A consumed request remained rejected after both +15-second and −15-second resource-process restarts. | [`scenario_summary.csv`](../../results/published/a07-20261124/scenario_summary.csv) |

**Speaking cue:** Only E01–E03 have 30 repeated trials. E04–E10 values above come from a one-trial smoke run. Time categories are inferred by the runner from declared validation rules; the service returns only a stable public error. The host clock was not changed.

**Pending placeholders:** `[Any new live-run measurements: not recorded; do not present as A07 evidence.]` `[Any additional statistic or performance claim: pending review.]` Do not infer a speedup from the local latency chart; the manifest records measurement limitations.

## Slide 6 — Scope and limitations

**On slide**

- Custom loopback JSON simulator; not Kerberos wire compatibility, Active Directory, or production effectiveness.
- Local SQLite persistence and ordinary process restart; not power-loss durability, distributed replay coordination, hostile rollback resistance, or exactly-once response recovery.
- Time offsets are logical controls; no host-clock/NTP modification.
- The no-cache mode is an intentionally incomplete comparison control, not a description of standard Kerberos deployments.
- Optional synthetic service-password guessing is excluded from claimed results until A09 approves evidence.

**Speaking cue:** State what the approved evidence measures and what it does not establish. No password-guessing result is included in this draft.

## Fallback for live-process failure

Switch to the approved published files in [`results/published/a07-20261124/`](../../results/published/a07-20261124/) and label every displayed table or figure **RECORDED OUTPUT — A07/G3 approved, 2026-11-24; not live**. Use `primary_metrics.csv`, `scenario_summary.csv`, and `time_categories.csv` for the table above; use `request_latency.svg` only as a descriptive local timing plot, not a speedup claim. The C01 Mermaid diagrams can explain the system if the live flow is unavailable, but are draft visuals, not captured runtime output. No approved terminal transcript or screenshot bundle is present in the repository.
