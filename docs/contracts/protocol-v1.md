# Simulator protocol v1 — frozen A01 contract

Status: specified, not implemented. G1 remains unreleased. This custom loopback JSON protocol models Kerberos roles; it is not the Kerberos wire protocol. Public vectors are in `data/fixtures/contract/vectors-v1.json`.

## Encoding and validation

All authenticated objects are JSON objects with exactly the documented fields. Reject duplicate keys, unknown/missing fields, non-finite numbers, floats, invalid UTF-8 and unsupported versions. Integers exclude booleans. Canonical bytes are `json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False).encode("ascii")`, after schema validation. Canonicalization covers logical JSON, not raw HTTP whitespace.

- HTTP body limit: 65,536 bytes; `Content-Type: application/json` required.
- IDs (`client_id`, `service_id`): ASCII regex `[a-z][a-z0-9_-]{0,63}`. Initial user `alice`, service `files`, TGS audience `tgs`; reserve `tgs` from resource-service IDs.
- `ticket_id` and `request_nonce`: 16 random bytes encoded as 32 lowercase hex characters, freshly generated for each ticket/request respectively.
- Times: integer UNIX seconds in `[0, 9007199254740991]`.
- Keys and MACs: 32 bytes, standard padded base64, exactly 44 ASCII characters. Decode strictly and require canonical re-encoding to match. Cipher nonce: 12 bytes, exactly 16 base64 characters. SHA-256 digests: 64 lowercase hex characters.
- Passwords: UTF-8, 1–1,024 encoded bytes, preserved without trimming/normalization. User IDs follow the ID rule. Reject excessive inputs before costly KDF work.

Nested schemas reject unknown fields too. Ticket plaintext is at most 8,192 canonical bytes; envelope ciphertext is plaintext plus the 16-byte GCM tag, never more than 8,208 decoded bytes. The only resource operation in v1 is `increment`, changing a local demonstration counter.

## Tickets and key ownership

Envelope, exact keys:

```json
{"version":1,"kind":"tgt","nonce":"<12 bytes base64>","ciphertext":"<ciphertext and tag base64>"}
```

`kind` is `tgt` or `service`. AES-256-GCM uses separate 32-byte long-term keys for TGS and resource service. AAD is ASCII `ins-kerberos-lab:ticket:v1:` followed by the envelope kind. The kind/version are checked before decryption. Plaintext is canonical JSON:

```json
{"version":1,"kind":"tgt","ticket_id":"<32 hex>","client_id":"alice","service_id":"tgs","issued_at":1700000000,"not_before":1700000000,"expires_at":1700000300,"session_key":"<32 bytes base64>"}
```

All fields shown are required. Plaintext kind must match envelope kind. A TGT audience must be `tgs`; service tickets must name `files` in this one-service lab. `issued_at <= not_before < expires_at`. Session keys are independently generated, not long-term keys. The client receives its session key separately and cannot decrypt its ticket. Resource code must never load the TGS long-term key through the shared loader.

Production helper `seal_ticket` generates a fresh random 96-bit encryption nonce internally and accepts no caller-supplied nonce. V1 assumes bounded lab usage and negligible random-nonce collision probability; it does not claim collision-proof nonce allocation under unlimited use. Fixed encryption nonces are permitted only in explicitly public test vectors, with distinct role keys. Application replay nonces do not serve as encryption nonces.

## Authenticated requests

Authenticator exact keys:

```json
{"version":1,"client_id":"alice","service_id":"files","ticket_id":"<32 hex>","timestamp":1700000000,"request_nonce":"<32 hex>","method":"POST","path":"/access-resource","body_sha256":"<64 hex>","ticket_sha256":"<64 hex>","mac":"<32 bytes base64>"}
```

`body_sha256 = SHA256(canonical_bytes(body)).hexdigest()`; `ticket_sha256` hashes canonical bytes of the entire encrypted envelope. HMAC-SHA256 uses the corresponding session key over `domain + canonical_bytes(authenticator_without_mac)`. Domains are `b"ins-kerberos-lab:auth:v1:tgs\0"` and `b"ins-kerberos-lab:auth:v1:resource\0"`. The verifier chooses the domain from its endpoint, not an untrusted request field. Verify through the library's constant-time MAC operation.

TGS authenticators bind method `POST`, path `/service-ticket`, service `tgs`, the TGT, and body `{"service_id":"files"}`. Resource authenticators bind method `POST`, path `/access-resource`, service `files`, its service ticket and body `{"operation":"increment"}`. Identity/ticket/service fields must match decrypted credentials. No query string or alternate method/path is accepted. Derive the operation binding from the validated endpoint/body, never solely from authenticator claims.

The client stores the entire structured request or its canonical bytes to simulate interception. Replaying preserves the ticket, authenticator (including nonce/time/MAC), and body. Reformatting HTTP JSON whitespace alone does not create a fresh request. A legitimate second request reuses a valid ticket with a newly authenticated request nonce.

## HTTP messages

### Login

