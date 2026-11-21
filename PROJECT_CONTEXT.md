# Project context for future chats

Last updated: 21 November 2026 (Asia/Kolkata).

## User's goal and constraints

- College Information and Network Security project and a paper for a small college conference.
- The Kerberos-style authentication/security topic has already been submitted. Keep that topic; refine its implementation and experiments.
- Four team members, realistically two active developers. The user owns the most consequential security work; one contributor owns the second most important implementation work; two contributors handle support tasks outside the critical build path.
- Repository: https://github.com/Thanmay-codes/INS-mini-project . Remote availability/content is not assumed verified.
- The user handles commands requiring Git credentials. Prepare files and local Git state without authenticating, pushing, or requesting credentials.
- Deadline, conference format/rubric, teammate names, and teammates' operating systems are not yet supplied. Use milestone order rather than invented calendar dates.

## Agreed scope

Build a local Python/Flask simulator with AS and TGS together in one KDC process, one resource-server process, and a CLI client. The central comparison uses identical session-key-authenticated requests with replay caching disabled and enabled. The additional feature is persistent atomic replay tracking, evaluated under concurrent duplicates and service restart. Clock offsets are controlled experiments. Add bounded synthetic service-password guessing after the replay core works.

The contribution is an evaluated student implementation of established techniques. No new protocol, new Kerberos vulnerability, proven literature gap, AD interoperability, production effectiveness, or conference acceptance has been established. Nonces, replay caches, and challenge-response already exist. AES alone does not prevent guessing weak passwords. A dictionary miss proves only non-recovery within the tested set/budget.

## Authoritative documents

- `docs/implementation-plan.md`: build specification, interfaces, experiment design, milestones, and completion criteria.
- `docs/team-work.md`: four-person ownership, bounded task list, and handoff rules.
- `docs/workflow/README.md`, `tasks.json`, `status.md`: execution order, exact ownership and lead-released gates. These refine the earlier broad team assignment.
- `docs/prompts/README.md`: copy-paste task prompts for all four contributors, including relative model-effort guidance.
- `docs/github-setup.md`: repository preparation and user-run Git commands.
- `docs/references/validity-research.md`: checked original references and corrected claims.
- `docs/references/conference-extension-research.md`: related work and publication limits.

Older proposal, architecture, college-conference, and roadmap files are background summaries. Use the implementation plan and team-work file when they differ. The original submission is preserved at `docs/planning/original-plan.txt`.

## Current implementation status

G1 is released. A01–A04 and B01/B02 are merged on main, verified at base
`084d80d6b92a465d4dd2db9c221a816d1ccf9119` (PR #5 / A04 merge).
The G1 release record was published in PR #4. Local branch
`work/a05-integration` adds A05 and is awaiting human review/merge; G2 remains
NOT RELEASED until merged-main checks and an exact SHA are recorded.

Implemented shared helpers: frozen v1 models/JSON, AES-GCM tickets, session-key
request MACs, Scrypt verifier, bounded service-key derivation, settings/logical
clocks, private initialization/material loaders and persistent atomic SQLite
replay/counter state. Merged apps now implement AS login, TGS issuance, protected
resource access, client authentication/captures/replay and implemented health.

A05 updates the launcher and root README and adds real-process AS→TGS→resource
integration. Normal and invalid journeys, same-ticket fresh requests, exact
capture replay, restart and launcher cleanup pass locally; see A05 handoff for
final commands/counts. No KDC/resource stubs or internal mocks are used by A05.
Earlier B02 tests still include an explicitly labeled resource contract stub.
Linux/Python 3.14 is the locally verified platform. B's Windows POSIX permission
assertion report remains an A-owned follow-up; no Windows ACL enforcement claim.

No experiment runner, reviewed E01–E10 measurements, plots or manuscript results
are released. Integration correctness is not scientific measurement. Ordinary
process restart does not establish power-loss durability, hostile filesystem
rollback resistance or recovery of lost responses after a committed operation.
Runtime secrets/captures stay in ignored private directories.

Human performs Git commits/pushes/authentication. Public fetches with credentials
disabled verified main; no authentication or push was performed by the agent.
Inspect Git state before further operations; origin/main can be stale because
verification fetched an explicit public URL into FETCH_HEAD. C/D support-task
completion has not been verified here.

## Next work

Review/merge A05, then rerun full-suite and independent contract/dependency checks
on merged main to release G2. Only after that may B resume B03 and A start A06
in parallel, respecting disjoint ownership. B03 should reconcile B's older client
usage page with the integrated launcher/root README. A06 should handle the
existing POSIX-only material-permission test assumption without pretending to
verify Windows ACLs. Later evidence/scientific work still follows the gates.

Only A updates this file after integration, recording completed checks and the next unfinished task. B/C/D write their own task handoffs instead, preventing concurrent central-file edits. Keep secrets, active tickets, replay databases, logs, and unreviewed raw outputs in ignored paths.
