"""DRSP-T4 deterministic, two-seed domain MiniLM fine-tuning.

The trainer consumes only the released T3 binary pair package and the frozen
T2 ranker-selection pools.  It never reads calibration/final data, selects the
generic-vs-domain winner, changes runtime behavior, or writes pickle/optimizer
state.  Public weights are emitted only after the fixed package gate passes.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import math
import os
import random
import re
import shutil
import stat
import subprocess
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Protocol, cast

from .domain_ranker_governance import GOVERNANCE_V2_PATH, check_publication_amendment
from .domain_ranker_hard_negatives import MANIFEST_PATH as T3_MANIFEST_PATH
from .domain_ranker_hard_negatives import PAIR_PATH as T3_PAIR_PATH
from .domain_ranker_partitions import LOCAL_POOLS_PATH, POOL_MANIFEST_PATH

VERSION = "domain-ranker-selective-prediction-development-v1"
SCHEMA_AUTHORIZATION = "pvr-drsp-t4-owner-authorization-v1"
SCHEMA_MANIFEST = "pvr-drsp-t4-public-checkpoint-manifest-v1"

BASE_CONFIG_PATH = Path("config/neural-reranker-comparison-v1.json")
BASE_MODEL_DIRECTORY = Path("model-cache/neural-reranker-comparison-v1/pointwise")
BASE_MODEL_MANIFEST_PATH = BASE_MODEL_DIRECTORY / "manifest.json"
OUTPUT_DIRECTORY = Path("artifacts/domain-ranker-selective-prediction-development-v1")
LOCAL_DIRECTORY = OUTPUT_DIRECTORY / "local-t4"
PACKAGE_DIRECTORY = OUTPUT_DIRECTORY / "public-checkpoint-v1"

AUTHORIZATION_PATH = PACKAGE_DIRECTORY / "owner-authorization.json"
MANIFEST_PATH = PACKAGE_DIRECTORY / "manifest.json"
MODEL_CARD_PATH = PACKAGE_DIRECTORY / "MODEL_CARD.md"
NOTICE_PATH = PACKAGE_DIRECTORY / "NOTICE.md"
LICENSE_PATH = PACKAGE_DIRECTORY / "LICENSE.txt"
PACKAGE_GITIGNORE_PATH = PACKAGE_DIRECTORY / ".gitignore"

FROZEN_GOVERNANCE_V2_FILE_SHA256 = (
    "2ce83d6790f05ad4c580f835b2b749809ce906860c37f4f385b8512a60937302"
)
FROZEN_T3_MANIFEST_FILE_SHA256 = (
    "22ba77b93461e8d693a69b80c018fb7286abb07e7a2c2c68bc578c2efeadc24c"
)
FROZEN_T3_PAIRS_SHA256 = (
    "50f88e73889b31e8f314e93b2cca9e4871934662b5218c6659a72fe06c0ca2ba"
)
FROZEN_T3_PACKAGE_SHA256 = (
    "89bc430289c36e75c6302e7aa4ecca1889f32df95e5199f61aba1f676b18022a"
)
FROZEN_T2_POOL_MANIFEST_FILE_SHA256 = (
    "ec27f7608865bef5983ae90a780b8779fa6a715bc8253d9dfa4ce046f79e4ac3"
)
FROZEN_T2_PRIVATE_POOLS_SHA256 = (
    "a54172a409e759dff89175aefc6a82a7de4c8828b5a7da5c119072bb8d9fa9a1"
)
FROZEN_BASE_CONFIG_SHA256 = (
    "3a88163cc7abc84468024f5e6410e0ca489a80a710b67b4c2474c4b4f7d7fad6"
)
FROZEN_BASE_MANIFEST_SHA256 = (
    "32f889bb415ef5a56760a299da0635e8e1704d46fe0b11ded06c563de896feb8"
)
FROZEN_BASE_WEIGHTS_SHA256 = (
    "821d1aa69520101d6e0737f78a042ae25b19e5cb9160701909d10434f4aeb0ae"
)
OWNER_STATEMENT_SHA256 = (
    "37e6c4a73e7b5f0bafa28453bc8756ef3d45f87162d0d1f802d1ff4bc2b26389"
)

BASE_MODEL_ID = "cross-encoder/ms-marco-MiniLM-L6-v2"
BASE_MODEL_REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
SEEDS = (17, 29)
MAX_EPOCHS = 4
EARLY_STOPPING_PATIENCE = 2
BATCH_SIZE = 16
EVAL_BATCH_SIZE = 32
LEARNING_RATE = 2e-5
WEIGHT_DECAY = 0.01
WARMUP_RATIO = 0.1
MAX_LENGTH = 128
GRADIENT_CLIP_NORM = 1.0
MIN_DELTA = 1e-12

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

_FORBIDDEN_TEXT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("aws_access_key", re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b")),
    ("authorization_credential", re.compile(r"(?i)authorization\s*:\s*(?:bearer|basic)\s+\S+")),
    ("secret", re.compile(r"(?i)\b(?:api[_-]?key|secret|password|token)\s*[:=]\s*[^\s,}\]]+")),
    ("secret_file", re.compile(r"(?i)(?:^|[/\\])\.env(?:\.[A-Za-z0-9_-]+)?\b")),
    ("path_traversal", re.compile(r"(?:^|[/\\])\.\.(?:[/\\]|$)")),
    ("local_path", re.compile(r"(?:/Users/|/home/|[A-Za-z]:\\Users\\)")),
    (
        "email",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    ),
)


class TensorMapping(Protocol):
    def items(self) -> Iterable[tuple[str, Any]]: ...


@dataclass(frozen=True, slots=True)
class TrainingExample:
    query: str
    candidate: str
    label: float


@dataclass(frozen=True, slots=True)
class EpochMetric:
    epoch: int
    mean_loss: float
    selection_mrr_at_10: float


@dataclass(frozen=True, slots=True)
class SeedResult:
    seed: int
    selected_epoch: int
    stop_epoch: int
    selected_mrr_at_10: float
    history: tuple[EpochMetric, ...]
    checkpoint_sha256: str
    checkpoint_size: int


def _canonical_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _content_sha256(payload: object) -> str:
    return hashlib.sha256(_canonical_bytes(payload)).hexdigest()


def _file_sha256(path: Path) -> str:
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{path}: required regular file is absent or unsafe")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_file(path: Path, expected: str, label: str) -> None:
    if _file_sha256(path) != expected:
        raise ValueError(f"{label} differs from the frozen SHA-256 binding")


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: could not read strict JSON") from error
    if not isinstance(payload, dict):
        raise TypeError(f"{path}: JSON root must be an object")
    return payload


def _load_jsonl(path: Path) -> tuple[dict[str, Any], ...]:
    rows: list[dict[str, Any]] = []
    try:
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                raise ValueError(f"{path}:{line_number}: blank JSONL line")
            payload = json.loads(line, object_pairs_hook=_reject_duplicate_keys)
            if not isinstance(payload, dict):
                raise TypeError(f"{path}:{line_number}: row must be an object")
            rows.append(payload)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{path}: could not read strict JSONL") from error
    return tuple(rows)


def _validate_content_digest(payload: Mapping[str, Any], field: str, label: str) -> None:
    body = {key: value for key, value in payload.items() if key != field}
    if payload.get(field) != _content_sha256(body):
        raise ValueError(f"{label} checksum is stale")


def _string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")
    return value.strip()


def _current_git_commit(root: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    commit = result.stdout.strip()
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("could not resolve a full Git commit for training lineage")
    return commit


def _validate_inputs(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    _require_file(
        root / GOVERNANCE_V2_PATH,
        FROZEN_GOVERNANCE_V2_FILE_SHA256,
        "effective governance v2",
    )
    effective = check_publication_amendment(root, require_local_catalog=True)
    permissions = effective.get("permissions")
    if not isinstance(permissions, dict) or (
        permissions.get("positive_local_domain_fine_tuning") is not True
        or permissions.get("public_safetensors_checkpoint_after_release_gate") is not True
        or permissions.get("runtime_activation") is not False
    ):
        raise ValueError("effective governance does not authorize bounded T4 training")

    _require_file(root / T3_MANIFEST_PATH, FROZEN_T3_MANIFEST_FILE_SHA256, "T3 manifest")
    _require_file(root / T3_PAIR_PATH, FROZEN_T3_PAIRS_SHA256, "T3 pairs")
    _require_file(
        root / POOL_MANIFEST_PATH,
        FROZEN_T2_POOL_MANIFEST_FILE_SHA256,
        "T2 candidate-pool manifest",
    )
    _require_file(root / LOCAL_POOLS_PATH, FROZEN_T2_PRIVATE_POOLS_SHA256, "T2 private pools")
    _require_file(root / BASE_CONFIG_PATH, FROZEN_BASE_CONFIG_SHA256, "base model config")
    _require_file(
        root / BASE_MODEL_MANIFEST_PATH,
        FROZEN_BASE_MANIFEST_SHA256,
        "base model manifest",
    )
    _require_file(
        root / BASE_MODEL_DIRECTORY / "model.safetensors",
        FROZEN_BASE_WEIGHTS_SHA256,
        "base model weights",
    )

    t3_manifest = _load_object(root / T3_MANIFEST_PATH)
    _validate_content_digest(t3_manifest, "manifest_sha256", "T3 manifest")
    if (
        t3_manifest.get("release_gate_passed") is not True
        or t3_manifest.get("published") is not True
        or t3_manifest.get("package_sha256") != FROZEN_T3_PACKAGE_SHA256
        or t3_manifest.get("next_allowed_action")
        != "DRSP-T4_requires_separate_owner_authorization_and_model_release_gate"
    ):
        raise ValueError("T3 package is not the authorized frozen training input")

    pool_manifest = _load_object(root / POOL_MANIFEST_PATH)
    _validate_content_digest(pool_manifest, "manifest_sha256", "T2 pool manifest")
    if pool_manifest.get("private_pool_artifact_sha256") != FROZEN_T2_PRIVATE_POOLS_SHA256:
        raise ValueError("T2 private pool binding differs from T4")
    return t3_manifest, pool_manifest


def build_authorization(root: Path, code_commit: str) -> dict[str, Any]:
    t3_manifest, pool_manifest = _validate_inputs(root)
    body: dict[str, Any] = {
        "schema_version": SCHEMA_AUTHORIZATION,
        "gate": "DRSP-T4",
        "authorization_date": "2026-10-09",
        "authorized_by": "project_owner",
        "owner_statement_sha256": OWNER_STATEMENT_SHA256,
        "decision": "execute_fixed_two_seed_domain_minilm_fine_tuning_and_release_gate",
        "authorized_actions": [
            "fine_tune_frozen_minilm_on_t3_binary_pairs_only",
            "early_stop_each_seed_on_frozen_t2_ranker_selection_mrr_at_10",
            "publish_two_safetensors_checkpoints_after_model_release_gate",
        ],
        "prohibited_actions": [
            "generic_vs_domain_winner_selection",
            "calibration_fit_or_threshold_selection",
            "positive_test_or_negative_holdout_read_or_scoring",
            "no_match_development_read_or_scoring",
            "fresh_final_evaluation",
            "runtime_change_or_activation",
            "pickle_or_optimizer_state_publication",
        ],
        "parent_bindings": {
            "governance_v2_file_sha256": FROZEN_GOVERNANCE_V2_FILE_SHA256,
            "t3_manifest_file_sha256": FROZEN_T3_MANIFEST_FILE_SHA256,
            "t3_manifest_content_sha256": t3_manifest["manifest_sha256"],
            "t3_pair_sha256": FROZEN_T3_PAIRS_SHA256,
            "t3_package_sha256": FROZEN_T3_PACKAGE_SHA256,
            "t2_pool_manifest_content_sha256": pool_manifest["manifest_sha256"],
            "t2_private_pool_sha256": FROZEN_T2_PRIVATE_POOLS_SHA256,
            "base_config_sha256": FROZEN_BASE_CONFIG_SHA256,
            "base_manifest_sha256": FROZEN_BASE_MANIFEST_SHA256,
            "base_weights_sha256": FROZEN_BASE_WEIGHTS_SHA256,
            "training_code_commit": code_commit,
            "training_module_sha256": _file_sha256(
                root / "src/product_variant_resolver/domain_ranker_training.py"
            ),
        },
        "recipe": training_recipe(),
        "rights_state": "owner_attested_not_independently_verified",
        "authority_scope": "frozen_third_party_catalog_relative_not_manufacturer_or_global_truth",
    }
    return {**body, "authorization_sha256": _content_sha256(body)}


def training_recipe() -> dict[str, Any]:
    return {
        "base_model_id": BASE_MODEL_ID,
        "base_model_revision": BASE_MODEL_REVISION,
        "objective": "binary_relevance_bce_with_logits",
        "serialization": "query_text_then_candidate_text",
        "seeds": list(SEEDS),
        "max_epochs": MAX_EPOCHS,
        "early_stopping_metric": "ranker_selection_mrr_at_10",
        "early_stopping_patience": EARLY_STOPPING_PATIENCE,
        "early_stopping_min_delta": MIN_DELTA,
        "batch_size": BATCH_SIZE,
        "evaluation_batch_size": EVAL_BATCH_SIZE,
        "learning_rate": LEARNING_RATE,
        "weight_decay": WEIGHT_DECAY,
        "warmup_ratio": WARMUP_RATIO,
        "max_length": MAX_LENGTH,
        "gradient_clip_norm": GRADIENT_CLIP_NORM,
        "device": "cpu",
        "training_checkpoint_dtype": "float32",
        "published_checkpoint_dtype": "float16",
    }


def load_training_examples(root: Path) -> tuple[TrainingExample, ...]:
    rows = _load_jsonl(root / T3_PAIR_PATH)
    if len(rows) != 345:
        raise ValueError("T3 pair count differs from the frozen 345-row contract")
    examples: list[TrainingExample] = []
    pair_ids: set[str] = set()
    query_ids: set[str] = set()
    for row in rows:
        pair_id = _string(row.get("pair_id"), "pair ID")
        if pair_id in pair_ids:
            raise ValueError("duplicate pair ID")
        pair_ids.add(pair_id)
        query_ids.add(_string(row.get("query_id"), "query ID"))
        if row.get("positive_label") != 1 or row.get("negative_label") != 0:
            raise ValueError("T3 pair labels differ from the binary contract")
        query = _string(row.get("query_text"), "query text")
        positive = _string(row.get("positive_text"), "positive text")
        negative = _string(row.get("negative_text"), "negative text")
        examples.extend(
            (
                TrainingExample(query=query, candidate=positive, label=1.0),
                TrainingExample(query=query, candidate=negative, label=0.0),
            )
        )
    if len(query_ids) != 69 or len(examples) != 690:
        raise ValueError("T4 training projection differs from the frozen 69-query/690-example set")
    return tuple(examples)


def load_selection_pools(root: Path) -> tuple[dict[str, Any], ...]:
    payload = _load_object(root / LOCAL_POOLS_PATH)
    _validate_content_digest(payload, "content_sha256", "T2 private candidate pools")
    raw_rows = payload.get("rows")
    if not isinstance(raw_rows, list):
        raise TypeError("T2 private candidate-pool rows are missing")
    selected: list[dict[str, Any]] = []
    for raw in raw_rows:
        if not isinstance(raw, dict):
            raise TypeError("T2 candidate-pool row must be an object")
        if raw.get("partition") == "ranker_selection":
            candidates = raw.get("candidates")
            if not isinstance(candidates, list) or len(candidates) != 25:
                raise ValueError("selection pool must contain exactly 25 candidates")
            selected.append(raw)
    if len(selected) != 30:
        raise ValueError("T4 early stopping requires exactly 30 frozen selection queries")
    return tuple(sorted(selected, key=lambda row: _string(row.get("case_id"), "case ID")))


def mrr_at_10_from_scores(
    pools: Sequence[Mapping[str, Any]], scores: Sequence[Sequence[float]]
) -> float:
    if len(pools) != len(scores) or not pools:
        raise ValueError("selection pools and score rows must be non-empty and aligned")
    reciprocal_sum = 0.0
    for pool, row_scores in zip(pools, scores, strict=True):
        candidates = pool.get("candidates")
        if not isinstance(candidates, list) or len(candidates) != len(row_scores):
            raise ValueError("candidate and score counts differ")
        target_uuid = _string(pool.get("target_uuid"), "selection target UUID")
        ranked: list[tuple[float, str]] = []
        for candidate, score in zip(candidates, row_scores, strict=True):
            if not isinstance(candidate, dict):
                raise TypeError("selection candidate must be an object")
            numeric_score = float(score)
            if not math.isfinite(numeric_score):
                raise ValueError("selection score is non-finite")
            ranked.append(
                (numeric_score, _string(candidate.get("canonical_uuid"), "candidate UUID"))
            )
        ranked.sort(key=lambda item: (-item[0], item[1]))
        rank = next(
            (index for index, (_, uuid) in enumerate(ranked, 1) if uuid == target_uuid), None
        )
        if rank is None:
            raise ValueError("selection target is absent from its frozen pool")
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
        if item.selection_mrr_at_10 > best_metric + MIN_DELTA:
            best_epoch = item.epoch
            best_metric = item.selection_mrr_at_10
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
        raise RuntimeError(
            "DRSP-T4 requires the pinned reranking dependencies in the project virtualenv"
        ) from error
    tokenizer_class = getattr(transformers, "AutoTokenizer", None)
    model_class = getattr(transformers, "AutoModelForSequenceClassification", None)
    save_file = getattr(safetensors_torch, "save_file", None)
    if tokenizer_class is None or model_class is None or not callable(save_file):
        raise RuntimeError("installed training dependencies are incompatible")
    return torch, tokenizer_class, model_class, save_file


def _configure_determinism(torch: Any, seed: int) -> None:
    random.seed(seed)
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    torch.manual_seed(seed)
    torch.use_deterministic_algorithms(True)
    torch.set_num_threads(1)


def _tokenized_batch(tokenizer: Any, rows: Sequence[TrainingExample], torch: Any) -> dict[str, Any]:
    encoded = tokenizer(
        [row.query for row in rows],
        [row.candidate for row in rows],
        padding=True,
        truncation=True,
        max_length=MAX_LENGTH,
        return_tensors="pt",
    )
    encoded["labels"] = torch.tensor([row.label for row in rows], dtype=torch.float32)
    return cast(dict[str, Any], encoded)


def _score_selection(model: Any, tokenizer: Any, pools: Sequence[dict[str, Any]], torch: Any) -> float:
    flattened: list[tuple[str, str]] = []
    widths: list[int] = []
    for pool in pools:
        query = _string(pool.get("query"), "selection query")
        candidates = cast(list[dict[str, Any]], pool["candidates"])
        widths.append(len(candidates))
        flattened.extend(
            (query, _string(candidate.get("rendered_text"), "selection candidate text"))
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
    score_rows: list[tuple[float, ...]] = []
    cursor = 0
    for width in widths:
        score_rows.append(tuple(raw_scores[cursor : cursor + width]))
        cursor += width
    return mrr_at_10_from_scores(pools, score_rows)


def _save_half_checkpoint(model: Any, destination: Path, save_file: Any) -> None:
    state = {}
    for name, tensor in cast(TensorMapping, model.state_dict()).items():
        value = tensor.detach().cpu().contiguous()
        if value.is_floating_point():
            value = value.to(dtype=importlib.import_module("torch").float16)
        state[name] = value
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Keep the tensor file free of unordered metadata maps. Complete model and
    # provenance metadata lives in the canonical package manifest, making the
    # safetensors bytes reproducible rather than merely behaviorally equivalent.
    save_file(state, str(destination))


def _train_seed(
    root: Path,
    seed: int,
    examples: Sequence[TrainingExample],
    pools: Sequence[dict[str, Any]],
    scratch_directory: Path,
) -> tuple[SeedResult, Path]:
    torch, tokenizer_class, model_class, save_file = _load_training_dependencies()
    _configure_determinism(torch, seed)
    tokenizer = tokenizer_class.from_pretrained(
        root / BASE_MODEL_DIRECTORY,
        local_files_only=True,
        trust_remote_code=False,
    )
    model = model_class.from_pretrained(
        root / BASE_MODEL_DIRECTORY,
        local_files_only=True,
        trust_remote_code=False,
        use_safetensors=True,
        dtype=torch.float32,
    )
    model.train()
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=LEARNING_RATE, weight_decay=WEIGHT_DECAY
    )
    total_steps = MAX_EPOCHS * math.ceil(len(examples) / BATCH_SIZE)
    warmup_steps = max(1, round(total_steps * WARMUP_RATIO))

    def learning_rate_lambda(step: int) -> float:
        if step < warmup_steps:
            return float(step + 1) / float(warmup_steps)
        remaining = max(0, total_steps - step)
        return float(remaining) / float(max(1, total_steps - warmup_steps))

    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, learning_rate_lambda)
    criterion = torch.nn.BCEWithLogitsLoss()
    rng = random.Random(seed)
    order = list(range(len(examples)))
    history: list[EpochMetric] = []
    best_metric = -math.inf
    stale = 0
    best_path = scratch_directory / f"seed-{seed}" / "model.safetensors"
    for epoch in range(1, MAX_EPOCHS + 1):
        rng.shuffle(order)
        losses: list[float] = []
        model.train()
        for start in range(0, len(order), BATCH_SIZE):
            rows = [examples[index] for index in order[start : start + BATCH_SIZE]]
            encoded = _tokenized_batch(tokenizer, rows, torch)
            labels = encoded.pop("labels")
            optimizer.zero_grad(set_to_none=True)
            logits = model(**encoded).logits.reshape(-1)
            loss = criterion(logits, labels)
            if not bool(torch.isfinite(loss)):
                raise ValueError("training loss became non-finite")
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), GRADIENT_CLIP_NORM)
            optimizer.step()
            scheduler.step()
            losses.append(float(loss.detach().cpu()))
        metric = _score_selection(model, tokenizer, pools, torch)
        history.append(
            EpochMetric(
                epoch=epoch,
                mean_loss=sum(losses) / len(losses),
                selection_mrr_at_10=metric,
            )
        )
        if metric > best_metric + MIN_DELTA:
            best_metric = metric
            stale = 0
            _save_half_checkpoint(model, best_path, save_file)
        else:
            stale += 1
        print(
            f"seed={seed} epoch={epoch} loss={history[-1].mean_loss:.8f} "
            f"selection_mrr_at_10={metric:.8f}",
            flush=True,
        )
        if stale >= EARLY_STOPPING_PATIENCE:
            break
    selected_epoch, stop_epoch, selected_metric = select_early_stopping(history)
    if not best_path.is_file():
        raise ValueError("training did not produce a best safetensors checkpoint")
    return (
        SeedResult(
            seed=seed,
            selected_epoch=selected_epoch,
            stop_epoch=stop_epoch,
            selected_mrr_at_10=selected_metric,
            history=tuple(history),
            checkpoint_sha256=_file_sha256(best_path),
            checkpoint_size=best_path.stat().st_size,
        ),
        best_path,
    )


def _copy_tokenizer_and_config(root: Path, staging: Path) -> None:
    shared = (
        "special_tokens_map.json",
        "tokenizer.json",
        "tokenizer_config.json",
        "vocab.txt",
    )
    for name in shared:
        # Normalize text assets to LF so public package bytes are platform-stable
        # and pass Git's whitespace gate even when the frozen cache uses CRLF.
        text = (root / BASE_MODEL_DIRECTORY / name).read_text(encoding="utf-8")
        (staging / name).write_text(text, encoding="utf-8", newline="\n")
    base_config = _load_object(root / BASE_MODEL_DIRECTORY / "config.json")
    base_config["torch_dtype"] = "float16"
    for seed in SEEDS:
        seed_directory = staging / f"seed-{seed}"
        seed_directory.mkdir(parents=True, exist_ok=True)
        (seed_directory / "config.json").write_bytes(_canonical_bytes(base_config))


def _license_text() -> str:
    return """Apache License
