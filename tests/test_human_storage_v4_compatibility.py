from __future__ import annotations

from pathlib import Path

import pytest

from product_variant_resolver import human_storage_v4_compatibility as compatibility
from product_variant_resolver.human_knowledge_identity import HumanKnowledgeV4Config
from product_variant_resolver.human_knowledge_identity_artifact import (
    load_human_knowledge_v4_config,
)
from product_variant_resolver.human_knowledge_selection import sha as file_sha
from product_variant_resolver.human_knowledge_storage_profile import REQUIRED_RUNTIME_SOURCES

ROOT = Path(__file__).resolve().parents[1]


def _load_compatible() -> HumanKnowledgeV4Config:
    return compatibility.load_human_storage_v4_config(
        ROOT / "config/human-knowledge-retrieval-v4.json",
        human_catalog_path=ROOT / "data/human_backed_catalog.json",
        review_family_path=ROOT / "data/review_family_knowledge.json",
        development_pack_path=(
            ROOT / "data/evaluation/family-retrieval-development-v1/development-pack.json"
        ),
        development_manifest_path=(
            ROOT
            / "data/evaluation/family-retrieval-development-v1/"
            "development-pack-manifest.json"
        ),
        dense_dimensions=192,
        root=ROOT,
    )


def _load_strict() -> HumanKnowledgeV4Config:
    return load_human_knowledge_v4_config(
        ROOT / "config/human-knowledge-retrieval-v4.json",
        human_catalog_path=ROOT / "data/human_backed_catalog.json",
        review_family_path=ROOT / "data/review_family_knowledge.json",
        development_pack_path=(
            ROOT / "data/evaluation/family-retrieval-development-v1/development-pack.json"
        ),
        development_manifest_path=(
            ROOT
            / "data/evaluation/family-retrieval-development-v1/"
            "development-pack-manifest.json"
        ),
        dense_dimensions=192,
        root=ROOT,
    )


def test_storage_compatibility_loads_frozen_math_without_rewriting_old_evidence() -> None:
    config = _load_compatible()
    assert config.character_score_floor == 0.5
    assert config.character_rrf_weight == 1.0
    assert config.artifact_sha256 == compatibility.MATH_ARTIFACT_SHA256

    with pytest.raises(ValueError, match="selection runtime source is stale"):
        _load_strict()


def test_compatibility_artifact_and_loader_are_profile_pinned() -> None:
    assert str(compatibility.COMPATIBILITY_FILE) in REQUIRED_RUNTIME_SOURCES
    assert (
        "src/product_variant_resolver/human_storage_v4_compatibility.py"
        in REQUIRED_RUNTIME_SOURCES
    )
    assert file_sha(ROOT / compatibility.COMPATIBILITY_FILE) == (
        compatibility.COMPATIBILITY_SHA256
    )


def test_unlisted_current_wrapper_hash_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def changed_sha(path: Path) -> str:
        if path.resolve() == (ROOT / "src/product_variant_resolver/api.py").resolve():
            return "0" * 64
        return file_sha(path)

    monkeypatch.setattr(compatibility, "sha", changed_sha)
    with pytest.raises(ValueError, match="allowed wrapper source differs"):
        _load_compatible()


def test_compatibility_artifact_checksum_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(compatibility, "COMPATIBILITY_SHA256", "0" * 64)
    with pytest.raises(ValueError, match="compatibility artifact checksum differs"):
        _load_compatible()
