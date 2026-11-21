# Four-person work allocation

The user requested the most consequential work, the second most consequential work for one active teammate, and two independent support assignments. Names can replace B/C/D later. This allocation supersedes the earlier two-person examples in the proposal notes.

For exact execution, use [the workflow](workflow/README.md), [the prompt index](prompts/README.md), and `docs/workflow/tasks.json`. They refine the broad A1/B1 assignments below into gated A01/B01 tasks and explicit per-file ownership. Contributors use role-owned handoffs; A alone updates central context/status after integration.

## Ownership

| Person | Priority | Owns | Critical build dependency? |
| --- | --- | --- | --- |
| A — you, project lead | Highest | Protocol/security design, shared crypto/types/time, replay defense, resource server, integration and scientific approval | Yes |
| B — active teammate | Second highest | KDC AS/TGS, normal client, scenario runners, measurement export and extension implementation | Yes |
| C — support teammate | Low dependency | Architecture/flow diagrams, presentation layout, demo cue cards | No |
| D — support teammate | Low dependency | Report template/formatting, reference metadata, installation-document review and final file packaging | No |

C and D have bounded tasks that can be replaced or finished late without breaking the software. They do not own the security design, experiment definitions, measurement generation, or scientific conclusions. Their output still gets a brief final review.

## A — your task list

1. **A1: freeze the shared contract.** Define ticket/authenticator schemas, canonical serialization, key separation, error semantics, time rules and configuration. Provide non-secret fixtures for B. Done when both sides can validate the same fixtures and reject mutations.
2. **A2: implement security primitives and setup.** Library ticket encryption, MAC/verification, validation helpers, injected clock, generated demo secrets, initialized stores. Done when round-trip, tamper, role-binding and boundary tests pass.
3. **A3: implement resource access.** Validate tickets/authenticators and a small operation. Add no-cache and cache-enabled modes. Done when the normal client and controlled replay comparison work.
4. **A4: implement persistent atomic replay protection.** SQLite uniqueness/transaction, shared-worker behavior, missing/corrupt-state rejection and restart preservation. Done when duplicate/concurrency/restart gates in the build plan pass.
5. **A5: integrate and review evidence.** Review B's KDC, runners and extension against the contract; verify comparison fairness and result provenance. Own final integration and security-sensitive decisions.
6. **A6: lead the scientific paper.** Own threat model, contribution framing, limitations, technical interpretation and final claim approval. Share methods/results writing with B.

Primary code: `src/kerberos_lab/common/`, `resource_server/`, `scripts/init_demo.py`; corresponding unit/security tests. You also own authoritative plan/context changes.

## B — second most important task list

1. **B1: AS and TGS.** Implement login, verifier use, TGT issuance and service-ticket issuance using A's shared helpers. Keep TGS validation unchanged across resource comparison modes. Done when valid/invalid exchange tests pass against the frozen fixtures.
2. **B2: normal client.** Implement the full AS → TGS → resource journey; keep the health command available. Done when one documented command completes a normal flow and exposes useful non-secret outcomes.
3. **B3: replay/time/concurrency runner.** Implement E01–E10 in the plan, restart orchestration, controlled clocks and fresh per-trial state. Preserve state within restart trials. Done when machine-readable outcomes distinguish duplicates from legitimate requests and protected operations.
4. **B4: measurement and analysis.** Export CSV/JSONL, environment/config metadata, summary tables and plots from actual measurements. Done when A can rerun selected scenarios and reproduce the conclusions.
5. **B5: bounded offline guessing extension.** After core gates pass, implement E11–E12 using A's library wrappers and approved KDF parameters. Done when counts/budget/outcomes are recorded without AD-compatibility or uncrackability claims.
6. **B6: integration tests and paper method/results draft.** Explain what the runners actually do; prepare reproducibility instructions and technical demo commands with A.

Primary code: `src/kerberos_lab/kdc/`, `client/`, `experiments/`, integration tests. Propose shared-interface changes to A before implementing around them.

## C — independent support tasks

- **C1:** Draw AS/TGS/resource architecture and normal/replay flows from the approved plan, storing editable sources in `docs/diagrams/`.
- **C2:** Prepare a presentation skeleton: problem, roles, architecture, demonstration, result placeholders, limitations and conclusion. Fill result slides only from approved exports.
- **C3:** Produce a short demo speaking script/cue cards and rehearse transitions with A/B.
- **C4:** Add approved screenshots after the runnable demo exists, with readable captions and secrets hidden.

Done when diagrams match the implemented system, editable files are present, and A/B approve captions. C can complete C1/C2 before working code exists; screenshots and final numbers are late additions. No core feature depends on these tasks.

## D — independent support tasks

- **D1:** Organize the conference manuscript template when the professors provide it. Until then, maintain a neutral outline without assuming IEEE/ACM format.
- **D2:** Check author names, paper titles, years, DOI links and version distinctions using the existing reference audit. Flag uncertain details to A; scientific interpretation remains with A/B.
- **D3:** Check spelling, caption numbering, table/figure references, bibliography formatting and export readability after technical content is supplied.
- **D4:** Follow installation instructions on a fresh copy if practical and report unclear steps. This is documentation feedback, not a substitute for A/B's automated validation.
- **D5:** Prepare the final submission folder inventory and presentation/report file names using approved content.

Done when the formatted artifacts contain the approved text/figures, references resolve, and the submission inventory matches the professors' instructions. No essential software or scientific result depends on D.

## Handoffs and overlap rules

- A publishes schemas/fixtures first; B implements against them. Keep one owner for each shared contract change.
- A and B review each other's integration points. A resolves security and scientific-claim decisions; B owns runner reproducibility.
- C/D use approved content and submit documents/diagrams without modifying code, private data or result values.
- Use separate working branches such as `feature/security-core`, `feature/kdc-experiments`, `docs/diagrams-slides`, and `docs/paper-formatting`. Branch names are suggestions, not existing branches.
- Keep changes small enough to explain, with completed checks recorded. A integrates core changes after checks pass. The user handles credential-requiring repository commands.
- If C/D are delayed, A/B continue the build. If B is delayed, A finishes one vertical normal/replay flow before adding the extension; avoid starting several half-finished components.

## Dependency order

```text
A1/A2 shared contract + helpers
       |                    \
       v                     v
B1/B2 KDC + client         A3/A4 resource + replay store
       \                    /
        v                  v
             Normal flow
                  |
           B3/B4 experiments
                  |
          A5 evidence approval
                  |
      B5 optional guessing extension
                  |
       A6/B6 paper and technical demo

C1–C4 and D1–D5 proceed alongside this sequence.
```
