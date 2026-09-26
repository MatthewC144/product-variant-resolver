# Neural reranker architecture comparison v1 — Tasks

Date: 2026-09-25. Mode: Lite / Lean Industrial. Status: **COMPLETE — NRC-T1–T10 closed; formal result `winner: null`**.

## Execution contract

Tasks execute strictly in order. NRC-T1–T6 build and validate the complete experiment machinery
without acquiring the external model or exposing formal test results. NRC-T7–T8 freeze external,
Train, and Dev state. NRC-T9 is the only task allowed to collect formal label-blind Test outputs.
NRC-T10 joins Test labels once, publishes the result, performs closure QA, and delivers to GitHub.

No task changes the FastAPI runtime, `PVR_RERANKER_ENABLED`, current calibration/policy,
PostgreSQL, canonical data, Human Knowledge RAG, review-family state, or release promotion. If an
earlier task fails its acceptance criteria, later tasks remain unchecked and do not run.

## Tasks

- [x] **NRC-T1 — Implement deterministic comparison contracts and pure ranking utilities.**
  _(→NRC-R1, NRC-R2, NRC-R3, NRC-R7, NRC-R9, NRC-R11, NRC-R15)_

  **Changes:** Add the frozen candidate/pool/ranked-case data models, canonical JSON/SHA-256 helpers,
  candidate-text allowlist renderer, exact 21-feature builder, deterministic score sorting, metric
  functions, paired rank transitions, category grouping, label-blind recursive validation, and
  source/benchmark denominator validation. Keep this code free of Torch/Sentence Transformers
  imports and disconnected from runtime service code.

  **Files:**
  `src/product_variant_resolver/neural_reranking.py`,
  `tests/evaluation/test_neural_reranking.py`.

  **Acceptance:** Tests prove the 100/58/21/21 and split/family contract, excluded fields never
  enter rendered text/features, missing ranks map exactly, feature order is stable, UUID is only a
  final tie-break, retrieval misses remain null, metrics expose exact numerators/denominators, and
  pool/raw validators reject labels recursively. Ruff, format, target strict MyPy, compile and the
  focused suite pass. Zero formal artifacts, network calls, optional dependency imports, retrieval
  calls, training, runtime changes, or Test exposure.

  **Owner:** task executor / backend implementation; QA by focused contract tests.

  **Completion evidence (2026-09-24):** Added dependency-free frozen candidate/signals/pool/scored
  contracts, canonical JSON/SHA-256 helpers, the allowlisted candidate text renderer, exact 21-field
  feature vector, deterministic ranking, raw-denominator metrics, failure-category grouping, paired
  transitions and recursive pool/raw label-blind validators. The committed benchmark validator
  distinguishes all hard-negative cases (`34/13/13`) from matched ranking hard negatives
  (`12/4/4`), while preserving exact `100/58/21/21` totals and family isolation. Nine focused,
  27 related and all 933 repository tests pass; Ruff, format, target strict MyPy, compile and diff
  checks pass. No optional neural import, formal directory, network, retrieval, training or runtime
  change exists.

