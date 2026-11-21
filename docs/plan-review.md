# Plan review and recommended direction

Follow-up primary-source validation is recorded in `docs/references/validity-research.md`. The resulting scope and controlled experiment design are in `docs/proposal.md`.

The project has a clear college-demo structure: working login flow, a visible failure, a defense, and repeatable measurements. Keep replay protection as the core deliverable and add offline service-password guessing after the core works.

## Correct the research framing

Describe these as **educational investigation questions and implementation risks**, rather than newly discovered research gaps. Nonces, challenge-response, and replay caches are established techniques. A defensible contribution is a controlled, reproducible comparison with explicit assumptions.

Suggested question 1: How do simulated clock offsets and missing or lost replay state affect acceptance of captured authentication requests, and how do replay caching and challenge-response change those outcomes?

Suggested question 2: Under a fixed offline guessing budget, how does service-account password strength affect recovery of passwords from synthetic encrypted service tickets?

## Technical corrections to carry into the report

- The 1978 Needham–Schroeder symmetric-key protocol uses nonces; do not say it relies entirely on timestamps. Timestamp-based revisions and Kerberos should be discussed separately. See the [Cornell key-establishment notes](https://www.cs.cornell.edu/courses/cs5430/2017sp/l/10-key-estab/notes.html) and verify the original paper before quoting it.
- Real Kerberos combines tickets with authenticators and replay protection; a reusable bearer ticket with only an expiry check is an intentionally incomplete baseline. Kerberos permits bounded clock skew rather than requiring perfect synchronization. See [RFC 4120, section 3.2.3](https://www.rfc-editor.org/rfc/rfc4120.html#section-3.2.3).
- Separate two effects: a still-valid bearer ticket can be replayed even with synchronized clocks; a server clock behind real time can additionally accept an actually expired ticket. Moving a clock ahead may instead reject legitimate requests. Simulated skew is not evidence of a successful real NTP compromise.
- A ticket sent directly to the resource server is a service ticket. A TGT is presented to the TGS. The proposed KDC layout keeps these names and roles distinct.
- A nonce in a ticket only prevents replay when authenticated state tracks consumption. Marking the ticket used makes it single-use. For reusable tickets, protect individual requests using authenticators/replay caching or server challenge-response.
- AES reduces practical guessing efficiency in real Kerberos compared with legacy RC4, but weak passwords remain a risk. Prioritize strong random managed service passwords and explain KDF differences. See [Microsoft's mitigation guidance](https://www.microsoft.com/en-us/security/blog/2024/10/11/microsofts-guidance-to-help-mitigate-kerberoasting/).
- Offline password guessing does not submit login attempts to the service. Ticket acquisition can still produce observable events: Microsoft documents event 4769 monitoring. Replace “undetectable” and “without triggering network alarms” with a narrower statement about the offline phase.
- A finite dictionary failing to recover a random password establishes “not recovered within this candidate set and budget,” not proof of uncrackability.
- Keep the identity-taxonomy paper as contextual reading; use the protocol RFC and operational security guidance to support specific protocol and mitigation claims. Omit citation counts, which change and are unnecessary for the bibliography.

## Practical scope

Use a CLI demonstration first. Add a dashboard only if the experiments, evidence, and report are complete. Do not spend the initial milestones implementing legacy RC4 or integrating a real Active Directory deployment.
