# Release status — lead-owned

Updated 21 November 2026. G1 released; A04/B01/B02 merged. A05 real-process integration is prepared locally, pending merge and G2 verification. Experiment measurements remain unfinished.

| Gate | State | Required evidence |
| --- | --- | --- |
| G1 shared core | RELEASED | A01–A03 verified at main `20efbae763774af69337e6c97d3b0f29f9ba5092`; 134 tests and fixture checks pass |
| G2 normal flow | NOT RELEASED | A04/B01/B02/A05 merged; normal and invalid full-flow checks pass |
| G3 reviewed core results | NOT RELEASED | A06/B03/B04/A07 merged; reviewed E01–E10 evidence published |
| Optional extension | NOT IMPLEMENTED | B05 merged; A reviews bounded actual measurements |
| Final paper package | NOT PREPARED | A08/B06 technical approval; C/D packaging and format checks |

A01–A04 and B01/B02 are on main at `084d80d6b92a465d4dd2db9c221a816d1ccf9119`. A05 is locally implemented on `work/a05-integration`, not yet merged. C01/D01 remain independent support tasks; their completion has not been verified here. All code-dependent prompts must check their listed predecessor files and evidence.

When A releases a gate, record the exact merged main commit, passing commands, handoff links, and remaining limitations below. Contributors report status in their own task handoffs instead of editing this file.

## G1 release — 21 November 2026

Verified public remote main via an unauthenticated fetch, then fast-forwarded local
main to `20efbae763774af69337e6c97d3b0f29f9ba5092` (PR #3 merge).
A03 commit `df511e4` is an ancestor; A01/A02 and their handoffs are present.
Release documentation was published via PR #4 (main merge `9ca854baeda044be0db5f0daca02ee3a2e176c2e`).

Passing checks on that merged code:

```bash
.venv/bin/python -m pytest -q --tb=short
.venv/bin/python docs/contracts/verify-fixtures.py
.venv/bin/python -m pip check
```

134 tests passed, independent A01 fixtures passed, dependencies consistent.
Evidence: [A01](../handoffs/A/A01.md), [A02](../handoffs/A/A02.md),
[A03](../handoffs/A/A03.md); [setup](../contracts/setup-v1.md).
No HTTP AS/TGS/resource protection, complete client journey or scientific
measurements are released by G1. Ordinary SQLite process persistence is tested;
power-loss durability and hostile local filesystem rollback are not established.

A04 and B01 own disjoint paths and may proceed in separate clones after this
release record is published. B must complete B00 first; B02 follows B01. Start
from latest main containing the release record, not an older task branch.

## A05 integration — prepared, G2 NOT RELEASED

Base: main `084d80d6b92a465d4dd2db9c221a816d1ccf9119`, containing
A04/B01/B02. Local branch: `work/a05-integration`. Real launcher/AS/TGS/client/
resource tests pass locally, including normal access, fresh same-ticket requests,
invalid credentials/ticket/role/context/time, capture/replay, restart and child
cleanup. See [A05 handoff](../handoffs/A/A05.md) for exact checks and outcomes.

The human must merge A05. Lead then reruns the full suite and independent fixture
checks on actual merged main and records its exact SHA before changing G2 to
RELEASED. B03 remains blocked until that release record is available. A06 can
then run in parallel with B03 on their owned paths. No E01–E10 measurements or
paper results have been produced by A05.
