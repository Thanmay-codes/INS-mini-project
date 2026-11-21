# Detailed implementation plan

Execution instructions and per-file ownership are in [the workflow](workflow/README.md) and [the task prompt index](prompts/README.md). They refine the broad component assignments below; implementation gates remain unreleased until actual code/checks pass.

## 1. Objective and boundaries

Retain the submitted topic: **Simulation and Security Analysis of Kerberos-Style Ticket-Based Authentication: Replay Attack Mitigation and Kerberoasting Vulnerability Assessment**. A shorter manuscript title can be chosen later if the professors allow it.

Deliver a reproducible student security study with two parts:

1. Core: authenticated ticket access, an intentionally incomplete no-replay-cache control, and a persistent atomic replay defense. Evaluate duplicates, legitimate reuse, concurrency, ordinary process restart, clock offsets, and validity boundaries.
2. Extension: bounded offline dictionary guessing against synthetic service tickets with weak versus generated random service passwords.

Use library cryptography and a custom educational message format. The paper describes this as Kerberos-style, with the extension described as Kerberoasting-inspired. The established techniques and publication limits are documented in [the validity audit](references/validity-research.md) and [related-work check](references/conference-extension-research.md).

The minimum build uses one local machine, one synthetic user, one service, two Flask applications, and a CLI. A dashboard, NTP exploitation, real AD deployment, RC4 implementation, ML detector, distributed cache, and novel cryptographic protocol are outside this build. Server challenge-response and a real MIT Kerberos adapter remain possible future work.

## 2. Architecture

```text
CLI client
  | POST /login: synthetic username + password
  v
KDC process / AS role ------------------------------ port 5000
  | returns TGT + client/TGS session key
  | POST /service-ticket: TGT + authenticated service request
  v
KDC process / TGS role
  | returns service ticket + client/service session key
  | POST /access-resource: service ticket + authenticated operation
  v
Resource process ---------------------------------- port 5001
  | validates identity, integrity, audience, times, operation binding
  | optionally consumes request identity in persistent replay cache
  v
SQLite-backed demo operation + structured outcome
```

Both applications bind to `127.0.0.1`. For concurrency tests, separate resource-worker processes bind to separate loopback ports while sharing the same service identity/key and replay database. Use a single-host shared SQLite store; this is not a network-distributed database experiment.

Passwords/session keys delivered through the local JSON login are a simulator simplification. Real Kerberos pre-authentication, transport protection, ASN.1 ticket encoding, and encryption profiles are not implemented. The report must state this.

## 3. Components and file ownership

Names below are planned modules, not features already implemented. The precise four-person assignment is in [team-work.md](team-work.md).

| Component | Planned location | Primary owner |
| --- | --- | --- |
| Types, validation, canonical serialization | `src/kerberos_lab/common/models.py` | A: user |
| Ticket encryption and request authentication | `src/kerberos_lab/common/crypto.py` | A |
| Wall-clock injection and configuration | `src/kerberos_lab/common/clock.py`, `settings.py` | A |
| Persistent atomic replay state | `src/kerberos_lab/common/replay_cache.py` | A |
| Resource validation and demo operation | `src/kerberos_lab/resource_server/` | A |
| Synthetic fixture/key initialization | `scripts/init_demo.py` | A |
| AS login and TGS issuance | `src/kerberos_lab/kdc/` | B: active contributor |
| Normal client journey | `src/kerberos_lab/client/` | B |
| Scenario runners and CSV export | `experiments/replay/` | B, reviewed by A |
| Offline guessing extension | `experiments/kerberoasting/` | B, reviewed by A |
| Analysis/plots from reviewed measurements | `experiments/analysis/` | B, interpreted with A |
| Diagrams and presentation | `docs/diagrams/`, `docs/presentation/` | C: support |
| Formatting, reference metadata, packaging | `docs/report/`, setup documentation | D: support |

## 4. Keys, tickets, and authenticators

Generate all demonstration secrets locally into ignored `data/private/`. Use distinct long-term keys for the TGS and resource service, and fresh session keys for client/TGS and client/service relationships. Store only a password verifier for the login user. Use the library's password-KDF API; A records its chosen parameters and verifies the implementation before B integrates it.

Tickets use library AES-GCM with correct per-key encryption-nonce handling. The application request nonce and encryption nonce have different purposes. AES-GCM is the simulator's choice, not a claim to implement a Kerberos encryption type.

| Object | Required fields/semantics |
| --- | --- |
| Encrypted envelope | Version, ticket kind, encoded encryption nonce, authenticated ciphertext; reject unsupported versions/kinds and malformed encodings |
| TGT plaintext | Ticket ID, client ID, audience `tgs`, issued/not-before/expiry times, client/TGS session key |
| Service-ticket plaintext | Ticket ID, client ID, requested service ID, issued/not-before/expiry times, client/service session key |
| Authenticated request | Client/service/ticket IDs, timestamp, fresh random request nonce, HTTP method, logical operation/path, body digest, authentication tag |

