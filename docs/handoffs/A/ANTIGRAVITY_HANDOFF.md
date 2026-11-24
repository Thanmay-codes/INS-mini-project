# Antigravity handoff — INS mini project

Last checked: 24 November 2026 (Asia/Kolkata).

## Current GitHub state

Repository: `Thanmay-codes/INS-mini-project`.

Public GitHub `main` was fetched without credentials and is at
`3845f42d983e6f741b47bf212c227f26b12efc9d`, merge PR #11
(`work/g3-release`). The previous work through G3 is in GitHub. G1, G2, A06,
B03, B04, the A07 reporting correction, A07 evidence and G3 release record are
merged. G3 passed the main-commit verification documented in
`docs/workflow/status.md`.

This handoff and its accompanying corrections to stale project-state wording
are being prepared on `work/antigravity-handoff`; they are local until the
human reviews, commits and pushes them. No credentialed Git operation has been
performed. Current working tree should be checked before continuing.

## User and project intent

This is a college Information and Network Security mini-project and small
conference paper. The submitted topic is Kerberos-style ticket authentication,
replay mitigation and a possible Kerberoasting-inspired extension. Keep the
submitted topic; frame the contribution as an evaluated educational
implementation of established techniques. Do not claim a new Kerberos flaw,
novel nonce/replay-cache defense, verified literature gap, Active Directory
interoperability, production effectiveness or conference acceptance.

The user is the lead and owns security-sensitive decisions and scientific
approval. There are four members, but realistically two are active: the user
(A) and one contributor (B). C and D have support tasks. The user handles
credential-requiring Git commands; leave commit/push/authentication to them and
never request or store credentials.

The initial proposal's wording was narrowed after checking the cited work:
ordinary timestamp skew is not itself a new Kerberos vulnerability, and a
single-use nonce does not remove the need for ticket expiry/time validation.
The core therefore evaluates an explicitly incomplete no-cache control against
a persistent atomic replay cache under controlled local clock offsets,
concurrency and process restart. The password-guessing idea is only an optional
synthetic, bounded extension; it is not a real Active Directory Kerberoasting
assessment. Use the checked sources and claim limits in the two research audit
files linked above.

## What was built and released

- A01–A03 established the protocol contracts, shared crypto/types, clock model,
  persistent stores and private demo initialization.
- A04/A05 plus B01/B02 implemented the local Flask KDC (AS and TGS), client,
  resource service and integrated normal flow. G1 and G2 are released.
- A06 reviewed replay safety and adversarial cases; B03 added reproducible
  E01–E10 replay/time/concurrency runners; B04 added traceable analysis.
- A07 identified a condition-level E04 denominator bug and inaccurate B03
  metadata. B fixed it in `636ba23`; regression tests were added and passed.
- A07 regenerated evidence from corrected code, independently checked raw
  records and published only sanitized outputs. G3 was released after merge and
  verification at current main `3845f42`.

The A07 evidence package is `results/published/a07-20261124/`. Its
`manifest.json` records producing code commit `636ba23f066b082eccc1d590e17f62608b2bd626`,
commands, source and export hashes, parameters and limitations. Raw run data
remain ignored under `results/raw/` and are local to the prior environment;
they do not transfer via Git. The sanitized, tracked summaries are the source of
truth for paper numbers.

Reviewed outcomes: E01–E10 smoke run had 46 attempts and no failed/transport
attempts. E04's four mutation phases each have expected=1, observed=1,
missing=0. E05 had one committed operation in each 2/4/8-worker condition;
E06/E10 reject replays after ordinary process restart; E09 fails closed for
missing/corrupt state. In the 30-trial E01–E03 run (300 attempts), no-cache
accepted 30/30 exact duplicates and the persistent cache accepted 0/30; each
mode rejected 0/90 legitimate E01/E03 requests. See the manifest and
`docs/report/content/lead/core-findings.md` for timings and caveats.

The measured system is a single-host educational simulator using Flask,
library cryptography, logical clock offsets, SQLite replay storage and local
worker processes. It is not real Kerberos/AD. Time-rejection categories are
runner-derived, process restart is not power-loss testing, and measured
latencies are descriptive local results, not a general performance or caching
speed claim. No NTP compromise, distributed replay coordination, hostile
rollback resistance or exactly-once response recovery was demonstrated.

## Current status and next tasks

G3 is released. The primary next task is B06: draft implementation-faithful
methods and results using only the approved published evidence. The complete
prompt is `docs/prompts/B/B06.md`; prerequisites and file ownership are in
`docs/workflow/README.md` and `docs/workflow/tasks.json`. Start B06 on a fresh
branch from the latest main, record its base SHA, and keep changes to B-owned
paths plus `docs/handoffs/B/B06.md`. Use a capable but economical model and
have A review methods, denominators and claims.

After B06 is merged, A08 writes/approves the abstract, contribution, threat
model, security design, discussion, limitations and conclusion. Its prompt is
`docs/prompts/A/A08.md`. Use stronger reasoning for A08's scientific decisions.
The optional B05 password-guessing extension and A09 review can be skipped if
time is short; do not imply it was completed. C/D diagrams, setup review,
presentation and manuscript formatting remain support work and should use
approved content only. No conference template or format requirements have yet
been provided.

## Known follow-ups

- A06 documented a B-owned KDC username-schema discrepancy: malformed IDs such
  as empty, uppercase or overlong usernames currently receive 401 rather than
  contract-level 400. It was not an observed authentication bypass and does not
  invalidate G3 evidence, but should be resolved before final protocol
  conformance signoff if B can take it as a separate scoped task.
- Native Windows process lifecycle/ACL behavior has not been verified.
- The professor's paper format, deadline, author list and conference rubric are
  unknown. Ask for these when preparing final submission packaging.
- `PROJECT_CONTEXT.md`, `docs/workflow/status.md` and the A07 manifest said the
  G3 record was still pending even though PR #11 was merged. This handoff branch
  corrects those stale statements and captures the verified current main SHA.

## Required operating rules

Before any task, read root `AGENTS.md`, `PROJECT_CONTEXT.md`,
`docs/workflow/README.md`, that task's prompt and `docs/workflow/tasks.json`.
For research-claim or paper work, consult
`docs/references/validity-research.md` and
`docs/references/conference-extension-research.md`. The execution workflow
defines task order, ownership and handoffs; do not edit another role's files.
Only A updates central project context and release status after merge and
verification. Every task writes its role-owned handoff with base SHA, changed
files, exact checks, results, limits and next step. Keep raw data/secrets out of
Git. Use TDD for nontrivial code changes when applicable. Never claim a gate is
released based only on a branch or prose; verify merged main.

At the start of a fresh Antigravity session, first inspect:

```bash
git status --short --branch
git fetch origin
git log -1 --oneline origin/main
```

The previously verified main SHA was
`3845f42d983e6f741b47bf212c227f26b12efc9d`. If the handoff branch has been
merged since this note was written, use its resulting main commit and read the
updated context/status instead of assuming the old SHA is current.
