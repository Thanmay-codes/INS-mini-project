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

A01–A03 are merged and G1 shared core is released against verified main commit
`20efbae763774af69337e6c97d3b0f29f9ba5092` (PR #3 merge, 21 November 2026).
The release record is prepared locally on `work/g1-release` for human publication.

Implemented: frozen v1 protocol/Python contracts and independent fixtures; strict
models/JSON/settings/logical clocks; AES-GCM tickets, session-key request MACs,
Scrypt password verification and bounded service-key derivation; persistent
SQLite replay stores with atomic counters, capacity limits and fail-closed state;
private role-specific material loading and new-run initialization CLI. See
`docs/contracts/setup-v1.md` and A01–A03 handoffs for APIs, commands and limits.
The existing KDC/resource HTTP apps still expose scaffold health behavior.

On the merged main SHA, 134 tests passed, independent contract fixture verification
passed and pip dependency checks were clean. Tests include real SQLite files,
concurrent child processes, ordinary exit/reopen, rollback, contention and setup
CLI. These establish shared-helper behavior, not HTTP security or measured paper
results. Power-loss durability and hostile local filesystem rollback are not
established. No runtime secrets were committed.

Not implemented: AS/login and TGS endpoints, protected resource wiring, complete
legitimate client journey, full-flow integration, attack runners, measurements,
plots and manuscript results. A04/B01 must connect authentication to replay-store
transactions; stateless MAC verification alone does not reject repeats.

The 22-task workflow, ownership boundaries and optional lightweight helper prompts
remain authoritative. B00/C01/D01 completion has not been verified in this checkout.
The human performs Git commits/pushes/authenticated operations. A public fetch with
credentials disabled verified the merge; no authentication or push was performed.
Inspect Git state before further operations; local origin/main may remain stale
because the verification fetched the explicit public URL into FETCH_HEAD.

## Next work

Publish the G1 release documentation branch, then start A04 (resource server) and
B01 (KDC, after B00) in separate clones from updated main. They can proceed in
parallel on disjoint owned paths. B02 follows B01; A05 waits for A04/B01/B02 merges
before releasing G2. G2/G3 remain unreleased. Follow workflow/status.md.

Only A updates this file after integration, recording completed checks and the next unfinished task. B/C/D write their own task handoffs instead, preventing concurrent central-file edits. Keep secrets, active tickets, replay databases, logs, and unreviewed raw outputs in ignored paths.