`POST /login` request: `{"username":"alice","password":"<local synthetic password>"}`.

Success HTTP 200:

```json
{"version":1,"tgt":{"version":1,"kind":"tgt","nonce":"...","ciphertext":"..."},"client_session":{"client_id":"alice","service_id":"tgs","ticket_id":"<TGT ID>","session_key":"<client/TGS key>","expires_at":1700000300}}
```

The username is the client ID. Login verifies a stored password verifier. This is plaintext credential/session-key delivery over loopback, an explicit educational simplification of Kerberos pre-authentication and protected key delivery. Never describe packet captures of this local login as a secure production exchange.

### Service ticket

`POST /service-ticket` request exact keys: `version` (1), `tgt` (envelope), `authenticator`, `body` (`{"service_id":"files"}`). Success HTTP 200 exact keys: `version`, `service_ticket`, `client_session`; the latter has the same five keys as login's client session, with `service_id="files"`, the service-ticket ID/key and its expiry. Require a valid client/TGS authenticator and consume it in the separate TGS replay store. Issue fresh session/ticket IDs after acceptance. Service-ticket expiry is `min(now + lifetime, tgt.expires_at)`; if it is not strictly after now, reject rather than issue an immediately expired ticket.

### Resource

`POST /access-resource` request exact keys: `version` (1), `service_ticket`, `authenticator`, `body` (`{"operation":"increment"}`). Success HTTP 200:

```json
{"version":1,"status":"granted","client_id":"alice","service_id":"files","request_nonce":"<request nonce>","operation":"increment","counter":1}
```

Success counter is a positive integer from the committed local store. Public errors have exactly `{"version":1,"error":"<code>"}`. Never return keys or full artifacts in resource responses/logs.

| HTTP | Error code | Conditions |
| --- | --- | --- |
| 400 | `malformed_request` | Invalid schema, encoding, size or value; unsupported version |
| 401 | `invalid_credentials` | Unknown login user or incorrect password; identical public response |
| 401 | `invalid_authentication` | Invalid ticket/MAC, wrong role/audience/identity/context, expired/not-yet-valid ticket or skew |
| 403 | `wrong_service` | Valid authenticated TGS request names an unsupported service; not a substitute for authenticating first |
| 409 | `replay_detected` | Duplicate authenticated request identity |
| 503 | `replay_state_unavailable` | Missing/corrupt/mismatched required store, capacity exhaustion, lock timeout or failed transaction |

Normalize framework JSON/content-type/oversize errors to 400 for these endpoints. Other routes/methods retain ordinary 404/405 behavior. Controlled private diagnostics can distinguish `bad_integrity`, `bad_context`, `ticket_not_yet_valid`, `ticket_expired`, `authenticator_skew`, `duplicate`, `capacity`, and `storage_error`; these reasons do not expose secrets in public responses. `/health` retains the existing shape during the scaffold; implemented apps return `{"status":"ok","role":"kdc|resource_server","stage":"implemented"}` after successful setup. Health is not a benchmark endpoint.

## Validation, time and state

Defaults: ticket lifetime 300 s; authenticator tolerance 30 s; ticket leeway equals that same tolerance; capacity 10,000 consumed records per store; SQLite busy timeout 5,000 ms. Capture verifier `now` once per validation. Acceptance requires both:

1. `ticket.not_before - skew <= now <= ticket.expires_at + skew`.
2. `abs(now - authenticator.timestamp) <= skew`.

All equalities are inclusive. A valid MAC and all identity/context checks are also required. Verify authentication before classifying time failures or touching replay state. Nonce tracking does not correct a wrong wall clock or remove ticket lifetime assumptions.

Resource modes share all validation and operation checks. `authenticator_no_cache` omits only consumption; `authenticator_cache` atomically consumes `(namespace, service_id, ticket_id, request_nonce)` with the counter increment. TGS always consumes requests regardless of resource mode. Cache duplicate detection has priority over capacity classification. Retain entries throughout a run: no automatic expiry/purge. At capacity, reject new identifiers; never evict an old one to accept traffic. Counter updates and consumed records roll back together on error. A response lost after commit does not provide result recovery/exactly-once semantics outside this local transaction.

Use a fresh explicit run directory for independent trials, but preserve it across restart segments. Stores are initialized explicitly; a server never silently creates a replacement. Every store operation opens an existing file in SQLite `mode=rw`, checks run/namespace/schema metadata, and fails closed on missing state. Use `BEGIN IMMEDIATE`, a uniqueness constraint and durable ordinary-process SQLite transactions. An ordinary process restart is not power-loss testing. Configuration changes and time injection are local process controls, not unauthenticated HTTP debug endpoints.

## Version/change control

V1 fixtures and signatures are the shared baseline for A02/A03. Any incompatible field, MAC input, boundary, storage or callable change requires a documented contract revision and refreshed fixtures/tests before G1 release. After G1, pause dependent interface work before an incompatible revision. A01 specifies behavior only; runtime and experiment claims require later checks.
