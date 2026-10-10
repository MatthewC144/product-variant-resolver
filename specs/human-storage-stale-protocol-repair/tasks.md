# Human-storage stale protocol repair — Tasks

Date: 2026-10-10. Mode: Lite / Lean Industrial.

- [x] **HSPR-T1 — Restore the frozen retrieval source and bridge known wrapper drift.** Remove only
  the unused `StructuredRetriever.version` metadata; add an exact-hash, storage-only compatibility
  artifact/loader for the three known wrapper revisions; verify v4 protocol replay, the 13 formerly
  failing API cases, related Pointwise/retrieval paths and fail-closed mutations; update review,
  evidence and project log. _(→HSPR-R1–R5)_
