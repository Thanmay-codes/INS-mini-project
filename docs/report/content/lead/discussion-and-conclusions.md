# Discussion, Limitations, and Conclusions (Lead-Authored)

## Discussion of Core Replay Results (`a07-20261124`)

The reviewed G3 evidence (`results/published/a07-20261124/`) isolates the impact of persistent atomic replay tracking while holding ticket encryption, HMAC request authentication, context binding, and time validation constant:

- **Duplicate rejection vs. legitimate availability:** In the 30-trial E01–E03 comparison (300 HTTP attempts, 0 transport failures), `authenticator_no_cache` accepted **30/30** exact duplicate E02 requests, whereas `authenticator_cache` accepted **0/30** (`409 replay_detected`). Both modes recorded **0/90** rejections across legitimate E01 and E03 requests, confirming that per-request nonce tracking blocks replays without preventing legitimate reuse of a valid service ticket with fresh authenticators.
- **Concurrency and restart persistence:** Under E05 (2, 4, and 8 concurrent worker processes sharing one key and SQLite store), `authenticator_cache` committed exactly **1** protected operation (`counter_max = 1`) in every worker-count condition. Under E06 and E10, previously consumed requests remained rejected (`409`) after ordinary resource-process restarts and ±15-second logical-time shifts.
- **Fail-closed behavior and time boundaries:** Missing and corrupt replay stores (E09) returned `503 replay_state_unavailable` rather than bypassing protection. E07 (−60 to +60 s) and E08 (−31 to +331 s) matched the declared inclusive ±30-second skew and ticket-leeway rules.
- **Latency interpretation:** Descriptive p50/p95 request latencies (e.g., E01 cache `11.8839 / 13.9820` ms vs. no-cache `12.4544 / 14.5174` ms; E02 cache `3.9937 / 14.9442` ms) reflect fixed mode order, cold process starts, and mixed accept/409 responses in E02. They do not support a general speedup or production-throughput claim.

## Discussion of Optional Password-Guessing Extension (`a09-extension-20261124`)

In the A09-reviewed extension (`results/published/extension/`), both E11 and E12 used identical simulator parameters (`AES-256-GCM`, `PBKDF2-HMAC-SHA256`, 16-byte salt, `100,000` iterations, `data/wordlists/demo.txt` with 5 candidates, and budget 5):

- **E11 (`weak_in_list`):** Recovered in **4/5** attempts (`113.9911` ms), demonstrating that AES-GCM authenticated encryption does not prevent offline dictionary recovery when the service key is derived from a weak password.
- **E12 (`random_absent`):** Not recovered after **5/5** attempts (`165.0101` ms; `not_recovered_within_list_budget`). This illustrates that removing predictable words from the tested list defeats the bounded search, without claiming general "uncrackability."

## Limitations

1. **Educational simulator, not production Kerberos/AD:** Uses custom JSON/HTTP envelopes, loopback transport, AES-256-GCM, and PBKDF2-HMAC-SHA256 rather than Kerberos V5 ASN.1, RFC 3962 AES string-to-key, or Active Directory RC4/Event 4769 telemetry.
2. **Sample size:** Only E01–E03 have 30 repeated trials; E04–E10 and E11–E12 are single-run functional/mechanism demonstrations.
3. **Persistence and delivery scope:** SQLite `DELETE` journal + `synchronous=FULL` demonstrates ordinary process restart durability, not power-loss durability, hostile filesystem rollback resistance, or exactly-once response recovery if a response is lost after commit.
4. **Known minor conformance and platform items:** As documented in A06, the KDC login handler returns `401` rather than contract `400` on syntactically malformed usernames (not an auth bypass; scheduled for a minor B conformance fix). Native Windows process-lifecycle/ACL checks remain unverified.

## Conclusions and Future Work

A persistent, transactionally atomic replay store integrated with session-key-authenticated request nonces eliminates exact-duplicate acceptance (0/30 vs. 30/30) across single-process, multi-worker, and restart scenarios while preserving legitimate ticket reuse (0/90 rejections). At the same time, the bounded offline-guessing extension confirms that transport/ticket encryption alone cannot compensate for weak service credentials. Future work includes resolving the minor KDC username-schema `400` mapping, testing native Windows ACL/process lifecycles, adding a challenge-response or cache-expiry comparison, and benchmarking against a pinned MIT Kerberos (`krb5`) adapter.
