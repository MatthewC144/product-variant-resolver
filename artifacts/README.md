# Model Artifacts

This directory contains two public MiniLM checkpoint packages retained to make the domain-adaptation
experiments inspectable.

| Package | Contents | Selection status |
|---|---|---|
| `domain-ranker-selective-prediction-development-v1/public-checkpoint-v1/` | Two fixed-seed safetensors checkpoints plus tokenizer/config/model cards | `winner: null` |
| `domain-ranker-v2-remediation/checkpoint-v1/` | Two preregistered RankNet-style checkpoints plus tokenizer/config/model cards | `winner: null` |

The checkpoints were successfully trained and packaged but were not selected for calibration or
runtime. “Published artifact” means reproducible experiment output, not deployed model.

Tokenizer and vocabulary files are duplicated across packages because each package is independently
checksum-bound and self-contained. Reconstructible ONNX exports, optimizer state, caches, and local
training diagnostics stay ignored.

See [Artifact Policy](../docs/ARTIFACT-POLICY.md) and [Results](../docs/RESULTS.md).

