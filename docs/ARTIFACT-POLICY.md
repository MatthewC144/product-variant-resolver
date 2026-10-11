# Artifact Policy

This policy explains why the repository contains both compact manifests and selected large
artifacts. It favors reproducibility and honest negative results while keeping local collection data
and reconstructible intermediates out of Git.

## Classification

| Class | Examples | Git policy |
|---|---|---|
| Source and contracts | `src/`, tests, specs, schemas | Commit |
| Frozen aggregate evidence | metrics JSON, manifests, QA, AI-eval | Commit |
| Selected reproducibility artifacts | published safetensors checkpoints and tokenizer/config | Commit when an experiment explicitly promises inspectable training output |
| Reconstructible binaries | ONNX exports, caches, temporary conversions | Local-only unless separately approved |
| Private row-level evaluation | output-blind query packs, labels, predictions | Local-only / ignored |
| Collection workspace | downloaded images, API responses, crawler scratch files, secrets | Local-only / ignored; remove after approved dataset materialization |

## Current large tracked inventory

The main size drivers are:

- Four retained float16 MiniLM checkpoints at about 43.3 MiB each: two from the original
  domain-ranker experiment and two from v2 remediation.
- Historical calibration/selection reports ranging from roughly 7–41 MiB.
- Frozen datasets and manifests required to explain or validate historical experiments.

At this cleanup baseline, `.git` is approximately 327 MiB. Local virtual environments, caches,
reconstructible ONNX files, and `model-cache/` are not part of the tracked artifact policy.

## Why checkpoints remain

The checkpoints are retained because the repository publicly documents a complete fine-tuning and
model-rejection workflow. `winner: null` means “not selected,” not “delete the experiment.” Keeping
the packages makes the negative result inspectable and prevents the documentation from claiming a
training deliverable that cannot be examined.

## Why this cleanup does not migrate binaries

Moving existing objects to Git LFS or GitHub Releases changes clone behavior, historical access,
and release instructions. Deleting or replacing artifacts may also invalidate hash-bound evidence.
Those actions require a separate migration plan and verification Gate; a readability cleanup should
not silently rewrite reproducibility history.

## Future migration criteria

Consider Git LFS or GitHub Releases when at least one condition holds:

- repository clone size materially blocks reviewers or CI;
- another checkpoint revision is added;
- a release download script and stable checksums are ready;
- historical hash/link compatibility has a documented migration path.

Until then, no new large binary should be committed without documenting its purpose, license,
checksum, reconstruction path, and why a manifest alone is insufficient.

