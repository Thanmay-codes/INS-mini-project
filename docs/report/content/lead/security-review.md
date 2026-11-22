# A06 security review — replay safety and retained state

Reviewed 22 November 2026. Base: main
`b8f365056fbfcc252a52d203fbf12d098b4b1be2` (merged G2 release).
Branch: `work/a06-security-review`. This is implementation correctness evidence,
not experiment measurements, a security proof or approval of paper results.

## Scope and outcome

Reviewed the v1 contracts, shared models/parser/crypto/time/material/store code,
resource handler, prior A02–A05 tests/handoffs and the KDC/client trust boundaries
needed to understand the flow. The trusted-local-host assumption, exact schemas,
separate role keys/domains and full-run retention policy remain unchanged.
No production code or public interface/schema/dependency was changed in A06;
B03 can continue against the released APIs.

No replay bypass or atomic-counter defect was observed in the reviewed paths and
executed cases. That statement is limited to this implementation and test set.
One previously reported test-portability defect was fixed. A low-impact KDC
input-schema discrepancy was reproduced and is assigned to B below.

## Evidence and observations

| Property | Evidence | Observed outcome |
| --- | --- | --- |
| Ticket integrity and role ownership | Existing A02 crypto vectors/tampering checks; A04/A05 handler tests | Wrong key, modified ciphertext, kind relabeling and TGT-at-resource fail; role keys remain separate |
| Request authorization and domain binding | New `test_valid_mac_cannot_authorize_a_different_role_or_context`, both modes | Even recomputed tags made with the synthetic session key cannot authorize wrong domain/method/path/service/client/ticket/body digest/envelope digest; no operation or nonce reservation |
| Strict request parsing | Existing schema/size/encoding cases plus new adversarial JSON cases | Deep nesting, unpaired Unicode surrogate and escaped duplicate version keys return exact 400 errors; untouched valid request can still execute |
| Clock rollback and retained replay identity | New forward/backward sequence, both modes | Previously consumed identity remains 409 at inclusive ±30 s points and after returning to original time; outside validity/freshness it returns 401 |
| No time-based purge / capacity reset | New large forward excursion then rollback with capacity=1 | Original remains duplicate, a new identity gets 503 and counter remains 1 |
| Nonce identity versus timestamp | New re-signing test after 60 s | Old authenticator is stale, but signing the same consumed nonce at fresh time still returns 409; a fresh nonce succeeds |
| Concurrent independent workers | Existing real-process A04 tests, rerun | Two same-key/store HTTP workers accept exactly the distinct identities; defended duplicates do not add committed operations; control executes all valid copies |
| Restart and state loss | Existing A03–A05 store/HTTP/process cases, rerun | Preserved state rejects duplicates after restart; missing/corrupt/wrong-metadata/schema state fails closed rather than reinitializing |
| Transaction rollback and contention | Existing real SQLite overflow/lock tests, rerun | Counter and nonce roll back together; lock/storage errors yield unavailable, with no no-cache fallback |
| Response uncertainty and process termination | New unread-response process tests, both modes | Request commits despite client discarding response. After worker termination/restart, defended retry is 409/counter=1; no-cache retry commits counter=2 |
| POSIX test permissions | Split material tests | POSIX verifies directory 0700/files 0600 separately; all platforms retain verifier, non-overwrite and role-isolation checks |

The new context tests intentionally create valid tags with a disposable synthetic
session key through an independent standard-library HMAC implementation. This
checks endpoint/context authorization rather than merely mutating an otherwise
invalid MAC. Production cryptography continues using the existing library APIs.
No runtime artifact, credential, ticket, authenticator or session key is included
in this report.

In the lost-response check, the test sends the actual HTTP body, closes without
reading the response, observes committed state through the public counter API,
then terminates the worker. Commit was observed **before** termination. This
checks committed-state persistence and retry ambiguity; it does not claim a kill
during an in-flight SQLite transaction, loss of machine power or storage-device
failure. Existing injected overflow/lock tests separately check rollback behavior.

