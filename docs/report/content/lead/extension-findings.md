# Optional Extension Findings — A09 Review

Review date: 24 November 2026. Base commit: `34a20a554d1fe0c625d24ace746b48960783653f`.

**Status: reviewed extension evidence prepared on `work/a09-extension-review`.**
Sanitized summaries and provenance are tracked in
[`results/published/extension/`](../../../../results/published/extension/).

## Reviewed E11–E12 observations

The runner [`experiments/kerberoasting/runner.py`](../../../../experiments/kerberoasting/runner.py)
uses the shared `derive_service_key` (`PBKDF2-HMAC-SHA256`, 16-byte salt,
`100,000` iterations) and `seal_ticket`/`open_ticket` (`AES-256-GCM`) helpers.
Acquisition and offline verification are strictly separated; offline verification
makes zero network calls and distinguishes malformed artifacts (`MalformedRequest`)
from candidate mismatches (`InvalidAuthentication`).

| Case | Password class | Attempts | Elapsed (ms) | Outcome |
| --- | --- | ---: | ---: | --- |
| E11 | `weak_in_list` | 4 / 5 | 113.9911 | `recovered` (index 4) |
| E12 | `random_absent` | 5 / 5 | 165.0101 | `not_recovered_within_list_budget` |

## Interpretation limits

- **Kerberoasting-inspired mechanism demo:** Uses simulator AES-256-GCM and
  PBKDF2-HMAC-SHA256 rather than Active Directory RC4 or RFC 3962 Kerberos
  string-to-key derivations.
- **Bounded wordlist scope:** E11 and E12 use the bundled 5-candidate
  `data/wordlists/demo.txt` list under identical KDF, salt-size, iteration, and
  budget settings. E12's non-recovery establishes only that the generated random
  password was absent from that list within the 5-attempt budget—never
  "uncrackability."
- **AES is not a standalone password fix:** E11 demonstrates that AES-GCM
  authenticated encryption does not prevent offline dictionary recovery when the
  service key is derived from a weak password.
- **No AD detection claim:** No Windows Event 4769 telemetry or enterprise
  detection capability is modeled or evaluated.
