# Editable diagrams

Contributor C owns architecture and flow diagrams. Base them on `docs/implementation-plan.md`: AS/TGS share the KDC process, the resource server accepts service tickets, and per-request authenticators carry replay identifiers. Save editable sources alongside exports.

**Status:** Draft diagrams for the simulator, not production Kerberos. G2 (normal flow) and G3 (reviewed core evidence) are released; the diagrams remain drafts pending A/B review against the implementation. Keep the labels provisional until that review is complete.

These are source-native Mermaid diagrams. They describe the custom educational simulator message format and local key-delivery simplifications, not Kerberos wire protocol or production deployment.

| Source | Caption / contents | Intended use |
| --- | --- | --- |
| [architecture.mmd](./architecture.mmd) | One KDC process containing AS and TGS, a separate resource server, ticket audiences, session-key-authenticated requests, and replay storage. | Paper architecture figure; presentation system overview. |
| [normal-authentication.mmd](./normal-authentication.mmd) | Login, TGT use at TGS, service-ticket issuance, and per-request nonce/MAC use at the resource server. | Paper protocol-flow figure; presentation normal-flow slide. |
| [replay-cache-comparison.mmd](./replay-cache-comparison.mmd) | Matched no-cache and cache-enabled resource comparisons, including exact replay and fresh-request paths. | Paper experiment/design figure; presentation replay demonstration. |

TGT audience is `tgs`; service-ticket audience is `files`. Only the service ticket is presented to the resource server. The request nonce is authenticated with the relevant session key; it is distinct from the ticket-encryption nonce.

Mermaid source is editable as text and can be rendered by Mermaid-compatible tooling. No application code or paid assets are required. Before using these figures in a paper or presentation, ask A/B to review technical labels and replace any draft wording that does not match the released implementation.
