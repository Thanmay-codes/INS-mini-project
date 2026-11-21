# Execution workflow

Use this file and `tasks.json` for task order and ownership. Use `docs/implementation-plan.md` for the build specification. Earlier broad assignments in `docs/team-work.md` are refined by this workflow. Individual copy-paste prompts are indexed in `docs/prompts/README.md`.

## First push and checkout

The initial push contains a scaffold and task instructions, not implemented authentication. Each person clones their own copy and creates their own virtual environment following the root README. A local `.venv` is intentionally absent from Git. Run the initial server/health check; no protocol test suite exists yet.

The human's first checkout commands are:

```bash
git clone https://github.com/Thanmay-codes/INS-mini-project.git
cd INS-mini-project
```

Then create the assigned task branch using the next command block (B00, C01 or D01 for those contributors). The agent can record the clean starting SHA before edits. Give it the full fenced prompt from its task file, or tell it to read that file and execute only that prompt. Each teammate works in a separate clone; two agents must not switch branches in the same working directory concurrently.

Humans run credential-requiring Git commands. Before each task, the human syncs local `main` with GitHub, creates a fresh task branch from that main, and records the starting commit SHA. Agent prompts work locally on that branch. Human reviewers commit/push/open the PR. A integrates after reviewing the handoff and checks.

```bash
# Human runs before EACH task, from a clean checkout.
git switch main
git pull --ff-only origin main
# Replace the branch name with the one shown in the task prompt.
git switch -c work/a01-contract
git rev-parse HEAD
```

Record that last SHA as the task's base commit. Use it in the scope check; using a moving `main`, `origin/main`, or the final task HEAD can hide changes. Agents preserve existing user work and stop for a dirty/unexpected branch rather than stashing/resetting it.

## Start order

| Stage | Start these tasks | Required state |
| --- | --- | --- |
| 0 | A01, B00, C01, D01 | Initial preparation commit pushed and cloned |
| 1 | A02, then A03 | Each predecessor reviewed and merged |
| G1 | A releases shared core | A01–A03 on main; tests pass; public Python APIs and fixtures are documented |
| 2 | A04 and B01 in parallel; B02 follows B01 | G1 released; B02 can test client behavior against frozen HTTP fixtures while A04 is in progress |
| 3 | A05 | A04, B01 and B02 merged; full normal-flow integration |
| G2 | A releases working normal flow | A05 smoke and negative-path integration checks pass |
| 4 | A06 and B03 in parallel | G2 released; tests and runner use separate owned files |
| 5 | B04, then A07 | B03 merged; A07 also requires A06 |
| G3 | A releases reviewed core evidence | E01–E10 verified, measured evidence reviewed and published by A |
| 6 | B05 optional, then A09 review; B06, then A08 draft | G3 released; optional extension results are included only after A09 publishes approved evidence |
| 7 | C02, then C03; D02 | G2 for demo scripts; G3 for final figures and installation documentation |
| 8 | A08 final review, then D03 | A/B technical content approved; C assets approved; conference format known or neutral draft explicitly retained |

C01 and D01 are independent support tasks. C02/D02 happen later because they describe actual commands/results. A01–A03 are the first critical path: B must not invent a second crypto API while waiting.

## File ownership

The precise allowlists are in `tasks.json`. Parent directory ownership does not authorize editing shared files outside the allowlist.

- A: shared contracts/core, resource server, initialization/launcher, settings/dependencies, central plans/context, reviewed published evidence, lead-authored scientific content.
- B: KDC/client, experiment code and their usage documentation, B-prefixed tests, experiment-authored manuscript content.
- C: editable diagrams and presentation materials.
- D: manuscript assembly/formatting/assets and D-owned setup/references documentation.
- Each role writes its own `docs/handoffs/<ROLE>/<TASK>.md`; only A updates central context, workflow status, dependencies, shared fixtures and root README.
- Tests have explicit file prefixes (`test_a_` and `test_b_`). A owns shared test configuration/fixtures. Avoid a shared `conftest.py` unless A releases it as part of the shared contract.
- A/B scientific content lives outside D's manuscript assembly files, so formatting does not overwrite working scientific drafts.

An out-of-scope change becomes a request in that task's handoff. The owning role implements it in a separate task or A records an explicit ownership transfer while no competing branch is active. A review does not silently grant concurrent ownership of another role's files.

## Handoff and merge

1. Human starts a clean task branch from current main and records its SHA.
2. Agent reads its prompt and prerequisites. If a prerequisite is missing, it writes a bounded blocker in its handoff and stops dependent work. It does not guess interfaces or mark a gate released.
3. Agent implements only its task, runs relevant checks, and records exact commands/outcomes plus changed paths.
4. Run `python scripts/check_task_scope.py --role B --base BASE_SHA` (choose the actual role/SHA). This is an advisory local boundary check, not a security sandbox or complete integration test.
5. Human reviews, commits and pushes the branch. A reviews tests/claims and integrates. Rebase/merge updates happen through the human's normal Git workflow; agents do not reset, force-push or discard changes.
6. After merge, A reruns affected integration checks, updates `PROJECT_CONTEXT.md`, and releases applicable gates in `status.md` with an exact main commit SHA and evidence. `tasks.json` is a static task graph, not a completion log.
7. Next dependent task starts from a fresh main containing all prerequisites. Use the latest main SHA, not the older preparation snapshot.

Disjoint file ownership prevents planned direct overlaps; it cannot guarantee zero integration bugs or conflicts if boundaries are ignored. The staged release gates and integration checks address those risks. Avoid simultaneous changes to shared interfaces/dependencies; require a new shared-core release when they change.

## Model effort

Use a lightweight model for B00, C01–C03, D01–D03, and bounded documentation/formatting work. Use a capable coding model for client plumbing and deterministic CSV/plot work after contracts stabilize. Use the strongest available reasoning/review for A01–A06, B01's trust boundaries, concurrency/persistence correctness, and scientific interpretation. These are relative task categories, not claims about any named model's price or accuracy.

Run one prompt at a time. Split cheap mechanical subtasks from security decisions; require the designated owner to review changes before releasing a gate. A smaller model can prepare fixtures or documentation from an approved contract but should not independently redesign the protocol.
