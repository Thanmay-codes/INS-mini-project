# Recommended academic project proposal

**Conference-paper clarification:** This document scopes an implementation-based mini project. It does not establish a novel technical contribution by itself. After the user clarified the small college-conference setting and two active contributors, the practical recommendation is to keep the submitted topic and use `docs/college-conference-plan.md`. Broader publication-oriented related work is in `docs/references/conference-extension-research.md`.

**Title:** Experimental Security Analysis of Kerberos-Style Ticket Authentication

**Decision:** Proceed with the existing idea as a small implementation and experimental evaluation. Revise its claims; a replacement topic is unnecessary. The recommendation below is an engineering assessment of scope, not a guarantee of approval under an unknown college rubric.

## Short proposal for submission

This project develops a simplified Kerberos-style authentication simulator using a Key Distribution Center with Authentication Server and Ticket-Granting Server roles, a resource server, and a client. It experimentally evaluates replay acceptance when request replay tracking is omitted and when it is enabled. Controlled clock offsets are used to examine authentication freshness and availability. A small extension demonstrates offline dictionary guessing against synthetic service tickets derived from weak and randomly generated service passwords. The project records authentication outcomes, legitimate-request rejection, and offline guessing effort under fixed configurations. Its contribution is a reproducible educational implementation and controlled evaluation of established security mechanisms, with explicit differences from real Kerberos and Active Directory.

## Research questions

1. When ticket encryption and session-key proof remain unchanged, how does enabling a replay cache change acceptance of a captured authentication request?
2. How do controlled clock offsets affect legitimate authentication and duplicate-request rejection under a specified skew tolerance?
3. In a small synthetic service-ticket demonstration, which passwords are recovered from a fixed candidate list under the same encryption, KDF parameters, and guessing budget?

These questions evaluate known mechanisms. They do not propose a previously unknown Kerberos flaw, a new nonce protocol, or a proof of cryptographic security. RFC 4120 already describes authenticators, tolerated clock skew, and replay defenses in [section 3.2.3](https://www.rfc-editor.org/rfc/rfc4120.html#section-3.2.3). Microsoft's [Kerberoasting guidance](https://www.microsoft.com/en-us/security/blog/2024/10/11/microsofts-guidance-to-help-mitigate-kerberoasting/) explicitly discusses weak service passwords, offline guessing, and AES limitations.

## Smallest useful implementation

- Two Flask processes: KDC on loopback port 5000, resource server on loopback port 5001.
- One client, one synthetic user, and one service; no Active Directory setup.
- TGT and service ticket with separate role keys and explicit validity intervals.
- Library authenticated encryption for tickets and session-key-authenticated requests. The simulator uses its own message format and does not claim Kerberos interoperability.
- An injectable clock, so offsets and expiry can be tested without changing the computer's clock.
- An atomic replay cache with a documented persistence and retention policy.
- A command-line runner exporting actual observations to CSV.
- A short offline dictionary extension using only generated local artifacts.

No dashboard, NTP exploitation, legacy RC4 implementation, enterprise deployment, or new cryptographic primitive is needed.

## Main replay comparison

Use two modes with the same ticket checks, authenticated request, session key, service identity, request binding, and timestamp tolerance:

For this Kerberos-style simulator, the authenticator may contain an authenticated per-request random nonce alongside its timestamp. The nonce must be bound to the ticket, service, and operation, and checked against consumed replay state. It is separate from the encryption nonce. This keeps the original nonce idea while accurately identifying duplicate tracking as an established defense; it does not reproduce the exact RFC authenticator format.

| Mode | Replay state | Purpose |
| --- | --- | --- |
| `authenticator_no_cache` | No duplicate tracking | Intentionally incomplete control |
| `authenticator_cache` | Atomic duplicate tracking | Defended comparison |

Capture the entire ticket-plus-authenticator request, send it once, and replay exactly that request. Keep the ticket, authenticated bytes, clock settings, and resource operation identical between modes. Initialize equivalent clean state for each trial. This isolates replay tracking rather than simultaneously adding proof of key possession and duplicate detection.

An optional ticket-only mode may explain why encryption alone is insufficient, but it is not the main experimental control. A nonce placed once inside a ticket and marked used would instead make the ticket single-use. It should not be presented as normal Kerberos ticket reuse.

## Minimum experiment matrix

1. Valid initial authenticated request in both modes.
2. Exact duplicate within the validity window in both modes.
3. Same ticket with a fresh authenticated request in both modes.
4. Tampered ticket and tampered authenticator rejection.
5. Legitimate requests with zero offset, offsets within tolerance, and offsets outside tolerance.
6. Ticket lifetime boundary checks, with the simulator's expiry/leeway rule stated explicitly.
7. Two concurrent copies in defended mode: at most one executes the protected operation.
8. Replay after resource-server restart: check persistent replay state or documented fail-closed recovery.

For skew tests, record both the client and server times, ticket bounds, authenticator time, and exact rejection reason. Do not assume every lagging clock makes a request pass: authenticator freshness and ticket validity are separate checks. Challenge-response can reduce clock agreement requirements for request freshness, but does not automatically correct lifetime decisions. It is optional future work for this small project.

Report accepted originals, accepted duplicates, rejected legitimate requests, and latency. Define a duplicate as the same authenticated request; obtaining a fresh ticket or generating a fresh authenticator is a different event. A protected operation should have an observable execution count, so the study measures repeated execution rather than relying only on HTTP status codes.

## Bounded service-password extension

Generate a synthetic service ticket under a password-derived key. Verify guesses by authenticated decryption using the same library cipher and KDF for all password cases. Demonstrate one weak password present in the tiny wordlist and one generated random password not present in it.

This intentionally constructed comparison illustrates dictionary coverage and service-secret selection. It does not estimate the entropy of all human passwords, prove the random password uncrackable, or establish real AD cracking speed. Changing both the password and encryption type in the same comparison would confound the result.

Record candidate order, attempts, elapsed time, KDF/salt/work factor, and the stopping rule. Report unsuccessful recovery as “not recovered from this candidate set within this budget.” Separate ticket acquisition logs from offline guessing; the latter does not require service login requests, while acquisition can be observable in AD. See Microsoft's [event 4769 documentation](https://learn.microsoft.com/en-us/previous-versions/windows/it-pro/windows-10/security/threat-protection/auditing/event-4769).

## Academic contribution and fallback

The deliverable is source code, a reproducible experiment runner, measured before/after tables, and a report explaining which assumptions cause each outcome. Reproduction and controlled evaluation are the intended contribution. A requirement for a novel algorithm or publishable protocol result would need a different scope; novelty has not been established here.

If the project must be smaller, keep only research questions 1 and 2 and use the title **Replay Protection and Clock-Skew Evaluation in a Kerberos-Style Simulator**. That still gives a complete implementation → experiment → mitigation → retest academic project. Service-password guessing can remain future work.
