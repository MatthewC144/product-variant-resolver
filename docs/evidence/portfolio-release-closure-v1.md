# Portfolio release closure v1

Date: 2026-10-11. Scope: current-checkout portfolio release verification only.
Status: **PASS WITH DISCLOSED STATIC-ANALYSIS DEBT**.

## Reproducible evidence

- Pytest: `1572 passed, 86 skipped, 1 warning in 913.04s`.
- Active-runtime/new-test Ruff: PASS.
- Python 3.12 compileall: PASS.
- Central fixture validator: PASS, manifest SHA-256
  `fb3f8ea6a72cef6af26ea71b035d20c86f0364267054bda3c5afbb0ac757da68`.
- Auxiliary result-set validator: PASS, dataset SHA-256
  `7839efc44ced91fe4ae885b7d3019c8d442fcf262fce73470713df52ff8c4e75`.
- Default and human-storage Compose static validation: PASS.
- In-process health and three-state API demonstration: PASS.
- Known-key/private-key/tracked-environment audit: PASS.
- `git diff --check`: PASS.

## Honest boundaries

Whole-repository Ruff reports 235 findings across 92 files. Strict MyPy reports 45 errors across 17
package files. These are disclosed baseline debt, not release-pass claims. The current runtime
remains the dependency-light RRF path; Pointwise/Listwise and domain checkpoints remain offline,
the dual-source calibrated policy remains unqualified, and no sealed holdout was opened.

The 86 skipped cases are explicit historical source-byte replays. New compatibility tests validate
the original commit-bound hashes and current exact wrapper allowlist without rewriting past
evidence or pretending historical metrics came from current code.