- [x] **NRC-T2 — Build the pinned local pointwise model supply-chain boundary.**
  _(→NRC-R4, NRC-R5, NRC-R10, NRC-R14)_

  **Changes:** Add the optional `reranking` dependency extra and Python 3.12 constraint file; add the
  immutable MiniLM model configuration; implement lazy optional imports, explicit-license model
  acquisition, file allowlisting, safetensors-only/checksum/revision validation, offline local-only
  loading, one-batch query/candidate scoring, and actionable dependency/model errors. Acquisition
  code exists, but this task does not invoke the network or install/download anything.

  **Files:**
  `pyproject.toml`,
  `constraints/reranking-python312.txt`,
  `config/neural-reranker-comparison-v1.json`,
  `src/product_variant_resolver/neural_reranking.py`,
  `tests/evaluation/test_neural_reranking.py`.

  **Acceptance:** Fake/local fixtures prove immutable revision and license binding, reject pickle,
  unexpected files, `trust_remote_code`, missing hashes and network outside acquisition; missing
  extras fail before artifact writes; batch permutations preserve identity-to-score mappings. Core
  package and full existing suite still run without neural extras. No real model files or formal
  experiment artifacts exist.

  **Owner:** task executor / backend implementation; QA by supply-chain and optional-import tests.

  **Completion evidence (2026-09-24):** Added an isolated `reranking` extra and direct Python 3.12
  constraints without installing them; committed an immutable config for the Apache-2.0 MiniLM
  model at revision `233902d25c440f23af6f7d6e94d2946bac0bee0a`. The acquisition boundary requires
  explicit license confirmation, requests exactly six config/tokenizer/safetensors files, rejects
  pickle/code/unexpected files, publishes only regular files, records SHA-256 and validates exact
  model/revision/license/config bindings. The offline adapter lazily imports the optional stack,
  requires safetensors, CPU float32, `local_files_only=True`, `trust_remote_code=False`, and scores
  each query's pairs in one call. Sixteen focused, 48 related and all 940 repository tests pass;
  targeted Ruff/format, strict MyPy, compile and diff checks pass. No dependency was installed, no
  network call/model download occurred, and model-cache/formal data/report directories remain absent.

- [x] **NRC-T3 — Implement the permutation-equivariant listwise network and trainer.**
  _(→NRC-R6, NRC-R7, NRC-R8, NRC-R10)_

  **Changes:** Implement train-only feature normalization, the fixed 21→32 candidate encoder, one
  four-head self-attention layer without positional embeddings, padded-candidate masks, scalar
  candidate head, masked listwise cross-entropy, deterministic CPU seed/optimizer schedule, Dev
  MRR early stopping, and safetensors checkpoint serialization. Torch remains a lazy optional import.

  **Files:**
  `src/product_variant_resolver/neural_reranking.py`,
  `tests/evaluation/test_neural_reranking.py`.

  **Acceptance:** Neural tests on synthetic tensors prove candidate permutations reproduce mapped
  scores within `1e-6`, padding cannot affect real candidates, train-only statistics never read
  Dev/Test, one training step reduces a controlled loss, fixed seed reproduces the selected epoch,
  and checkpoint/schema/hash drift fails closed. No benchmark Test labels, formal model, or runtime
  integration is used.

  **Owner:** task executor / backend implementation; QA by optional neural contract tests.

  **Completion evidence (2026-09-25):** Added train-only two-field normalization, immutable
  listwise examples/history/early-stopping contracts, the lazy PyTorch 21→32 encoder plus one
  four-head/64-feedforward Transformer layer with no positional channel, padding masks, masked
  cross-entropy, fixed CPU seed/float32/AdamW schedule, Dev MRR@10 selection, and safetensors-only
  checkpoint/manifest validation. Dependency-free tests prove exact architecture wiring, Train-only
  statistics, untouched binary/rank features, earliest-tie/patience behavior, lazy dependency
  errors, and rejection of schema/hash/shape drift. The suite also contains real Torch tensor tests
  for permutation, padding, one-step loss and repeatability; per the frozen execution plan they are
  collected but deliberately skipped until NRC-T7 installs the approved optional environment.
  Core results are 22 passed/2 skipped focused, 54 passed/2 skipped related, and 946 passed/2
  skipped across all 948 repository tests. Targeted Ruff/format, strict MyPy, compile and diff checks
  pass. No dependency, model, formal artifact, retrieval, training run or Test label was introduced.