Use canonical serialized bytes and a library MAC such as HMAC-SHA256 for request authentication. Bind the ticket identity, service, operation and body; separate TGS and resource contexts with explicit labels. The service ticket remains opaque to the client; deliver the client's corresponding session key separately through the simulator's authenticated exchanges.

Validate types, sizes, required fields and encodings before use. Define a request-size limit. Return stable error codes without disclosing secrets or detailed decryption failures. Log request IDs/outcomes rather than passwords, keys or complete tickets.

## 5. API contract

Only `/health` exists now. The other endpoints are planned.

| Endpoint | Input/output | Invalid outcome |
| --- | --- | --- |
| KDC `GET /health` | Existing scaffold health response | Service unavailable |
| KDC `POST /login` | Credentials → TGT and client/TGS session material | `401 invalid_credentials` |
| KDC `POST /service-ticket` | TGT + authenticated service request → service ticket and client/service session material | Invalid TGT, authenticator, freshness or requested service rejected |
| Resource `GET /health` | Existing health response | Service unavailable |
| Resource `POST /access-resource` | Service ticket + authenticated demo operation → granted resource and operation result | Invalid credentials/context/time rejected; duplicate returns `409 replay_detected` |

Use `400 malformed_request`, `401 invalid_authentication`, `403 wrong_service` where it does not expose sensitive validation details, `409 replay_detected`, and `503 replay_state_unavailable` as the draft contract. Freeze exact JSON shapes and HTTP mappings during M1, before parallel implementation. Controlled test logs may record more precise time-validation reasons than the public response.

The TGS uses its own validation/replay namespace. The intentionally incomplete switch applies only to the resource-server study; TGS behavior remains unchanged between resource experiment modes.

## 6. Replay defense and protected operation

The main modes are:

- `authenticator_no_cache`: verify the ticket and session-key-authenticated request, including audience, operation and time checks, but omit duplicate tracking. Label it intentionally incomplete.
- `authenticator_cache`: perform the same validation and atomically consume the authenticated request identity in SQLite.

Use a uniqueness constraint scoped to service, ticket, and request nonce. Use separate database connections per process and an explicit transaction. Distinguish duplicate conflicts from locks, corruption and other storage failures; storage failures reject access rather than disable protection.

Use a SQLite-backed counter as the small observable protected operation. In defended mode, record request consumption and the counter update in the same transaction. Count authentication decisions and committed operations separately. This allows a precise local transaction claim; it does not establish exactly-once behavior for external services or arbitrary side effects. A crash after commit but before a response can leave the client uncertain; replay rejection is not automatic response recovery.

Initialize replay stores explicitly in `init_demo.py`. A normal server start opens an existing initialized store. Missing or corrupt required state produces a clear startup/access failure. Reset state only through an explicit lab setup/reset operation; never silently recreate it after restart during an experiment.

For the small core experiments, retain replay entries for the full run and impose a documented capacity limit that rejects excess work. Do not implement automatic wall-clock-based cache purging initially: it would add rollback/retention complexity without helping this bounded lab. Use a fresh isolated run directory between independent trials; preserve it across the restart phase of the same trial. Cache-expiry optimization is future work.

## 7. Time model

Use an injected clock with per-role offsets; never modify host time or NTP. Measure elapsed duration with a monotonic timer.

Proposed defaults for configuration, finalized in M1: ticket lifetime 300 seconds and allowed skew 30 seconds. State the exact boundary rule: accept an authenticator when its timestamp differs from service time by at most the tolerance, and accept a ticket inside its explicitly configured not-before/expiry allowance. Record that ticket leeway, including whether boundaries are inclusive. Include exact-boundary tests so implementation and paper agree.

Nonce replay tracking does not eliminate ticket-time assumptions. A clock offset may cause rejection rather than successful replay. Record server time, authenticator time, ticket bounds and rejection reason separately. With all replay entries retained during a run, rollback must not cause a previously consumed request identity to be forgotten.

## 8. Experiments and evidence

For the main causal comparison, freeze keys, ticket, authenticator, request body, timestamp policy and workload; change only replay tracking. Each mode begins in an equivalent clean initial state. Fresh legitimate requests use fresh authenticated nonces. Use a common logical clock in deterministic tests and an actual local process setup for process/concurrency measurements.

| ID | Scenario | Required observation |
| --- | --- | --- |
| E01 | Valid initial request | Both modes accept |
| E02 | Exact duplicate while otherwise valid | No-cache control accepts; defended mode rejects |
| E03 | Same valid ticket, fresh authenticated request | Both modes accept |
| E04 | Modified ticket/authenticator/body, wrong service | Validation rejects |
| E05 | 2, 4, 8 concurrent copies | Defended mode commits at most one protected operation |
| E06 | Restart resource process, replay original | Defended mode retains consumed state and rejects |
| E07 | Offsets -60, -15, 0, +15, +60 seconds | Report acceptance and precise time-check outcomes |
| E08 | Just before/at/after validity boundaries | Matches the specified tolerance/expiry rules |
| E09 | Required replay database missing/corrupt | Service rejects/fails clearly; protection is not bypassed |
| E10 | Forward/backward simulated time with a consumed request | No forgetting of consumed identity during retained-state run |
| E11 | Weak service password, fixed dictionary | Recover when the candidate is present |
| E12 | Random service password, same dictionary/KDF/budget | Report actual bounded recovery outcome |

