# Repository Hygiene Cleanup v1 — QA Review

Verdict: **PASS**  
Mode: Lite / Lean Industrial

## Coverage

| Requirement | Evidence | Result |
|---|---|---|
| R1 | Root README repository map; current package description | PASS |
| R2 | Thirteen tracked directory entry points | PASS |
| R3 | Three legacy documents start with Historical status banners | PASS |
| R4 | Obsolete permission draft removed; current links repaired | PASS |
| R5 | `pyproject.toml` uses entity-resolution/LTR positioning | PASS |
| R6 | `.gitattributes` marks safetensors binary and report/evaluation JSON generated | PASS |
| R7 | Hygiene test verifies forbidden local-only paths are not tracked | PASS |
| R8 | Expanded public link/terminology tests | PASS |
| R9 | Hash-bound models, reports, snapshots, and superseded drafts retained | PASS |
| R10 | Review, evidence, decision, Project Log, commit/push record | PASS |

## Verification

- Focused pytest: **70 passed**; one upstream Starlette/AnyIO deprecation warning.
- Documentation/hygiene tests: 8 passed.
- Ruff on changed documentation tests: all checks passed.
- Strict MyPy on six active runtime modules: no issues.
- README: 213 lines, within the 150–250 public landing-page target.
- Public/current terminology scan: no Dual-RAG wording in the checked current and bannered legacy pages.
- Curated Markdown links: all resolve.
- `git diff --check`: pass.
- Secret scan: no known API key or private-key header found.

## Removal record

Removed `docs/FANDOM-SOURCE-PERMISSION-GUIDE.md`. It was a time-sensitive, unexecuted request
template and explicitly stated that no permission had been sent or received. It was not a license,
source snapshot, experiment result, or runtime contract. Its planning context remains in the
historical roadmap/Project Log and the file is recoverable from Git history.

## Preserved content

- Four published safetensors checkpoints and their independent tokenizer packages.
- Large historical selection/calibration reports.
- Explicitly superseded drafts protected by lineage tests.
- Specs, owner gates, decisions, source snapshots, and negative results.

Deleting or moving these would invalidate manifests, relative links, and reproducibility claims.

## Deferred high-risk work

Git LFS/Releases migration, package-module relocation, mass evidence moves, and Git-history rewrite
remain separate migrations. Current checkout readability no longer depends on those actions.
