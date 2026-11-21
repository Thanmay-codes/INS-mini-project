# Experiment plan

These are planned scenarios, not measured results. Keep scenario configuration and runners here; store generated output under `results/`.

The main controlled comparison is `authenticator_no_cache` versus `authenticator_cache`, with identical tickets, authenticated requests, clock checks, and request binding. The ticket-only scenarios below are optional teaching demonstrations. Compare cache behavior without changing proof-of-possession requirements at the same time.

| Scenario | Mode/change | Expected observation |
| --- | --- | --- |
| Normal access | Valid credentials and ticket | Access accepted |
| Invalid ticket | Modify encrypted ticket | Integrity validation rejects it |
| Valid-ticket replay | Ticket-only baseline, zero skew | Original and copy accepted |
| Expired-ticket control | Ticket-only baseline, zero skew | Expired ticket rejected |
| Expired ticket with skew | Same ticket, RS clock behind | May be accepted within the induced validity window |
| Defended replay | Replay identical authenticated request | Original accepted; duplicate rejected |
| No-cache replay control | Same authenticated request, cache disabled | Original and duplicate accepted within freshness and lifetime bounds |
| Legitimate ticket reuse | Same ticket, fresh authenticated request | Accepted while valid |
| Defended expired ticket | Accurate clock and expired ticket | Rejected regardless of request freshness |
| Concurrent duplicate | Two copies at the same time | At most one accepted |
| Restart replay | Restart server between original and replay | No replay window caused by lost cache state |
| Weak service password | Offline dictionary, fixed KDF | Recovered if candidate is in the list |
| Random service password | Same dictionary, cipher, KDF, and budget | Report whether recovered within budget |

Use a fake/injected clock rather than waiting for expiry or changing the operating-system clock. Use `time.perf_counter()` for elapsed durations. Keep candidate order and KDF work factor fixed when comparing passwords; change one variable at a time.

Evaluate clock offsets inside and outside the configured tolerance. A delayed or expired request is not guaranteed to pass under skew: both ticket validity and authenticator freshness must be satisfied. State whether ticket expiry includes leeway; RFC 4120 permits skew around ticket validity boundaries. Count protected-operation executions as well as response statuses.

For replay, acceptance/rejection and false rejection of legitimate requests are the primary measures. Latency is secondary. For offline guessing, record guesses attempted, guesses per second, elapsed time, recovery outcome, and budget. Repeat measurements and summarize their variation; distinguish measured outcomes from expected outcomes.
