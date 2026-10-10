"""DRV2-T5 fixed two-seed pairwise MiniLM training and release packaging."""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import random
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from .domain_ranker_training import (
    _license_text,
    _scan_text_files,
    _validate_safetensors,
)
from .domain_ranker_v2_candidate_pools import (
    LOCAL_POOLS_PATH,
    POINTWISE_CONFIG_PATH,
    POINTWISE_CONFIG_SHA256,
    POINTWISE_MANIFEST_SHA256,
    POINTWISE_MODEL_PATH,
    POINTWISE_WEIGHTS_SHA256,
    _contains_public_row_level_data,
)
from .domain_ranker_v2_governance import (
    _canonical_bytes,
    _content_sha256,
    _file_sha256,
    _load_object,
    _require_file,
    _string,
    _validate_digest,
)
from .domain_ranker_v2_hard_negatives import (
    AUTHORIZATION_PATH as T4_AUTHORIZATION_PATH,
)
from .domain_ranker_v2_hard_negatives import LOCAL_TRIPLES_PATH
from .domain_ranker_v2_hard_negatives import MANIFEST_PATH as T4_MANIFEST_PATH
from .domain_ranker_v2_hard_negatives import check as check_t4

SCHEMA_AUTHORIZATION = "pvr-drv2-t5-owner-authorization-v1"
SCHEMA_MANIFEST = "pvr-drv2-pairwise-checkpoint-manifest-v1"
VERSION = "domain-ranker-v2-remediation-checkpoint-v1"

OUTPUT_DIRECTORY = Path("artifacts/domain-ranker-v2-remediation")
LOCAL_DIRECTORY = OUTPUT_DIRECTORY / "local-t5"
PACKAGE_DIRECTORY = OUTPUT_DIRECTORY / "checkpoint-v1"

AUTHORIZATION_PATH = PACKAGE_DIRECTORY / "owner-authorization.json"
MANIFEST_PATH = PACKAGE_DIRECTORY / "manifest.json"
MODEL_CARD_PATH = PACKAGE_DIRECTORY / "MODEL_CARD.md"
NOTICE_PATH = PACKAGE_DIRECTORY / "NOTICE.md"
LICENSE_PATH = PACKAGE_DIRECTORY / "LICENSE.txt"

T4_AUTHORIZATION_FILE_SHA256 = "6673ee5d58108020631ee57f892cbbbacc21cc2dc3dab2f99d21324ca541dadf"
T4_MANIFEST_FILE_SHA256 = "d036834ec4751d3231aa9847ff3f0dadc513aac2004d62f58a4206ea42e11ec9"
T4_LOCAL_TRIPLES_FILE_SHA256 = "71ec252b78b6bf10358363449f4480556dfbe0f3da031c74203ce3ed10f20572"
T4_MANIFEST_CONTENT_SHA256 = "2c4334db61f1d448290f36ab657909f66e6ee3ace263a92a075d8101434fca6b"
T4_LOCAL_TRIPLES_CONTENT_SHA256 = "5855d753b5567f0659f32ab685d68bf01277a3f4d99c62dbfd83024f2ef32411"
T3_LOCAL_POOLS_FILE_SHA256 = "0c889bfc06755a49ba779f2df64a4e4d87d3de676bf47063fcfcdec454022b24"
T3_LOCAL_POOLS_CONTENT_SHA256 = "7beb612fd5834a2886d8946e01cb88a966de4bf95db14dbe7e42fbbaa5dd5d7b"
OWNER_STATEMENT_SHA256 = "37e6c4a73e7b5f0bafa28453bc8756ef3d45f87162d0d1f802d1ff4bc2b26389"

BASE_MODEL_ID = "cross-encoder/ms-marco-MiniLM-L6-v2"
BASE_MODEL_REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
SEEDS = (17, 29)
MAX_EPOCHS = 4
EARLY_STOPPING_PATIENCE = 2
MIN_DELTA = 1e-12
TRIPLE_BATCH_SIZE = 8
EVAL_BATCH_SIZE = 32
LEARNING_RATE = 1e-5
WEIGHT_DECAY = 0.01
WARMUP_RATIO = 0.1
MAX_LENGTH = 128
GRADIENT_CLIP_NORM = 1.0
EXPECTED_TRIPLE_COUNT = 332
EXPECTED_TRAIN_QUERY_COUNT = 112
EXPECTED_VALIDATION_QUERY_COUNT = 30

