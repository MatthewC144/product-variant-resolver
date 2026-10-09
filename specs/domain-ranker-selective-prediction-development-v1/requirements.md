# Domain ranker and selective prediction development v1 — Requirements

Date: 2026-10-09. Mode: Lite / Lean Industrial. Status: **T1 and T1A complete; T2+ pending owner Gates**.

## Goal

Build one governed ML development loop for three related improvements:

1. development-only hard-negative mining;
2. domain fine-tuning of the pinned MiniLM cross-encoder;
3. calibration and selective prediction after the ranker is frozen.

The milestone remains offline development until later Gates authorize execution or activation.
T1A makes a minimized hard-negative pair package and an actual safetensors checkpoint eligible for
future public release after artifact-specific release Gates; it does not publish either artifact,
authorize a new final-test run, activate FastAPI, or permit reuse of the already-opened 53-positive
and 20-negative holdouts. A future fresh-final aggregate report and runtime code/config/model
manifest may also be public, but only after their separate execution or activation Gates pass.

## Observable requirements

- **DRSP-R1 — Purpose-specific data Gate.** WHEN a row is proposed for mining, training,
  calibration or evaluation, THE SYSTEM SHALL require a checksum-bound authorization that names
  the exact permitted use, fields, label authority, retention, publication scope and checkpoint
  scope. Existing evaluation permission SHALL NOT imply model-training permission.
- **DRSP-R2 — Permanent legacy-holdout denylist.** THE SYSTEM SHALL reject every record, query,
  identity and parent hash belonging to the opened 53-positive ranking test and 20-negative
  no-match holdout from mining, transformer fitting, model selection, calibration fitting,
  threshold selection and any future-final manifest.
- **DRSP-R3 — Split before model access.** WHEN development data is admitted, THE SYSTEM SHALL
  assign connected groups to exactly one of `ranker_train`, `ranker_selection`, `calibration_fit`,
  `calibration_selection` or `fresh_final` before scoring or mining. Normalized duplicates, source
  events, aliases, casting families and target releases SHALL NOT cross partitions.
- **DRSP-R4 — Frozen candidate pools.** WHEN candidate pools are built, THE SYSTEM SHALL bind the
  catalog, renderer, retrievers, Top-K and generic model hashes. IF the expected release is absent,
  THEN the row SHALL be reported as a retrieval miss and SHALL NOT receive an injected target.
- **DRSP-R5 — Hard-negative meaning.** A hard negative SHALL be a high-ranking wrong release with
  valid catalog-relative evidence, prioritizing same-casting, adjacent-year, wrong-series,
  wrong-identifier or wrong-color candidates. Evidence-insufficient near duplicates SHALL be held
  or assigned graded/ambiguous relevance instead of being forced to negative.
- **DRSP-R6 — One-shot train-only mining.** WHEN negatives are mined, THE SYSTEM SHALL use only
  `ranker_train` queries and the frozen generic model/RRF candidate pools. Development v1 SHALL NOT
  iteratively remine using the fine-tuned model, and ranks or errors from selection, calibration or
  final partitions SHALL NOT affect the miner.
- **DRSP-R7 — Controlled domain fine-tuning.** THE SYSTEM SHALL fine-tune only the immutable
  `cross-encoder/ms-marco-MiniLM-L6-v2` revision already pinned by the project, using fixed
  serialization, seed, objective, hyperparameters, early-stopping rule and safetensors-only output.
- **DRSP-R8 — Fair ranker comparison.** WHEN the domain model is evaluated, THE SYSTEM SHALL compare
  the generic and domain Pointwise rankers on identical frozen candidate pools and report exact
  Top-1, casting Top-1, MRR@10, Recall@25, hard-negative accuracy and CPU rerank latency. It SHALL
  report `winner: null` if the preregistered gate is not met.
- **DRSP-R9 — Ranker freeze before calibration.** WHEN calibration begins, THE SYSTEM SHALL require
  an immutable selected-ranker manifest and checkpoint hash. No ranker, renderer, feature or
  candidate-pool change is permitted after that boundary.
- **DRSP-R10 — Calibration isolation.** Calibration fitting and threshold selection SHALL use
  family-disjoint rows not used for ranker training or ranker selection. The same frozen scores
  SHALL be used for every predeclared calibration arm.