Start performance measurements with 30 independent trials per selected condition, reporting the denominator and run-to-run variation. Use the same machine and load schedule, record versions and configuration, and separate startup time from request latency. Increase sample count only if needed for stable estimates. Deterministic functional checks do not need repetition merely to inflate the sample size.

The runner generates request-level JSONL plus summary CSV. Record run/trial IDs, mode, scenario, offsets, worker count, ticket lifetime, skew/leeway, decision/reason, latency, operation count, and relevant KDF/guess-budget fields for the extension. Save environment/configuration with each run. Do not write session keys or complete tickets into publishable results.

Primary measures: duplicate acceptance fraction, legitimate-request rejection fraction, committed operation count, restart replay outcome. Secondary measures: p50/p95 latency, throughput where meaningful, and replay-store size. Offline measures: guesses attempted, elapsed time and recovery outcome within budget.

Raw outputs stay ignored under `results/raw/`. A and B review reproducibility and interpretation, then export selected sanitized evidence into tracked `results/published/`. Only approved numbers flow into paper tables/figures; C and D do not edit measurement values.

## 9. Synthetic password-guessing extension

After the core, issue a synthetic service ticket under a password-derived service key. Keep AES mode, KDF, salt/work factor, candidate list and budget fixed between password cases. Record all non-secret parameters. Verify candidates by authenticated decryption and count every attempted candidate.

Use the bundled tiny demonstration list. A weak password deliberately present in it and a generated random password absent from it illustrate dictionary coverage; they do not establish population-wide password strength. Label failures as not recovered from this list within this budget. Keep ticket acquisition and offline guessing separate in the demo/logs. Do not call simulator events Windows event 4769 or claim actual AD cracking performance.

## 10. Milestones and completion gates

There is no supplied deadline, so milestones specify order rather than calendar promises.

| Milestone | Work | Done when |
| --- | --- | --- |
| M0: preparation | Folders, plan, ownership, local environment, Git handoff | Documents agree on scope; current health starters run |
| M1: contracts/shared core | Schemas, config/time model, crypto, local setup, safe fixtures | Round-trip/tampering/type/boundary checks pass; A and B agree on request/response fixtures |
| M2: normal flow | AS login → TGT → TGS → service ticket → protected operation | One client completes the flow; bad credentials, wrong audiences and altered artifacts fail |
| M3: replay defense | No-cache control, SQLite atomic consumption, persistent operation | Duplicate, fresh reuse, concurrent copies, missing-state and restart checks pass |
| M4: core evaluation | Clock matrix, repeatable runner, CSV/JSONL, reviewed plots | E01–E10 run reproducibly; A and B approve evidence and limitations |
| M5: extension | Bounded local offline guessing | E11–E12 produce documented actual results, or are explicitly marked future work if time is tight |
| M6: paper/demo | Method/results/discussion, checked references, figures, slides | Claims match code/evidence; fresh setup/demo rehearsal succeeds; professor format requirements applied |

M1 precedes independently integrated protocol work. C and D can work on support artifacts from M0 without blocking M1–M5. A reviews scientific claims, security-critical changes and evidence before integration. If time is short, complete M4 and the paper before expanding M5.

## 11. Paper and demo deliverables

Keep the original topic, with a precise implementation/evaluation contribution: persistent atomic request-replay tracking and measured behavior in a declared local failure/time model. Cite established defenses. The manuscript includes architecture/threat model, implementation, experiment design, measured results, limitations, conclusion, and references.

Required reproducibility bundle: installation steps, dependency snapshot, non-secret configuration/fixtures, experiment commands, sanitized reviewed results, figure-generation instructions, and environment information. Add a short demo of normal access, repeat acceptance in the incomplete mode, rejection in defended mode, concurrent/restart results, and the optional password experiment.

Use `docs/report/manuscript/` for paper source once the conference template is known, `docs/report/assets/` for approved manuscript exports, and `docs/presentation/` for slides/demo notes. A and B write methods, results and conclusions. C and D handle supporting exposition/formatting under review.

## 12. Final completion checklist

- All core acceptance gates M1–M4 pass with meaningful automated checks.
- Shared-store resource workers and ordinary restart experiments are demonstrated.
- Scientific results are actual outputs, with seeds/configuration/environment and denominators.
- No-cache and defended comparisons change only the intended defense variable.
- The paper labels simulated transport, crypto format, time assumptions and bounded wordlist honestly.
- Secrets/private tickets/databases/logs are excluded from Git; reviewed sanitized evidence is explicitly selected.
- The user handles credential-requiring Git commands and final repository publication.
- Final report, demo and team ownership records reflect completed work.
