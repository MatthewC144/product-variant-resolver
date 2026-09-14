"""Final-v2 query freeze/check only. No retrieval, approval generation or expected labels."""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from .human_knowledge_identity import IdentityCorePolicy
from .human_knowledge_identity_artifact import RUNTIME_SOURCES, load_human_knowledge_v4_config
from .human_knowledge_identity_selection import publish_new
from .human_knowledge_selection import load_object, sha
from .identity import normalize_text

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = Path("data/evaluation/family-retrieval-v2")
WINNER_COMMIT = "a9a3730bf4d6ae47ddb1fff853e951081c81570c"
ARTIFACT = "config/human-knowledge-retrieval-v4.json"
ARTIFACT_SHA = "82c94a2629da6936bec3e4a2983e67c70d69e94cb94a9817375f891d59b1ae6b"
SELECTION = "reports/human-knowledge-identity-development-v1/selection.json"
AUTHOR_SOURCES = ("src/product_variant_resolver/family_retrieval_final_v2.py",
    "scripts/author_family_retrieval_query_pack_v2.py")
INPUTS = (ARTIFACT, SELECTION, *RUNTIME_SOURCES,
    "src/product_variant_resolver/human_knowledge_identity_selection.py",
    "data/evaluation/human-knowledge-identity-development-v1/protocol.json",
    "data/evaluation/human-knowledge-identity-development-v1/protocol-manifest.json",
    "data/evaluation/family-retrieval-v1/query-pack.json",
    "data/evaluation/family-retrieval-development-v1/development-pack.json",
    "data/review_family_registry.json", "data/review_family_registry_manifest.json",
    "data/review_family_knowledge.json", "data/review_family_knowledge_manifest.json",
    "data/human_backed_catalog.json", "data/human_backed_catalog_manifest.json")
COUNTS = {"positive_family": 84, "merge_control": 4, "hold_control": 7, "unrelated_control": 10}
STYLES = {"marketplace_noise": 42, "lexical_variation": 42, "merge_existing_family": 4,
    "held_identity": 7, "no_overlap": 10}
GATES = {"positive_recall_at_5": .85, "positive_recall_at_1": .65, "mrr_at_5": .75,
    "positive_style_recall_at_5": .75, "family_coverage_at_5": .90, "merge_recall_at_5": 1.0,
    "forbidden_family_candidates": 0, "unrelated_nonempty": 0}
EXCLUDED = ["training", "calibration", "threshold_selection", "retriever_tuning", "query_rewriting",
    "canonical_identity", "release_variant_truth", "postgresql_ingestion", "production_accuracy_claim"]
POLICY = {"method": "explicitly_composed_synthetic_questions_after_committed_v4_winner",
    "new_final_candidate_outputs_viewed": False, "prior_development_outputs_known": True,
    "same_families_not_unseen_casting_split": True, "independent_human_review_required": True,
    "not_live_marketplace_data": True, "not_independent_author_or_population_sample": True}


def json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def case_sha(case: dict[str, Any]) -> str:
    return hashlib.sha256(json_text(case).encode()).hexdigest()


def git(root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=False)


def committed_winner(root: Path = ROOT) -> dict[str, Any]:
    if git(root, "merge-base", "--is-ancestor", WINNER_COMMIT, "HEAD").returncode:
        raise ValueError("qualified winner commit is not an ancestor")
    if sha(root / ARTIFACT) != ARTIFACT_SHA:
        raise ValueError("selected artifact differs from committed winner")
    for name in INPUTS:
        result = git(root, "show", f"{WINNER_COMMIT}:{name}")
        if result.returncode or result.stdout.encode() != (root / name).read_bytes():
            raise ValueError(f"winner/input bytes differ from committed baseline: {name}")
    if git(root, "cat-file", "-e", f"{WINNER_COMMIT}:{DIRECTORY}/query-pack.json").returncode == 0:
        raise ValueError("final questions already existed at winner commit")
    config = load_human_knowledge_v4_config(root / ARTIFACT, root=root,
        human_catalog_path=root / "data/human_backed_catalog.json",
        review_family_path=root / "data/review_family_knowledge.json",
        development_pack_path=root / "data/evaluation/family-retrieval-development-v1/development-pack.json",
        development_manifest_path=root / "data/evaluation/family-retrieval-development-v1/development-pack-manifest.json",
        dense_dimensions=192)
    timestamp = git(root, "show", "-s", "--format=%cI", WINNER_COMMIT).stdout.strip()
    return {"commit": WINNER_COMMIT, "committed_at": timestamp, "artifact": ARTIFACT,
        "artifact_sha256": ARTIFACT_SHA, "artifact_version": config.artifact_version,
        "configuration": {"character_score_floor": config.character_score_floor,
            "character_rrf_weight": config.character_rrf_weight}}


