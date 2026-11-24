# Release status — lead-owned

Updated 24 November 2026. G1/G2 are released. A07's corrected, reviewed evidence
is prepared on `work/a07-evidence-final`; G3 remains NOT RELEASED until that work
is merged and verified on the exact resulting main commit.

| Gate | State | Required evidence |
| --- | --- | --- |
| G1 shared core | RELEASED | A01–A03 verified at main `20efbae763774af69337e6c97d3b0f29f9ba5092`; 134 tests and fixture checks pass |
| G2 normal flow | RELEASED | A04/B01/B02/A05 verified at main `82915dfd63e873d75733e021cdac17e0ec369b25`; 254 tests and fixture checks pass |
| G3 reviewed core results | NOT RELEASED | A07 branch merge plus merged-main verification of reviewed E01–E10 evidence |
| Optional extension | NOT IMPLEMENTED | B05 merged; A reviews bounded actual measurements |
| Final paper package | NOT PREPARED | A08/B06 technical approval; C/D packaging and format checks |

A01–A06 and B01–B04 are present, along with B's reporting correction, on main
`636ba23f066b082eccc1d590e17f62608b2bd626`. A07's reviewed evidence is ready on
`work/a07-evidence-final`; C/D completion has not been verified here.

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

## A07 review — 24 November 2026, publication blocked

Base: `05422d01232607f609983e770f82e86d3333e5b2`. Regenerated smoke:
46 attempts across E01–E10; repeated E01–E03: 300 attempts / 30 trials per
scenario. No unexpected outcomes or transport failures. Functional/counter and
latency calculations were independently checked; these remain unapproved audit
observations. See [A07 handoff](../handoffs/A/A07.md) and
[preliminary findings](../report/content/lead/core-findings.md).

Blocking B-owned work: correct per-phase E04 denominators (currently 4 expected
versus 1 actual per phase/trial), actual trial-major ordering metadata, and
startup timer boundary/label. No B-owned files or released interfaces were edited.

Resume evidence regeneration/review after corrections are merged. Do not mark A07
complete merely because its blocker note is merged. No approved evidence exists
in results/published; G3, optional extension and final paper gates are unchanged.
