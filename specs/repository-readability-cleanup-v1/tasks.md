# Repository Readability Cleanup v1 — Tasks

## P0 — Portfolio landing path

- [x] 1. Rewrite README as a 150–250 line landing page. _(→R1, R2, R3, R6, R10)_
  - Keep one primary metric family and a clear denominator.
  - Move chronology and detailed QA out of the first reading path.
- [x] 2. Update `docs/PORTFOLIO-GUIDE.md` to the same positioning and guardrails. _(→R2, R3, R5)_
- [x] 3. Add the technical documentation index and architecture overview. _(→R4, R6)_

## P1 — Navigation, evidence, and quality

- [x] 4. Add `CODE-TOUR.md`, `RESULTS.md`, and `LIMITATIONS.md`. _(→R3, R4, R10)_
- [x] 5. Add artifact policy/inventory and historical archive entry. _(→R4, R7, R10)_
- [x] 6. Repair active-core Ruff/MyPy findings without changing behavior. _(→R8, R10)_
- [x] 7. Add documentation claim and public-link tests. _(→R3, R9)_
- [x] 8. Update measured-artifact tests to point to the historical results page. _(→R3, R10)_

## Verification and closeout

- [x] 9. Run focused documentation, API, retrieval, Ruff, MyPy, and link checks. _(→R8, R9, R10)_
- [x] 10. Record the decision, QA review, evidence, and detailed Project Log entry. _(→R11)_
- [x] 11. Commit and push the verified cleanup to GitHub `main`. _(→R11)_

## Deferred P2 options — not part of this Gate

- Git LFS or GitHub Releases migration for retained checkpoints.
- Moving historical experiment orchestration out of the package.
- Broad archive directory migration of immutable evidence.
- Whole-repository Ruff/MyPy debt cleanup.
