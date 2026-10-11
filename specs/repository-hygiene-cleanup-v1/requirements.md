# Repository Hygiene Cleanup v1 — Requirements

Mode: **Lite / Lean Industrial**  
Scope: GitHub navigation, active/historical classification, stale-content cleanup, and repository
hygiene. Resolver behavior and frozen evaluation remain out of scope.

## Requirements

### R1 — Root navigation

WHEN a reader opens the repository, THE SYSTEM SHALL explain the purpose of every tracked top-level
directory and route the reader toward active code rather than historical chronology.

### R2 — Directory entry points

WHEN a reader enters `src/product_variant_resolver`, `data`, `specs`, `reports`, `artifacts`,
`scripts`, `runtime`, `tests`, `config`, `migrations`, or `ui`, THE SYSTEM SHALL provide a README that
states purpose, active versus historical status, and what should not be inferred from the contents.

### R3 — Active versus historical distinction

WHEN an old roadmap or experiment plan remains visible, THE SYSTEM SHALL mark it as historical and
link to the current documentation index. Public technical navigation SHALL NOT present a completed
historical milestone as the next project step.

### R4 — Remove misleading obsolete content

IF a document contains no executed permission, result, or runtime contract and only preserves a
time-sensitive crawler permission draft, THEN THE SYSTEM SHALL remove it from the current checkout
and repair all links. Git history remains the recovery mechanism.

### R5 — Package positioning

WHEN package metadata is displayed, THE SYSTEM SHALL describe confidence-aware product entity
resolution and learning-to-rank rather than an outdated deterministic MVP.

### R6 — GitHub artifact clarity

WHEN GitHub renders large model or generated-report files, THE SYSTEM SHALL identify safetensors as
binary and generated report JSON as generated, without deleting hash-bound artifacts.

### R7 — Local-only hygiene

WHEN hygiene tests inspect tracked paths, THE SYSTEM SHALL reject `.env`, caches, virtual
environments, local HW data, model cache, temporary collection workspaces, and Python bytecode.

### R8 — Link and terminology integrity

WHEN public/current documentation tests run, THE SYSTEM SHALL verify that local links resolve and
that primary documentation does not restore Dual-RAG positioning. Historical documents MAY retain
terminology only when clearly bannered.

### R9 — Evidence preservation

IF a checkpoint, report, superseded draft, or source snapshot is hash-bound by tests, manifests, or
evidence, THEN THE SYSTEM SHALL retain it unless a separately verified migration replaces every
binding.

### R10 — Traceable delivery

WHEN cleanup completes, THE SYSTEM SHALL record removed content, adjusted files, reasons, test
results, recovery notes, and deferred high-risk work in review, evidence, decisions, and Project Log.

