# Verification plan

No protocol tests exist yet because authentication is not implemented. The running scaffold can be checked with `python -m kerberos_lab.client`.

Use `docs/implementation-plan.md` for the current security/completion gates and `docs/team-work.md` for test ownership. Tests for future cache-expiry optimization are separate from the initial retained-state replay policy.

Add pytest tests alongside the relevant implementation milestones:

- `unit/`: authenticated ticket round-trips and tampering, validity boundaries using an injected clock, replay-cache atomicity and expiry.
- `integration/`: AS → TGS → RS journey, wrong password, wrong service, and invalid ticket.
- `security/`: duplicate request rejection, fresh authenticator acceptance, concurrent duplicates, restart replay handling, and bounded synthetic offline guessing.

Once test modules exist, run `.venv/bin/python -m pytest`. Do not report an empty test directory as a passing security suite.