- [x] **NRC-T4 — Implement protocol and label-blind Train/Dev candidate-pool lifecycle.**
  _(→NRC-R1, NRC-R2, NRC-R3, NRC-R8, NRC-R9, NRC-R10, NRC-R14)_

  **Changes:** Add experiment paths/schemas, source binding, exact denominator/family validation,
  exclusive-create artifact writers, protocol/manifests, Train/Dev query projection, one-call
  candidate collection through the unchanged canonical retriever, candidate reconstruction, pool
  validation and idempotent `unchanged` behavior. Implement `--freeze-protocol` and the applicable
  read-only checks using temporary synthetic fixtures only.

  **Files:**
  `src/product_variant_resolver/neural_reranker_comparison.py`,
  `tests/evaluation/test_neural_reranker_comparison.py`.

  **Acceptance:** Tests prove one retrieval call per included case, byte-identical ordered candidates,
  complete retrieval evidence, no expected labels or neural outputs, exact family separation,
  source-hash binding, no overwrite, and rejection of partial/tampered state. No formal repository
  artifact, external model acquisition, training, or Test collection occurs.

  **Owner:** task executor / backend implementation; QA by lifecycle/integrity tests.

  **Completion evidence (2026-09-25):** Added a source-bound protocol and immutable Train/Dev pool
  lifecycle around the existing sparse+dense+structured→RRF retriever. The contract validates the
  exact 100-case benchmark and family isolation, projects only the ordered 58 Train and 21 Dev
  queries, invokes retrieval exactly once per projected case, freezes complete source/structured/RRF
  evidence and timings, and recursively prohibits labels, metrics and neural outputs. Canonical JSON
  manifests bind config, benchmark, catalog, both implementation files, dependencies and the future
  pointwise manifest. Exclusive whole-directory publication supports only `created` or validated
  `unchanged`; partial state, query/source drift, malformed ranks/timings, family leakage and byte
  tampering fail closed without overwrite. Eight new focused tests pass; the related suite is
  41 passed/2 optional-neural skipped and the full suite is 954 passed/2 skipped across 956 tests.
  Ruff, format, strict MyPy and compile pass. Tests used temporary fixtures only: no formal
  experiment directory, model cache, report, network request, dependency install, training or Test
  collection was created.

- [x] **NRC-T5 — Implement Train/Dev fitting and immutable model-selection lifecycle.**
  _(→NRC-R4, NRC-R5, NRC-R6, NRC-R7, NRC-R8, NRC-R9, NRC-R10, NRC-R14)_

  **Changes:** Implement controlled Train/Dev label joins, frozen pointwise score collection,
  train-only normalization fitting, target-in-pool eligibility accounting, listwise training, Dev
  early stopping, pointwise/listwise manifests, safetensors checkpoint binding and `--fit`. Isolate
  Test label access behind a separate loader that this phase cannot import or invoke.

  **Files:**
  `src/product_variant_resolver/neural_reranker_comparison.py`,
  `tests/evaluation/test_neural_reranker_comparison.py`.

  **Acceptance:** Synthetic integration tests prove only matched Train targets fit weights, Dev only
  selects the epoch, missing targets are counted rather than injected, pointwise weights remain
  unchanged, Test-label loader calls fail the test, valid repeats return `unchanged`, and any config,
  pool, model or dependency drift invalidates the phase. No formal fitting runs in this task.

  **Owner:** task executor / backend implementation; QA by Train/Dev leakage and artifact tests.

  **Completion evidence (2026-09-25):** Added a controlled Train/Dev label projection, frozen
  per-case pointwise pair scoring, deterministic pointwise ranking manifest, target-in-pool
  eligibility accounting, 21-feature list construction, Train-only normalization verification,
  listwise trainer/Dev early-stopping validation, and a three-file exclusive `models/` lifecycle.
  The fitted phase binds protocol, pool, pointwise model, dependencies, training-label checksum,
  feature schema, architecture/hyperparameters, normalizer, history, selected epoch and safetensors
  checkpoint hash. It skips Test rows before reading label fields and does not invoke the complete
  benchmark/Test-label validator during fitting. Missing targets remain retrieval misses and are
  never injected; only eligible matched Train examples fit weights, while eligible Dev examples
  select the epoch. Four new synthetic integration tests (12 lifecycle tests total) prove 35/36
  Train and 11/12 Dev eligibility under one deliberate miss per split, frozen pointwise weights,
  no Test access, valid-repeat `unchanged`, no extra scoring/training, partial-state rejection and
  config/pool/pointwise/checkpoint/dependency drift failure without overwrite. Related QA is
  45 passed/2 optional-neural skipped; the full repository is 958 passed/2 skipped across 960 tests.
  No formal fit, model download, package install, Test collection or repository model artifact ran.