TEXT_FILES = (
    ".gitignore",
    "LICENSE.txt",
    "MODEL_CARD.md",
    "NOTICE.md",
    "manifest.json",
    "owner-authorization.json",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
    "seed-17/config.json",
    "seed-29/config.json",
)
WEIGHT_FILES = ("seed-17/model.safetensors", "seed-29/model.safetensors")
PACKAGE_FILES = frozenset((*TEXT_FILES, *WEIGHT_FILES))


class TensorMapping(Protocol):
    def items(self) -> Iterable[tuple[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class PairwiseTriple:
    triple_id: str
    case_id: str
    query: str
    positive: str
    negative: str


@dataclass(frozen=True, slots=True)
class EpochMetric:
    epoch: int
    mean_pairwise_loss: float
    validation_mrr_at_10: float


@dataclass(frozen=True, slots=True)
class SeedResult:
    seed: int
    selected_epoch: int
    stop_epoch: int
    selected_validation_mrr_at_10: float
    history: tuple[EpochMetric, ...]
    checkpoint_sha256: str
    checkpoint_size: int


def training_recipe() -> dict[str, Any]:
    return {
        "base_model_id": BASE_MODEL_ID,
        "base_model_revision": BASE_MODEL_REVISION,
        "objective": "pairwise_logistic_ranknet_softplus",
        "loss": "mean_softplus(-(positive_logit-negative_logit))",
        "seeds": list(SEEDS),
        "max_epochs": MAX_EPOCHS,
        "early_stopping_partition": "ranker_validation",
        "early_stopping_metric": "validation_mrr_at_10",
        "early_stopping_patience": EARLY_STOPPING_PATIENCE,
        "early_stopping_min_delta": MIN_DELTA,
        "triple_batch_size": TRIPLE_BATCH_SIZE,
        "forward_pair_count_per_full_batch": TRIPLE_BATCH_SIZE * 2,
        "evaluation_batch_size": EVAL_BATCH_SIZE,
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "scheduler": "linear_warmup_then_linear_decay",
        "warmup_ratio": WARMUP_RATIO,
        "max_length": MAX_LENGTH,
        "gradient_clip_norm": GRADIENT_CLIP_NORM,
        "device": "cpu",
        "training_checkpoint_dtype": "float32",
        "published_checkpoint_dtype": "float16",
        "selection_partition_access": "prohibited_until_DRV2-T6",
    }


def _current_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    )
    commit = result.stdout.strip()
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise ValueError("could not resolve T5 implementation commit")
    return commit


def _validate_parent_chain(root: Path) -> dict[str, Any]:
    for path, digest, label in (
        (T4_AUTHORIZATION_PATH, T4_AUTHORIZATION_FILE_SHA256, "T4 authorization"),
        (T4_MANIFEST_PATH, T4_MANIFEST_FILE_SHA256, "T4 manifest"),
        (LOCAL_TRIPLES_PATH, T4_LOCAL_TRIPLES_FILE_SHA256, "T4 local triples"),
        (LOCAL_POOLS_PATH, T3_LOCAL_POOLS_FILE_SHA256, "T3 local candidate pools"),
        (POINTWISE_CONFIG_PATH, POINTWISE_CONFIG_SHA256, "base model config"),
        (POINTWISE_MODEL_PATH / "manifest.json", POINTWISE_MANIFEST_SHA256, "base manifest"),
        (
            POINTWISE_MODEL_PATH / "model.safetensors",
            POINTWISE_WEIGHTS_SHA256,
            "base weights",
        ),
    ):
        _require_file(root / path, digest, label)
    manifest = check_t4(root)
    if (
        manifest.get("manifest_sha256") != T4_MANIFEST_CONTENT_SHA256
        or manifest.get("status") != "pairwise_mining_ready"
        or manifest.get("next_allowed_action") != "DRV2-T5_requires_separate_owner_authorization"
    ):
        raise ValueError("T4 does not authorize the separate T5 owner Gate")
    return manifest


def build_authorization(root: Path, code_commit: str) -> dict[str, Any]:
    t4_manifest = _validate_parent_chain(root)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_AUTHORIZATION,
        "gate": "DRV2-T5",
        "authorization_date": "2026-10-10",
        "authorized_by": "project_owner",
        "owner_statement_sha256": OWNER_STATEMENT_SHA256,
        "decision": "execute_fixed_two_seed_pairwise_minilm_training_and_release_gate",
        "authorized_actions": [
            "train_only_on_frozen_332_t4_pairwise_triples",
            "early_stop_only_on_30_frozen_validation_pools",
            "publish_two_float16_safetensors_checkpoints_with_aggregate_history",
            "validate_offline_loading_and_exact_file_allowlist",
        ],
        "prohibited_actions": [
            "read_or_score_ranker_selection_partition",
            "change_recipe_after_validation_metrics_are_visible",
            "generic_vs_domain_winner_selection",
            "positive_test_negative_holdout_or_no_match_development_access",
            "calibration_final_evaluation_or_runtime_activation",
            "pickle_optimizer_or_training_state_publication",
            "public_row_level_queries_triples_or_validation_predictions",
        ],
        "bindings": {
            "t4_manifest_file_sha256": T4_MANIFEST_FILE_SHA256,
            "t4_manifest_content_sha256": t4_manifest["manifest_sha256"],
            "t4_local_triples_file_sha256": T4_LOCAL_TRIPLES_FILE_SHA256,
            "t4_local_triples_content_sha256": T4_LOCAL_TRIPLES_CONTENT_SHA256,
            "t3_local_pools_file_sha256": T3_LOCAL_POOLS_FILE_SHA256,
            "t3_local_pools_content_sha256": T3_LOCAL_POOLS_CONTENT_SHA256,
            "base_config_sha256": POINTWISE_CONFIG_SHA256,
            "base_manifest_sha256": POINTWISE_MANIFEST_SHA256,
            "base_weights_sha256": POINTWISE_WEIGHTS_SHA256,
            "implementation_commit": code_commit,
            "implementation_module_sha256": _file_sha256(
                root / "src/product_variant_resolver/domain_ranker_v2_training.py"
            ),
            "safetensor_validation_helper_sha256": _file_sha256(
                root / "src/product_variant_resolver/domain_ranker_training.py"
            ),
        },
        "recipe": training_recipe(),
        "rights_state": "owner_attested_not_independently_verified",
        "authority_scope": "frozen_community_catalog_relative_not_manufacturer_or_global_truth",
    }
    result = {**body, "authorization_sha256": _content_sha256(body)}
    if _contains_public_row_level_data(result):
        raise ValueError("T5 authorization contains row-level material")
    return result


