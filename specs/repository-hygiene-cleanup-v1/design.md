# Repository Hygiene Cleanup v1 — Design

## Overview

The repository contains 1,112 tracked files because it preserves code, data contracts, evaluation
artifacts, governance decisions, and negative experiments. Deleting everything that is not on the
runtime import path would make the repo smaller but would also invalidate its engineering claims.
This cleanup therefore organizes by reader intent and removes only one clearly obsolete,
non-evidentiary permission draft.

## Repository map

Each tracked top-level directory receives a short README. These files classify contents into:

1. active runtime;
2. optional integration;
3. frozen evaluation/evidence;
4. historical or generated material;
5. local-only content that must never be committed.

The root README links to those indexes so GitHub browsing has a clear route without requiring file
moves that would invalidate manifests and relative links.

## Historical-document treatment

`REAL-CATALOG-ROADMAP.md`, `HUMAN-STORAGE-PROFILE-GUIDE.md`, and
`T49-2-ISOLATED-TEST-PLAN.md` remain at their existing paths because specs/evidence reference them.
Each receives a prominent historical banner and updated authority-separated terminology. They are
removed from current technical navigation.

`FANDOM-SOURCE-PERMISSION-GUIDE.md` is deleted because it is an unexecuted, time-sensitive request
template—not evidence of permission—and the project no longer uses it as a current collection path.
Its historical planning context remains in the roadmap, decision log, evidence, and Git history.

## Artifact handling

No checkpoint or large historical report is deleted. Exact duplicate tokenizer/vocabulary files are
part of two independently hash-bound checkpoint packages, so their small duplication is safer than
cross-package symlinks. `.gitattributes` marks safetensors as binary and report JSON as generated for
clearer GitHub diffs.

## Interfaces and behavior

No Python API, FastAPI schema, retrieval component, score, model, threshold, data membership, or
runtime default changes. `pyproject.toml` changes only its human-readable package description.

## Error handling and tests

- Repository-hygiene tests assert folder indexes, historical banners, package wording, binary
  attributes, and absence of forbidden tracked paths.
- Existing documentation link/claim tests expand to the new indexes.
- Focused API and historical compatibility tests protect the unchanged runtime/evidence boundary.
- Deleted content is recoverable from Git history.

## Deferred work

Git LFS/Releases migration, source-module relocation, evidence directory moves, and Git-history
rewriting are independent high-risk projects. They are not required to make the current GitHub
checkout understandable.

