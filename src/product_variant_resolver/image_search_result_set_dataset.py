"""Strict contract for multi-title image-search result-set evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from .identity import normalize_text
from .image_search_evaluation import ExpectedFullIdentity
from .schemas import StrictModel
from .serper_dual_source_evaluation import (
    DATASET as POSITIVE_DATASET,
)
from .serper_dual_source_evaluation import (
    FROZEN_DATASET_SHA256 as POSITIVE_DATASET_SHA256,
)
from .serper_dual_source_evaluation import (
    load_frozen_grouped_split,
    load_serper_dual_source_dataset,
)
from .serper_dual_source_policy_calibration import (
    POLICY_DATASET,
    POLICY_DATASET_SHA256,
    load_policy_dataset,
)

VERSION = "image-search-result-set-query-v1"
DATASET = Path("data/evaluation/image-search-result-set-query-v1/dataset.json")
FROZEN_DATASET_SHA256 = "7839efc44ced91fe4ae885b7d3019c8d442fcf262fce73470713df52ff8c4e75"
CATALOG_SHA256 = "b4e0747450a5447c2bf66b0838c91f3f723a19ac97c90c7ac3636cf3a9a709d4"
MAX_RESULTS = 10

DevelopmentRole = Literal["positive_development", "no_match_development"]
Truth = Literal["catalog_present", "catalog_relative_no_match"]
ChallengeType = Literal["catalog_present", "same_casting_absent_release", "absent_casting"]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path} must contain an object")
    return value


class SearchResultText(StrictModel):
    raw: str = Field(min_length=1, max_length=512)
    cleaned: str = Field(min_length=1, max_length=512)

    @field_validator("raw", "cleaned")
    @classmethod
    def strip_and_reject_urls(cls, value: str) -> str:
        stripped = value.strip()
        lowered = stripped.casefold()
        if not stripped or "http://" in lowered or "https://" in lowered:
            raise ValueError("result text must be nonblank and URL-free")
        return stripped


class ResultSetRecord(StrictModel):
    id: str = Field(pattern=r"^isrs-[0-9]{4}$")
    parent_target_id: str = Field(pattern=r"^(?:sds|sdsp)-target-[0-9]{4}$")
    development_role: DevelopmentRole
    truth: Truth
    challenge_type: ChallengeType
    expected_casting: str = Field(min_length=1)
    expected_full_identity: ExpectedFullIdentity
    results: list[SearchResultText] = Field(max_length=MAX_RESULTS)

    @field_validator("expected_casting")
    @classmethod
    def strip_casting(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("expected casting must be nonblank")
        return stripped

    @model_validator(mode="after")
    def validate_semantics(self) -> ResultSetRecord:
        if normalize_text(self.expected_casting) != normalize_text(
            self.expected_full_identity.casting
        ):
            raise ValueError("expected casting differs from full identity")
        if self.development_role == "positive_development":
            if (
                self.truth != "catalog_present"
                or self.challenge_type != "catalog_present"
                or not self.parent_target_id.startswith("sds-target-")
            ):
                raise ValueError("positive development semantics changed")
        elif (
            self.truth != "catalog_relative_no_match"
            or self.challenge_type == "catalog_present"
            or not self.parent_target_id.startswith("sdsp-target-")
        ):
            raise ValueError("no-match development semantics changed")
        raw_keys = [normalize_text(item.raw) for item in self.results]
        if len(raw_keys) != len(set(raw_keys)):
            raise ValueError("result titles must be unique inside one set")
        return self


class ResultSetDataset(StrictModel):
    dataset_version: Literal["image-search-result-set-query-v1"]
    catalog_sha256: Literal["b4e0747450a5447c2bf66b0838c91f3f723a19ac97c90c7ac3636cf3a9a709d4"]
    positive_parent_dataset_sha256: Literal[
        "05213c4c8d101d844b179359aef63264b8579c2f728b14f5adbe7a3a75a56034"
    ]
    policy_parent_dataset_sha256: Literal[
        "7df621e277e5c702f2d1277daf84d883e6e98a50f9c2ad69b052594c18ecbbf1"
    ]
    record_count: Literal[140]
    result_count: int = Field(ge=0, le=1_400)
    records: list[ResultSetRecord]

    @model_validator(mode="after")
    def validate_counts(self) -> ResultSetDataset:
        if len(self.records) != self.record_count:
            raise ValueError("record count changed")
        if [row.id for row in self.records] != [f"isrs-{index:04d}" for index in range(1, 141)]:
            raise ValueError("record IDs must be contiguous")
        parent_ids = [row.parent_target_id for row in self.records]
        if len(parent_ids) != len(set(parent_ids)):
            raise ValueError("parent target IDs must be unique")
        counts = Counter(row.development_role for row in self.records)
        if counts != {"positive_development": 100, "no_match_development": 40}:
            raise ValueError("development role counts changed")
        if self.result_count != sum(len(row.results) for row in self.records):
            raise ValueError("result count does not equal nested result rows")
        return self


def load_dataset(path: Path) -> ResultSetDataset:
    return ResultSetDataset.model_validate(_read_object(path))


def _expected_membership(root: Path) -> list[dict[str, object]]:
    if _sha256(root / POSITIVE_DATASET) != POSITIVE_DATASET_SHA256:
        raise ValueError("positive parent dataset changed")
    if _sha256(root / POLICY_DATASET) != POLICY_DATASET_SHA256:
        raise ValueError("policy parent dataset changed")
    positive = load_serper_dual_source_dataset(root / POSITIVE_DATASET)
    split = load_frozen_grouped_split(positive, root / POSITIVE_DATASET)
    positive_pairs = {image.target_id: image for image, _shopping in positive.target_pairs()}
    expected: list[dict[str, object]] = []
    for target_id in split.development_target_ids:
        row = positive_pairs[target_id]
        expected.append(
            {
                "parent_target_id": target_id,
                "development_role": "positive_development",
                "truth": "catalog_present",
                "challenge_type": "catalog_present",
                "expected_casting": row.expected_casting,
                "expected_full_identity": row.expected_full_identity,
            }
        )
    policy = load_policy_dataset(root / POLICY_DATASET)
    for image, _shopping in policy.target_pairs():
        if image.partition != "no_match_development":
            continue
        expected.append(
            {
                "parent_target_id": image.target_id,
                "development_role": "no_match_development",
                "truth": image.truth,
                "challenge_type": image.challenge_type,
                "expected_casting": image.expected_casting,
                "expected_full_identity": image.expected_full_identity,
            }
        )
    if len(expected) != 140:
        raise ValueError("expected development membership changed")
    return expected


def validate_membership(dataset: ResultSetDataset, root: Path) -> None:
    expected = _expected_membership(root)
    for actual, frozen in zip(dataset.records, expected, strict=True):
        for field in (
            "parent_target_id",
            "development_role",
            "truth",
            "challenge_type",
            "expected_casting",
            "expected_full_identity",
        ):
            if getattr(actual, field) != frozen[field]:
                raise ValueError(f"{actual.id} differs from frozen parent field {field}")


def check(root: Path, dataset_path: Path | None = None) -> ResultSetDataset:
    path = dataset_path or root / DATASET
    if dataset_path is None and _sha256(path) != FROZEN_DATASET_SHA256:
        raise ValueError("result-set dataset differs from the frozen contract")
    dataset = load_dataset(path)
    validate_membership(dataset, root)
    if path == root / DATASET:
        contents = sorted(item.name for item in path.parent.iterdir())
        if contents != ["dataset.json"]:
            raise ValueError("result-set dataset directory must contain only dataset.json")
    return dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate image-search result-set evidence")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--dataset", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    dataset_path = args.dataset.resolve() if args.dataset is not None else None
    dataset = check(root, dataset_path)
    path = dataset_path or root / DATASET
    print(
        json.dumps(
            {
                "status": "valid",
                "record_count": dataset.record_count,
                "result_count": dataset.result_count,
                "empty_result_set_count": sum(not row.results for row in dataset.records),
                "dataset_sha256": _sha256(path),
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