def load_pairwise_triples(root: Path) -> tuple[PairwiseTriple, ...]:
    payload = _load_object(root / LOCAL_TRIPLES_PATH)
    _validate_digest(payload, "content_sha256", "T4 local triples")
    if payload.get("content_sha256") != T4_LOCAL_TRIPLES_CONTENT_SHA256:
        raise ValueError("T4 local triple content binding changed")
    rows = payload.get("triples")
    if not isinstance(rows, list) or len(rows) != EXPECTED_TRIPLE_COUNT:
        raise ValueError("T5 requires exactly 332 frozen triples")
    triples: list[PairwiseTriple] = []
    triple_ids: set[str] = set()
    case_ids: set[str] = set()
    for raw in rows:
        if not isinstance(raw, dict):
            raise TypeError("T5 triple row is malformed")
        triple_id = _string(raw.get("triple_id"), "triple ID")
        if triple_id in triple_ids:
            raise ValueError("T5 triple IDs must be unique")
        triple_ids.add(triple_id)
        case_id = _string(raw.get("case_id"), "case ID")
        case_ids.add(case_id)
        if (
            raw.get("negative_category") != "same_casting_wrong_exact_release"
            or not isinstance(raw.get("conflicting_query_fields"), list)
            or not raw["conflicting_query_fields"]
        ):
            raise ValueError("T5 triple lacks T4 evidence-qualified label semantics")
        triples.append(
            PairwiseTriple(
                triple_id=triple_id,
                case_id=case_id,
                query=_string(raw.get("query"), "triple query"),
                positive=_string(raw.get("positive_text"), "positive text"),
                negative=_string(raw.get("negative_text"), "negative text"),
            )
        )
    if len(case_ids) != EXPECTED_TRAIN_QUERY_COUNT:
        raise ValueError("T5 triple query count differs from the frozen 112-query contract")
    return tuple(triples)


