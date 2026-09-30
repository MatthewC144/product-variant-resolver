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

- Recorded decisions: **17 / 20**
- Approved for a later catalog batch gate: **17**
- Held: **0**
- Rejected: **0**
- Pending: **3**
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

Private ledger SHA-256: `ee09c79f16417b84d8c8de29e3a2185ef33afd88e3bda89c1331bdf328b9a749`.
Event head SHA-256: `816dc61934e0df58869e427fbea24af6d89eeef6c10521e9b618afd99dc4e6f1`.
Git predecessor commit: `dc8ab225c6493bccbce2e217f0d135a216b404d0`.
