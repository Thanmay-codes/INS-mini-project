# Implementation roadmap

The authoritative milestone definitions and acceptance gates are in [the detailed implementation plan](implementation-plan.md#10-milestones-and-completion-gates). Ownership is in [team-work.md](team-work.md). This file is an earlier high-level checklist.

The current scope for the small college conference and two active contributors is in `docs/college-conference-plan.md`; `docs/proposal.md` provides the initial experimental design. Build the replay study first, including persistent atomic replay tracking; keep service-password guessing as the bounded extension. These plans do not establish a new cryptographic method.

## 0. Workspace — ready

- [x] Python package and dependency declaration
- [x] Separate KDC and resource-server starters
- [x] Launcher and health-check client
- [x] Experiment, testing, evidence, report, and presentation folders
- [x] Original plan retained and technical corrections documented

## 1. Working authentication flow — build next

- [ ] Generate synthetic users, role-specific keys, and a demo service.
- [ ] Implement AS login and encrypted TGT issuance.
- [ ] Implement TGS service-ticket issuance.
- [ ] Implement resource-server ticket validation.
- [ ] Implement the normal client journey.
- [ ] Implement session-key-authenticated requests with freshness and request binding.
- [ ] Check valid flow, invalid login, tampered ticket, wrong service, and expiry.

Done when one command demonstrates login → TGT → service ticket → protected resource, and malformed or invalid tickets are rejected. State clearly that the initial ticket-only mode is intentionally incomplete.

## 2. Replay demonstration and defense — core project

- [ ] Replay a copied request while its ticket is valid and clocks agree.
- [ ] Use identical authenticated requests in no-cache and cache-enabled modes.
- [ ] Add atomic replay caching; compare exact duplicate acceptance with all other checks unchanged.
- [ ] Evaluate legitimate requests under offsets within and outside the skew tolerance.
- [ ] Test ticket lifetime boundaries separately, including the stated expiry/leeway policy.
- [ ] Check fresh legitimate requests still work using the same valid ticket.
- [ ] Check duplicate concurrent requests and replay after server restart.
- [ ] Keep challenge-response as optional future work after the minimum project is complete.

Done when the captured request is rejected in defended mode, normal requests still work, and clock effects are reported separately from replay effects.

## 3. Synthetic Kerberoasting — extension

- [ ] Issue a lab service ticket under a key derived from a deliberately weak password.
- [ ] Recover that password offline from the tiny bundled candidate list.
- [ ] Repeat with a strong random password under the same cipher and KDF.
- [ ] Record candidates, attempts, elapsed time, and stopping budget.
- [ ] Explain real Kerberos encryption types and acquisition telemetry as limitations/context.

Done when weak-password recovery is reproducible and strong-password results are described within the tested budget. No AD compatibility claim is needed.

## 4. Evidence, report, and viva

- [ ] Automate the experiment matrix in `experiments/README.md`.
- [ ] Export actual measurements to CSV; record environment and configuration.
- [ ] Produce reviewed result tables and figures.
- [ ] Complete the report, references, and short demo script.

Suggested work order: finish milestones 1 and 2 before adding milestone 3 or a web dashboard. If time is tight, submit a well-tested replay study and describe Kerberoasting as the extension.
