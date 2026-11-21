# Agent prompt index

Give an agent the complete fenced prompt from ONE file below. Use a fresh task branch and copy of the repository. The prompt makes the agent read the shared execution rules; no extra explanation from the chat is required.

First read [the workflow](../workflow/README.md) and [gate status](../workflow/status.md). All paths in prompts are repository-relative, so they work in any teammate's clone. `tasks.json` provides static dependencies and ownership.

| Person | Start now | Later prompts, in order |
| --- | --- | --- |
| A — you | [A01 contract](A/A01.md) | [A02 shared core](A/A02.md), [A03 persistent stores/setup](A/A03.md), [A04 resource server](A/A04.md), [A05 normal-flow integration](A/A05.md), [A06 security review](A/A06.md), [A07 evidence publication](A/A07.md), [A08 scientific content/review](A/A08.md); [A09 optional extension review](A/A09.md) after B05 |
| B — active contributor | [B00 setup/preflight](B/B00.md) | After G1: [B01 KDC](B/B01.md), [B02 client](B/B02.md); after G2: [B03 experiment runner](B/B03.md), [B04 analysis](B/B04.md); after G3: [B05 optional guessing](B/B05.md), [B06 methods/results draft](B/B06.md) |
| C — diagrams/presentation | [C01 planned diagrams](C/C01.md) | After G2: [C02 demo/presentation](C/C02.md); after reviewed evidence: [C03 final assets](C/C03.md) |
| D — report/docs | [D01 references/template skeleton](D/D01.md) | After G3: [D02 setup documentation](D/D02.md); after technical content: [D03 manuscript assembly](D/D03.md) |

Start-now means the initial preparation commit has been pushed/cloned; it does not mean all future code exists. A01–A03 release the interfaces that B needs. C/D draft only their bounded support artifacts and never fabricate result values.

## Agent common rules

Read `docs/prompts/common-rules.md` before executing any task. Each prompt includes its role, branch, prerequisites, allowed task outputs, exact completion criteria, and a role-owned handoff. Agents do not commit/push/authenticate unless the human separately changes the existing Git boundary.

## Cost-conscious use for A

- A01/A02/A03/A04/A06: use a strong reasoning/coding model and review the security decisions carefully.
- A05: use a capable coding model for orchestration, with a strong review of failures and protocol assumptions.
- A07: a lightweight model can inventory/hash approved files and format tables; A validates provenance, denominators and conclusions with stronger review.
- A08: a lightweight model can format text and repair local references; A writes/approves contribution claims and interpretation with strong review.

Within a prompt, finish a bounded substep and verify it before continuing. The common handoff makes it possible to switch models between tasks without relying on this chat's memory. No model-specific prices or guarantees are assumed.

Four additional copy-paste [lightweight helper prompts](A/cheap-tasks.md) cover fixture auditing, clock tests, evidence inventory and draft consistency. They are optional substeps under A's review and do not release gates.
