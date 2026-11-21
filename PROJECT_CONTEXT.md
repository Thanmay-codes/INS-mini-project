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

Implemented and previously smoke-checked: Python package, local `.venv`, dependency snapshot, KDC and resource-server Flask starters exposing only `/health`, health client, and launcher. Project folders, detailed plans, ownership, paper folders, and Git handoff files are prepared.

Prepared workflow: 22 individual task prompts, static ownership/dependency registry, unreleased gate ledger, role-specific handoff locations, scientific-content separation and a local advisory scope checker. The role prompts are ready to hand to agents after the preparation commit is pushed/cloned. They are instructions, not completed implementation. The first tasks are A01, B00, C01 and D01; B's KDC implementation waits for G1 (A01–A03 merged/tested).

Four additional optional lightweight helper prompts are in `docs/prompts/A/cheap-tasks.md`. They audit contract fixtures, add bounded clock tests, inventory measurements and check approved drafts; A retains security/scientific approval. Workflow validation checked all 22 task files, acyclic prerequisites, allowed output paths, disjoint role-boundary probes and local links. The scope-checker CLI passed disposable-repository checks for allowed untracked/staged edits, shared-file rejection, cross-owner move rejection and fixed-base enforcement. These are workflow checks, not authentication or experiment results.

Not implemented: identity initialization, ticket encryption, login, TGS issuance, authenticated requests, protected resource, replay cache, clock injection, attack runners, measurements, plots, protocol tests, and manuscript results. Configuration examples describe future interfaces; no loader exists yet. No scientific measurements exist.

Local Git was initialized on `main`, with `origin` set to `https://github.com/Thanmay-codes/INS-mini-project.git`. No commit, push, remote creation or successful authentication was performed. Inspect `git status` and `git remote -v` for current state before the next Git operation.

Preparation checks passed: 26 required directories exist; local Markdown links resolve; package/configuration TOML and the header-only result CSV parse; private/environment/raw-log paths are ignored while plans and reviewed-evidence folders remain visible to Git. These checks validate preparation, not protocol security.

## Next work

Run the A01 prompt, then A02/A03, to release the shared contract/helpers/setup as G1. B runs B00 setup immediately and waits for G1 before B01/B02; C01/D01 can start immediately. After G1, A04 and B01 can proceed in parallel on disjoint paths. Follow workflow/status.md for later gates.

Only A updates this file after integration, recording completed checks and the next unfinished task. B/C/D write their own task handoffs instead, preventing concurrent central-file edits. Keep secrets, active tickets, replay databases, logs, and unreviewed raw outputs in ignored paths.
