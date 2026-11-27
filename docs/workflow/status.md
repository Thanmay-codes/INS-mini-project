# Release status — lead-owned

Updated 27 November 2026. G1/G2/G3, optional extension (B05/A09), technical
drafts (B06/A08), diagrams/presentation (C01–C03), and neutral manuscript
assembly (D01–D03) are merged on verified public main
`9a112f54cc1df08494425b12241a0dfde9ac9de7` (PR #20).

| Gate | State | Required evidence |
| --- | --- | --- |
| G1 shared core | RELEASED | A01–A03 verified at main `20efbae763774af69337e6c97d3b0f29f9ba5092`; 134 tests and fixture checks pass |
| G2 normal flow | RELEASED | A04/B01/B02/A05 verified at main `82915dfd63e873d75733e021cdac17e0ec369b25`; 254 tests and fixture checks pass |
| G3 reviewed core results | RELEASED | A07 evidence verified on main `3845f42d983e6f741b47bf212c227f26b12efc9d`; 296 tests, fixtures, dependencies and manifest hashes pass |
| Optional extension | RELEASED | B05 merged at `34a20a5`; A09 reviewed evidence merged at `5df55aa`; 310 tests pass after KDC username-schema fix (`abf1ef8`) |
| Final paper package | NEUTRAL DRAFT READY | A08/B06, C01–C03, and D01–D03 merged at `9a112f5`; awaiting professor template, author names, and deadline |

A01–A09, B00–B06, C01–C03, and D01–D03 are all merged on verified main
`9a112f54cc1df08494425b12241a0dfde9ac9de7`.

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

## A07 initial audit — 24 November 2026, corrected before publication

Base: `05422d01232607f609983e770f82e86d3333e5b2`. This initial audit regenerated:
46 attempts across E01–E10; repeated E01–E03: 300 attempts / 30 trials per
scenario. No unexpected outcomes or transport failures. Functional/counter and
latency calculations were independently checked; these remain unapproved audit
observations. See [A07 handoff](../handoffs/A/A07.md) and
[preliminary findings](../report/content/lead/core-findings.md).

It requested B-owned corrections to the per-phase E04 denominators (then 4 expected
versus 1 actual per phase/trial), actual trial-major ordering metadata, and
startup timer boundary/label. No B-owned files or released interfaces were edited.

The correction merged at `636ba23f066b082eccc1d590e17f62608b2bd626`; A then
regenerated and published reviewed evidence through A07. The G3 release below
supersedes this historical blocked state.

## G3 release — 24 November 2026

Verified public main `3845f42d983e6f741b47bf212c227f26b12efc9d` after PR #10
merged A07 and PR #11 published G3. The corrected runner/analyzer source commit recorded in the evidence
manifest is `636ba23f066b082eccc1d590e17f62608b2bd626`.

```bash
.venv/bin/python -m pytest -q --tb=short
.venv/bin/python docs/contracts/verify-fixtures.py
.venv/bin/python -m pip check
.venv/bin/python -m json.tool results/published/a07-20261124/manifest.json >/dev/null
```

Results: **296 passed** on Linux/Python 3.14.8; the A01 fixture verifier and
dependency check passed. All five tracked evidence-artifact hashes match
`results/published/a07-20261124/manifest.json`, whose raw-source hashes and
commands make the reviewed E01–E10 smoke run and 30-trial E01–E03 run traceable.
Evidence: [A07 handoff](../handoffs/A/A07.md),
[core findings](../report/content/lead/core-findings.md), and
[published manifest](../../results/published/a07-20261124/manifest.json).

G3 permits B06 methods/results drafting and A08 after B06's merge. B05/A09 is
optional and remains outside G3. This release still does not establish production
Kerberos/AD behavior, NTP compromise, power-loss durability, distributed replay
protection or exactly-once response recovery.