def load_validation_pools(root: Path) -> tuple[dict[str, Any], ...]:
    payload = _load_object(root / LOCAL_POOLS_PATH)
    _validate_digest(payload, "content_sha256", "T3 local candidate pools")
    if payload.get("content_sha256") != T3_LOCAL_POOLS_CONTENT_SHA256:
        raise ValueError("T3 local pool content binding changed")
    rows = payload.get("rows")
    if not isinstance(rows, list):
        raise TypeError("T3 local pool rows are malformed")
    validation: list[dict[str, Any]] = []
    for row in rows:
        if not isinstance(row, dict):
            raise TypeError("T3 candidate-pool row is malformed")
        if row.get("partition") != "ranker_validation":
            continue
        candidates = row.get("candidates")
        if not isinstance(candidates, list) or len(candidates) != 25:
            raise ValueError("T5 validation pool must contain exactly 25 candidates")
        if row.get("target_retrieved") is not True:
            raise ValueError("T5 validation target is absent")
        validation.append(row)
    if len(validation) != EXPECTED_VALIDATION_QUERY_COUNT:
        raise ValueError("T5 requires exactly 30 validation pools")
    return tuple(sorted(validation, key=lambda row: _string(row.get("case_id"), "case ID")))


def pairwise_ranknet_loss(positive_logits: Any, negative_logits: Any, torch: Any) -> Any:
    if positive_logits.shape != negative_logits.shape or positive_logits.numel() == 0:
        raise ValueError("pairwise logits must be non-empty and aligned")
    return torch.nn.functional.softplus(-(positive_logits - negative_logits)).mean()


def mrr_at_10_from_scores(
    pools: Sequence[Mapping[str, Any]], scores: Sequence[Sequence[float]]
) -> float:
    if len(pools) != len(scores) or not pools:
        raise ValueError("validation pools and scores must be non-empty and aligned")
    reciprocal_sum = 0.0
    for pool, row_scores in zip(pools, scores, strict=True):
        candidates = pool.get("candidates")
        if not isinstance(candidates, list) or len(candidates) != len(row_scores):
            raise ValueError("validation candidate and score counts differ")
        target_uuid = _string(pool.get("target_uuid"), "validation target UUID")
        ranked: list[tuple[float, str]] = []
        for candidate, score in zip(candidates, row_scores, strict=True):
            if not isinstance(candidate, dict):
                raise TypeError("validation candidate is malformed")
            numeric_score = float(score)
            if not math.isfinite(numeric_score):
                raise ValueError("validation score is non-finite")
            ranked.append(
                (numeric_score, _string(candidate.get("canonical_uuid"), "candidate UUID"))
            )
        ranked.sort(key=lambda item: (-item[0], item[1]))
        rank = next(
            (index for index, (_, uuid) in enumerate(ranked, 1) if uuid == target_uuid), None
        )
        if rank is None:
            raise ValueError("validation target is absent from its frozen pool")
        if rank <= 10:
            reciprocal_sum += 1.0 / rank
    return reciprocal_sum / len(pools)


def select_early_stopping(history: Sequence[EpochMetric]) -> tuple[int, int, float]:
    if not history:
        raise ValueError("early stopping requires at least one epoch")
    best_epoch = 0
    best_metric = -math.inf
    stale = 0
    stop_epoch = history[-1].epoch
    for expected_epoch, item in enumerate(history, 1):
        if item.epoch != expected_epoch or item.epoch > MAX_EPOCHS:
            raise ValueError("epoch history must be contiguous and within the frozen budget")
        if item.validation_mrr_at_10 > best_metric + MIN_DELTA:
            best_epoch = item.epoch
            best_metric = item.validation_mrr_at_10
            stale = 0
        else:
            stale += 1
        if stale >= EARLY_STOPPING_PATIENCE:
            stop_epoch = item.epoch
            break
    return best_epoch, stop_epoch, best_metric


def _load_training_dependencies() -> tuple[Any, Any, Any, Any]:
    try:
        torch = importlib.import_module("torch")
        transformers = importlib.import_module("transformers")
        safetensors_torch = importlib.import_module("safetensors.torch")
    except ImportError as error:
        raise RuntimeError("DRV2-T5 requires the pinned reranking dependencies") from error
    tokenizer_class = getattr(transformers, "AutoTokenizer", None)
    model_class = getattr(transformers, "AutoModelForSequenceClassification", None)
    save_file = getattr(safetensors_torch, "save_file", None)
    if tokenizer_class is None or model_class is None or not callable(save_file):
        raise RuntimeError("installed T5 training dependencies are incompatible")
    return torch, tokenizer_class, model_class, save_file


