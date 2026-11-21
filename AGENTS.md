# Project context

Before planning or changing this project, read `PROJECT_CONTEXT.md`. It records the user's scope, current implementation status, and Git credential boundary.

For implementation, read `docs/implementation-plan.md`. Before executing a task, read `docs/workflow/README.md`, its role's prompt in `docs/prompts/`, and the allowlist/dependencies in `docs/workflow/tasks.json`. This execution workflow refines the broad assignment in `docs/team-work.md` and takes precedence for task order, file ownership and handoffs. When checking research claims or writing the paper, consult `docs/references/validity-research.md` and `docs/references/conference-extension-research.md`.

Each task writes its own `docs/handoffs/<ROLE>/<TASK>.md`. Only A, acting as lead/integrator, updates `PROJECT_CONTEXT.md` and `docs/workflow/status.md` after merge and relevant checks. B/C/D request central changes through their handoffs. Mark a feature implemented only when its code exists and relevant checks pass. Keep experiment measurements traceable to generated evidence.

The user performs Git commands requiring credentials. Local Git preparation is permitted; leave authenticated operations to the user and keep credentials out of files and chat.