def corpus(root: Path) -> tuple[dict[str, Any], set[str], set[str], set[str]]:
    registry = load_object(root / "data/review_family_registry.json")
    projection = load_object(root / "data/review_family_knowledge.json")
    human = load_object(root / "data/human_backed_catalog.json")
    values: set[str] = set()
    for section in ("new_families", "merge_links", "hold_exclusions"):
        for item in registry[section]:
            values.update((item["display_name"], f"{item['brand']} {item['display_name']}"))
    for item in projection["documents"]:
        values.update((item["casting"], f"{item['brand']} {item['casting']}", *item["aliases"]))
    for item in human["castings"]:
        values.update((item["casting"], f"{item['brand']} {item['casting']}"))
        for variant in item["provisional_variants"]:
            for field in ("human_label_names", "pricing_keywords", "initial_names"):
                values.update(variant[field])
            for field in ("series_label", "variant_label"):
                if variant[field]:
                    values.add(variant[field])
    indexed = {normalize_text(value) for value in values if normalize_text(value)}
    old_queries = {normalize_text(case["query_text"]) for name in (
        "data/evaluation/family-retrieval-v1/query-pack.json",
        "data/evaluation/family-retrieval-development-v1/development-pack.json")
        for case in load_object(root / name)["cases"]}
    tokens = {token for text in indexed for token in text.split()}
    return registry, indexed, old_queries, tokens


def validate_cases(cases: list[dict[str, Any]], root: Path = ROOT) -> dict[str, Any]:
    registry, indexed, previous, tokens = corpus(root)
    if len(cases) != 105 or dict(Counter(case["case_type"] for case in cases)) != COUNTS:
        raise ValueError("final composition must be exactly 84/4/7/10")
    if dict(Counter(case["challenge_style"] for case in cases)) != STYLES:
        raise ValueError("final style coverage differs")
    ids = [case["case_id"] for case in cases]
    normalized = [normalize_text(case["query_text"]) for case in cases]
    compact = [value.replace(" ", "") for value in normalized]
    policy = IdentityCorePolicy()
    previous_compact = {value.replace(" ", "") for value in previous | indexed}
    previous_cores = {policy.core(value).replace(" ", "") for value in previous if policy.core(value)}
    if ids != sorted(ids) or len(set(ids)) != 105 or len(set(normalized)) != 105 or len(set(compact)) != 105:
        raise ValueError("duplicate/unsorted final IDs or queries")
    groups: dict[str, set[str]] = defaultdict(set)
    covered: dict[str, set[str]] = defaultdict(set)
    expected = {"positive_family": {item["review_family_id"] for item in registry["new_families"]},
        "merge_control": {item["source_family_review_id"] for item in registry["merge_links"]},
        "hold_control": {item["review_family_id"] for item in registry["hold_exclusions"]}}
    for case, query, squeezed in zip(cases, normalized, compact, strict=True):
        if set(case) != {"case_id", "case_type", "challenge_style", "query_text", "review_reference"}:
            raise ValueError("query case contains label/output or unexpected fields")
        if (not re.fullmatch(r"fr2-[a-z0-9_-]+", case["case_id"]) or not query or len(query) > 512
                or query in previous | indexed or squeezed in previous_compact
                or policy.core(query).replace(" ", "") in previous_cores):
            raise ValueError(f"reused/invalid old, indexed or identity-core query: {case['case_id']}")
        kind, reference = case["case_type"], case["review_reference"]
        if kind == "unrelated_control":
            if (set(reference) != {"kind", "control_id"} or reference["kind"] != kind
                    or set(query.split()) & tokens or case["challenge_style"] != "no_overlap"):
                raise ValueError("unrelated query/reference has corpus-token overlap")
            continue
        required_kind = "review_family" if kind == "positive_family" else kind
        if (set(reference) != {"kind", "review_family_id"} or reference["kind"] != required_kind
                or reference["review_family_id"] not in expected[kind]):
            raise ValueError("case references an unapproved/uncovered identity")
        family_id = reference["review_family_id"]
        covered[kind].add(family_id)
        if kind == "positive_family":
            groups[family_id].add(case["challenge_style"])
        elif case["challenge_style"] != {"merge_control": "merge_existing_family", "hold_control": "held_identity"}[kind]:
            raise ValueError("control has the wrong style")
    if any(covered[kind] != expected[kind] for kind in expected) or any(
            styles != {"marketplace_noise", "lexical_variation"} for styles in groups.values()):
        raise ValueError("final family/pair/control coverage incomplete")
    return {"normalized_duplicates": 0, "compact_duplicates": 0, "previous_or_indexed_reuse": 0,
        "previous_nonempty_identity_core_reuse": 0, "unrelated_token_overlap": 0,
        "old_question_count": len(previous), "indexed_string_count": len(indexed),
        "positive_families": len(groups), "counts": COUNTS, "styles": STYLES,
        "not_a_semantic_paraphrase_or_query_identity_independence_proof": True}