def _configure_determinism(torch: Any, seed: int) -> None:
    random.seed(seed)
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)


def _tokenize_triples(tokenizer: Any, rows: Sequence[PairwiseTriple]) -> dict[str, Any]:
    queries = [row.query for row in rows] + [row.query for row in rows]
    candidates = [row.positive for row in rows] + [row.negative for row in rows]
    return cast(
        dict[str, Any],
        tokenizer(
            queries,
            candidates,
            padding=True,
            truncation=True,
            max_length=MAX_LENGTH,
            return_tensors="pt",
        ),
    )


def _score_validation(
    model: Any, tokenizer: Any, pools: Sequence[dict[str, Any]], torch: Any
) -> float:
    flattened: list[tuple[str, str]] = []
    widths: list[int] = []
    for pool in pools:
        query = _string(pool.get("query"), "validation query")
        candidates = cast(list[dict[str, Any]], pool["candidates"])
        widths.append(len(candidates))
        flattened.extend(
            (query, _string(candidate.get("rendered_text"), "validation candidate text"))
            for candidate in candidates
        )
    raw_scores: list[float] = []
    model.eval()
    with torch.no_grad():
        for start in range(0, len(flattened), EVAL_BATCH_SIZE):
            batch = flattened[start : start + EVAL_BATCH_SIZE]
            encoded = tokenizer(
                [item[0] for item in batch],
                [item[1] for item in batch],
                padding=True,
                truncation=True,
                max_length=MAX_LENGTH,
                return_tensors="pt",
            )
            logits = model(**encoded).logits.reshape(-1)
            raw_scores.extend(float(value) for value in logits.detach().cpu().tolist())
    rows: list[tuple[float, ...]] = []
    cursor = 0
    for width in widths:
        rows.append(tuple(raw_scores[cursor : cursor + width]))
        cursor += width
    return mrr_at_10_from_scores(pools, rows)


def _save_half_checkpoint(model: Any, destination: Path, save_file: Any, torch: Any) -> None:
    state: dict[str, Any] = {}
    for name, tensor in cast(TensorMapping, model.state_dict()).items():
        value = tensor.detach().cpu().contiguous()
        if value.is_floating_point():
            value = value.to(dtype=torch.float16)
        state[name] = value
    destination.parent.mkdir(parents=True, exist_ok=True)
    save_file(state, str(destination))


