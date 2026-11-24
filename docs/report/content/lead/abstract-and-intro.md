# Abstract, Objectives, and Background (Lead-Authored)

## Working Title

**Simulation and Security Analysis of Kerberos-Style Ticket-Based Authentication: Replay Attack Mitigation and Kerberoasting Vulnerability Assessment**
*(Short title option if permitted by the venue: **Experimental Security Analysis of Kerberos-Style Ticket Authentication**.)*

## Abstract

Ticket-based network authentication separates initial user verification from subsequent service access, reducing repeated exposure of long-term user secrets. However, correctness depends on strict cryptographic binding, freshness checks, and stateful replay tracking. This paper presents an educational, single-host Python/Flask simulator implementing a Kerberos-style Authentication Server (AS), Ticket-Granting Server (TGS), CLI client, and protected resource server. Using identical AES-256-GCM tickets, HMAC-SHA-256 request authenticators, and logical clock controls, we compare an intentionally incomplete no-cache control (`authenticator_no_cache`) against a persistent atomic SQLite replay store (`authenticator_cache`) that records consumed request identities and increments a protected operation counter within a single transaction. Across 30 independent trials per condition (300 requests), the no-cache control accepted 30/30 exact duplicate requests while the persistent cache accepted 0/30, with 0/90 legitimate-request rejections in both modes. Functional smoke runs (46 attempts across E01–E10) further demonstrate single-operation serialization across 2, 4, and 8 concurrent worker processes, replay rejection across ordinary process restarts and ±15-second logical clock shifts, fail-closed `503` behavior on missing or corrupt stores, and expected inclusive ±30-second skew/leeway boundaries. An optional, bounded Kerberoasting-inspired offline verification experiment (E11–E12, PBKDF2-HMAC-SHA256 with AES-256-GCM) illustrates that authenticated encryption alone does not prevent recovery of a weak password present in a 5-word list (4/5 attempts), whereas a generated random password absent from that list is not recovered within the 5-attempt budget. We present these results as an evaluated student implementation and controlled local measurement study of established defenses, without claiming a new protocol, a new Kerberos vulnerability, or Active Directory interoperability.

## Objectives and Modest Contribution

1. **Reproducible educational implementation:** Build a modular, testable local ticket-authentication lab with explicit JSON/HTTP contracts, role-separated keys, and deterministic clock injection.
2. **Controlled replay-mitigation evaluation:** Isolate the effect of persistent atomic replay tracking by holding ticket format, MAC verification, body/endpoint binding, and time validation constant between `authenticator_no_cache` and `authenticator_cache`, and testing concurrency, ordinary restart, and missing/corrupt store states.
3. **Bounded offline password-guessing demonstration:** Illustrate why password strength and key derivation remain critical even when service tickets use authenticated encryption (AES-256-GCM).

**Contribution boundary:** Replay caching, session-key-authenticated nonces, and clock-skew bounds are established mechanisms specified in [RFC 4120 §3.2.3](https://www.rfc-editor.org/rfc/rfc4120.html#section-3.2.3) and tested in upstream implementations such as MIT Kerberos (`t_rcfile2.c`). This project's contribution is a reproducible student implementation and systematic local evaluation of those mechanisms, not a new cryptographic protocol or a previously unknown Kerberos flaw.

## Background and Related Work

- **Trusted third-party authentication:** Needham and Schroeder (1978) introduced trusted authentication servers, session-key distribution, and nonce-based challenge/response exchanges (`§4` explicitly uses nonces rather than relying purely on timestamps).
- **Kerberos replay and clock-skew limitations:** Bellovin and Merritt (1990; expanded Winter USENIX 1991) analyzed replay-cache implementation challenges, unauthenticated time-service risks, and offline password-guessing attacks against password-derived ciphertexts. Davis, Geer, and Ts'o (1996) further examined clock-drift handling in Kerberos.
- **Identity-attack taxonomy and Kerberoasting context:** Pöhn and Hommel (2023) provide a taxonomy of identity-management attacks for background classification (though it does not evaluate Kerberoasting mechanics). Microsoft's Kerberoasting guidance (2024) and MITRE ATT&CK T1558.003 note that AES encryption alone does not protect weak service-account passwords against offline guessing, and that TGS requests can generate observable controller telemetry (e.g., Windows Event 4769) while subsequent offline guessing generates none.
