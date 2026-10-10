# Human-storage stale protocol repair — Requirements

Date: 2026-10-10. Mode: Lite / Lean Industrial.

- **HSPR-R1 — Preserve the immutable protocol.** WHEN the repair is applied, THE SYSTEM SHALL keep
  the existing v4 protocol, manifest, selection artifact and checksum constants byte-unchanged.
- **HSPR-R2 — Restore exact source binding.** WHEN `load_identity_protocol()` validates the current
  workspace, THE SYSTEM SHALL observe the frozen SHA-256 for `retrieval.py` without an exception.
- **HSPR-R3 — Preserve retrieval behavior.** THE SYSTEM SHALL remove only metadata with no runtime
  consumer and SHALL NOT change sparse, dense, structured, PostgreSQL or RRF calculations. THE
  SYSTEM SHALL keep the historical v4 selection evidence byte-identical while admitting only the
  exact, separately enumerated current wrapper versions required by the optional storage app.
- **HSPR-R4 — Restore the experimental API contract.** WHEN a valid private mock profile starts,
  THE SYSTEM SHALL create `HumanStorageResolverService`; its existing 13 API expectations SHALL pass.
- **HSPR-R5 — Retain fail-closed behavior.** IF profile, snapshot, source or backend integrity fails,
  THEN health/resolve SHALL remain unavailable without falling back to a different identity source.

The repair does not authorize protocol re-freezing, model changes, storage rollout, PostgreSQL
writes, domain-ranker work or runtime-default changes. A later source change must fail closed until
a new reviewed compatibility artifact is created; wildcard or semantic-version admission is not
allowed.