- [x] **NRC-T6 — Implement one-time Test collection, scoring, gates, reports and complete CLI.**
  _(→NRC-R3, NRC-R4, NRC-R5, NRC-R6, NRC-R7, NRC-R8, NRC-R9, NRC-R10, NRC-R11,
  NRC-R12, NRC-R13, NRC-R14, NRC-R15, NRC-R16, NRC-R17)_

  **Changes:** Implement label-free `--collect-test`, label-joined `--score`, full `--check`, raw-row
  recursive label prohibition, one shared candidate list cloned into three arms, warmed timing,
  pointwise/listwise invariance preflight, exact metrics and paired transitions, NRC-R12/R13
  recommendation/null logic, canonical JSON/Markdown reports, and deterministic SVG comparison
  charts. Register the installed command with all six mutually exclusive phases.

  **Files:**
  `src/product_variant_resolver/neural_reranker_comparison.py`,
  `tests/evaluation/test_neural_reranker_comparison.py`,
  `pyproject.toml`.

  **Acceptance:** Temporary synthetic end-to-end tests prove Test retrieval occurs exactly once,
  raw artifacts contain no expected labels/metrics/winner, errored rows never retry, scoring cannot
  alter model/raw bytes, all gate failure combinations produce `winner: null`, deterministic winner
  ordering works, reports disclose denominators/disclaimers, charts match JSON, and partial or
  inconsistent phases fail. Installed CLI help, targeted checks and full existing suite pass. No
  formal benchmark or model download runs yet.

  **Owner:** task executor / backend implementation; QA by synthetic E2E and regression tests.

  **Completion evidence (2026-09-25):** Added a six-phase installed CLI and completed the synthetic
  one-time Test lifecycle. Collection runs invariance preflight and warm-up only on Train/Dev rows,
  retrieves each of the 21 Test queries exactly once, freezes one shared ordered candidate list,
  and derives RRF, pointwise and listwise arms without exposing expected labels, metrics or a
  winner. Per-case failures are persisted and never retried. The separate scoring phase joins Test
  labels only after raw publication, preserves every model/raw byte, reports exact denominators,
  metrics, category slices and paired rank transitions, and applies all six NRC-R12 gates before a
  deterministic NRC-R13 recommendation; any failed gate yields `winner: null`. Canonical JSON,
  Markdown and two data-bound SVG charts include score semantics, model versions, shared candidates,
  arm scores, timings and evidence scope, while manifests and full checks reject partial, drifted,
  tampered or inconsistent phases. Eleven new synthetic tests bring this lifecycle suite to 23;
  related QA is 56 passed/2 optional-neural skipped and full QA is 969 passed/2 skipped across 971 tests.
  Ruff/format, strict MyPy, compile, diff and installed-help checks pass. Only temporary fixtures
  were used: no formal data/report/model-cache directory, network request, dependency/model download,
  real Test collection, runtime/API/Dual RAG/PostgreSQL or canonical-data change occurred.

