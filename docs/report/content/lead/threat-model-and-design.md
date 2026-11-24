# Threat Model and Security Design (Lead-Authored)

## Threat Model and Trust Boundaries

The simulator models a single-host local environment (`127.0.0.1`) with one synthetic client (`alice`), one combined KDC process (AS + TGS roles on port 5000), and one or more resource-server worker processes (port 5001 or distinct loopback ports for concurrency).

- **In-scope adversary capabilities:**
  - Capturing a valid `POST /access-resource` JSON request and replaying the exact bytes (or reformatted JSON) within the ticket and authenticator validity window.
  - Submitting concurrent duplicate requests to multiple resource-server workers sharing the same service key and replay store.
  - Replaying a previously consumed request after an ordinary resource-server process restart or a simulated ±15-second logical clock shift.
  - Modifying ticket ciphertexts, authenticator fields, HTTP method/path context, service audience, or request bodies, or presenting a TGT to the resource endpoint.
  - Performing offline dictionary verification against a synthetically acquired service ticket (E11–E12) without network interaction.
- **Declared simplifications and out-of-scope threats:**
  - **Trusted local host and loopback JSON:** Login credentials and session keys are delivered over local JSON without TLS, ASN.1 encoding, or Kerberos pre-authentication. A privileged local administrator who can read `data/private/` keys or substitute valid SQLite snapshots before process startup is out of scope.
  - **Logical clocks only:** Host system time and NTP are never modified; clock offsets and frozen timestamps are injected per role.
  - **Ordinary restart vs. storage/power faults:** Process termination and restart are tested; power-loss durability, disk write-cache loss, and distributed multi-host replay coordination are outside this model.

## Cryptographic and Protocol Design

All shared primitives reside in `src/kerberos_lab/common/`:

1. **Key separation and password verification:** `scripts/init_demo.py` generates independent 32-byte long-term keys for the TGS (`tgs.key`) and resource service (`service.key`), plus a salted Scrypt verifier (`n=16384, r=8, p=1`, 16-byte salt) in `user.json` for `alice`.
2. **Ticket envelopes (AES-256-GCM):** Both TGTs (`kind="tgt"`, `service_id="tgs"`) and service tickets (`kind="service"`, `service_id="files"`) are serialized as canonical ASCII JSON (`canonical_bytes`) and sealed with `AESGCM` using a fresh 12-byte random nonce and domain-separated AAD (`ins-kerberos-lab:ticket:v1:<kind>`).
3. **Request authenticators (HMAC-SHA-256):** Each `POST /service-ticket` or `POST /access-resource` request includes an authenticator bound to `client_id`, `service_id`, `ticket_id`, `timestamp`, a 32-hex-character `request_nonce`, `method`, `path`, `body_sha256`, and `ticket_sha256`. The MAC is computed over explicit domain prefixes (`ins-kerberos-lab:auth:v1:tgs\0` and `ins-kerberos-lab:auth:v1:resource\0`) using the corresponding session key.
4. **Strict validation and error stability:** Parsers reject duplicate JSON keys, non-finite floats, booleans in integer fields, unknown keys, and oversized payloads (`>65,536` bytes) with `400 malformed_request`. Authentication, integrity, audience, and time-window failures return `401 invalid_authentication` without leaking internal decryption or timing diagnostics.

## Persistent Atomic Replay Defense and Time Rules

- **Atomic SQLite transaction:** In `authenticator_cache` mode, `ReplayStore.consume_and_increment` opens a per-request SQLite connection (`DELETE` rollback journal, `synchronous=FULL`, `BEGIN IMMEDIATE`) and checks `(service_id, ticket_id, request_nonce)` uniqueness before incrementing the `counters` table in the **same transaction**. A failed counter update rolls back the nonce reservation.
- **Fail-closed storage semantics:** Missing, replaced, schema-mismatched, corrupt, or capacity-exhausted replay stores raise `ReplayStateUnavailable` (`503 replay_state_unavailable`) rather than falling back to no-cache execution.
- **Time-window boundaries (inclusive):** Default ticket lifetime is 300 seconds, with `allowed_clock_skew_seconds = 30` and `ticket_boundary_leeway_seconds = 30`. Both authenticator freshness (`|now - timestamp| <= 30`) and ticket validity (`not_before - 30 <= now <= expires_at + 30`) are inclusive. Retained replay entries are never purged by clock rollback during a run, so consumed identities remain rejected (`409 replay_detected`) if logical time moves backward.
