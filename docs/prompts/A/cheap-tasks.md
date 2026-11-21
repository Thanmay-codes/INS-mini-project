# Optional small tasks for a lightweight model

These are bounded helper tasks, not replacements for the 22 main prompts or new release gates. Run one on a fresh lead-owned branch from current main after its prerequisites. Read the common rules, record BASE_SHA, and merge/review it before another task touches the same file. A reviews changes; the helper never releases a gate or redesigns security behavior.

## L01 — contract fixture audit, after A01

```text
Act as a lightweight helper for lead A, task L01. Read AGENTS.md, PROJECT_CONTEXT.md, docs/prompts/common-rules.md, docs/contracts/protocol-v1.md and docs/contracts/python-api-v1.md. A01 must already be merged; if its files are absent, report the missing prerequisite.

Use a fresh work/a-l01-fixture-audit branch with a recorded starting BASE_SHA. Read every JSON/TOML fixture under data/fixtures/contract/. Parse it with the standard library, compare field names/types/example encodings and expected validity labels with the approved contract, and list any inconsistencies. Keep public disposable test material distinct from runtime secrets. Do not modify schemas, helpers or fixtures and do not invent cryptographic validation results for code that does not exist yet.

Write only docs/handoffs/A/L01.md using the handoff template, with paths checked, exact commands, findings and proposed corrections for A. Run python scripts/check_task_scope.py --role A --base BASE_SHA. Return the report without committing/pushing or proceeding to another task.
```

## L02 — time helper tests, after A02

```text
Act as a lightweight helper for lead A, task L02. Read AGENTS.md, PROJECT_CONTEXT.md, common task rules, the released A01 time/API contract and A02's actual implemented clock/validation helpers. A02 must already be merged.

Use a fresh work/a-l02-clock-tests branch with recorded BASE_SHA. Add only tests/unit/test_a_clock_boundaries.py and docs/handoffs/A/L02.md. Test documented deterministic/offset clocks, equality at the exact allowed boundary, values just inside/outside it, and invalid configuration/type inputs through the actual public API. Use logical clocks; do not sleep or modify OS time. Do not duplicate tests already present merely to increase count. If all useful cases already exist, report that instead of adding redundant tests.

Run the new/relevant existing clock tests. If the implementation disagrees with the frozen contract, record the discrepancy for A rather than changing production code or choosing a new boundary rule. Run the role A scope check using the starting SHA. Report actual outcomes and leave Git publication to the human. A reviews these tests before using them as release evidence.
```

## L03 — measurement inventory, before A07 review

```text
Act as a lightweight helper for lead A, task L03. Read AGENTS.md, PROJECT_CONTEXT.md, common task rules, A06/B03/B04 handoffs and the actual documented runner/analysis commands. The code and raw outputs must already exist locally; ignored raw files are not supplied by a teammate's push.

Use a fresh work/a-l03-evidence-inventory branch with recorded BASE_SHA. Inventory the local candidate core-result artifacts, record file sizes and SHA-256 digests, code commit, run/scenario IDs, declared counts and non-secret environment/config paths. Check expected columns and identify missing/failed trials. Do not print or copy secrets/private ticket artifacts, change numeric values, approve conclusions or publish files to results/published/.

Write only docs/handoffs/A/L03.md with the inventory, exact commands, missing evidence and questions for the lead. If raw outputs are absent, report the exact generation command prerequisite rather than fabricate an inventory. Run the role A scope check. Stop for A07's scientific review; no gate release or Git publication.
```

## L04 — approved lead draft consistency check, after A08 draft

```text
Act as a lightweight helper for lead A, task L04. Read AGENTS.md, PROJECT_CONTEXT.md, common task rules, docs/report/content/lead/, the approved B methods/results source and results/published/ manifest. A08's draft and approved core evidence must exist.

Use a fresh work/a-l04-draft-check branch with recorded BASE_SHA. Check local links, source-artifact references, inconsistent terminology, unsupported completed-feature wording, missing units/denominators and disagreement between quoted numbers and approved tables. Flag optional-extension claims unless A09 approval exists. Check wording against the existing reference audit without inventing new literature claims.

Write only docs/handoffs/A/L04.md with exact file/section findings and proposed wording corrections. Do not edit scientific drafts, results, manuscript assembly files or source code. Distinguish mechanical issues from interpretations needing strong review. Run the role A scope check and return the report to the lead. Leave commits/pushes to the human.
```