- [x] **NRC-T7 — Acquire and verify the real local model, then freeze the formal protocol and Train/Dev pool.**
  _(→NRC-R1, NRC-R2, NRC-R3, NRC-R4, NRC-R5, NRC-R8, NRC-R9, NRC-R10, NRC-R14)_

  **Precondition:** NRC-T1–T6 complete with green pre-freeze QA. Network use and dependency/model
  download require explicit owner approval at execution time. The expected pointwise snapshot is
  roughly 90 MB plus optional Python packages and Torch.

  **Execution:** Install the pinned `reranking` environment, record resolved dependency versions,
  acquire only the approved MiniLM safetensors/tokenizer files with `--confirm-license`, validate
  local offline loading and model hashes, then execute formal `--freeze-protocol` exactly once.

  **Artifacts:**
  local ignored `model-cache/neural-reranker-comparison-v1/pointwise/`,
  `data/evaluation/neural-reranker-comparison-v1/protocol/`,
  `data/evaluation/neural-reranker-comparison-v1/pool/`.

  **Acceptance:** Model/revision/license/file hashes are complete; formal protocol binds config,
  source, catalog, benchmark, code and dependencies; Train/Dev pool has exact expected cases and no
  labels/neural scores; retrieval and source errors are zero; repeat freeze returns `unchanged`;
  Test raw/report directories remain absent. Run focused neural/lifecycle tests and full regression.

  **Owner:** task executor executes approved acquisition/freeze; QA validates manifests and absence.

  **Completion evidence (2026-09-25):** Installed the approved optional stack only in the project
  virtual environment: Sentence Transformers 3.4.1, Torch 2.7.1 and safetensors 0.5.3. The resolved
  macOS ARM64/Python 3.12.13 neural tree is frozen as 33 direct/transitive pins and `uv pip check`
  reports all 74 installed packages compatible. Acquired the Apache-2.0 MiniLM revision
  `233902d25c440f23af6f7d6e94d2946bac0bee0a` as exactly six allowlisted regular files; its 88 MB
  local snapshot manifest hash is
  `32f889bb415ef5a56760a299da0635e8e1704d46fe0b11ded06c563de896feb8` and its safetensors hash is
  `821d1aa69520101d6e0737f78a042ae25b19e5cb9160701909d10434f4aeb0ae`. Strict offline loading and
  real pair scoring passed; repeated acquisition returned `unchanged` without a download.

  The formal protocol is `frozen_pre_test` and records the exact 100/58/21/21 benchmark, 120-product
  `fixture-v1` catalog, source hashes, canonical retriever and resolved core versions. Its label-free
  pool contains exactly 58 Train and 21 Dev rows with 1,973 shared candidates, zero empty rows and
  zero candidates lacking retrieval-source evidence. Full `--check` returned `valid`, and a second
  freeze returned `unchanged`. `models/`, Test `raw/`, and the report directory remain absent.
  Real neural QA is now 47/47, related QA is 58/58, and full QA is 971 passed with zero skips; Ruff,
  strict MyPy, compile and diff checks pass. No Test collection, fitting, scoring, recommendation,
  runtime/API/Dual RAG/PostgreSQL or canonical-data change occurred.

- [x] **NRC-T8 — Run formal Train/Dev scoring and freeze both neural model manifests.**
  _(→NRC-R4, NRC-R5, NRC-R6, NRC-R7, NRC-R8, NRC-R9, NRC-R10, NRC-R14)_

  **Precondition:** NRC-T7 artifacts validate byte-for-byte and formal Test output is absent.

  **Execution:** Execute formal `--fit` exactly once. Preserve pointwise base hashes, pointwise
  Train/Dev logits, train-only normalizer, listwise epoch history, selected Dev epoch, final
  safetensors checkpoint and complete manifests. Run batch-order, padding and permutation preflight
  against the frozen real models.

  **Acceptance:** No Test labels or Test neural scores are accessed; all fitted data comes from
  matched Train families with targets present; Dev alone selects the checkpoint; numeric outputs are
  finite; invariance tolerances pass; repeat fit returns `unchanged`; raw Test and final reports are
  still absent. Any failure blocks NRC-T9 rather than changing architecture or hyperparameters.

  **Owner:** task executor runs the frozen fit; QA verifies leakage and neural contracts.

  **Completion evidence (2026-09-25):** Executed the formal fit once under strict offline mode.
  The frozen MiniLM weights scored all 79 Train/Dev rows and 1,973 existing candidates without
  changing the pool; the pointwise manifest records frozen weights, exact model revision/hash,
  deterministic ranks, finite logits, CPU float32, score tolerance `1e-6`, and
  `test_labels_loaded=false`/`test_scored=false`. All 36 matched Train cases and all 12 matched Dev
  cases had their targets in the frozen pool; 22 Train and 9 Dev non-matched cases were excluded,
  with zero retrieval misses.

  Only the 36 eligible Train lists fit the 21→32 candidate-set attention head and Train-only
  normalizer. Dev MRR@10 was 1.0 from epoch 1 through epoch 11, so the predeclared strict-improvement
  plus 10-epoch-patience rule selected the earliest epoch 1 checkpoint instead of post-hoc choosing
  a later equal epoch. The checkpoint SHA-256 is
  `9386c0593ec07ad2b9eb0f6daa613b66f7b117e0e6c5a33be2e8705dbe18aead`; its manifest preserves
  history, normalization, architecture, hyperparameters, seed and source hashes. Real frozen-model
  batch-order, candidate-permutation and padding preflights passed. A second fit returned
  `unchanged`, full `--check` returned `valid`, and Test `raw/` plus reports remain absent. Related
  QA is 58/58 and full QA is 971/971; Ruff, strict MyPy, compile and diff checks pass. No Test label,
  Test neural score, recommendation, runtime/API/Dual RAG/PostgreSQL or canonical-data change occurred.