## Test portability correction

B previously reported that the mixed material test's POSIX permission assertions
fail on Windows even though the material/role behavior works. Moved only those
assertions into `test_private_run_permissions_on_posix`, skipped outside POSIX.
The original verifier/non-overwrite/resource-isolation test still runs everywhere.
B should remove its old manual deselection when testing the merged A06 revision.

This is test portability, not a Windows security implementation. Windows ACLs,
native console lifecycle and native getpass behavior have not been verified on
this Linux review machine. Native Windows validation remains follow-up work.

## B-owned conformance follow-up

A direct Flask HTTP-handler probe against the actual KDC at the base revision
sent login usernames of length 0, uppercase `Alice`, and 65 lowercase characters,
with an otherwise valid synthetic password. All three returned
`401 invalid_credentials`, not a grant. The v1 ID rule is
`[a-z][a-z0-9_-]{0,63}` and malformed values map to 400. The login handler checks
that username is text but does not enforce that identifier rule before its KDF.

**Request to B:** enforce the existing username syntax in
`src/kerberos_lab/kdc/app.py` before password verification, with B-owned tests for
empty/uppercase/overlong names returning 400. Preserve the uniform 401 response
and comparable KDF work for syntactically valid unknown users versus wrong
passwords. Handle this in a B-owned conformance fix, keeping runner files separate.
No shared API or schema revision is requested.

This is a low-impact validation/error-classification discrepancy, not an observed
authentication grant or replay bypass. It does not block replay-runner development;
resolve it before final complete-protocol conformance signoff. B-owned code was
not modified. The manual probe used temporary private state and printed only
username lengths/status/error codes, not credentials or ticket material.

## Residual risks and interpretation limits

- The no-cache control is intentionally incomplete. Both modes still validate
  ticket/MAC/role/context/body/time; only duplicate tracking is bypassed.
- Clock injection does not eliminate ticket lifetime or skew assumptions.
  Retained entries stop reacceptance after rollback; a wrong clock can still
  reject legitimate requests. There is no NTP exploitation implementation.
- The store serializes a local SQLite counter with replay consumption. It does
  not provide exactly-once delivery, distributed side effects or response
  recovery. A lost response leaves the client uncertain; 409 is not a result.
- Capacity exhaustion is deliberately fail-closed. Authenticated traffic can
  exhaust a bounded run and affect availability; records are not evicted to
  permit more traffic. Fresh independent trials need fresh directories.
- Private state and the host filesystem are trusted. Live handles detect path
  replacement, but a valid same-run snapshot substituted before a fresh open,
  or privileged in-place edits, lack an external trusted history for detection.
  Permission bits are not a defense against a malicious local administrator.
- Library AES-GCM/HMAC/KDF vectors and random nonce tests are correctness checks,
  not cryptographic proofs or collision-free allocation under unlimited load.
- Login/session delivery over loopback JSON is the declared educational
  simplification. No production Kerberos/AD interoperability, TLS-protected
  credential exchange, NTP compromise or Kerberoasting result is established.
- A06 correctness tests produce no latency/throughput estimate, E01–E10 trial
  matrix, reviewed figure or publication-ready scientific conclusion. B03/B04
  generate candidate evidence; A07 reviews it before publication. G3 is unreleased.

## Reproduction

From an installed development environment at the reviewed branch:

```bash
python -m pytest tests/security/test_a_replay_safety.py tests/security/test_a_resource_processes.py tests/unit/test_a_material.py -q --tb=short
python -m pytest -q --tb=short
python docs/contracts/verify-fixtures.py
python -m pip check
```

Exact local outcomes, task base and changed files are recorded in
[the A06 handoff](../../../handoffs/A/A06.md). Existing A04/A05 process cases use
real loopback servers; older B02's labeled resource stub remains separate.