Version 2.0, January 2004
https://www.apache.org/licenses/

Copyright 2026 Product Variant Resolver contributors

Licensed under the Apache License, Version 2.0 (the \"License\");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an \"AS IS\" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""


def _model_card(results: Sequence[SeedResult]) -> str:
    lines = "\n".join(
        f"- Seed {result.seed}: selected epoch {result.selected_epoch}, "
        f"early-stop epoch {result.stop_epoch}, selection MRR@10 "
        f"{result.selected_mrr_at_10:.8f}."
        for result in results
    )
    return f"""# Product Variant Resolver domain MiniLM checkpoints v1

These two checkpoints fine-tune `{BASE_MODEL_ID}` revision `{BASE_MODEL_REVISION}` on the
released DRSP-T3 binary hard-negative pairs. They are experimental ranking artifacts for the
frozen Hot Wheels community-catalog-relative resolver task.

## Training

- Objective: binary Pointwise relevance with BCE-with-logits.
- Seeds: 17 and 29; fixed recipe; train data only from the 345 T3 pairs.
- Early stopping: frozen 30-query ranker-selection MRR@10; no final or calibration data.
- Published weights: float16 safetensors only; no optimizer state or pickle payload.

{lines}

## Intended use and limitations

Use only for offline candidate reranking and the separately gated DRSP-T5 comparison. These
weights are not a product identifier by themselves, are not manufacturer-certified, and do not
establish global truth. The data and redistribution permissions are owner-attested and were not
independently verified. Color and edition remain incomplete. T4 does not select a winner, calibrate
confidence, evaluate a final holdout, activate runtime, or expose an inference endpoint.
"""


def _notice() -> str:
    return f"""Product Variant Resolver domain MiniLM checkpoints v1

Base model: {BASE_MODEL_ID}
Pinned revision: {BASE_MODEL_REVISION}
Base-model license recorded by the frozen local manifest: Apache-2.0.

The derived checkpoints are distributed under Apache-2.0. Training used a minimized T3 pair
projection whose source/redistribution rights are owner-attested, not independently verified.
Catalog-relative labels are not Mattel/manufacturer certification or global truth. See MODEL_CARD.md
and manifest.json for complete lineage and limitations.
"""


def _package_gitignore() -> str:
    allowed = "\n".join(f"!/{name}" for name in sorted(PACKAGE_FILES - {".gitignore"}))
    directories = "\n".join(f"!/{name}/" for name in ("seed-17", "seed-29"))
    return f"*\n!/.gitignore\n{directories}\n{allowed}\n"


def _scan_text_files(directory: Path, names: Sequence[str]) -> dict[str, int]:
    findings = {label: 0 for label, _ in _FORBIDDEN_TEXT_PATTERNS}
    for name in names:
        text = (directory / name).read_text(encoding="utf-8")
        for label, pattern in _FORBIDDEN_TEXT_PATTERNS:
            findings[label] += len(pattern.findall(text))
    if any(findings.values()):
        raise ValueError(f"checkpoint text package contains forbidden material: {findings}")
    return findings


def _validate_exact_package_files(directory: Path) -> None:
    actual: set[str] = set()
    for path in directory.rglob("*"):
        if path.is_symlink():
            raise ValueError("checkpoint package must not contain symlinks")
        if path.is_file():
            actual.add(path.relative_to(directory).as_posix())
    if actual != PACKAGE_FILES:
        raise ValueError(
            f"checkpoint package file allowlist mismatch; missing={sorted(PACKAGE_FILES - actual)}, "
            f"extra={sorted(actual - PACKAGE_FILES)}"
        )


def _validate_safetensors(path: Path) -> dict[str, list[int]]:
    try:
        safetensors = importlib.import_module("safetensors")
    except ImportError as error:
        raise RuntimeError("safetensors is required for checkpoint validation") from error
    safe_open = getattr(safetensors, "safe_open", None)
    if not callable(safe_open):
        raise TypeError("installed safetensors API is incompatible")
    shapes: dict[str, list[int]] = {}
    with safe_open(str(path), framework="pt", device="cpu") as handle:
        # ``safe_open`` exposes keys() but is not a Mapping or iterable.
        for key in handle.keys():  # noqa: SIM118
            tensor = handle.get_tensor(key)
            shapes[key] = list(tensor.shape)
    if not shapes or not any(key.endswith("classifier.weight") for key in shapes):
        raise ValueError("checkpoint tensors do not match a sequence classifier")
    return shapes


def _validate_offline_load(directory: Path) -> None:
    torch, tokenizer_class, model_class, _ = _load_training_dependencies()
    tokenizer_class.from_pretrained(
        directory,
        local_files_only=True,
        trust_remote_code=False,
    )
    for seed in SEEDS:
        model_class.from_pretrained(
            directory / f"seed-{seed}",
            local_files_only=True,
            trust_remote_code=False,
            use_safetensors=True,
            dtype=torch.float32,
        )


def _package_digest(files_sha256: Mapping[str, str]) -> str:
    return _content_sha256({"schema": "pvr-drsp-t4-package-digest-v1", "files": files_sha256})


def _materialize_package(
    root: Path,
    authorization: Mapping[str, Any],
    results: Sequence[SeedResult],
    checkpoints: Mapping[int, Path],
) -> None:
    PACKAGE_DIRECTORY_ABS = root / PACKAGE_DIRECTORY
    PACKAGE_DIRECTORY_ABS.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".public-checkpoint-v1-", dir=PACKAGE_DIRECTORY_ABS.parent))
    try:
        _copy_tokenizer_and_config(root, stage)
        for result in results:
            destination = stage / f"seed-{result.seed}" / "model.safetensors"
            shutil.copyfile(checkpoints[result.seed], destination)
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
            name: _file_sha256(stage / name)
            for name in sorted(PACKAGE_FILES - {"manifest.json"})
        }
        manifest_body: dict[str, Any] = {
            "schema_version": SCHEMA_MANIFEST,
            "version": VERSION,
            "status": "published_release_gate_passed",
            "published": True,
            "release_gate_passed": True,
            "authorization_sha256": authorization["authorization_sha256"],
            "bindings": cast(Mapping[str, Any], authorization["parent_bindings"]),
            "recipe": training_recipe(),
            "training": {
                "pair_count": 345,
                "training_query_count": 69,
                "binary_example_count": 690,
                "selection_query_count": 30,
                "results": [asdict(result) for result in results],
                "generic_vs_domain_winner_selected": False,
            },
            "files_sha256": preliminary_files,
            "tensor_schema_sha256": _content_sha256(tensor_shapes),
            "guardrails": {
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
                "base_license_evidence": "frozen_local_manifest_reports_Apache-2.0",
                "artifact_license_and_notice_present": True,
                "model_card_and_intended_use_limitations_present": True,
                "training_rights_limitation_disclosed": True,
                "source_lineage_and_sha256_complete": True,
                "safetensors_only": True,
                "offline_load_trust_remote_code_false": True,
                "permanent_holdout_intersection": 0,
                "text_scan_passed": True,
                "ordinary_git_blob_max_checkpoint_bytes": max(
                    result.checkpoint_size for result in results
                ),
                "ordinary_git_blob_under_50_mib": max(
                    result.checkpoint_size for result in results
                ) < 50 * 1024 * 1024,
            },
            "rights_state": "owner_attested_not_independently_verified",
            "limitations": [
                "not_manufacturer_or_global_truth",
                "training_and_redistribution_rights_not_independently_verified",
                "selection_partition_used_only_for_early_stopping",
                "winner_selection_deferred_to_DRSP-T5",
                "no_calibration_final_evaluation_or_runtime_activation",
            ],
            "next_allowed_action": "DRSP-T5_requires_separate_owner_authorization",
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
        if PACKAGE_DIRECTORY_ABS.exists():
            shutil.rmtree(PACKAGE_DIRECTORY_ABS)
        os.replace(stage, PACKAGE_DIRECTORY_ABS)
    finally:
        if stage.exists():
            shutil.rmtree(stage)


def train(root: Path) -> dict[str, Any]:
    code_commit = _current_git_commit(root)
    authorization = build_authorization(root, code_commit)
    examples = load_training_examples(root)
    pools = load_selection_pools(root)
    scratch = root / LOCAL_DIRECTORY
    if scratch.exists():
        shutil.rmtree(scratch)
    scratch.mkdir(parents=True, mode=0o700)
    results: list[SeedResult] = []
    checkpoints: dict[int, Path] = {}
    try:
        for seed in SEEDS:
            result, checkpoint = _train_seed(root, seed, examples, pools, scratch)
            results.append(result)
            checkpoints[seed] = checkpoint
        _materialize_package(root, authorization, results, checkpoints)
    finally:
        if scratch.exists():
            shutil.rmtree(scratch)
    return check(root)


def check(root: Path) -> dict[str, Any]:
    directory = root / PACKAGE_DIRECTORY
    _validate_exact_package_files(directory)
    authorization = _load_object(root / AUTHORIZATION_PATH)
    _validate_content_digest(authorization, "authorization_sha256", "T4 authorization")
    manifest = _load_object(root / MANIFEST_PATH)
    _validate_content_digest(manifest, "manifest_sha256", "T4 manifest")
    if (
        manifest.get("release_gate_passed") is not True
        or manifest.get("published") is not True
        or manifest.get("authorization_sha256") != authorization.get("authorization_sha256")
        or manifest.get("next_allowed_action")
        != "DRSP-T5_requires_separate_owner_authorization"
    ):
        raise ValueError("T4 checkpoint release state is invalid")
    file_hashes = manifest.get("files_sha256")
    if not isinstance(file_hashes, dict):
        raise TypeError("T4 manifest file hashes are missing")
    for name in sorted(PACKAGE_FILES - {"manifest.json"}):
        if file_hashes.get(name) != _file_sha256(directory / name):
            raise ValueError(f"T4 package file hash differs: {name}")
    if manifest.get("package_sha256") != _package_digest(
        cast(Mapping[str, str], file_hashes)
    ):
        raise ValueError("T4 package digest is stale")
    for name in WEIGHT_FILES:
        _validate_safetensors(directory / name)
    _scan_text_files(directory, TEXT_FILES)
    _validate_offline_load(directory)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Train or validate the frozen DRSP-T4 ranker")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true", help="validate the existing package only")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = args.root.resolve()
    manifest = check(root) if args.check else train(root)
    print(
        json.dumps(
            {
                "status": "valid" if args.check else "trained",
                "package_sha256": manifest["package_sha256"],
                "results": manifest["training"]["results"],
            },
            ensure_ascii=False,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
