# Shared contract release

A01 specifies [protocol-v1.md](protocol-v1.md) and [python-api-v1.md](python-api-v1.md), plus public disposable examples in `data/fixtures/contract/`. A02/A03 implemented these interfaces and G1 is released. B01/A04 implement the HTTP apps; A05 integrates the launcher and complete journey, pending merged-main G2 verification. See `docs/workflow/status.md` for exact gate evidence.

Only A changes shared contracts. B starts its KDC implementation after G1 is merged and released, reads the actual public API, and requests changes through its own handoff if necessary. No contributor should infer signatures from historical proposal prose.

Run the independent public-example check from the repository root:

```bash
.venv/bin/python docs/contracts/verify-fixtures.py
```

It checks the independent declared vectors/cases. Runtime correctness is checked by the Python test suite; fixture verification alone does not test HTTP handlers or the replay store. See the A01–A05 handoffs for implementation evidence and limits.

Use [private setup](setup-v1.md) and [integrated runtime controls](runtime-v1.md) for current commands. These status annotations change no v1 field, callable or security rule.
