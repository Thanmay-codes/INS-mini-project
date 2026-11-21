# Shared contract release

A01 specifies [protocol-v1.md](protocol-v1.md) and [python-api-v1.md](python-api-v1.md), plus public disposable examples in `data/fixtures/contract/`. A02/A03 must implement the specified interfaces and checks. G1 is NOT RELEASED; the documents are not existing runtime APIs.

Only A changes shared contracts. B starts its KDC implementation after G1 is merged and released, reads the actual public API, and requests changes through its own handoff if necessary. No contributor should infer signatures from historical proposal prose.

Run the independent public-example check from the repository root:

```bash
.venv/bin/python docs/contracts/verify-fixtures.py
```

It checks the declared vectors/cases, not the complete future production validator, HTTP handlers or replay store. See `docs/handoffs/A/A01.md` for task status and remaining work.
