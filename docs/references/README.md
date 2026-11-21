# Sources and citation notes

See [the completed validity audit](validity-research.md) for the original-paper checks, exact support for each claim, version distinctions, and access limits.

## Protocol and operational sources

- Neuman, C., Yu, T., Hartman, S., & Raeburn, K. (2005). [The Kerberos Network Authentication Service (V5), RFC 4120](https://www.rfc-editor.org/rfc/rfc4120.html). Especially section 3.2.3 for authenticators, clock skew, and replay caching.
- Microsoft (2024). [Microsoft's guidance to help mitigate Kerberoasting](https://www.microsoft.com/en-us/security/blog/2024/10/11/microsofts-guidance-to-help-mitigate-kerberoasting/). Supports password-strength, managed-account, encryption, and detection discussion.
- Cornell CS 5430 (2017). [Key Establishment](https://www.cs.cornell.edu/courses/cs5430/2017sp/l/10-key-estab/notes.html). Supplementary explanation of Needham–Schroeder and the Denning–Sacco timestamp modification.

## References supplied in the initial proposal

The follow-up audit verified these references through original text, author/university copies, and publication metadata. Direct DOI access was unreliable. Do not treat each citation as support for every claim in the original plan.

- Needham, R. M., & Schroeder, M. D. (1978). Using encryption for authentication in large networks of computers. *Communications of the ACM*, 21, 993–999. [DOI](https://doi.org/10.1145/359657.359659).
- Bellovin, S. M., & Merritt, M. (1990). Limitations of the Kerberos authentication system. *ACM SIGCOMM Computer Communication Review*, 20(5), 119–132. [Verified DOI](https://doi.org/10.1145/381906.381946). The [accessible author PDF](https://www.cs.columbia.edu/~smb/papers/kerblimit.usenix.pdf) is the expanded Winter USENIX 1991 version; cite that version when using its inspected text.
- Pöhn, D., & Hommel, W. (2023). Towards an Improved Taxonomy of Attacks Related to Digital Identities and Identity Management Systems. *Security and Communication Networks*, 2023, article 5573310, 30 pages. [DOI](https://doi.org/10.1155/2023/5573310). Use for taxonomy context, rather than Kerberoasting-specific claims.

Citation counts are omitted because they are time-dependent and unnecessary. For final academic claims, cite the specific protocol section, original paper passage, or operational guidance that supports the statement.
