# CAR catalog proposal review — public method and progress

Catalog proposals are reviewed one at a time in the canonical packet order. The
project owner uses explicit owner attestation while resolver/model output remains
hidden. The private append-only ledger binds each answer to the frozen packet, proposal,
product-record and parent-catalog checksums.
Git commits are the external immutable prefix anchor: a later event must extend the
progress committed at HEAD by exactly one canonical event. Rehashing mutable JSON alone
cannot prove append-only history and is rejected.
Before a new event is committed, precommit verification also requires the caller's
external expected ordinal, row identities, decision, exact owner response and bounded
reason; the mutable ledger cannot authorize its own wording.
The verifier walks first-parent history through every commit carrying identical progress
bytes. The commit that introduced those bytes must name its own first parent as the
predecessor; later code-only commits cannot launder a rewritten history.

## Current progress

- Recorded decisions: **6 / 20**
- Approved for a later catalog batch gate: **6**
- Held: **0**
- Rejected: **0**
- Pending: **14**
- Proposal artifacts remain `staged`: **20**
- Catalog records applied: **0**
- Exact-authority records approved: **0**
- Resolver output consulted: **false**
- Network requests: **0**
- RHB-T5 authorized: **false**

An owner approval here records only a catalog-proposal decision. It does not edit
`data/catalog.json`, change the staged proposal artifact, approve exact authority, or
authorize RHB-T5. Catalog application waits for a separate batch application Gate after
all 20 proposals have been reviewed.

Private ledger SHA-256: `1ac84b8b6a3508c042e441e9ce748d29503fb14efb2a09d07e1fcc36615fe678`.
Event head SHA-256: `d1ab5c7acd17758c287fa229abc7efb7af9d7f3951f6abfa2be206a66b85568d`.
Git predecessor commit: `a186cfb8842291e18f908b9a7222127da37db921`.
