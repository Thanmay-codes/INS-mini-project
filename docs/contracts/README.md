# Shared contract release

A01 creates `protocol-v1.md` and `python-api-v1.md` here, plus non-secret examples in `data/fixtures/contract/`. A02/A03 implement those interfaces and checks. These files currently do not exist: G1 is NOT RELEASED.

Only A changes shared contracts. B starts its KDC implementation after G1 is merged and released, reads the actual public API, and requests changes through its own handoff if necessary. No contributor should infer signatures from historical proposal prose.