def _train_seed(
    root: Path,
    seed: int,
    triples: Sequence[PairwiseTriple],
    validation_pools: Sequence[dict[str, Any]],
    scratch: Path,
) -> tuple[SeedResult, Path]:
    torch, tokenizer_class, model_class, save_file = _load_training_dependencies()
    _configure_determinism(torch, seed)
    tokenizer = tokenizer_class.from_pretrained(
        root / POINTWISE_MODEL_PATH, local_files_only=True, trust_remote_code=False
    )
    model = model_class.from_pretrained(
        root / POINTWISE_MODEL_PATH,
        local_files_only=True,
        trust_remote_code=False,
        use_safetensors=True,
        dtype=torch.float32,
    )
    optimizer = torch.optim.AdamW(model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY)
    total_steps = MAX_EPOCHS * math.ceil(len(triples) / TRIPLE_BATCH_SIZE)
    warmup_steps = max(1, round(total_steps * WARMUP_RATIO))

    def learning_rate_lambda(step: int) -> float:
        if step < warmup_steps:
            return float(step + 1) / float(warmup_steps)
        remaining = max(0, total_steps - step)
        return float(remaining) / float(max(1, total_steps - warmup_steps))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, learning_rate_lambda)
    rng = random.Random(seed)
    order = list(range(len(triples)))
    history: list[EpochMetric] = []
    best_metric = -math.inf
    stale = 0
    best_path = scratch / f"seed-{seed}" / "model.safetensors"
    for epoch in range(1, MAX_EPOCHS + 1):
        rng.shuffle(order)
        losses: list[float] = []
        model.train()
        for start in range(0, len(order), TRIPLE_BATCH_SIZE):
            rows = [triples[index] for index in order[start : start + TRIPLE_BATCH_SIZE]]
            encoded = _tokenize_triples(tokenizer, rows)
            optimizer.zero_grad(set_to_none=True)
            logits = model(**encoded).logits.reshape(-1)
            midpoint = len(rows)
            loss = pairwise_ranknet_loss(logits[:midpoint], logits[midpoint:], torch)
            if not bool(torch.isfinite(loss)):
                raise ValueError("T5 pairwise loss became non-finite")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP_NORM)
            optimizer.step()
            scheduler.step()
            losses.append(float(loss.detach().cpu()))
        validation_mrr = _score_validation(model, tokenizer, validation_pools, torch)
        history.append(
            EpochMetric(
                epoch=epoch,
                mean_pairwise_loss=sum(losses) / len(losses),
                validation_mrr_at_10=validation_mrr,
            )
        )
        if validation_mrr > best_metric + MIN_DELTA:
            best_metric = validation_mrr
            stale = 0
            _save_half_checkpoint(model, best_path, save_file, torch)
        else:
            stale += 1
        print(
            f"seed={seed} epoch={epoch} pairwise_loss={history[-1].mean_pairwise_loss:.8f} "
            f"validation_mrr_at_10={validation_mrr:.8f}",
            flush=True,
        )
        if stale >= EARLY_STOPPING_PATIENCE:
            break
    selected_epoch, stop_epoch, selected_metric = select_early_stopping(history)
    if not best_path.is_file():
        raise ValueError("T5 training did not produce a best safetensors checkpoint")
    return (
        SeedResult(
            seed=seed,
            selected_epoch=selected_epoch,
            stop_epoch=stop_epoch,
            selected_validation_mrr_at_10=selected_metric,
            history=tuple(history),
            checkpoint_sha256=_file_sha256(best_path),
            checkpoint_size=best_path.stat().st_size,
        ),
        best_path,
    )


def _copy_tokenizer_and_config(root: Path, staging: Path) -> None:
    for name in ("special_tokens_map.json", "tokenizer.json", "tokenizer_config.json", "vocab.txt"):
        text = (root / POINTWISE_MODEL_PATH / name).read_text(encoding="utf-8")
        (staging / name).write_text(text, encoding="utf-8", newline="\n")
    config = _load_object(root / POINTWISE_MODEL_PATH / "config.json")
    config["torch_dtype"] = "float16"
    for seed in SEEDS:
        directory = staging / f"seed-{seed}"
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "config.json").write_bytes(_canonical_bytes(config))


def _model_card(results: Sequence[SeedResult]) -> str:
    lines = "\n".join(
        f"- Seed {result.seed}: selected epoch {result.selected_epoch}, stop epoch "
        f"{result.stop_epoch}, validation MRR@10 {result.selected_validation_mrr_at_10:.8f}."
        for result in results
    )
    return f"""# Product Variant Resolver pairwise domain MiniLM checkpoints v2

These checkpoints fine-tune `{BASE_MODEL_ID}` revision `{BASE_MODEL_REVISION}` on 332
community-catalog-relative same-casting exact-release triples.

## Fixed training recipe

- Objective: RankNet-style pairwise logistic loss, `softplus(-(positive-negative))`.
- Seeds: 17 and 29; learning rate `1e-5`; at most four epochs.
- Early stopping: 30 frozen validation queries, MRR@10, patience two.
- Published weights: float16 safetensors only; no optimizer or pickle state.

{lines}

## Intended use and limitations

These are experimental offline ranking artifacts for the separately gated DRV2-T6 comparison.
T5 does not read the selection partition, choose a winner, calibrate confidence, run a final test,
activate runtime or expose an endpoint. Labels are relative to a frozen community snapshot and are
not manufacturer-certified or global truth. Source and redistribution rights are owner-attested,
not independently verified; color and edition remain incomplete.
"""


def _notice() -> str:
    return f"""Product Variant Resolver pairwise domain MiniLM checkpoints v2

Base model: {BASE_MODEL_ID}
Pinned revision: {BASE_MODEL_REVISION}
Base-model license recorded by the frozen local manifest: Apache-2.0.

Derived checkpoints are distributed under Apache-2.0. Training labels are frozen-community-
catalog-relative and are not Mattel/manufacturer certification or global truth. Source and
redistribution rights are owner-attested, not independently verified. See MODEL_CARD.md and
manifest.json for lineage and limitations.
"""


