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
All 20 owner decisions are recorded. The next permitted step is the separate catalog
batch application owner Gate; this progress artifact does not apply catalog records.

## Current progress

- Recorded decisions: **20 / 20**
- Approved for a later catalog batch gate: **20**
- Held: **0**
- Rejected: **0**
- Pending: **0**
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

Private ledger SHA-256: `c1fe895d5fa525b49c9115ffc4883e0b6d54bc172a3af7dc2fcb73ab9bc39b85`.
Event head SHA-256: `7dbcda7f83682e2e15f1d940c32d9004750679f692afef2e37bda6bd658eac74`.
Git predecessor commit: `ee51c69b23a690f87e76a8d72c39e1a3c0c5e54d`.
