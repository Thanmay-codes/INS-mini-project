# Presentation and viva outline

1. Explain the authentication problem and AS/TGS/RS roles.
2. Show a normal authentication journey.
3. Replay the captured request against the intentionally incomplete baseline.
4. Show clock skew as a separate experiment.
5. Enable replay defense and retry; demonstrate legitimate ticket reuse.
6. (Optional, after A09 approval) Show A09-recorded synthetic weak-password recovery.
7. (Optional) Show A09-recorded bounded non-recovery for a random absent password.
8. Present core and optional measured outcomes, limitations, and practical mitigation context.

Prepare to explain why encryption alone does not stop replay, why a nonce needs authenticated state, why the resource server must not accept a TGT, why AES alone does not eliminate password guessing, and which portions differ from real Kerberos.