def _package_gitignore() -> str:
    allowed = "\n".join(f"!/{name}" for name in sorted(PACKAGE_FILES - {".gitignore"}))
    directories = "\n".join(f"!/{name}/" for name in ("seed-17", "seed-29"))
    return f"*\n!/.gitignore\n{directories}\n{allowed}\n"


def _validate_exact_package_files(directory: Path) -> None:
    actual: set[str] = set()
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError("T5 checkpoint package must not contain symlinks")
        if path.is_file():
            actual.add(path.relative_to(directory).as_posix())
    if actual != PACKAGE_FILES:
        raise ValueError("T5 checkpoint package file allowlist mismatch")


def _validate_offline_load(directory: Path) -> None:
    torch, tokenizer_class, model_class, _ = _load_training_dependencies()
    tokenizer_class.from_pretrained(directory, local_files_only=True, trust_remote_code=False)
    for seed in SEEDS:
        model_class.from_pretrained(
            directory / f"seed-{seed}",
            local_files_only=True,
            trust_remote_code=False,
            use_safetensors=True,
            dtype=torch.float32,
        )


def _package_digest(files_sha256: Mapping[str, str]) -> str:
    return _content_sha256({"schema": "pvr-drv2-t5-package-digest-v1", "files": files_sha256})


def _materialize_package(
    root: Path,
    authorization: Mapping[str, Any],
    results: Sequence[SeedResult],
    checkpoints: Mapping[int, Path],
) -> None:
    destination = root / PACKAGE_DIRECTORY
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise FileExistsError("DRV2-T5 checkpoint package already exists")
    stage = Path(tempfile.mkdtemp(prefix=".checkpoint-v1-", dir=destination.parent))
    try:
        _copy_tokenizer_and_config(root, stage)
        for result in results:
            shutil.copyfile(
                checkpoints[result.seed], stage / f"seed-{result.seed}" / "model.safetensors"
            )
        (stage / "owner-authorization.json").write_bytes(_canonical_bytes(authorization))
        (stage / "MODEL_CARD.md").write_text(_model_card(results), encoding="utf-8")
        (stage / "NOTICE.md").write_text(_notice(), encoding="utf-8")
        (stage / "LICENSE.txt").write_text(_license_text(), encoding="utf-8")
        (stage / ".gitignore").write_text(_package_gitignore(), encoding="utf-8")

        tensor_shapes = {
            f"seed-{seed}": _validate_safetensors(stage / f"seed-{seed}" / "model.safetensors")
            for seed in SEEDS
        }
        preliminary_files = {
            name: _file_sha256(stage / name) for name in sorted(PACKAGE_FILES - {"manifest.json"})
        }
        manifest_body: dict[str, Any] = {
            "schema_version": SCHEMA_MANIFEST,
            "version": VERSION,
            "status": "pairwise_checkpoints_released",
            "published": True,
            "release_gate_passed": True,
            "authorization_sha256": authorization["authorization_sha256"],
            "bindings": authorization["bindings"],
            "recipe": training_recipe(),
            "training": {
                "triple_count": EXPECTED_TRIPLE_COUNT,
                "train_query_count": EXPECTED_TRAIN_QUERY_COUNT,
                "validation_query_count": EXPECTED_VALIDATION_QUERY_COUNT,
                "results": [asdict(result) for result in results],
                "generic_vs_domain_winner_selected": False,
            },
            "files_sha256": preliminary_files,
            "tensor_schema_sha256": _content_sha256(tensor_shapes),
            "guardrails": {
                "selection_rows_read_or_scored": 0,
                "positive_test_rows_read_or_scored": 0,
                "negative_holdout_rows_read_or_scored": 0,
                "no_match_development_rows_read_or_scored": 0,
                "calibration_fits": 0,
                "fresh_final_evaluations": 0,
                "model_selection_runs": 0,
                "runtime_default_changed": False,
                "runtime_activations": 0,
                "optimizer_state_published": False,
                "pickle_weights_published": False,
            },
            "release_gate": {
                "exact_file_allowlist": sorted(PACKAGE_FILES),
                "artifact_license_notice_and_model_card_present": True,
                "source_and_training_rights_limitation_disclosed": True,
                "safetensors_only": True,
                "offline_load_trust_remote_code_false": True,
                "text_scan_passed": True,
                "ordinary_git_blob_under_50_mib": max(result.checkpoint_size for result in results)
                < 50 * 1024 * 1024,
            },
            "rights_state": "owner_attested_not_independently_verified",
            "limitations": [
                "not_manufacturer_or_global_truth",
                "training_and_redistribution_rights_not_independently_verified",
                "validation_used_only_for_early_stopping",
                "selection_partition_unread_until_DRV2-T6",
                "no_calibration_final_evaluation_or_runtime_activation",
            ],
            "next_allowed_action": "DRV2-T6_requires_separate_owner_authorization",
        }
        manifest_body["package_sha256"] = _package_digest(preliminary_files)
        manifest = {**manifest_body, "manifest_sha256": _content_sha256(manifest_body)}
        (stage / "manifest.json").write_bytes(_canonical_bytes(manifest))
        _validate_exact_package_files(stage)
        _scan_text_files(stage, TEXT_FILES)
        _validate_offline_load(stage)
        for path in stage.rglob("*"):
            if path.is_file():
                path.chmod(stat.S_IRUSR | stat.S_IWUSR | stat.S_IRGRP | stat.S_IROTH)
        os.replace(stage, destination)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def train(root: Path) -> dict[str, Any]:
    authorization = build_authorization(root, _current_commit(root))
    triples = load_pairwise_triples(root)
    validation = load_validation_pools(root)
    scratch = root / LOCAL_DIRECTORY
    if scratch.exists():
        raise FileExistsError("DRV2-T5 scratch directory already exists")
    scratch.mkdir(parents=True, mode=0o700)
    results: list[SeedResult] = []
    checkpoints: dict[int, Path] = {}
    try:
        for seed in SEEDS:
            result, checkpoint = _train_seed(root, seed, triples, validation, scratch)
            results.append(result)
            checkpoints[seed] = checkpoint
        _materialize_package(root, authorization, results, checkpoints)
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)
    return check(root)


