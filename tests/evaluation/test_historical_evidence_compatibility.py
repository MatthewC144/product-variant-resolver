from __future__ import annotations

import hashlib
import json
import subprocess
from pathlib import Path

from product_variant_resolver import family_retrieval_final_v2 as family_v2
from product_variant_resolver.human_knowledge_selection import sha

ROOT = Path(__file__).resolve().parents[2]
COMPATIBILITY = ROOT / (
    "data/evaluation/human-storage-profile-development-v1/"
    "runtime-v4-compatibility-v1.json"
)
HSP_FREEZE_MANIFEST = ROOT / (
    "data/evaluation/human-storage-profile-development-v1/freeze/manifest.json"
)
T2_POOL_MANIFEST = ROOT / (
    "data/evaluation/domain-ranker-selective-prediction-development-v1/"
    "candidate-pool-manifest.json"
)
T2_PRIVATE_POOLS = ROOT / (
    "data/evaluation/domain-ranker-selective-prediction-development-v1/"
    "local-t2/candidate-pools.json"
)


def _git_blob(commit: str, relative: str) -> bytes:
    result = subprocess.run(
        ["git", "show", f"{commit}:{relative}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    return result.stdout


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _content_digest(value: dict[str, object]) -> str:
    body = dict(value)
    body.pop("content_sha256", None)
    return _digest(
        (
            json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
        ).encode()
    )


def test_family_v2_sources_remain_bound_to_the_winner_commit() -> None:
    manifest = json.loads(
        (ROOT / family_v2.DIRECTORY / "query-pack-manifest.json").read_text()
    )
    for relative in family_v2.INPUTS:
        assert manifest["source_sha256"][relative] == _digest(
            _git_blob(family_v2.WINNER_COMMIT, relative)
        )
    for relative in family_v2.AUTHOR_SOURCES:
        assert manifest["source_sha256"][relative] == sha(ROOT / relative)


def test_historical_wrappers_and_current_allowlist_are_both_exact() -> None:
    compatibility = json.loads(COMPATIBILITY.read_text())
    freeze_manifest = json.loads(HSP_FREEZE_MANIFEST.read_text())
    historical = compatibility["historical_selection_sources"]
    current = compatibility["allowed_current_wrapper_sources"]
    for relative in current:
        assert freeze_manifest["source_sha256"][relative] == historical[relative]
        assert sha(ROOT / relative) == current[relative]
        assert current[relative] != historical[relative]


def test_t2_candidate_pool_content_is_immutable_despite_source_evolution() -> None:
    manifest = json.loads(T2_POOL_MANIFEST.read_text())
    private = json.loads(T2_PRIVATE_POOLS.read_text())
    assert manifest["private_pool_artifact_sha256"] == sha(T2_PRIVATE_POOLS)
    assert private["content_sha256"] == _content_digest(private)
    historical_retrieval = manifest["bindings"]["code_sha256"][
        "src/product_variant_resolver/retrieval.py"
    ]
    assert historical_retrieval != sha(ROOT / "src/product_variant_resolver/retrieval.py")