- **DRSP-R11 — Score semantics.** Public and private artifacts SHALL distinguish neural relevance
  scores from calibrated correctness estimates. Raw Pointwise logits SHALL NOT be called
  confidence or probability.
- **DRSP-R12 — Selective prediction.** Threshold selection SHALL maximize coverage only after
  satisfying frozen exact-match, no-match and false-decision safety gates. IF no threshold satisfies
  them, THEN the run SHALL publish a shortfall and SHALL NOT relax the gates.
- **DRSP-R13 — Reliability evidence.** Development reports SHALL include Brier score, negative log
  likelihood, fixed-bin ECE with bin counts, reliability rows, precision/risk-coverage curves and
  AURC. Small-sample uncertainty and not-applicable slices SHALL remain visible.
- **DRSP-R14 — Artifact-specific publication boundary.** WHEN an artifact is prepared for release,
  THE SYSTEM SHALL apply an explicit publication allowlist. Versioned row-level hard-negative pair
  packages and actual safetensors checkpoint weights MAY be Git-tracked and publicly released only
  after their artifact-specific release Gates pass. This exception SHALL NOT publish split
  membership, calibration rows, final-test rows, row-level final predictions, secrets, PII, local
  paths or unrelated raw source data; all non-allowlisted row-level artifacts remain private.
- **DRSP-R15 — Model lineage and public package Gate.** Every checkpoint SHALL bind the base model
  ID and revision, file hashes, license evidence, dependency/SBOM hashes, data/manifests, code
  commit, seed, hyperparameters, selected epoch and checkpoint SHA-256. A public package SHALL
  contain safetensors weights, a model card, artifact license/NOTICE, training-rights limitation and
  reproducibility manifest; it SHALL reject pickle weights, optimizer state, secrets and unscanned
  metadata. Loading SHALL remain offline with `trust_remote_code=false`. Oversized weights SHALL use
  Git LFS or a release asset rather than an ordinary Git blob.
- **DRSP-R16 — Publicability, execution and activation isolation.** Fresh-final aggregate reports
  and runtime code/config/model artifacts MAY be public, but publication eligibility SHALL NOT
  authorize creation or reading of a final dataset, execution or post-result tuning, runtime
  activation, a public endpoint, or a default FastAPI change. Each action SHALL require a separate
  checksum-bound Owner Gate and QA evidence. Until those Gates pass, the policy SHALL remain
  `runtime_eligible=false`, final evaluation SHALL remain unexecuted and runtime SHALL remain inactive.

## Scope exclusions

- No Listwise retraining, Pairwise/ListMLE architecture search or learned bi-encoder.
- No LLM, Agent, GraphRAG or generative identity decision.
- No live Fandom, marketplace or image collection without a separate source-specific permission.
- No reuse of the opened 53-positive or 20-negative holdouts.
- No public row-level artifact except a release-gated hard-negative pair package; no public
  checkpoint except a release-gated safetensors package.
- No claim of manufacturer/global truth, production accuracy or runtime readiness.

## Acceptance gates proposed for owner confirmation

### Ranker qualification

- exact-release Top-1 improves by at least 3 cases on a 30-row ranker-selection partition;
- MRR@10 improves by at least 0.02 and does not regress;
- same-family hard-negative accuracy improves by at least 10 percentage points;
- casting Top-1 regresses by no more than one case;
- Recall@25 does not fall;
- CPU p95 is at most 1.25 times the generic baseline and no more than 200 ms;
- at least two training seeds show the same improvement direction.

### Calibration and selective-prediction qualification

- Brier improves by at least 0.01 over a generic-ranker calibration baseline;
- NLL and fixed-bin ECE do not worsen;
- accepted exact precision is at least 90%, with at least six accepted positives;
- catalog-present exact recall is at least 20%;
- no-match precision is at least 90% and no-match recall is at least 50%;
- catalog-present false-no-match rate is at most 10%;
- known catalog-relative negative false-match count is zero;
- exact risk at the selected operating point is at most 10%, coverage is at least 25%, and combined
  abstention is at most 65%.

Failure to meet a gate is a valid negative result. Thresholds, samples and metrics SHALL NOT be
changed after results are visible merely to obtain a passing claim.
