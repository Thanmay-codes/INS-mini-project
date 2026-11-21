# Scope for the college conference

This records the college-conference scope decision. For execution, use [the detailed implementation plan](implementation-plan.md) and [the current four-person assignment](team-work.md); they supersede the earlier two-person work split below.

## Context and recommendation

The user clarified that this is a small college conference, the topic has already been submitted, and a four-person team realistically has two active contributors. Keep the existing Kerberos-style authentication/security topic. Refine the implementation and evaluation within that topic rather than proposing a different subject.

The earlier `docs/proposal.md` is a mini-project foundation. A modest student paper can build on it by defining one focused implementation contribution and a systematic evaluation. This is a feasibility recommendation; the conference/professors' actual assessment criteria have not been provided. No claim of a new cryptographic protocol, new Kerberos vulnerability, or verified literature gap is justified.

## Recommended additional feature

Implement **persistent, concurrency-safe replay protection** for authenticated requests in the simulator.

1. Each request carries a session-key-authenticated nonce, ticket/service identity, timestamp, and operation binding. The application request nonce is distinct from the cipher's encryption nonce.
2. The defended server validates the ticket and authenticator, then uses an atomic SQLite transaction/unique constraint to record the consumed request identity before accepting it. Duplicate concurrent requests must not both pass duplicate checking.
3. Replay state survives an ordinary service-process restart. State retention and expiry rules are explicit. Missing/corrupt state must trigger a documented fail-closed recovery policy rather than silently accepting old requests.
4. Instrument a local protected operation and the authentication decision separately. Do not claim general exactly-once business execution from atomic replay tracking: a crash between recording acceptance and executing an operation is a separate application-level issue.

The individual mechanisms are established. The intended student-paper contribution is the integrated implementation and measured analysis of its security/availability behavior under a specified fault model. RFC 4120 already addresses [replay state and cache loss](https://www.rfc-editor.org/rfc/rfc4120.html#section-3.2.3), and MIT already has [expiry, multiprocess, and race tests](https://raw.githubusercontent.com/krb5/krb5/master/src/lib/krb5/rcache/t_rcfile2.c). Neither persistence nor concurrency testing should be described as a newly invented defense.

## Small evaluation

Use `authenticator_no_cache` and `authenticator_cache` as the main controlled comparison: the same ticket/authenticator checks, keys, request bytes, and time settings; only duplicate tracking changes. A ticket-only demonstration is optional background, not the sole control.

| Scenario | What to measure |
| --- | --- |
| Normal valid request | Acceptance and latency |
| Exact captured duplicate | Duplicate acceptance/rejection |
| Fresh request using same valid ticket | Unnecessary legitimate rejection |
| Concurrent copies | Number accepted and operation count |
| Service-process restart followed by replay | Whether consumed replay state is retained |
| Clock offsets inside/outside tolerance | Legitimate rejection and exact reason |
| Ticket/authenticator validity boundaries | Stated freshness and expiry policy |

Report request counts, duplicate acceptance fraction, legitimate rejection fraction, latency distributions, and experiment configuration. A process restart is not a machine power failure. Simulated clock offsets are not a demonstrated NTP exploit. A clock-based validity policy still needs its stated time assumptions, even when nonces are present.

## Kerberoasting extension

Keep it small and secondary: one synthetic service, one weak password, one generated random password, one fixed candidate list, and identical cipher/KDF settings. Measure attempts, runtime, and bounded recovery outcome. Describe the mechanism as Kerberoasting-inspired unless using actual Kerberos formats and key derivation. Do not claim a small dictionary miss proves password strength in general. See [Microsoft's technical guidance](https://www.microsoft.com/en-us/security/blog/2024/10/11/microsofts-guidance-to-help-mitigate-kerberoasting/).

## Two-person work split

- Contributor 1: KDC/client flow, ticket encryption/validation, and authenticated request format.
- Contributor 2: replay-cache implementation, scenario runner, and measurement export.
- Together: integration, interpretation, reference checking, report, and demonstration. Complete the replay study before the password-guessing extension.

## Accurate explanation for professors

“We are retaining the submitted Kerberos-style authentication topic. Our paper will evaluate a persistent, concurrency-safe replay-defense implementation using normal requests, captured duplicates, server restarts, concurrent requests, and controlled clock offsets. We will compare it with the same authenticated request flow without replay tracking and report security outcomes and performance overhead. A small synthetic service-password guessing experiment will illustrate Kerberoasting risks. We are evaluating established mechanisms in our simulator, rather than claiming a new flaw in Kerberos.”

## Publication boundary

This is a reasonable scope to present to the professors for a student implementation/evaluation paper. If the venue specifically requires a new algorithm or a previously unreported technical finding, this scope does not establish that requirement. A larger cross-layer fault-injection benchmark with validation against real MIT Kerberos is a possible later research direction, described in `docs/references/conference-extension-research.md`; it is not mandatory for the stated two-person college scope.