def review_text(pack: dict[str, Any], checksum: str, root: Path) -> str:
    registry = load_object(root / "data/review_family_registry.json")
    names = {item.get("review_family_id", item.get("source_family_review_id")): item["display_name"]
        for section in ("new_families", "merge_links", "hold_exclusions") for item in registry[section]}
    lines = ["# Final v2 — 105 題待確認清單", "", "狀態：等待專案 owner 確認；尚無正式答案、候選或評分。", "",
        f"整份 query-pack SHA-256：`{checksum}`", "",
        f"選定模型提交：`{WINNER_COMMIT}`；設定：0.50 / 1.0。", "",
        "請確認題目與『打算驗證的對象』是否合理；這些對象只是審核參考，不是模型輸出。",
        "正例：應找回對應 casting family；合併：應沿用既有人工 casting，不另建 family。",
        "暫緩：該 family 尚未核准建立，不要求所有人工候選為空。無關：應沒有人工知識候選。", "",
        "84 正例（42 車款各兩種題型）、4 合併、7 暫緩、10 無關。",
        "題目是人工／AI 編寫的合成題，不是新抓取的市場資料；同一批車款，不是未見車款測試。",
        "作者知道舊開發結果，但未執行或查看這 105 題的新候選。人工確認不能消除所有來源偏差。", "",
        "每題完整校驗碼在 query-pack-manifest.json 的 case_sha256；下表顯示前 12 位供對照。", "",
        "| # | Case ID | 類型 | 打算驗證的對象 | Query（完整原文） | Case SHA 前12位 |",
        "|---:|---|---|---|---|---|"]
    labels = {"positive_family": "正例", "merge_control": "合併", "hold_control": "暫緩", "unrelated_control": "無關"}
    for number, case in enumerate(pack["cases"], 1):
        name = names.get(case["review_reference"].get("review_family_id"), "非車款詞語")
        query = case["query_text"].replace("|", "\\|")
        lines.append(f"| {number} | {case['case_id']} | {labels[case['case_type']]} / {case['challenge_style']} | "
            f"{name} | {query} | `{case_sha(case)[:12]}` |")
    lines += ["", "若有題目不合理，請指出 Case ID；尚未評分，可以版本化修訂後重新確認。",
        "若全部合理，請明確確認『同意這 105 題及其對應對象作為 final v2 測試』，並指向本份校驗碼。",
        "只有確認後，才記錄你的審核、建立正式 expected labels／benchmark；benchmark 提交後才跑一次 final。", ""]
    return "\n".join(lines)


