"""Attributable final-v2 family labels; never retrieves or scores any final question."""
from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from . import family_retrieval_final_v2 as questions
from .human_knowledge_identity_selection import publish_new
from .human_knowledge_selection import load_object, sha

ROOT = questions.ROOT
DIRECTORY = questions.DIRECTORY / "approved"
QUERY_COMMIT = "8f2891882f2836bfe492c7404e01654dea8b9fd9"
QUERY_SHA = "b23b69912c678c027461c96eb23f113484c5a8ed6218c06d90026704abe5102b"
SOURCES = ("src/product_variant_resolver/family_retrieval_final_v2_labels.py",
    "scripts/build_family_retrieval_benchmark_v2.py")
FILES = ("owner-decisions.json", "benchmark.json", "benchmark-manifest.json")
QUESTION_FILES = ("query-pack.json", "query-pack-manifest.json", "owner-review.md")
SCOPE = "casting_family_targets_only_not_release_variant_or_canonical_ground_truth"
CONTEXT = {
    "target_confirmation": "首先驗證對象沒有問題。但是想確認，車子除了casting重要外，顏色或是一些特點也對於最終結果一樣重要。請問這部分會在其他部分被考慮到嗎？",
    "scope_explained": "105 題即使通過，也只能證明這一批 casting／family 檢索達標，不能宣稱整個版本辨識已完成。",
    "proceed_confirmation": "沒有問題，請繼續下一步",
}


def committed_questions(root: Path = ROOT) -> dict[str, Any]:
    if questions.git(root, "merge-base", "--is-ancestor", QUERY_COMMIT, "HEAD").returncode:
        raise ValueError("question freeze commit is not an ancestor")
    for name in QUESTION_FILES:
        path = questions.DIRECTORY / name
        result = questions.git(root, "show", f"{QUERY_COMMIT}:{path}")
        if result.returncode or result.stdout.encode() != (root / path).read_bytes():
            raise ValueError("questions/review differ from committed freeze")
    if sha(root / questions.DIRECTORY / "query-pack.json") != QUERY_SHA:
        raise ValueError("wrong question approval checksum")
    pack = load_object(root / questions.DIRECTORY / "query-pack.json")
    return cast(dict[str, Any], questions.check(pack["cases"], root))


def expected_cases(pack: dict[str, Any], root: Path) -> list[dict[str, Any]]:
    registry = load_object(root / "data/review_family_registry.json")
    projection = load_object(root / "data/review_family_knowledge.json")
    human = load_object(root / "data/human_backed_catalog.json")
    families = {item["review_family_id"]: item for item in projection["documents"]}
    merges = {item["source_family_review_id"]: item for item in registry["merge_links"]}
    holds = {item["review_family_id"] for item in registry["hold_exclusions"]}
    castings = {item["casting_id"]: item for item in human["castings"]}
    if (len(families) != 42 or len(merges) != 4 or len(holds) != 7
            or set(families) != {item["review_family_id"] for item in registry["new_families"]}
            or set(families) & (set(merges) | holds)):
        raise ValueError("materialized/held family boundary changed")
    rows = []
    for case in pack["cases"]:
        kind = case["case_type"]
        reference = case["review_reference"]
        if kind == "positive_family":
            family_id = reference["review_family_id"]
            family = families[family_id]
            expected = {"knowledge_type": "review_family", "review_family_id": family_id,
                "review_family_uuid": family["review_family_uuid"]}
            group = "family:" + family_id
        elif kind == "merge_control":
            family_id = reference["review_family_id"]
            link = merges[family_id]
            target = castings[link["target_casting_id"]]
            if (target["casting_uuid"] != link["target_casting_uuid"]
                    or not target["provisional_variants"]):
                raise ValueError("merge target has no compatible provisional casting")
            expected = {"knowledge_type": "provisional_variant", "casting_id": target["casting_id"],
                "casting_uuid": target["casting_uuid"], "forbidden_review_family_id": family_id}
            group = "merge:" + family_id
        elif kind == "hold_control":
            family_id = reference["review_family_id"]
            if family_id not in holds:
                raise ValueError("hold no longer excluded")
            expected = {"expected_materialized": False, "forbidden_review_family_id": family_id}
            group = "hold:" + family_id
        elif kind == "unrelated_control":
            expected = {"expected_candidate_count": 0, "zero_token_overlap": True}
            group = "unrelated:" + reference["control_id"]
        else:
            raise ValueError("unexpected case kind")
        rows.append({**case, "expected": expected, "casting_group_id": group, "split": "test"})
    return rows


def approval_context(value: dict[str, Any]) -> None:
    # This is a versioned journal of this specific visible conversation, not an NLP consent detector.
    # A generic proceed instruction alone cannot produce this record. No cryptographic identity claim.
    if questions.json_text(value) != questions.json_text(CONTEXT):
        raise ValueError("explicit target confirmation and scope/proceed context required")


def source_hashes(root: Path) -> dict[str, str]:
    names = (*questions.INPUTS, *questions.AUTHOR_SOURCES, *SOURCES,
        *(str(questions.DIRECTORY / name) for name in QUESTION_FILES))
    return {name: sha(root / name) for name in names}


