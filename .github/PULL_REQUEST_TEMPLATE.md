## Change

Describe the completed change and its purpose. Link the task ID/prompt from `docs/workflow/tasks.json` and the role-owned task handoff. Include the starting base commit SHA.

## Validation

Record the commands/scenarios run and observed outcomes, including `python scripts/check_task_scope.py --role ROLE --base BASE_SHA`. For documentation-only work, state what was checked. Identify mocks separately from real process tests.

## Integration notes

Identify shared-contract requests, affected experiment assumptions, or remaining work. Contributors update their own handoff; A updates central context/gate status after merge and integration checks. Cite required predecessor merges/gates.
