# Project context for future chats

Last updated: 24 November 2026 (Asia/Kolkata).

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

G1, G2 and G3 are released. A06, B03 runner, B04 analyzer, B's A07 reporting
correction and A07 evidence are merged on verified main
`38fe775067042f40e06e3cd05bce05ffabf00f6c`. The core application,
launcher, shared crypto/state and security review exist. A06 corrected the
POSIX-only permission-test assumption; Windows ACLs remain unverified.

A07 is merged and its G3 evidence was rechecked on exact main. Fresh regeneration produced 46 E01–E10 smoke
attempts plus 300 E01–E03 attempts across 30 trials per scenario, with zero
failed or transport attempts. Independent record checks reproduced 30/30
no-cache versus 0/30 cache duplicate grants, 0/90 legitimate rejections per
mode, correct E04 phase denominators, single successful operations in every
E05 worker-count condition, restart replay rejection and declared offset/boundary
outcomes. Sanitized outputs and provenance are tracked in
`results/published/a07-20261124/`; raw inputs remain ignored.

The G3 release record is prepared on `work/g3-release`; its evidence source is
the tracked `results/published/a07-20261124/` manifest. Optional password
experiments and final manuscript/presentation remain pending. No production
Kerberos/AD, NTP exploitation, power-loss or exactly-once claim is made.

The new global instruction path `/home/thanmay/.agents/main.md` was requested but
is absent on this machine; project instructions were available and followed.
The human still performs commits/pushes/authenticated operations. Public fetches
used disabled credentials. Native Windows lifecycle/ACL validation and A06's
minor B-owned login username-schema follow-up remain outside this evidence task.

## Next work

Human reviews and merges `work/g3-release`. Then B starts B06 from that updated
main to draft implementation-faithful methods/results from published evidence.
A08 follows B06's merge. B05/A09 remains optional and is not implied by G3.

Only A updates this file after integration, recording completed checks and the next unfinished task. B/C/D write their own task handoffs instead, preventing concurrent central-file edits. Keep secrets, active tickets, replay databases, logs, and unreviewed raw outputs in ignored paths.
