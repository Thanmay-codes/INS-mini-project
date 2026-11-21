# Public contract fixtures

A01 supplies `vectors-v1.json` with explicit synthetic request/response and crypto/KDF examples, `cases-v1.json` with expected schema/authentication/time outcomes, and `invalid-json-v1.txt` with a duplicate-key input. These are public disposable test material, separate from `data/private/` runtime secrets. Fixed example keys/nonces/passwords must never become runtime initialization defaults.

The expected outcomes describe the v1 contract; they are not actual HTTP measurements. The independent `docs/contracts/verify-fixtures.py` checks the declared examples without importing future shared helpers. A02/A03 must add actual implementation tests. All time values are synthetic and require an injected fixture clock rather than today's wall time.
