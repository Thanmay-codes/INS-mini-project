# Synthetic service-ticket guessing

Place the local offline dictionary demo here after service-ticket issuance works. Its only inputs should be a lab-generated ticket artifact, the public KDF parameters, and the bundled small candidate list.

Keep authentication failures from guessed keys distinguishable from malformed input. Treat successful authenticated decryption as candidate verification. Report this as a mechanism demonstration; it is not an AD-compatible ticket cracker or a benchmark of real Kerberos encryption types.