def documents(pack: dict[str, Any], context: dict[str, Any], recorded_at: str,
              root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    approval_context(context)
    timestamp = datetime.fromisoformat(recorded_at)
    if (not recorded_at.endswith("Z") or timestamp.tzinfo is None
            or timestamp <= datetime.fromisoformat(pack["authored_at"])
            or timestamp > datetime.now(UTC)):
        raise ValueError("recording time must follow query freeze and not be in the future")
    rows = expected_cases(pack, root)
    decisions = {"schema_version": "pvr-family-retrieval-owner-decisions-v2",
        "status": "approved", "decided_by": "project_owner", "recorded_by": "codex",
        "recorded_at": recorded_at, "message_timestamp": None,
        "evidence_method": "visible_conversation_excerpts_not_signed_identity_proof",
        "conversation_context": context, "scope": SCOPE, "query_commit": QUERY_COMMIT,
        "query_pack_sha256": QUERY_SHA, "decision_granularity": "whole_pack_confirmed_targets",
        "new_final_retrieval_executed": False,
        "decisions": [{"case_id": case["case_id"], "case_sha256": questions.case_sha(case),
            "decision": "approve", "expected": row["expected"]}
            for case, row in zip(pack["cases"], rows, strict=True)]}
    benchmark = {"schema_version": "pvr-family-retrieval-benchmark-v2",
        "benchmark_version": pack["benchmark_version"], "status": "frozen_owner_approved",
        "frozen_at": recorded_at, "split": "test", "split_counts": {"train": 0, "dev": 0, "test": 105},
        "scope": SCOPE, "query_pack_sha256": QUERY_SHA, "query_commit": QUERY_COMMIT,
        "winner": pack["winner"], "counts": pack["counts"], "styles": pack["styles"],
        "final_gates": pack["final_gates"], "family_coverage_denominator": 42,
        "authorship_policy": pack["authorship_policy"], "excluded_from": pack["excluded_from"],
        "eligible_for": ["human_knowledge_retrieval_evaluation_after_benchmark_commit"],
        "new_final_retrieval_executed": False, "cases": rows}
    return decisions, benchmark


def validate(root: Path = ROOT) -> dict[str, Any]:
    pack = committed_questions(root)
    directory = root / DIRECTORY
    decisions = load_object(directory / FILES[0])
    benchmark = load_object(directory / FILES[1])
    manifest = load_object(directory / FILES[2])
    expected_decisions, expected_benchmark = documents(pack, decisions["conversation_context"],
        decisions["recorded_at"], root)
    if (questions.json_text(decisions) != questions.json_text(expected_decisions)
            or questions.json_text(benchmark) != questions.json_text(expected_benchmark)):
        raise ValueError("approval or benchmark labels/queries/metadata changed")
    expected_manifest = {"schema_version": "pvr-family-retrieval-benchmark-manifest-v2",
        "status": "frozen_owner_approved_not_scored", "query_pack_sha256": QUERY_SHA,
        "owner_decisions_sha256": sha(directory / FILES[0]), "benchmark_sha256": sha(directory / FILES[1]),
        "source_sha256": source_hashes(root), "case_sha256": {
            row["case_id"]: questions.case_sha(row) for row in benchmark["cases"]},
        "new_final_retrieval_executed": False}
    if questions.json_text(manifest) != questions.json_text(expected_manifest):
        raise ValueError("benchmark manifest or input/builder checksums changed")
    return cast(dict[str, Any], benchmark)


def freeze(context: dict[str, Any], root: Path = ROOT) -> None:
    directory = root / DIRECTORY
    if directory.exists():
        raise ValueError("approved benchmark already exists; refuse overwrite")
    pack = committed_questions(root)
    recorded_at = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    decisions, benchmark = documents(pack, context, recorded_at, root)
    sources = source_hashes(root)
    staging = Path(tempfile.mkdtemp(prefix=".approved-final-v2-", dir=directory.parent))
    try:
        publish_new(staging / FILES[0], decisions)
        publish_new(staging / FILES[1], benchmark)
        manifest = {"schema_version": "pvr-family-retrieval-benchmark-manifest-v2",
            "status": "frozen_owner_approved_not_scored", "query_pack_sha256": QUERY_SHA,
            "owner_decisions_sha256": sha(staging / FILES[0]), "benchmark_sha256": sha(staging / FILES[1]),
            "source_sha256": sources, "case_sha256": {
                row["case_id"]: questions.case_sha(row) for row in benchmark["cases"]},
            "new_final_retrieval_executed": False}
        publish_new(staging / FILES[2], manifest)
        if directory.exists():
            raise ValueError("approved directory appeared; refuse replacement")
        # A competing nonempty approved directory cannot be replaced by rename.
        os.rename(staging, directory)
    finally:
        if staging.exists():
            for name in FILES:
                (staging / name).unlink(missing_ok=True)
            staging.rmdir()


def require_committed_benchmark(root: Path = ROOT) -> str:
    """T5 precondition: validate without retrieval, then prove label/builder commit ancestry."""
    validate(root)
    result = questions.git(root, "log", "-1", "--format=%H", "--", str(DIRECTORY / FILES[2]))
    commit = result.stdout.strip()
    if result.returncode or not commit:
        raise ValueError("benchmark must be committed before scoring")
    for name in (*(str(DIRECTORY / name) for name in FILES), *SOURCES):
        content = questions.git(root, "show", f"{commit}:{name}")
        if content.returncode or content.stdout.encode() != (root / name).read_bytes():
            raise ValueError("benchmark/builder differs from its freeze commit")
    return cast(str, commit)
