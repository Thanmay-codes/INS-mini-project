# Release status — lead-owned

Updated 21 November 2026. G1 and G2 released. A05 is merged and real-process normal/invalid integration checks pass on merged main. Experiment measurements remain unfinished.

| Gate | State | Required evidence |
| --- | --- | --- |
| G1 shared core | RELEASED | A01–A03 verified at main `20efbae763774af69337e6c97d3b0f29f9ba5092`; 134 tests and fixture checks pass |
| G2 normal flow | RELEASED | A04/B01/B02/A05 verified at main `82915dfd63e873d75733e021cdac17e0ec369b25`; 254 tests and fixture checks pass |
| G3 reviewed core results | NOT RELEASED | A06/B03/B04/A07 merged; reviewed E01–E10 evidence published |
| Optional extension | NOT IMPLEMENTED | B05 merged; A reviews bounded actual measurements |
| Final paper package | NOT PREPARED | A08/B06 technical approval; C/D packaging and format checks |

A01–A05 and B01/B02 are merged and verified at `82915dfd63e873d75733e021cdac17e0ec369b25`. A06 and B03 are eligible after this release record is published. C01/D01 remain independent support tasks; their completion has not been verified here. All code-dependent prompts must check their listed predecessor files and evidence.

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

## G2 release — 21 November 2026

Verified public main with credentials disabled, fast-forwarded local main to
`82915dfd63e873d75733e021cdac17e0ec369b25` (PR #6 / A05 merge), and
reran checks on that exact merged code. A04/B01/B02 and A05 are present.
Release documentation is prepared on `work/g2-release` for human publication.

```bash
.venv/bin/python -m pytest -q --tb=short
.venv/bin/python docs/contracts/verify-fixtures.py
.venv/bin/python -m pip check
```

Results: **254 passed**, independent A01 fixtures pass, dependencies consistent.
Evidence: [A04](../handoffs/A/A04.md), [B01](../handoffs/B/B01.md),
[B02](../handoffs/B/B02.md), [A05](../handoffs/A/A05.md),
[runtime controls](../contracts/runtime-v1.md).

Real launcher/AS/TGS/client/resource checks cover normal access, same-ticket fresh
requests, invalid credentials/artifacts/roles/context/time, exact capture/replay,
restart and child cleanup. Linux/Python 3.14 is the verified platform; native
Windows lifecycle and the existing POSIX permission assertion remain follow-ups.
No E01–E10 measurements, paper results, power-loss durability or production
Kerberos/AD interoperability are established by G2.

After publication, A06 and B03 may start in parallel from fresh main containing
this release record. B03 follows its existing prompt; its old blocker is now
satisfied. B04 follows B03, and A07 waits for both A06 and B04. G3 remains
NOT RELEASED. B should reconcile its older client usage page; A06 should handle
the platform-specific permission assertion without claiming Windows ACL checks.
