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

- Recorded decisions: **10 / 20**
- Approved for a later catalog batch gate: **10**
- Held: **0**
- Rejected: **0**
- Pending: **10**
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

Private ledger SHA-256: `faf3668e48be36a6c4c5db50e45a7ce0c047cdc723a8bb1023e5f318c16420cb`.
Event head SHA-256: `5a0270c693401773dfc5a979aab4791a47fced8e6c1870cdd1d2d58dc9df82d1`.
Git predecessor commit: `860342eb92c866f377a6964ebc48d37d5dda68ee`.
