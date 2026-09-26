"""Deterministic contracts for the neural reranker comparison experiment.

This module deliberately has no eager neural-library import.  It defines the public data boundary,
feature order, ranking arithmetic, metrics, model adapters, and label-blind validation while keeping
Torch, Sentence Transformers, and safetensors behind explicit lazy boundaries.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import math
import os
import shutil
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Protocol, cast
from uuid import UUID

ARMS = ("rrf", "neural_pointwise", "neural_listwise")
SPLITS = ("train", "dev", "test")
SOURCE_NAMES = ("sparse", "dense", "structured")
STRUCTURED_NAMES = ("year", "collector_number", "series_position", "color", "series")

FEATURE_SCHEMA = (
    "pointwise_logit",
    "rrf_score",
    "reciprocal_rrf_rank",
    "sparse_present",
    "dense_present",
    "structured_present",
    "reciprocal_sparse_rank",
    "reciprocal_dense_rank",
    "reciprocal_structured_rank",
    "year_match",
    "collector_number_match",
    "series_position_match",
    "color_match",
    "series_match",
    "year_conflict",
    "collector_number_conflict",
    "series_position_conflict",
    "color_conflict",
    "series_conflict",
    "match_count_over_five",
    "conflict_count_over_five",
)

EXPECTED_SPLIT_COUNTS = {"train": 58, "dev": 21, "test": 21}
EXPECTED_STATUS_COUNTS = {
    "train": {"matched": 36, "ambiguous": 12, "no_match": 10},
    "dev": {"matched": 12, "ambiguous": 4, "no_match": 5},
    "test": {"matched": 12, "ambiguous": 4, "no_match": 5},
}
EXPECTED_HARD_NEGATIVE_COUNTS = {"train": 34, "dev": 13, "test": 13}
EXPECTED_MATCHED_HARD_NEGATIVE_COUNTS = {"train": 12, "dev": 4, "test": 4}

LABEL_KEYS = frozenset(
    {
        "expected_status",
        "expected_uuid",
        "expected_canonical_uuid",
        "expected_canonical_id",
        "expected_label",
        "label",
        "labels",
        "label_notes",
        "ground_truth",
        "casting_family",
        "failure_category",
        "hard_negative",
        "target",
        "target_id",
        "target_uuid",
        "target_rank",
        "relevance",
        "is_positive",
    }
)
RESULT_KEYS = frozenset(
    {
        "winner",
        "eligible",
        "eligibility",
        "gate",
        "gates",
        "metric",
        "metrics",
        "accuracy",
        "recommendation",
    }
)
POOL_SCORE_KEYS = frozenset(
    {
        "pointwise_score",
        "pointwise_logit",
        "pointwise_rank",
        "listwise_score",
        "listwise_logit",
        "listwise_rank",
        "neural_score",
        "neural_rank",
    }
)

POINTWISE_MODEL_ID = "cross-encoder/ms-marco-MiniLM-L6-v2"
POINTWISE_REVISION = "233902d25c440f23af6f7d6e94d2946bac0bee0a"
POINTWISE_LICENSE = "Apache-2.0"
POINTWISE_MANIFEST_NAME = "manifest.json"
POINTWISE_REQUIRED_FILES = (
    "config.json",
    "model.safetensors",
    "special_tokens_map.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.txt",
)
LISTWISE_SEED = 20260924
LISTWISE_INPUT_DIM = 21
LISTWISE_HIDDEN_DIM = 32
LISTWISE_ATTENTION_HEADS = 4
LISTWISE_FEEDFORWARD_DIM = 64
LISTWISE_DROPOUT = 0.0
LISTWISE_LEARNING_RATE = 1e-3
LISTWISE_WEIGHT_DECAY = 1e-4
LISTWISE_BATCH_SIZE = 8
LISTWISE_MAX_EPOCHS = 100
LISTWISE_PATIENCE = 10
NORMALIZED_FEATURE_INDICES = (0, 1)
LISTWISE_ARCHITECTURE = (
    ("input_dim", LISTWISE_INPUT_DIM),
    ("hidden_dim", LISTWISE_HIDDEN_DIM),
    ("attention_heads", LISTWISE_ATTENTION_HEADS),
    ("feedforward_dim", LISTWISE_FEEDFORWARD_DIM),
    ("encoder_layers", 1),
    ("dropout", LISTWISE_DROPOUT),
    ("positional_embeddings", False),
)
UNSAFE_MODEL_SUFFIXES = frozenset(
    {".bin", ".ckpt", ".dill", ".exe", ".pkl", ".pickle", ".pt", ".pth", ".py", ".so"}
)

Split = Literal["train", "dev", "test"]
Direction = Literal["improved", "unchanged", "regressed"]
AcquisitionStatus = Literal["created", "unchanged"]


class SnapshotDownloader(Protocol):
    def __call__(
        self,
        *,
        model_id: str,
        revision: str,
        allowed_files: tuple[str, ...],
        cache_dir: Path,
    ) -> Path: ...


class CrossEncoderModel(Protocol):
    def predict(
        self,
        sentences: Sequence[tuple[str, str]],
        *,
        batch_size: int,
        show_progress_bar: bool,
        convert_to_numpy: bool,
    ) -> object: ...


class CrossEncoderFactory(Protocol):
    def __call__(self, model_name: str, **kwargs: object) -> CrossEncoderModel: ...


class SafeTensorAdapter(Protocol):
    def save_file(
        self,
        tensors: Mapping[str, object],
        filename: str,
        metadata: Mapping[str, str] | None = None,
    ) -> None: ...

    def load_file(self, filename: str, device: str = "cpu") -> Mapping[str, object]: ...


@dataclass(frozen=True, slots=True)
class PointwiseModelConfig:
    experiment_id: str
    model_id: str
    revision: str
    license: str
    required_files: tuple[str, ...]
    allowed_files: tuple[str, ...]
    device: str
    dtype: str
    num_labels: int
    max_length: int
    local_files_only: bool
    trust_remote_code: bool
    config_sha256: str


@dataclass(frozen=True, slots=True)
class ModelFileRecord:
    path: str
    size: int
    sha256: str


@dataclass(frozen=True, slots=True)
class LocalModelManifest:
    schema_version: int
    model_id: str
    revision: str
    license: str
    config_sha256: str
    files: tuple[ModelFileRecord, ...]


@dataclass(frozen=True, slots=True)
class FeatureNormalizer:
    feature_schema: tuple[str, ...]
    normalized_indices: tuple[int, ...]
    means: tuple[float, ...]
    standard_deviations: tuple[float, ...]
    fitted_split: str = "train"

    def __post_init__(self) -> None:
        if self.feature_schema != FEATURE_SCHEMA:
            raise ValueError("normalizer feature schema differs from the frozen 21-field schema")
        if self.normalized_indices != NORMALIZED_FEATURE_INDICES:
            raise ValueError("normalizer may only transform pointwise_logit and rrf_score")
        if len(self.means) != 2 or len(self.standard_deviations) != 2:
            raise ValueError("normalizer requires exactly two means and standard deviations")
        if self.fitted_split != "train":
            raise ValueError("normalizer must be fitted from train only")
        for value in (*self.means, *self.standard_deviations):
            _require_finite(value, "normalizer statistic")
        if any(value <= 0 for value in self.standard_deviations):
            raise ValueError("normalizer standard deviations must be positive")

    def transform(self, row: Sequence[float]) -> tuple[float, ...]:
        values = _validated_feature_row(row)
        result = list(values)
        for offset, feature_index in enumerate(self.normalized_indices):
            result[feature_index] = (
                result[feature_index] - self.means[offset]
            ) / self.standard_deviations[offset]
        return tuple(result)


@dataclass(frozen=True, slots=True)
class ListwiseExample:
    features: tuple[tuple[float, ...], ...]
    target_index: int

    def __post_init__(self) -> None:
        if not self.features or len(self.features) > 25:
            raise ValueError("listwise example requires between 1 and 25 candidates")
        for row in self.features:
            _validated_feature_row(row)
        if not 0 <= self.target_index < len(self.features):
            raise ValueError("listwise target_index is outside the candidate list")


@dataclass(frozen=True, slots=True)
class TrainingEpoch:
    epoch: int
    train_loss: float
    dev_mrr_at_10: float

    def __post_init__(self) -> None:
        if self.epoch < 1:
            raise ValueError("training epoch must be positive")
        _require_finite(self.train_loss, "training loss")
        _require_finite(self.dev_mrr_at_10, "dev MRR@10")
        if self.train_loss < 0 or not 0 <= self.dev_mrr_at_10 <= 1:
            raise ValueError("training epoch contains an invalid metric")


@dataclass(frozen=True, slots=True)
class EarlyStoppingSelection:
    selected_epoch: int
    stop_epoch: int
    selected_dev_mrr_at_10: float


@dataclass(slots=True)
class ListwiseTrainingResult:
    model: object
    normalizer: FeatureNormalizer
    history: tuple[TrainingEpoch, ...]
    selected_epoch: int
    selected_dev_mrr_at_10: float


@dataclass(frozen=True, slots=True)
class ListwiseCheckpointManifest:
    schema_version: int
    feature_schema: tuple[str, ...]
    feature_schema_sha256: str
    architecture: tuple[tuple[str, int | float | bool], ...]
    seed: int
    selected_epoch: int
    normalizer: FeatureNormalizer
    tensor_shapes: tuple[tuple[str, tuple[int, ...]], ...]
    checkpoint_sha256: str


def _config_string(row: Mapping[str, object], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"pointwise config requires nonblank {key}")
    return value


def _config_bool(row: Mapping[str, object], key: str) -> bool:
    value = row.get(key)
    if not isinstance(value, bool):
        raise TypeError(f"pointwise config requires boolean {key}")
    return value


def _config_int(row: Mapping[str, object], key: str) -> int:
    value = row.get(key)
    if not isinstance(value, int) or isinstance(value, bool):
        raise TypeError(f"pointwise config requires integer {key}")
    return value


def _config_files(row: Mapping[str, object], key: str) -> tuple[str, ...]:
    value = row.get(key)
    if not isinstance(value, list) or not value:
        raise ValueError(f"pointwise config requires nonempty {key}")
    if any(not isinstance(item, str) or not item.strip() for item in value):
        raise ValueError(f"pointwise config {key} must contain nonblank paths")
    files = tuple(cast(list[str], value))
    if len(files) != len(set(files)):
        raise ValueError(f"pointwise config {key} contains duplicate paths")
    for name in files:
        path = Path(name)
        if path.name != name or path.is_absolute() or ".." in path.parts:
            raise ValueError(f"pointwise config {key} contains an unsafe path")
        if path.suffix.lower() in UNSAFE_MODEL_SUFFIXES:
            raise ValueError(f"pointwise config {key} contains an unsafe model file")
    return files


def load_pointwise_model_config(path: Path) -> PointwiseModelConfig:
    """Load and fail closed on any drift from the approved v1 pointwise contract."""

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read pointwise model config: {path}") from error
    if not isinstance(payload, Mapping):
        raise TypeError("neural reranker config must be an object")
    if payload.get("schema_version") != 1:
        raise ValueError("neural reranker config schema_version must be 1")
    experiment_id = payload.get("experiment_id")
    if experiment_id != "neural-reranker-comparison-v1":
        raise ValueError("neural reranker config has an unexpected experiment_id")
    pointwise_value = payload.get("pointwise")
    if not isinstance(pointwise_value, Mapping):
        raise TypeError("neural reranker config requires pointwise object")
    pointwise = cast(Mapping[str, object], pointwise_value)
    required_files = _config_files(pointwise, "required_files")
    allowed_files = _config_files(pointwise, "allowed_files")
    config = PointwiseModelConfig(
        experiment_id=experiment_id,
        model_id=_config_string(pointwise, "model_id"),
        revision=_config_string(pointwise, "revision"),
        license=_config_string(pointwise, "license"),
        required_files=required_files,
        allowed_files=allowed_files,
        device=_config_string(pointwise, "device"),
        dtype=_config_string(pointwise, "dtype"),
        num_labels=_config_int(pointwise, "num_labels"),
        max_length=_config_int(pointwise, "max_length"),
        local_files_only=_config_bool(pointwise, "local_files_only"),
        trust_remote_code=_config_bool(pointwise, "trust_remote_code"),
        config_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    if config.model_id != POINTWISE_MODEL_ID:
        raise ValueError("pointwise model_id differs from the approved v1 model")
    if config.revision != POINTWISE_REVISION:
        raise ValueError("pointwise revision differs from the approved immutable revision")
    if config.license != POINTWISE_LICENSE:
        raise ValueError("pointwise license differs from the approved Apache-2.0 declaration")
    if config.required_files != POINTWISE_REQUIRED_FILES:
        raise ValueError("pointwise required_files differs from the approved v1 snapshot")
    if config.allowed_files != config.required_files:
        raise ValueError("pointwise allowed_files must exactly equal required_files")
    if (
        config.device != "cpu"
        or config.dtype != "float32"
        or config.num_labels != 1
        or config.max_length != 128
    ):
        raise ValueError("pointwise runtime settings differ from the approved CPU float32 contract")
    if not config.local_files_only:
        raise ValueError("pointwise local_files_only must be true")
    if config.trust_remote_code:
        raise ValueError("pointwise trust_remote_code must be false")
    return config


def _model_file_records(
    directory: Path,
    files: tuple[str, ...],
    *,
    allow_source_symlinks: bool = False,
) -> tuple[ModelFileRecord, ...]:
    records: list[ModelFileRecord] = []
    for name in files:
        path = directory / name
        if not path.is_file() or (path.is_symlink() and not allow_source_symlinks):
            raise ValueError(f"pointwise snapshot is missing a regular file: {name}")
        records.append(
            ModelFileRecord(path=name, size=path.stat().st_size, sha256=sha256_path(path))
        )
    return tuple(records)


def _manifest_payload(manifest: LocalModelManifest) -> dict[str, object]:
    return {
        "schema_version": manifest.schema_version,
        "model_id": manifest.model_id,
        "revision": manifest.revision,
        "license": manifest.license,
        "config_sha256": manifest.config_sha256,
        "files": [
            {"path": item.path, "size": item.size, "sha256": item.sha256} for item in manifest.files
        ],
    }


def _parse_manifest(path: Path) -> LocalModelManifest:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("pointwise model manifest is missing or invalid") from error
    if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
        raise ValueError("pointwise model manifest schema is invalid")
    files_value = payload.get("files")
    if not isinstance(files_value, list):
        raise TypeError("pointwise model manifest requires files[]")
    records: list[ModelFileRecord] = []
    for item in files_value:
        if not isinstance(item, Mapping):
            raise TypeError("pointwise model manifest contains an invalid file record")
        name = item.get("path")
        size = item.get("size")
        digest = item.get("sha256")
        if (
            not isinstance(name, str)
            or not isinstance(size, int)
            or isinstance(size, bool)
            or size < 0
            or not isinstance(digest, str)
            or len(digest) != 64
        ):
            raise ValueError("pointwise model manifest contains an invalid file record")
        records.append(ModelFileRecord(path=name, size=size, sha256=digest))
    string_fields = {}
    for key in ("model_id", "revision", "license", "config_sha256"):
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"pointwise model manifest requires {key}")
        string_fields[key] = value
    return LocalModelManifest(
        schema_version=1,
        model_id=string_fields["model_id"],
        revision=string_fields["revision"],
        license=string_fields["license"],
        config_sha256=string_fields["config_sha256"],
        files=tuple(records),
    )


def validate_local_pointwise_model(
    config: PointwiseModelConfig,
    directory: Path,
) -> LocalModelManifest:
    """Validate provenance, exact file allowlist and every local snapshot byte."""

    if not directory.is_dir() or directory.is_symlink():
        raise ValueError("pointwise model directory is missing or unsafe")
    entries = {item.name for item in directory.iterdir()}
    expected = set(config.allowed_files) | {POINTWISE_MANIFEST_NAME}
    unexpected = entries - expected
    missing = expected - entries
    if unexpected:
        raise ValueError(
            f"pointwise model directory contains unexpected files: {sorted(unexpected)}"
        )
    if missing:
        raise ValueError(f"pointwise model directory is missing files: {sorted(missing)}")
    if any((directory / name).suffix.lower() in UNSAFE_MODEL_SUFFIXES for name in entries):
        raise ValueError("pointwise model directory contains an unsafe model file")
    manifest_path = directory / POINTWISE_MANIFEST_NAME
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ValueError("pointwise model manifest must be a regular local file")
    manifest = _parse_manifest(manifest_path)
    if (
        manifest.model_id != config.model_id
        or manifest.revision != config.revision
        or manifest.license != config.license
        or manifest.config_sha256 != config.config_sha256
    ):
        raise ValueError("pointwise model manifest provenance differs from config")
    actual_records = _model_file_records(directory, config.required_files)
    if manifest.files != actual_records:
        raise ValueError("pointwise model manifest file hashes or sizes do not match")
    return manifest


def _default_snapshot_downloader() -> SnapshotDownloader:
    try:
        module = importlib.import_module("huggingface_hub")
    except ImportError as error:
        raise RuntimeError(
            "neural reranking dependencies are missing; install "
            "'product-variant-resolver[reranking]' with "
            "constraints/reranking-python312.txt"
        ) from error
    snapshot_download = getattr(module, "snapshot_download", None)
    if not callable(snapshot_download):
        raise TypeError("huggingface_hub.snapshot_download is unavailable")

    def download(
        *,
        model_id: str,
        revision: str,
        allowed_files: tuple[str, ...],
        cache_dir: Path,
    ) -> Path:
        result = snapshot_download(
            repo_id=model_id,
            revision=revision,
            allow_patterns=list(allowed_files),
            ignore_patterns=["*.bin", "*.ckpt", "*.pkl", "*.pickle", "*.pt", "*.pth", "*.py"],
            cache_dir=str(cache_dir),
            local_files_only=False,
        )
        if not isinstance(result, str):
            raise TypeError("model acquisition returned an invalid snapshot path")
        return Path(result)

    return download


def acquire_pointwise_model(
    config: PointwiseModelConfig,
    destination: Path,
    *,
    confirm_license: bool,
    downloader: SnapshotDownloader | None = None,
) -> AcquisitionStatus:
    """Acquire one explicitly approved snapshot; this is the only network-capable boundary."""

    if not confirm_license:
        raise ValueError("model acquisition requires explicit Apache-2.0 license confirmation")
    if destination.exists():
        validate_local_pointwise_model(config, destination)
        return "unchanged"
    active_downloader = downloader if downloader is not None else _default_snapshot_downloader()
    with tempfile.TemporaryDirectory(prefix="pvr-pointwise-download-") as cache_name:
        snapshot = active_downloader(
            model_id=config.model_id,
            revision=config.revision,
            allowed_files=config.allowed_files,
            cache_dir=Path(cache_name),
        )
        if not snapshot.is_dir() or snapshot.is_symlink():
            raise ValueError("downloaded pointwise snapshot is missing or unsafe")
        entries = {item.name for item in snapshot.iterdir()}
        if entries != set(config.allowed_files):
            raise ValueError("downloaded pointwise snapshot differs from the exact file allowlist")
        # Hugging Face's download cache may expose immutable blobs through symlinks.  They are
        # accepted only at this acquisition boundary and copied as regular files; the published
        # local model directory rejects every symlink.
        source_records = _model_file_records(
            snapshot,
            config.required_files,
            allow_source_symlinks=True,
        )
        manifest = LocalModelManifest(
            schema_version=1,
            model_id=config.model_id,
            revision=config.revision,
            license=config.license,
            config_sha256=config.config_sha256,
            files=source_records,
        )

        destination.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix=f".{destination.name}-", dir=destination.parent))
        try:
            for name in config.required_files:
                shutil.copyfile(snapshot / name, stage / name)
            (stage / POINTWISE_MANIFEST_NAME).write_bytes(
                canonical_json_bytes(_manifest_payload(manifest))
            )
            validate_local_pointwise_model(config, stage)
            if destination.exists():
                raise FileExistsError(
                    f"pointwise destination appeared during acquisition: {destination}"
                )
            os.rename(stage, destination)
        finally:
            if stage.exists():
                shutil.rmtree(stage)
    validate_local_pointwise_model(config, destination)
    return "created"


def _default_cross_encoder_factory() -> CrossEncoderFactory:
    try:
        sentence_transformers = importlib.import_module("sentence_transformers")
        torch = importlib.import_module("torch")
    except ImportError as error:
        raise RuntimeError(
            "neural reranking dependencies are missing; install "
            "'product-variant-resolver[reranking]' with "
            "constraints/reranking-python312.txt"
        ) from error
    factory = getattr(sentence_transformers, "CrossEncoder", None)
    float32 = getattr(torch, "float32", None)
    if not callable(factory) or float32 is None:
        raise RuntimeError("installed neural reranking dependencies are incompatible")
    return cast(CrossEncoderFactory, factory)


@dataclass(slots=True)
class LocalPointwiseScorer:
    version: str
    model: CrossEncoderModel
    batch_size: int = 25

    @classmethod
    def load(
        cls,
        config: PointwiseModelConfig,
        model_directory: Path,
        *,
        factory: CrossEncoderFactory | None = None,
        torch_dtype: object | None = None,
        batch_size: int = 25,
    ) -> LocalPointwiseScorer:
        validate_local_pointwise_model(config, model_directory)
        active_factory = factory
        if active_factory is None:
            active_factory = _default_cross_encoder_factory()
            torch_module = importlib.import_module("torch")
            torch_dtype = torch_module.float32
        if torch_dtype is None:
            raise ValueError("pointwise loader requires an explicit float32 dtype")
        model = active_factory(
            str(model_directory),
            num_labels=config.num_labels,
            max_length=config.max_length,
            device=config.device,
            automodel_args={"torch_dtype": torch_dtype, "use_safetensors": True},
            trust_remote_code=False,
            local_files_only=True,
        )
        if batch_size < 1:
            raise ValueError("pointwise batch_size must be positive")
        return cls(
            version=f"{config.model_id}@{config.revision}", model=model, batch_size=batch_size
        )

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[float, ...]:
        if not pairs:
            return ()
        if any(not query.strip() or not candidate.strip() for query, candidate in pairs):
            raise ValueError("pointwise pairs require nonblank query and candidate text")
        raw = self.model.predict(
            pairs,
            batch_size=self.batch_size,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        if isinstance(raw, (str, bytes, bytearray)) or not isinstance(raw, Sequence):
            if hasattr(raw, "tolist"):
                raw = raw.tolist()
            else:
                raise ValueError("pointwise model returned a non-sequence result")
        values = tuple(float(value) for value in cast(Sequence[Any], raw))
        if len(values) != len(pairs):
            raise ValueError("pointwise model returned the wrong score count")
        for value in values:
            _require_finite(value, "pointwise score")
        return values


def _validated_feature_row(row: Sequence[float]) -> tuple[float, ...]:
    if len(row) != len(FEATURE_SCHEMA):
        raise ValueError("listwise feature row must use the frozen 21-field schema")
    values = tuple(float(value) for value in row)
    if not all(math.isfinite(value) for value in values):
        raise ValueError("listwise feature row contains a non-finite value")
    return values


def fit_train_feature_normalizer(
    train_rows: Sequence[Sequence[float]],
) -> FeatureNormalizer:
    """Fit the two approved continuous fields from Train rows only."""

    if not train_rows:
        raise ValueError("train normalizer requires at least one candidate row")
    rows = tuple(_validated_feature_row(row) for row in train_rows)
    means: list[float] = []
    standard_deviations: list[float] = []
    for feature_index in NORMALIZED_FEATURE_INDICES:
        values = [row[feature_index] for row in rows]
        mean = sum(values) / len(values)
        variance = sum((value - mean) ** 2 for value in values) / len(values)
        deviation = math.sqrt(variance)
        means.append(mean)
        standard_deviations.append(deviation if deviation > 0 else 1.0)
    return FeatureNormalizer(
        feature_schema=FEATURE_SCHEMA,
        normalized_indices=NORMALIZED_FEATURE_INDICES,
        means=tuple(means),
        standard_deviations=tuple(standard_deviations),
    )


def select_early_stopping_epoch(
    history: Sequence[TrainingEpoch],
    *,
    patience: int = LISTWISE_PATIENCE,
) -> EarlyStoppingSelection:
    """Choose the earliest best Dev epoch and stop after the fixed no-improvement budget."""

    if not history:
        raise ValueError("early stopping requires at least one epoch")
    if patience < 1:
        raise ValueError("early stopping patience must be positive")
    best_epoch = 0
    best_metric = -math.inf
    stale_epochs = 0
    stop_epoch = history[-1].epoch
    for expected_epoch, item in enumerate(history, start=1):
        if item.epoch != expected_epoch:
            raise ValueError("training history epochs must be contiguous from one")
        if item.epoch > LISTWISE_MAX_EPOCHS:
            raise ValueError("training history exceeds the fixed epoch budget")
        if item.dev_mrr_at_10 > best_metric:
            best_metric = item.dev_mrr_at_10
            best_epoch = item.epoch
            stale_epochs = 0
        else:
            stale_epochs += 1
        if stale_epochs >= patience:
            stop_epoch = item.epoch
            break
    return EarlyStoppingSelection(
        selected_epoch=best_epoch,
        stop_epoch=stop_epoch,
        selected_dev_mrr_at_10=best_metric,
    )


def _optional_dependency_error() -> RuntimeError:
    return RuntimeError(
        "neural reranking dependencies are missing; install "
        "'product-variant-resolver[reranking]' with "
        "constraints/reranking-python312.txt"
    )


def _load_torch() -> Any:
    try:
        return importlib.import_module("torch")
    except ImportError as error:
        raise _optional_dependency_error() from error


def _load_safetensors_torch() -> SafeTensorAdapter:
    try:
        module = importlib.import_module("safetensors.torch")
    except ImportError as error:
        raise _optional_dependency_error() from error
    if not callable(getattr(module, "save_file", None)) or not callable(
        getattr(module, "load_file", None)
    ):
        raise TypeError("installed safetensors.torch API is incompatible")
    return cast(SafeTensorAdapter, module)


def configure_torch_determinism(torch_module: Any) -> None:
    """Freeze the CPU seed and deterministic-algorithm mode before model creation."""

    torch_module.manual_seed(LISTWISE_SEED)
    torch_module.use_deterministic_algorithms(True)
    torch_module.set_num_threads(1)


def build_candidate_set_reranker(*, torch_module: Any | None = None) -> object:
    """Create the fixed no-position 21→32 one-layer candidate-set attention model."""

    torch = _load_torch() if torch_module is None else torch_module
    nn = torch.nn

    class CandidateSetReranker(nn.Module):  # type: ignore[misc, name-defined]
        def __init__(self) -> None:
            super().__init__()
            self.candidate_encoder = nn.Sequential(
                nn.Linear(LISTWISE_INPUT_DIM, LISTWISE_HIDDEN_DIM),
                nn.GELU(),
                nn.LayerNorm(LISTWISE_HIDDEN_DIM),
            )
            layer = nn.TransformerEncoderLayer(
                d_model=LISTWISE_HIDDEN_DIM,
                nhead=LISTWISE_ATTENTION_HEADS,
                dim_feedforward=LISTWISE_FEEDFORWARD_DIM,
                dropout=LISTWISE_DROPOUT,
                batch_first=True,
                device="cpu",
                dtype=torch.float32,
            )
            self.context_encoder = nn.TransformerEncoder(
                layer,
                num_layers=1,
                enable_nested_tensor=False,
            )
            self.score_head = nn.Linear(LISTWISE_HIDDEN_DIM, 1)

        def forward(self, features: Any, padding_mask: Any) -> Any:
            if features.ndim != 3 or features.shape[-1] != LISTWISE_INPUT_DIM:
                raise ValueError("listwise tensor must have shape [batch, candidates, 21]")
            if padding_mask.shape != features.shape[:2]:
                raise ValueError("listwise padding mask shape differs from candidate tensor")
            if bool(padding_mask.all(dim=1).any().item()):
                raise ValueError("listwise batch cannot contain an all-padding row")
            encoded = self.candidate_encoder(features)
            contextual = self.context_encoder(
                encoded,
                src_key_padding_mask=padding_mask,
            )
            logits = self.score_head(contextual).squeeze(-1)
            return logits.masked_fill(padding_mask, float("-inf"))

    model = CandidateSetReranker()
    return model.to(device="cpu", dtype=torch.float32)


def _padded_listwise_batch(
    examples: Sequence[ListwiseExample],
    normalizer: FeatureNormalizer,
    torch_module: Any,
) -> tuple[Any, Any, Any]:
    if not examples:
        raise ValueError("listwise batch cannot be empty")
    largest_list = max(len(example.features) for example in examples)
    feature_rows: list[list[tuple[float, ...]]] = []
    padding_rows: list[list[bool]] = []
    targets: list[int] = []
    zero_row = (0.0,) * LISTWISE_INPUT_DIM
    for example in examples:
        normalized = [normalizer.transform(row) for row in example.features]
        padding = largest_list - len(normalized)
        feature_rows.append([*normalized, *([zero_row] * padding)])
        padding_rows.append([False] * len(normalized) + [True] * padding)
        targets.append(example.target_index)
    features = torch_module.tensor(feature_rows, dtype=torch_module.float32, device="cpu")
    padding_mask = torch_module.tensor(padding_rows, dtype=torch_module.bool, device="cpu")
    target_tensor = torch_module.tensor(targets, dtype=torch_module.long, device="cpu")
    return features, padding_mask, target_tensor


def _dev_mrr_at_10(
    model: Any,
    examples: Sequence[ListwiseExample],
    normalizer: FeatureNormalizer,
    torch_module: Any,
) -> float:
    model.eval()
    reciprocal_sum = 0.0
    with torch_module.no_grad():
        for start in range(0, len(examples), LISTWISE_BATCH_SIZE):
            batch = examples[start : start + LISTWISE_BATCH_SIZE]
            features, padding_mask, targets = _padded_listwise_batch(
                batch, normalizer, torch_module
            )
            logits = model(features, padding_mask)
            orders = logits.argsort(dim=1, descending=True).tolist()
            target_values = targets.tolist()
            for order, target in zip(orders, target_values, strict=True):
                rank = order.index(target) + 1
                if rank <= 10:
                    reciprocal_sum += 1.0 / rank
    return reciprocal_sum / len(examples)


def train_listwise_model(
    train_examples: Sequence[ListwiseExample],
    dev_examples: Sequence[ListwiseExample],
    *,
    torch_module: Any | None = None,
) -> ListwiseTrainingResult:
    """Train only the small listwise head; Dev selects an epoch and never fits statistics."""

    if not train_examples or not dev_examples:
        raise ValueError("listwise training requires nonempty Train and Dev examples")
    torch = _load_torch() if torch_module is None else torch_module
    configure_torch_determinism(torch)
    normalizer = fit_train_feature_normalizer(
        [row for example in train_examples for row in example.features]
    )
    model = cast(Any, build_candidate_set_reranker(torch_module=torch))
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=LISTWISE_LEARNING_RATE,
        weight_decay=LISTWISE_WEIGHT_DECAY,
    )
    history: list[TrainingEpoch] = []
    best_metric = -math.inf
    best_state: dict[str, object] | None = None
    stale_epochs = 0
    for epoch in range(1, LISTWISE_MAX_EPOCHS + 1):
        model.train()
        total_loss = 0.0
        batch_count = 0
        for start in range(0, len(train_examples), LISTWISE_BATCH_SIZE):
            batch = train_examples[start : start + LISTWISE_BATCH_SIZE]
            features, padding_mask, targets = _padded_listwise_batch(batch, normalizer, torch)
            optimizer.zero_grad(set_to_none=True)
            logits = model(features, padding_mask)
            loss = torch.nn.functional.cross_entropy(logits, targets)
            loss.backward()
            optimizer.step()
            total_loss += float(loss.detach().cpu().item())
            batch_count += 1
        dev_mrr = _dev_mrr_at_10(model, dev_examples, normalizer, torch)
        history.append(
            TrainingEpoch(
                epoch=epoch,
                train_loss=total_loss / batch_count,
                dev_mrr_at_10=dev_mrr,
            )
        )
        if dev_mrr > best_metric:
            best_metric = dev_mrr
            best_state = {
                name: tensor.detach().cpu().clone() for name, tensor in model.state_dict().items()
            }
            stale_epochs = 0
        else:
            stale_epochs += 1
        if stale_epochs >= LISTWISE_PATIENCE:
            break
    if best_state is None:  # pragma: no cover - nonempty Dev always supplies a finite metric
        raise AssertionError("listwise training did not select a checkpoint")
    selection = select_early_stopping_epoch(history)
    model.load_state_dict(best_state, strict=True)
    model.eval()
    return ListwiseTrainingResult(
        model=model,
        normalizer=normalizer,
        history=tuple(history),
        selected_epoch=selection.selected_epoch,
        selected_dev_mrr_at_10=selection.selected_dev_mrr_at_10,
    )


def score_listwise_features(
    model: object,
    rows: Sequence[Sequence[float]],
    normalizer: FeatureNormalizer,
    *,
    torch_module: Any | None = None,
) -> tuple[float, ...]:
    if not rows or len(rows) > 25:
        raise ValueError("listwise scoring requires between 1 and 25 candidates")
    torch = _load_torch() if torch_module is None else torch_module
    example = ListwiseExample(
        features=tuple(_validated_feature_row(row) for row in rows),
        target_index=0,
    )
    features, padding_mask, _targets = _padded_listwise_batch((example,), normalizer, torch)
    active_model = cast(Any, model)
    active_model.eval()
    with torch.no_grad():
        raw = active_model(features, padding_mask)[0].tolist()
    scores = tuple(float(value) for value in raw[: len(rows)])
    for value in scores:
        _require_finite(value, "listwise score")
    return scores


def _feature_schema_sha256() -> str:
    return sha256_bytes(canonical_json_bytes({"feature_schema": list(FEATURE_SCHEMA)}))


def _normalizer_payload(normalizer: FeatureNormalizer) -> dict[str, object]:
    return {
        "feature_schema": list(normalizer.feature_schema),
        "normalized_indices": list(normalizer.normalized_indices),
        "means": list(normalizer.means),
        "standard_deviations": list(normalizer.standard_deviations),
        "fitted_split": normalizer.fitted_split,
    }


def _checkpoint_manifest_payload(manifest: ListwiseCheckpointManifest) -> dict[str, object]:
    return {
        "schema_version": manifest.schema_version,
        "feature_schema": list(manifest.feature_schema),
        "feature_schema_sha256": manifest.feature_schema_sha256,
        "architecture": {name: value for name, value in manifest.architecture},
        "seed": manifest.seed,
        "selected_epoch": manifest.selected_epoch,
        "normalizer": _normalizer_payload(manifest.normalizer),
        "tensor_shapes": [
            {"name": name, "shape": list(shape)} for name, shape in manifest.tensor_shapes
        ],
        "checkpoint_sha256": manifest.checkpoint_sha256,
    }


def _tensor_shapes(state: Mapping[str, object]) -> tuple[tuple[str, tuple[int, ...]], ...]:
    shapes: list[tuple[str, tuple[int, ...]]] = []
    for name in sorted(state):
        tensor = state[name]
        raw_shape = getattr(tensor, "shape", None)
        if raw_shape is None:
            raise TypeError(f"checkpoint state {name} is not tensor-like")
        shape = tuple(int(value) for value in raw_shape)
        shapes.append((name, shape))
    if not shapes:
        raise ValueError("listwise checkpoint cannot be empty")
    return tuple(shapes)


def save_listwise_checkpoint(
    checkpoint_path: Path,
    result: ListwiseTrainingResult,
    *,
    adapter: SafeTensorAdapter | None = None,
) -> Path:
    """Save only model tensors; optimizer state is deliberately excluded."""

    if checkpoint_path.suffix != ".safetensors":
        raise ValueError("listwise checkpoint must use the .safetensors extension")
    manifest_path = checkpoint_path.with_suffix(".manifest.json")
    if checkpoint_path.exists() or manifest_path.exists():
        raise FileExistsError("listwise checkpoint or manifest already exists")
    active_adapter = adapter if adapter is not None else _load_safetensors_torch()
    model = cast(Any, result.model)
    state = {
        name: tensor.detach().cpu().contiguous() for name, tensor in model.state_dict().items()
    }
    tensor_shapes = _tensor_shapes(state)
    checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{checkpoint_path.name}-", dir=checkpoint_path.parent
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    temporary.unlink()
    try:
        active_adapter.save_file(
            state,
            str(temporary),
            metadata={
                "format": "pt",
                "architecture": "candidate-set-reranker-v1",
                "feature_schema_sha256": _feature_schema_sha256(),
            },
        )
        manifest = ListwiseCheckpointManifest(
            schema_version=1,
            feature_schema=FEATURE_SCHEMA,
            feature_schema_sha256=_feature_schema_sha256(),
            architecture=LISTWISE_ARCHITECTURE,
            seed=LISTWISE_SEED,
            selected_epoch=result.selected_epoch,
            normalizer=result.normalizer,
            tensor_shapes=tensor_shapes,
            checkpoint_sha256=sha256_path(temporary),
        )
        manifest_path.write_bytes(canonical_json_bytes(_checkpoint_manifest_payload(manifest)))
        os.rename(temporary, checkpoint_path)
    finally:
        if temporary.exists():
            temporary.unlink()
    validate_listwise_checkpoint(checkpoint_path, adapter=active_adapter)
    return manifest_path


def _parse_normalizer(value: object) -> FeatureNormalizer:
    if not isinstance(value, Mapping):
        raise TypeError("checkpoint manifest normalizer must be an object")
    feature_schema = value.get("feature_schema")
    normalized_indices = value.get("normalized_indices")
    means = value.get("means")
    deviations = value.get("standard_deviations")
    fitted_split = value.get("fitted_split")
    if not all(
        isinstance(item, list) for item in (feature_schema, normalized_indices, means, deviations)
    ):
        raise TypeError("checkpoint manifest normalizer arrays are invalid")
    if not isinstance(fitted_split, str):
        raise TypeError("checkpoint manifest normalizer fitted_split is invalid")
    if any(not isinstance(item, str) for item in cast(list[object], feature_schema)):
        raise TypeError("checkpoint manifest normalizer feature_schema is invalid")
    return FeatureNormalizer(
        feature_schema=tuple(cast(list[str], feature_schema)),
        normalized_indices=tuple(int(item) for item in cast(list[Any], normalized_indices)),
        means=tuple(float(item) for item in cast(list[Any], means)),
        standard_deviations=tuple(float(item) for item in cast(list[Any], deviations)),
        fitted_split=fitted_split,
    )


def validate_listwise_checkpoint(
    checkpoint_path: Path,
    *,
    adapter: SafeTensorAdapter | None = None,
) -> ListwiseCheckpointManifest:
    if (
        checkpoint_path.suffix != ".safetensors"
        or not checkpoint_path.is_file()
        or checkpoint_path.is_symlink()
    ):
        raise ValueError("listwise safetensors checkpoint is missing")
    manifest_path = checkpoint_path.with_suffix(".manifest.json")
    if manifest_path.is_symlink():
        raise ValueError("listwise checkpoint manifest must be a regular local file")
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("listwise checkpoint manifest is missing or invalid") from error
    if not isinstance(payload, Mapping) or payload.get("schema_version") != 1:
        raise ValueError("listwise checkpoint manifest schema is invalid")
    feature_schema = payload.get("feature_schema")
    architecture = payload.get("architecture")
    tensor_shapes_value = payload.get("tensor_shapes")
    if feature_schema != list(FEATURE_SCHEMA):
        raise ValueError("listwise checkpoint feature schema drift")
    if architecture != {name: value for name, value in LISTWISE_ARCHITECTURE}:
        raise ValueError("listwise checkpoint architecture drift")
    if payload.get("feature_schema_sha256") != _feature_schema_sha256():
        raise ValueError("listwise checkpoint feature schema hash drift")
    if payload.get("seed") != LISTWISE_SEED:
        raise ValueError("listwise checkpoint seed drift")
    selected_epoch = payload.get("selected_epoch")
    checkpoint_sha256 = payload.get("checkpoint_sha256")
    if (
        not isinstance(selected_epoch, int)
        or isinstance(selected_epoch, bool)
        or not 1 <= selected_epoch <= LISTWISE_MAX_EPOCHS
        or not isinstance(checkpoint_sha256, str)
        or checkpoint_sha256 != sha256_path(checkpoint_path)
    ):
        raise ValueError("listwise checkpoint epoch or file hash drift")
    if not isinstance(tensor_shapes_value, list):
        raise TypeError("listwise checkpoint tensor_shapes must be a list")
    declared_shapes: list[tuple[str, tuple[int, ...]]] = []
    for item in tensor_shapes_value:
        if not isinstance(item, Mapping):
            raise TypeError("listwise checkpoint tensor shape record is invalid")
        name = item.get("name")
        shape = item.get("shape")
        if not isinstance(name, str) or not isinstance(shape, list):
            raise TypeError("listwise checkpoint tensor shape record is invalid")
        declared_shapes.append((name, tuple(int(value) for value in shape)))
    active_adapter = adapter if adapter is not None else _load_safetensors_torch()
    state = active_adapter.load_file(str(checkpoint_path), device="cpu")
    actual_shapes = _tensor_shapes(state)
    if tuple(declared_shapes) != actual_shapes:
        raise ValueError("listwise checkpoint tensor names or shapes drift")
    return ListwiseCheckpointManifest(
        schema_version=1,
        feature_schema=FEATURE_SCHEMA,
        feature_schema_sha256=_feature_schema_sha256(),
        architecture=LISTWISE_ARCHITECTURE,
        seed=LISTWISE_SEED,
        selected_epoch=selected_epoch,
        normalizer=_parse_normalizer(payload.get("normalizer")),
        tensor_shapes=actual_shapes,
        checkpoint_sha256=checkpoint_sha256,
    )


def _require_finite(value: float, name: str) -> None:
    if not math.isfinite(value):
        raise ValueError(f"{name} must be finite")


def _validate_unique_pairs(
    pairs: tuple[tuple[str, int], ...] | tuple[tuple[str, float], ...],
    *,
    allowed: tuple[str, ...],
    name: str,
) -> None:
    keys = [key for key, _value in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError(f"{name} contains duplicate sources")
    if any(key not in allowed for key in keys):
        raise ValueError(f"{name} contains an unsupported source")


@dataclass(frozen=True, slots=True)
class CandidateTextFields:
    brand: str
    casting: str
    release_year: int | None = None
    series: str | None = None
    color: str | None = None
    collector_number: str | None = None
    series_position: str | None = None
    edition: str | None = None
    aliases: tuple[str, ...] = ()
    identifiers: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.brand.strip() or not self.casting.strip():
            raise ValueError("candidate brand and casting are required")
        if self.release_year is not None and not 1900 <= self.release_year <= 2200:
            raise ValueError("candidate release_year is outside the supported range")
        if any(not value.strip() for value in (*self.aliases, *self.identifiers)):
            raise ValueError("candidate aliases and identifiers must be nonblank")


@dataclass(frozen=True, slots=True)
class FrozenCandidate:
    canonical_uuid: str
    canonical_id: str
    text: CandidateTextFields
    source_ranks: tuple[tuple[str, int], ...]
    source_scores: tuple[tuple[str, float], ...]
    structured_matches: tuple[str, ...]
    structured_conflicts: tuple[str, ...]
    rrf_rank: int
    rrf_score: float

    def __post_init__(self) -> None:
        try:
            UUID(self.canonical_uuid)
        except (TypeError, ValueError) as error:
            raise ValueError("candidate canonical_uuid is invalid") from error
        if not self.canonical_id.strip():
            raise ValueError("candidate canonical_id is required")
        if not 1 <= self.rrf_rank <= 25:
            raise ValueError("candidate rrf_rank must be between 1 and 25")
        _require_finite(self.rrf_score, "candidate rrf_score")
        if self.rrf_score < 0:
            raise ValueError("candidate rrf_score must be nonnegative")
        _validate_unique_pairs(
            self.source_ranks,
            allowed=SOURCE_NAMES,
            name="candidate source_ranks",
        )
        _validate_unique_pairs(
            self.source_scores,
            allowed=SOURCE_NAMES,
            name="candidate source_scores",
        )
        if any(rank < 1 for _source, rank in self.source_ranks):
            raise ValueError("candidate source rank must be positive")
        for _source, score in self.source_scores:
            _require_finite(score, "candidate source score")
        matches = set(self.structured_matches)
        conflicts = set(self.structured_conflicts)
        if len(matches) != len(self.structured_matches):
            raise ValueError("candidate structured_matches contains duplicates")
        if len(conflicts) != len(self.structured_conflicts):
            raise ValueError("candidate structured_conflicts contains duplicates")
        if (matches | conflicts) - set(STRUCTURED_NAMES):
            raise ValueError("candidate structured evidence contains an unsupported field")
        if matches & conflicts:
            raise ValueError("candidate field cannot be both a match and a conflict")

    def source_rank(self, source: str) -> int | None:
        return dict(self.source_ranks).get(source)


@dataclass(frozen=True, slots=True)
class FrozenSignals:
    normalized_title: str
    tokens: tuple[str, ...]
    year: int | None = None
    collector_number: str | None = None
    series_position: str | None = None
    quantity: int | None = None
    multipack_hint: bool = False
    color_hints: tuple[str, ...] = ()
    series_hints: tuple[str, ...] = ()
    parse_warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.normalized_title.strip() or not self.tokens:
            raise ValueError("frozen signals require normalized text and tokens")
        if any(not token.strip() for token in self.tokens):
            raise ValueError("frozen signal tokens must be nonblank")
        if self.quantity is not None and self.quantity < 1:
            raise ValueError("frozen signal quantity must be positive")


@dataclass(frozen=True, slots=True)
class CandidatePoolRow:
    case_id: str
    split: Split
    query: str
    signals: FrozenSignals
    retrieval_timings_ms: tuple[tuple[str, float], ...]
    candidates: tuple[FrozenCandidate, ...]

    def __post_init__(self) -> None:
        if not self.case_id.strip() or not self.query.strip():
            raise ValueError("candidate pool row requires case_id and query")
        if self.split not in SPLITS:
            raise ValueError("candidate pool row has invalid split")
        if len(self.candidates) > 25:
            raise ValueError("candidate pool row exceeds 25 candidates")
        identities = [candidate.canonical_uuid for candidate in self.candidates]
        if len(identities) != len(set(identities)):
            raise ValueError("candidate pool row contains duplicate identities")
        ranks = [candidate.rrf_rank for candidate in self.candidates]
        if ranks != list(range(1, len(ranks) + 1)):
            raise ValueError("candidate pool row RRF ranks must be ordered and contiguous")
        timing_names = [name for name, _value in self.retrieval_timings_ms]
        if len(timing_names) != len(set(timing_names)):
            raise ValueError("candidate pool row contains duplicate timing names")
        for _name, value in self.retrieval_timings_ms:
            _require_finite(value, "candidate pool timing")
            if value < 0:
                raise ValueError("candidate pool timing must be nonnegative")


@dataclass(frozen=True, slots=True)
class RankedCandidate:
    canonical_uuid: str
    canonical_id: str
    rrf_rank: int
    score: float
    rank: int


@dataclass(frozen=True, slots=True)
class ScoredCase:
    case_id: str
    failure_category: str
    hard_negative: bool
    expected_canonical_uuid: str
    target_ranks: tuple[tuple[str, int | None], ...]

    def __post_init__(self) -> None:
        if not self.case_id.strip() or not self.failure_category.strip():
            raise ValueError("scored case requires case_id and failure_category")
        try:
            UUID(self.expected_canonical_uuid)
        except (TypeError, ValueError) as error:
            raise ValueError("scored case expected_canonical_uuid is invalid") from error
        arms = [arm for arm, _rank in self.target_ranks]
        if tuple(arms) != ARMS:
            raise ValueError("scored case target_ranks must use the declared arm order")
        for _arm, rank in self.target_ranks:
            if rank is not None and not 1 <= rank <= 25:
                raise ValueError("scored case target rank must be null or between 1 and 25")

    def rank_for(self, arm: str) -> int | None:
        if arm not in ARMS:
            raise ValueError(f"unknown comparison arm: {arm}")
        return dict(self.target_ranks)[arm]


@dataclass(frozen=True, slots=True)
class MetricValue:
    numerator: float
    denominator: int
    value: float


@dataclass(frozen=True, slots=True)
class PairedRankTransition:
    case_id: str
    baseline_rank: int | None
    compared_rank: int | None
    direction: Direction


@dataclass(frozen=True, slots=True)
class BenchmarkContract:
    total_count: int
    split_counts: tuple[tuple[str, int], ...]
    status_counts: tuple[tuple[str, tuple[tuple[str, int], ...]], ...]
    hard_negative_counts: tuple[tuple[str, int], ...]
    matched_hard_negative_counts: tuple[tuple[str, int], ...]
    family_count: int


def _normalized_field(value: object) -> str:
    if value is None:
        return "<missing>"
    normalized = " ".join(str(value).strip().lower().split())
    return normalized or "<missing>"


def _normalized_collection(values: tuple[str, ...]) -> str:
    normalized = sorted({_normalized_field(value) for value in values})
    normalized = [value for value in normalized if value != "<missing>"]
    return "; ".join(normalized) if normalized else "<missing>"


def render_candidate_text(fields: CandidateTextFields) -> str:
    """Render only the approved public catalog fields in a stable order."""

    values = (
        ("brand", fields.brand),
        ("casting", fields.casting),
        ("year", fields.release_year),
        ("series", fields.series),
        ("color", fields.color),
        ("collector", fields.collector_number),
        ("series_position", fields.series_position),
        ("edition", fields.edition),
    )
    rendered = [f"{name}={_normalized_field(value)}" for name, value in values]
    rendered.append(f"aliases={_normalized_collection(fields.aliases)}")
    rendered.append(f"identifiers={_normalized_collection(fields.identifiers)}")
    return " | ".join(rendered)


def candidate_feature_vector(
    candidate: FrozenCandidate,
    pointwise_logit: float,
) -> tuple[float, ...]:
    """Return the immutable 21-feature vector declared by the design."""

    _require_finite(pointwise_logit, "pointwise logit")
    source_ranks = dict(candidate.source_ranks)
    matches = set(candidate.structured_matches)
    conflicts = set(candidate.structured_conflicts)

    def reciprocal(source: str) -> float:
        rank = source_ranks.get(source)
        return 0.0 if rank is None else 1.0 / rank

    result = (
        float(pointwise_logit),
        candidate.rrf_score,
        1.0 / candidate.rrf_rank,
        *(1.0 if source in source_ranks else 0.0 for source in SOURCE_NAMES),
        *(reciprocal(source) for source in SOURCE_NAMES),
        *(1.0 if name in matches else 0.0 for name in STRUCTURED_NAMES),
        *(1.0 if name in conflicts else 0.0 for name in STRUCTURED_NAMES),
        len(matches) / 5.0,
        len(conflicts) / 5.0,
    )
    if len(result) != len(FEATURE_SCHEMA):  # pragma: no cover - schema edit guard
        raise AssertionError("candidate feature schema length drift")
    if not all(math.isfinite(value) for value in result):
        raise ValueError("candidate feature vector contains a non-finite value")
    return tuple(result)


def rank_scores(
    candidates: Sequence[FrozenCandidate],
    scores: Sequence[float],
) -> tuple[RankedCandidate, ...]:
    if len(candidates) != len(scores):
        raise ValueError("candidate and score counts differ")
    identities = [candidate.canonical_uuid for candidate in candidates]
    if len(identities) != len(set(identities)):
        raise ValueError("ranking input contains duplicate identities")
    for score in scores:
        _require_finite(float(score), "ranking score")
    ordered = sorted(
        zip(candidates, scores, strict=True),
        key=lambda item: (-float(item[1]), item[0].rrf_rank, item[0].canonical_uuid),
    )
    return tuple(
        RankedCandidate(
            canonical_uuid=candidate.canonical_uuid,
            canonical_id=candidate.canonical_id,
            rrf_rank=candidate.rrf_rank,
            score=float(score),
            rank=rank,
        )
        for rank, (candidate, score) in enumerate(ordered, start=1)
    )


def _metric(numerator: float, denominator: int) -> MetricValue:
    value = numerator / denominator if denominator else 0.0
    return MetricValue(numerator=numerator, denominator=denominator, value=value)


def ranking_metrics(cases: Sequence[ScoredCase], arm: str) -> dict[str, MetricValue]:
    if arm not in ARMS:
        raise ValueError(f"unknown comparison arm: {arm}")
    ranks = [case.rank_for(arm) for case in cases]
    hard_ranks = [case.rank_for(arm) for case in cases if case.hard_negative]
    reciprocal_sum = sum(1.0 / rank for rank in ranks if rank is not None and rank <= 10)
    return {
        "top1_accuracy": _metric(float(sum(rank == 1 for rank in ranks)), len(ranks)),
        "mrr_at_10": _metric(reciprocal_sum, len(ranks)),
        "hard_negative_accuracy": _metric(
            float(sum(rank == 1 for rank in hard_ranks)), len(hard_ranks)
        ),
        "recall_at_10": _metric(
            float(sum(rank is not None and rank <= 10 for rank in ranks)), len(ranks)
        ),
        "recall_at_25": _metric(
            float(sum(rank is not None and rank <= 25 for rank in ranks)), len(ranks)
        ),
    }


def metrics_by_failure_category(
    cases: Sequence[ScoredCase],
    arm: str,
) -> dict[str, dict[str, MetricValue]]:
    categories = sorted({case.failure_category for case in cases})
    return {
        category: ranking_metrics(
            [case for case in cases if case.failure_category == category], arm
        )
        for category in categories
    }


def paired_rank_transitions(
    cases: Sequence[ScoredCase],
    compared_arm: str,
    *,
    baseline_arm: str = "rrf",
) -> tuple[PairedRankTransition, ...]:
    if baseline_arm not in ARMS or compared_arm not in ARMS:
        raise ValueError("paired transition contains an unknown arm")

    def comparison_value(rank: int | None) -> float:
        return math.inf if rank is None else float(rank)

    transitions: list[PairedRankTransition] = []
    for case in cases:
        baseline = case.rank_for(baseline_arm)
        compared = case.rank_for(compared_arm)
        baseline_value = comparison_value(baseline)
        compared_value = comparison_value(compared)
        if compared_value < baseline_value:
            direction: Direction = "improved"
        elif compared_value > baseline_value:
            direction = "regressed"
        else:
            direction = "unchanged"
        transitions.append(
            PairedRankTransition(
                case_id=case.case_id,
                baseline_rank=baseline,
                compared_rank=compared,
                direction=direction,
            )
        )
    return tuple(transitions)


def _walk_json(value: object, forbidden_keys: frozenset[str], path: str) -> None:
    if isinstance(value, Mapping):
        for raw_key, child in value.items():
            if not isinstance(raw_key, str):
                raise TypeError(f"{path} contains a non-string JSON key")
            normalized = raw_key.strip().lower()
            if normalized in forbidden_keys or normalized.startswith("expected_"):
                raise ValueError(f"{path}.{raw_key} is forbidden in a label-blind artifact")
            _walk_json(child, forbidden_keys, f"{path}.{raw_key}")
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for index, child in enumerate(value):
            _walk_json(child, forbidden_keys, f"{path}[{index}]")
        return
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError(f"{path} contains a non-finite number")
    if value is not None and not isinstance(value, (str, int, float, bool)):
        raise ValueError(f"{path} contains a non-JSON value")


def validate_label_blind_payload(value: object) -> None:
    _walk_json(value, LABEL_KEYS | RESULT_KEYS, "$")


def validate_candidate_pool_payload(value: object) -> None:
    _walk_json(value, LABEL_KEYS | RESULT_KEYS | POOL_SCORE_KEYS, "$")


def validate_raw_test_payload(value: object) -> None:
    _walk_json(value, LABEL_KEYS | RESULT_KEYS, "$")


def canonical_json_bytes(value: object) -> bytes:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return (encoded + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_path(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def _require_string(row: Mapping[str, object], key: str) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"benchmark row requires nonblank {key}")
    return value


def validate_benchmark_contract(payload: Mapping[str, object]) -> BenchmarkContract:
    cases_value = payload.get("cases")
    if not isinstance(cases_value, list):
        raise TypeError("benchmark must contain cases[]")
    cases: list[Mapping[str, object]] = []
    for index, raw in enumerate(cases_value):
        if not isinstance(raw, Mapping):
            raise TypeError(f"benchmark case {index} must be an object")
        if any(not isinstance(key, str) for key in raw):
            raise ValueError(f"benchmark case {index} has a non-string key")
        cases.append(cast(Mapping[str, object], raw))

    if len(cases) != 100:
        raise ValueError("benchmark must contain exactly 100 cases")

    split_counts = {split: 0 for split in SPLITS}
    status_counts = {
        split: {status: 0 for status in ("matched", "ambiguous", "no_match")} for split in SPLITS
    }
    hard_counts = {split: 0 for split in SPLITS}
    matched_hard_counts = {split: 0 for split in SPLITS}
    seen_case_ids: set[str] = set()
    family_splits: dict[str, str] = {}

    for row in cases:
        case_id = _require_string(row, "case_id")
        split = _require_string(row, "split")
        status = _require_string(row, "expected_status")
        family = _require_string(row, "casting_family")
        if case_id in seen_case_ids:
            raise ValueError(f"duplicate benchmark case_id: {case_id}")
        seen_case_ids.add(case_id)
        if split not in SPLITS:
            raise ValueError(f"benchmark case {case_id} has invalid split")
        if status not in status_counts[split]:
            raise ValueError(f"benchmark case {case_id} has invalid expected_status")
        previous_split = family_splits.setdefault(family, split)
        if previous_split != split:
            raise ValueError(f"casting family leaks across splits: {family}")
        split_counts[split] += 1
        status_counts[split][status] += 1
        hard_negative = row.get("hard_negative")
        if not isinstance(hard_negative, bool):
            raise TypeError(f"benchmark case {case_id} has invalid hard_negative")
        if hard_negative:
            hard_counts[split] += 1
            if status == "matched":
                matched_hard_counts[split] += 1
        if status == "matched":
            target = _require_string(row, "expected_canonical_uuid")
            try:
                UUID(target)
            except ValueError as error:
                raise ValueError(f"benchmark case {case_id} has invalid target UUID") from error

    if split_counts != EXPECTED_SPLIT_COUNTS:
        raise ValueError("benchmark split counts differ from the frozen contract")
    if status_counts != EXPECTED_STATUS_COUNTS:
        raise ValueError("benchmark status counts differ from the frozen contract")
    if hard_counts != EXPECTED_HARD_NEGATIVE_COUNTS:
        raise ValueError("benchmark hard-negative counts differ from the frozen contract")
    if matched_hard_counts != EXPECTED_MATCHED_HARD_NEGATIVE_COUNTS:
        raise ValueError("benchmark matched hard-negative counts differ from the frozen contract")

    return BenchmarkContract(
        total_count=len(cases),
        split_counts=tuple((split, split_counts[split]) for split in SPLITS),
        status_counts=tuple(
            (
                split,
                tuple(
                    (status, status_counts[split][status])
                    for status in ("matched", "ambiguous", "no_match")
                ),
            )
            for split in SPLITS
        ),
        hard_negative_counts=tuple((split, hard_counts[split]) for split in SPLITS),
        matched_hard_negative_counts=tuple((split, matched_hard_counts[split]) for split in SPLITS),
        family_count=len(family_splits),
    )
