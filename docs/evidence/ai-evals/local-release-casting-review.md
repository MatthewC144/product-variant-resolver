# AI-eval note — local release casting review queue

Date: 2026-09-17. Verdict: **PASS for review support; excluded from resolver truth**.

This artifact is deterministic code output, not an LLM answer. It is nevertheless evaluated under
the project's AI-output gate because a future reviewer or agent may consume it while preparing
catalog decisions.

| Rubric | Result | Evidence |
|---|---|---|
| Grounding | PASS | Every private cluster retains source record IDs and exact observed labels. |
| Authority | PASS | Both catalogs are labeled as candidate sources; fixture/human matches do not approve identity. |
| Integrity | PASS | Same inputs reproduce queue SHA-256 `7961d4e6…b883`; reordered inputs are identical. |
| Safety | PASS | Existing canonical UUID, runtime usage, or non-null color fails closed. |
| Privacy | PASS | Public artifacts contain aggregate counts and hashes, not labels or rows. |
| Auditability | PASS | Four candidate classes, collision flags, priorities, and hold decisions are explicit. |

The queue is ineligible for canonical API responses, calibration/evaluation labels, automatic SQL
promotion, and either Dual RAG runtime corpus. Human review must inspect attributable evidence and
record a separate decision event before any later promotion workflow may be considered.