- [x] **NRC-T9 — Execute the single formal label-blind Test collection.**
  _(→NRC-R3, NRC-R4, NRC-R5, NRC-R6, NRC-R8, NRC-R9, NRC-R10, NRC-R14, NRC-R15)_

  **Precondition:** NRC-T8 and all pre-Test checks pass; source/config/model files are frozen.

  **Execution:** Run formal `--collect-test` exactly once. Each of 21 Test queries performs one
  unchanged canonical retrieval; all three arms consume cloned byte-equivalent candidates. Persist
  RRF/pointwise/listwise scores, ranks, timings and errors without expected labels, accuracy,
  eligibility or winner fields. Do not retry an errored row.

  **Artifacts:**
  `data/evaluation/neural-reranker-comparison-v1/raw/test-raw.json`,
  `data/evaluation/neural-reranker-comparison-v1/raw/test-raw-manifest.json`.

  **Acceptance:** Exactly 21 unique label-free rows and at most 21 retrieval calls; candidate
  identity/order equality is proven across arms; all source/model bindings validate; repeat collect
  returns `unchanged` without retrieval; expected-label keys are absent recursively. No source,
  config, model or hyperparameter change is allowed after this task under v1.

  **Owner:** task executor runs collection; QA validates label blindness, call count and immutability.

  **Completion evidence (2026-09-25):** After a full pre-Test `valid` check and explicit absence of
  raw/report state, executed the one formal collection under strict offline inference. Exactly 21
  unique Test queries made exactly 21 unchanged canonical retrieval calls; every row succeeded with
  25 candidates, producing 525 shared candidate observations and zero retrieval/model errors. RRF
  preserved the frozen candidate order, while pointwise and listwise each ranked the same 25 UUIDs
  without adding, dropping or substituting candidates.

  Recursive inspection found no expected/target/label/accuracy/metric/winner/eligibility keys. The
  manifest records `label_blind=true`, `test_collection_executed=true`, all protocol/pool/model/
  checkpoint/source bindings, `retrieval_call_count=21`, and `retrieval_error_count=0`. Raw SHA-256
  is `948582264e67ad6d686a4409a41100149118d12b6e4548bbdc1265d778756884`; its manifest SHA-256 is
  `d52000451be8b844067f2ac20d4a170231c93a2fd64253c73488552c4e779105`. A second collection returned
  `unchanged`, full `--check` returned `valid`, all frozen pre-Test hashes remained identical, and
  reports remain absent. Related QA is 58/58 and full QA is 971/971; Ruff, strict MyPy, compile and
  diff checks pass. No Test label, metric, recommendation or post-output source/model change occurred.

