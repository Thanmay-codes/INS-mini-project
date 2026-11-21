# Architecture and implementation boundaries

This is a background overview. The current module contracts, replay retention policy, time model and completion gates are specified in [the implementation plan](implementation-plan.md), which takes precedence if this overview differs.

## Two processes, three authentication roles

Keep two Flask processes. The first is a Key Distribution Center (KDC) containing AS and TGS roles; the second is the Resource/Service Server (RS). This adds a meaningful service-ticket flow without requiring three servers.

Planned application-level flow (not the Kerberos wire protocol):

```text
Client -- POST /login -------------> KDC / AS
       <- TGT + client/TGS key -----
Client -- POST /service-ticket ----> KDC / TGS
       <- service ticket + key -----
Client -- POST /access-resource ---> Resource server
       <- protected resource -------
```

Only `GET /health` exists in the starter. Authentication endpoints above are planned.

## Ticket and key ownership

The TGT is encrypted under a KDC-only TGS key. The resource server cannot decrypt it. The service ticket is encrypted under that service's long-term key, known by the KDC and the service. It carries the client identity, service identity, validity interval, a ticket identifier, and the client/service session key. The client receives its session key separately through the authenticated login/TGS exchange; it does not decrypt its service ticket.

Use separate keys for separate roles. Do not log passwords or session keys. The Flask JSON login over loopback is an educational simplification of Kerberos pre-authentication and transport behavior. Document it in the report.

## Planned replay modes

1. `ticket_only`: intentionally incomplete bearer-ticket baseline that checks integrity, service identity, and lifetime, but lacks proof of session-key possession and replay protection. Label this clearly in every result.
2. `authenticator_no_cache`: session-key-authenticated requests bound to the ticket, target service, and request context, with freshness checks but no duplicate tracking. This is the main intentionally incomplete experimental control.
3. `authenticator_cache`: use the identical authenticated request and validation rules, adding an atomic replay-cache insert. Legitimate clients can reuse a ticket with fresh authenticators; captured duplicate requests are rejected while replay state is retained correctly.
4. `challenge_response` (optional future work): the server issues a random single-use challenge; the client proves possession of the session key over the challenge, service identity, ticket ID, and request context. Consume the challenge atomically and expire it. This reduces dependence on client/server clock agreement for request freshness while retaining ticket lifetime checks.

The recommended small study compares modes 2 and 3 to isolate the replay cache. Mode 1 is an optional introductory demonstration; mode 4 is outside the minimum scope. See `docs/proposal.md` for the experimental controls.

A single nonce inside a ticket plus a used-ticket set instead makes the whole ticket single-use. It can be a small additional comparison, but changes normal ticket reuse semantics. Random values alone do not prevent replay: they must be authenticated, checked, and consumed.

The challenge nonce and the AES-GCM encryption nonce have different jobs. AES-GCM nonces must be unique per encryption key; they are not the application's replay cache.

## Shared components to implement next

- `common/crypto.py`: authenticated encryption using the cryptography library; no hand-written ciphers. AES-GCM is a simulation choice, not an implementation of Kerberos encryption types.
- `common/tickets.py`: explicit ticket types and input validation.
- `common/clock.py`: injectable wall clock and configurable per-role offset; never change the host clock or NTP settings. Use a monotonic clock to measure elapsed time.
- `common/replay_cache.py`: atomic check-and-record with expiry and documented restart behavior. Start with SQLite for persistence; assess multiple-worker behavior before claiming replay safety.
- Local demo identities and service secrets in ignored `data/private/`, generated during a later setup milestone. No generated secrets are needed for this scaffold.

## Kerberoasting extension boundary

Issue a synthetic service ticket encrypted under a password-derived service key, and guess only from the bundled tiny wordlist against that local artifact. Compare weak and generated random service passwords with the same cipher and KDF first. Record KDF algorithm, salt, work factor, candidate count, hardware, and budget.

The offline script should need no network requests after ticket acquisition. Record ticket-issuance events separately to explain where detection is possible. Do not describe custom AES-GCM/PBKDF2 results as Active Directory RC4/AES cracking benchmarks. A real Kerberos encryption-type comparison is optional and requires its own accurate implementation and validation.