def check(root: Path) -> dict[str, Any]:
    _validate_parent_chain(root)
    directory = root / PACKAGE_DIRECTORY
    _validate_exact_package_files(directory)
    authorization = _load_object(root / AUTHORIZATION_PATH)
    manifest = _load_object(root / MANIFEST_PATH)
    _validate_digest(authorization, "authorization_sha256", "T5 authorization")
    _validate_digest(manifest, "manifest_sha256", "T5 manifest")
    if authorization.get("bindings", {}).get("implementation_module_sha256") != _file_sha256(
        root / "src/product_variant_resolver/domain_ranker_v2_training.py"
    ):
        raise ValueError("T5 implementation binding changed")
    if (
        manifest.get("release_gate_passed") is not True
        or manifest.get("published") is not True
        or manifest.get("authorization_sha256") != authorization.get("authorization_sha256")
        or manifest.get("next_allowed_action") != "DRV2-T6_requires_separate_owner_authorization"
    ):
        raise ValueError("T5 checkpoint release state is invalid")
    file_hashes = manifest.get("files_sha256")
    if not isinstance(file_hashes, dict):
        raise TypeError("T5 manifest file hashes are missing")
    for name in sorted(PACKAGE_FILES - {"manifest.json"}):
        if file_hashes.get(name) != _file_sha256(directory / name):
            raise ValueError(f"T5 package file hash differs: {name}")
    if manifest.get("package_sha256") != _package_digest(cast(Mapping[str, str], file_hashes)):
        raise ValueError("T5 package digest is stale")
    if _contains_public_row_level_data(authorization) or _contains_public_row_level_data(manifest):
        raise ValueError("T5 public package contains row-level material")
    for name in WEIGHT_FILES:
        _validate_safetensors(directory / name)
    _scan_text_files(directory, TEXT_FILES)
    _validate_offline_load(directory)
    return manifest


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Train or check DRV2-T5 pairwise checkpoints")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--acknowledge-owner-authorization", action="store_true")
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if args.run:
        if not args.acknowledge_owner_authorization:
            parser.error("--run requires --acknowledge-owner-authorization")
        manifest = train(root)
        status = "trained"
    elif args.check:
        manifest = check(root)
        status = "valid"
    else:
        parser.error("choose --run or --check")
    print(
        json.dumps(
            {
                "status": status,
                "package_sha256": manifest["package_sha256"],
                "results": manifest["training"]["results"],
                "next_allowed_action": manifest["next_allowed_action"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