- [x] **NRC-T10 — Score once, publish the honest result, close QA, and deliver GitHub state.**
  _(→NRC-R9, NRC-R11, NRC-R12, NRC-R13, NRC-R14, NRC-R15, NRC-R16, NRC-R17)_

  **Precondition:** NRC-T9 raw bytes and all upstream manifests validate. Model/product source is
  frozen; only measured-artifact regression tests and documentation may be added after scoring.

  **Execution:** Run formal `--score` exactly once, join Test labels, compute all required metrics,
  paired transitions, failure categories, latency and gates, then freeze comparison JSON/manifest,
  Markdown and SVGs. Add regression tests for the measured immutable artifacts. Create `review.md`,
  public evidence, AI-eval, README result table, accepted decision record and narrative Project Log;
  mark tasks accurately for winner or null branch.

  **Artifacts:**
  `reports/neural-reranker-comparison-v1/`,
  `specs/neural-reranker-comparison/review.md`,
  `docs/evidence/neural-reranker-comparison-v1.md`,
  `docs/evidence/ai-evals/neural-reranker-comparison-v1.md`,
  README/roadmap/decision/log updates.

  **Acceptance:** Formal `--check`, focused neural/evaluation tests, related integrations, full suite,
  Ruff, format, target strict MyPy, compile, artifact hashes, README/report consistency, absence of
  runtime/API/PostgreSQL/canonical/Human Knowledge diffs and `git diff --check` pass. Publish exact
  12-matched Test denominators and either a gate-qualified shadow recommendation or `winner: null`;
  never claim production accuracy. Commit and push only `Product Variant Resolver` repository files.

  **Owner:** task executor for immutable scoring, QA for G3*, doc curator responsibilities for
  review/evidence/log, then repository delivery.

  **Completion evidence (2026-09-25):** Joined Test labels once against the immutable raw artifact
  and published canonical JSON, Markdown and two SVGs. All three arms achieve Top-1 `12/12`, MRR@10
  `12/12`, Recall@10/25 `12/12`, and matched hard-negative accuracy `4/4`; every pointwise/listwise
  paired target transition is rank 1→1. RRF resolver p95 is 1.398 ms, pointwise 89.164 ms, and
  listwise 89.583 ms. Both neural arms pass hard-negative, MRR, Recall@25, latency and zero-error
  gates but fail the required Top-1 gain gate (`0.00 < 0.05`). The deterministic result is therefore
  `winner: null`, not a post-Test tie-break or neural promotion; RRF remains the runtime default.

  Report JSON SHA-256 is `f0493fc5d7b30b5e57ee382cf14e06e4fddbcebc62228b9f4b5a0dcec45b3dd2`.
  Repeat score returns `unchanged` and full `--check` returns `valid`. Four measured-artifact
  regressions bind exact report/raw hashes, metrics/gates, transitions, label blindness, candidate
  parity and README consistency. QA review, public evidence, AI-eval, README table, Roadmap,
  decision and narrative Project Log all publish the same bounded null result. Related QA is 62/62
  and full QA is 975/975; Ruff/format, strict MyPy, compile, artifact/hash checks and diff checks
  pass. No runtime/API/calibration/Dual RAG/PostgreSQL/canonical/Human Knowledge/release change was
  made. Only this repository's files are committed and pushed for delivery.

## Gate checkpoints

### G1* — Specification confirmation

Requirements, design and tasks are confirmed; G1* closed on 2026-09-24. That confirmation authorized
sequential work beginning with NRC-T1 only, not model download or later formal phases.

### G2 — Implementation readiness before external/formal execution

NRC-T1–T6 must all be checked with green focused, synthetic E2E and full regression tests before
NRC-T7 can request network permission. At G2, formal experiment directories and model cache must
still be absent.

### G3* — Experiment and release closure

NRC-T7–T10 must preserve every phase boundary and immutable hash. G3* passes only when the formal
result—winner or null—is reproducible, QA review/evidence/AI-eval/README/Project Log agree, and
runtime remains unchanged.

G3* closed on 2026-09-25: experiment/release integrity passes, neural promotion fails its exact
incremental-value gate, `winner: null` is reproducible, and RRF remains unchanged at runtime.

## Owner confirmation checkpoint

The owner confirmed this task plan on 2026-09-24. Sequential implementation is authorized, but each
turn still advances one task. Confirmation does not pre-authorize NRC-T7 network access or
model/dependency download; that external action will be described again and request permission when
reached. It also does not authorize repeated Test collection, post-Test model changes, runtime
activation, API changes, or database writes.

The owner subsequently authorized NRC-T7 through NRC-T10 one task at a time. The external install/
download occurred only at NRC-T7; Test collection and label join each occurred once, with no
post-Test source/model/hyperparameter change or runtime/database action.