def freeze(cases: list[dict[str, Any]], root: Path = ROOT) -> None:
    directory = root / DIRECTORY
    outputs = [directory / name for name in ("query-pack.json", "query-pack-manifest.json", "owner-review.md")]
    if directory.exists():
        raise ValueError("final query artifacts already exist; check, never overwrite")
    winner = committed_winner(root)
    audit = validate_cases(cases, root)
    authored_at = datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    if datetime.fromisoformat(authored_at) <= datetime.fromisoformat(winner["committed_at"]):
        raise ValueError("question freeze must be after winner commit")
    pack = {"schema_version": "pvr-family-retrieval-query-pack-v2", "benchmark_version": "family-retrieval-holdout-v2",
        "query_pack_version": "family-retrieval-query-pack-v2", "status": "pending_owner_review", "split": "test",
        "authored_at": authored_at, "authored_by": "evaluation_query_author", "authorship_policy": POLICY,
        "eligible_for": ["human_knowledge_retrieval_evaluation_after_owner_approval"], "excluded_from": EXCLUDED,
        "counts": COUNTS, "styles": STYLES, "final_gates": GATES, "winner": winner, "cases": cases}
    checksum = hashlib.sha256(json_text(pack).encode()).hexdigest()
    text = review_text(pack, checksum, root)
    manifest = {"schema_version": "pvr-family-retrieval-query-pack-manifest-v2", "status": "frozen_pending_owner_review",
        "query_pack_sha256": checksum, "owner_review_sha256": hashlib.sha256(text.encode()).hexdigest(),
        "case_sha256": {case["case_id"]: case_sha(case) for case in cases}, "winner": winner,
        "source_sha256": {name: sha(root / name) for name in INPUTS + AUTHOR_SOURCES}, "audit": audit,
        "new_final_retrieval_executed": False, "expected_labels_created": False, "owner_approval_recorded": False}
    # Publish one complete staged directory, not a partial pack followed by a missing manifest.
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=".family-retrieval-v2-", dir=directory.parent))
    try:
        publish_new(staging / outputs[0].name, pack)
        publish_new(staging / outputs[1].name, manifest)
        with (staging / outputs[2].name).open("x", encoding="utf-8") as handle:
            handle.write(text)
        if directory.exists():
            raise ValueError("final directory appeared during freeze; refuse replacement")
        os.rename(staging, directory)
    finally:
        if staging.exists():
            for name in ("query-pack.json", "query-pack-manifest.json", "owner-review.md"):
                (staging / name).unlink(missing_ok=True)
            staging.rmdir()


def check(cases: list[dict[str, Any]], root: Path = ROOT) -> dict[str, Any]:
    directory = root / DIRECTORY
    pack = load_object(directory / "query-pack.json")
    manifest = load_object(directory / "query-pack-manifest.json")
    if (set(pack) != {"schema_version", "benchmark_version", "query_pack_version", "status", "split", "authored_at",
                "authored_by", "authorship_policy", "eligible_for", "excluded_from", "counts", "styles", "final_gates", "winner", "cases"}
            or pack["schema_version"] != "pvr-family-retrieval-query-pack-v2"
            or pack["benchmark_version"] != "family-retrieval-holdout-v2" or pack["query_pack_version"] != "family-retrieval-query-pack-v2"
            or pack["authored_by"] != "evaluation_query_author"
            or pack["eligible_for"] != ["human_knowledge_retrieval_evaluation_after_owner_approval"]
            or pack["cases"] != cases or pack["status"] != "pending_owner_review" or pack["split"] != "test"
            or set(manifest) != {"schema_version", "status", "query_pack_sha256", "owner_review_sha256", "case_sha256", "winner",
                "source_sha256", "audit", "new_final_retrieval_executed", "expected_labels_created", "owner_approval_recorded"}
            or manifest["schema_version"] != "pvr-family-retrieval-query-pack-manifest-v2"
            or manifest["status"] != "frozen_pending_owner_review"
            or pack["authorship_policy"] != POLICY or pack["counts"] != COUNTS or pack["styles"] != STYLES
            or pack["final_gates"] != GATES or pack["excluded_from"] != EXCLUDED
            or pack["winner"] != committed_winner(root) or manifest["winner"] != pack["winner"]
            or sha(directory / "query-pack.json") != manifest["query_pack_sha256"]
            or manifest["case_sha256"] != {case["case_id"]: case_sha(case) for case in cases}
            or manifest["audit"] != validate_cases(cases, root)
            or set(manifest["source_sha256"]) != set(INPUTS + AUTHOR_SOURCES)
            or any(sha(root / name) != value for name, value in manifest["source_sha256"].items())
            or any(manifest[key] is not False for key in ("new_final_retrieval_executed", "expected_labels_created", "owner_approval_recorded"))):
        raise ValueError("final-v2 freeze is stale, modified or mislabeled")
    if datetime.fromisoformat(pack["authored_at"]) <= datetime.fromisoformat(pack["winner"]["committed_at"]):
        raise ValueError("final authoring timestamp does not follow committed winner")
    text = review_text(pack, manifest["query_pack_sha256"], root)
    if ((directory / "owner-review.md").read_text() != text
            or sha(directory / "owner-review.md") != manifest["owner_review_sha256"]):
        raise ValueError("owner review differs from frozen pairs")
    return cast(dict[str, Any], pack)


def require_approval(root: Path = ROOT) -> None:
    """Current handoff gate: approval must be separately recorded after explicit owner instruction."""
    path = root / DIRECTORY / "owner-decisions.json"
    if not path.exists():
        raise ValueError("STOP: final-v2 owner approval is not recorded; labels/retrieval prohibited")
    raise ValueError("STOP: approval/label validation must be implemented in the next approved phase")
