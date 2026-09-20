"""Select an experimental identity-token admission policy on development data only."""

from __future__ import annotations

import argparse
import hashlib
import json
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from .human_knowledge import (
    HumanKnowledgeCatalog,
    HumanKnowledgeDocument,
    load_human_knowledge_catalog,
)
from .human_knowledge_false_positive_development import (
    DATA_DIRECTORY as FALSE_POSITIVE_DATA_DIRECTORY,
)
from .human_knowledge_false_positive_development import (
    validate_pack as validate_false_positive_pack,
)
from .human_knowledge_identity import (
    HumanKnowledgeIdentityRetriever,
    HumanKnowledgeV4Config,
    IdentityCorePolicy,
)
from .retrieval import HashingEmbedding
from .signals import extract_signals

VERSION = "human-knowledge-admission-development-v1"
PROTOCOL_SCHEMA = "pvr-human-knowledge-admission-development-protocol-v1"
REPORT_SCHEMA = "pvr-human-knowledge-admission-development-selection-v1"
DATA_DIRECTORY = Path("data/evaluation") / VERSION
REPORT_DIRECTORY = Path("reports") / VERSION
SOURCE = "src/product_variant_resolver/human_knowledge_admission_development.py"
FALSE_POSITIVE_SOURCE = "src/product_variant_resolver/human_knowledge_false_positive_development.py"
EXISTING_PACK = Path("data/evaluation/family-retrieval-development-v1/development-pack.json")
EXISTING_MANIFEST = Path(
    "data/evaluation/family-retrieval-development-v1/development-pack-manifest.json"
)
CORPUS_INPUTS = (
    Path("data/human_backed_catalog.json"),
    Path("data/review_family_knowledge.json"),
    Path("data/review_family_knowledge_manifest.json"),
)
CANDIDATE_LIMIT = 5
DIMENSIONS = 192
CHARACTER_SCORE_FLOOR = 0.5
CHARACTER_RRF_WEIGHT = 1.0
TOKEN_SIMILARITY = 0.8
CONFIGURATIONS = (
    ("baseline", 0.0),
    ("coverage-050", 0.5),
    ("coverage-067", 2 / 3),
    ("coverage-075", 0.75),
    ("coverage-100", 1.0),
)
GATES = {
    "existing_positive_hits_at_5": 168,
    "merge_hits_at_5": 4,
    "existing_forbidden_candidates": 0,
    "unrelated_nonempty": 0,
    "new_required_hits_at_5": 24,
    "retrieval_errors": 0,
}


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise TypeError(f"{path.name}: root must be an object")
    return value


def _catalog(root: Path) -> HumanKnowledgeCatalog:
    return load_human_knowledge_catalog(*(root / path for path in CORPUS_INPUTS))


def _sources(root: Path) -> dict[str, str]:
    names = (
        *CORPUS_INPUTS,
        EXISTING_PACK,
        EXISTING_MANIFEST,
        FALSE_POSITIVE_DATA_DIRECTORY / "development-pack.json",
        FALSE_POSITIVE_DATA_DIRECTORY / "development-pack-manifest.json",
        Path(SOURCE),
        Path(FALSE_POSITIVE_SOURCE),
    )
    return {str(name): _sha(root / name) for name in names}


def build_protocol(root: Path) -> dict[str, Any]:
    existing = _load(root / EXISTING_PACK)
    new = validate_false_positive_pack(root)
    if len(existing.get("cases", [])) != 199 or len(new.get("cases", [])) != 24:
        raise ValueError("development input denominators differ from contract")
    return {
        "schema_version": PROTOCOL_SCHEMA,
        "version": VERSION,
        "status": "frozen_before_grid_execution",
        "sources": _sources(root),
        "corpus_document_count": 142,
        "query_counts": {"existing_development": 199, "false_positive_development": 24},
        "candidate_limit": CANDIDATE_LIMIT,
        "base_retriever": {
            "version": "human-knowledge-hybrid-v4",
            "character_score_floor": CHARACTER_SCORE_FLOOR,
            "character_rrf_weight": CHARACTER_RRF_WEIGHT,
            "dense_embedding": "hashing-v1",
            "dense_dimensions": DIMENSIONS,
        },
        "identity_coverage": {
            "allowed_fields": ["casting", "aliases"],
            "normalization": "identity-core-policy-v1",
            "token_similarity_floor": TOKEN_SIMILARITY,
            "match_modes": [
                "exact",
                "compact_containment_min_3",
                "prefix_abbreviation_min_2",
                "numeric_suffix_min_2",
                "sequence_matcher_ratio",
            ],
        },
        "configurations": [
            {"configuration_id": name, "minimum_identity_token_coverage": threshold}
            for name, threshold in CONFIGURATIONS
        ],
        "gates": GATES,
        "winner_order": [
            "eligible_only",
            "minimum_new_forbidden_hit_cases",
            "minimum_identity_token_coverage",
        ],
        "eligible_for": ["development_selection_only"],
        "excluded_from": [
            "runtime_activation",
            "final_accuracy",
            "private_local_evaluation",
            "canonical_truth",
            "release_variant_truth",
            "color_truth",
        ],
        "private_local_artifacts_read": False,
        "retrieval_executed": False,
    }


def _assert_file(path: Path, content: str) -> None:
    if not path.is_file() or path.read_text(encoding="utf-8") != content:
        raise ValueError(f"{path} differs from deterministic artifact")


def freeze_protocol(root: Path) -> str:
    protocol = build_protocol(root)
    manifest = {
        "schema_version": "pvr-human-knowledge-admission-development-manifest-v1",
        "version": VERSION,
        "protocol_sha256": hashlib.sha256(_json(protocol).encode()).hexdigest(),
        "source_sha256": protocol["sources"],
        "retrieval_executed": False,
        "private_local_artifacts_read": False,
    }
    outputs = {"protocol.json": _json(protocol), "protocol-manifest.json": _json(manifest)}
    directory = root / DATA_DIRECTORY
    if directory.exists():
        if {path.name for path in directory.iterdir()} != set(outputs):
            raise ValueError("admission protocol directory is partial or conflicting")
        for name, content in outputs.items():
            _assert_file(directory / name, content)
        return "unchanged"
    directory.mkdir()
    try:
        for name, content in outputs.items():
            with (directory / name).open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
    except BaseException:
        for path in directory.iterdir():
            path.unlink()
        directory.rmdir()
        raise
    return "created"


def validate_protocol(root: Path) -> dict[str, Any]:
    expected = build_protocol(root)
    directory = root / DATA_DIRECTORY
    manifest = {
        "schema_version": "pvr-human-knowledge-admission-development-manifest-v1",
        "version": VERSION,
        "protocol_sha256": hashlib.sha256(_json(expected).encode()).hexdigest(),
        "source_sha256": expected["sources"],
        "retrieval_executed": False,
        "private_local_artifacts_read": False,
    }
    _assert_file(directory / "protocol.json", _json(expected))
    _assert_file(directory / "protocol-manifest.json", _json(manifest))
    return expected


def _token_matches(identity_token: str, query_token: str) -> bool:
    if identity_token == query_token:
        return True
    shorter, longer = sorted((identity_token, query_token), key=len)
    if len(shorter) >= 3 and shorter in longer:
        return True
    if len(shorter) >= 2 and longer.startswith(shorter):
        return True
    if len(shorter) >= 2 and shorter.isdigit() and longer.isdigit() and longer.endswith(shorter):
        return True
    return SequenceMatcher(None, identity_token, query_token).ratio() >= TOKEN_SIMILARITY


def identity_token_coverage(query: str, document: HumanKnowledgeDocument) -> float:
    policy = IdentityCorePolicy()
    query_tokens = tuple(policy.core(query).split())
    if not query_tokens:
        return 0.0
    identities = document.character_identity_texts
    coverages = []
    for identity in identities:
        tokens = tuple(policy.core(identity).split())
        if not tokens:
            continue
        matched = sum(
            any(_token_matches(identity_token, query_token) for query_token in query_tokens)
            for identity_token in tokens
        )
        coverages.append(matched / len(tokens))
    return max(coverages, default=0.0)


def _candidate(candidate: Any, query: str) -> dict[str, Any]:
    return {
        "knowledge_id": candidate.document.knowledge_id,
        "knowledge_uuid": str(candidate.document.knowledge_uuid),
        "knowledge_type": candidate.document.knowledge_type,
        "casting_id": getattr(candidate.document, "casting_id", None),
        "source_rank": candidate.rrf_rank,
        "identity_token_coverage": identity_token_coverage(query, candidate.document),
    }


def _cases(root: Path) -> list[dict[str, Any]]:
    existing = _load(root / EXISTING_PACK)
    new = validate_false_positive_pack(root)
    return [{"dataset": "existing", **case} for case in existing["cases"]] + [
        {"dataset": "false_positive", **case} for case in new["cases"]
    ]


def collect(root: Path) -> dict[str, Any]:
    protocol = validate_protocol(root)
    catalog = _catalog(root)
    retriever = HumanKnowledgeIdentityRetriever(
        catalog,
        HashingEmbedding(DIMENSIONS),
        HumanKnowledgeV4Config(
            CHARACTER_SCORE_FLOOR,
            CHARACTER_RRF_WEIGHT,
            artifact_version=f"{VERSION}-grid",
            artifact_sha256=_sha(root / DATA_DIRECTORY / "protocol.json"),
        ),
    )
    rows = []
    for case in _cases(root):
        query = case["query_text"]
        try:
            candidates, work = retriever.retrieve_with_work(extract_signals(query), CANDIDATE_LIMIT)
            row = {
                "candidates": [_candidate(candidate, query) for candidate in candidates],
                "work": work.as_dict(),
                "error": None,
            }
        except Exception as error:  # noqa: BLE001 - preserve every development error once
            row = {
                "candidates": [],
                "work": None,
                "error": {"type": type(error).__name__, "message": str(error)},
            }
        rows.append(
            {
                "dataset": case["dataset"],
                "case_id": case["case_id"],
                "query_text": query,
                **row,
            }
        )
    if len(rows) != 223:
        raise ValueError("grid collection must contain exactly 223 rows")
    return {
        "schema_version": "pvr-human-knowledge-admission-development-raw-v1",
        "version": VERSION,
        "protocol_sha256": _sha(root / DATA_DIRECTORY / "protocol.json"),
        "configuration_count": len(CONFIGURATIONS),
        "query_count": 223,
        "retrieval_calls": 223,
        "candidate_limit": CANDIDATE_LIMIT,
        "corpus_document_count": 142,
        "base_retriever": protocol["base_retriever"],
        "rows": rows,
    }


def _filtered(row: dict[str, Any], threshold: float) -> list[dict[str, Any]]:
    return [
        candidate
        for candidate in row["candidates"]
        if candidate["identity_token_coverage"] + 1e-12 >= threshold
    ]


def summarize(
    cases: list[dict[str, Any]], rows: list[dict[str, Any]], threshold: float
) -> dict[str, Any]:
    counts = {
        "existing_positive_hits_at_5": 0,
        "existing_positive_hits_at_1": 0,
        "merge_hits_at_5": 0,
        "existing_forbidden_candidates": 0,
        "unrelated_nonempty": 0,
        "new_required_hits_at_5": 0,
        "new_forbidden_hit_cases_at_5": 0,
        "new_forbidden_candidates_at_5": 0,
        "retrieval_errors": 0,
    }
    case_results = []
    for case, row in zip(cases, rows, strict=True):
        if (
            row["dataset"] != case["dataset"]
            or row["case_id"] != case["case_id"]
            or row["query_text"] != case["query_text"]
        ):
            raise ValueError("raw row differs from ordered development case")
        candidates = _filtered(row, threshold)
        counts["retrieval_errors"] += row["error"] is not None
        result: dict[str, Any] = {"dataset": case["dataset"], "case_id": case["case_id"]}
        if case["dataset"] == "false_positive":
            required = case["expected"]["required"]
            forbidden = case["expected"]["forbidden"]
            required_rank = next(
                (
                    index
                    for index, candidate in enumerate(candidates, 1)
                    if candidate["knowledge_id"] == required["knowledge_id"]
                    and candidate["knowledge_uuid"] == required["knowledge_uuid"]
                ),
                None,
            )
            forbidden_ranks = [
                index
                for index, candidate in enumerate(candidates, 1)
                if candidate["knowledge_id"] == forbidden["knowledge_id"]
                and candidate["knowledge_uuid"] == forbidden["knowledge_uuid"]
            ]
            counts["new_required_hits_at_5"] += required_rank is not None
            counts["new_forbidden_hit_cases_at_5"] += bool(forbidden_ranks)
            counts["new_forbidden_candidates_at_5"] += len(forbidden_ranks)
            result.update(required_rank=required_rank, forbidden_ranks=forbidden_ranks)
        elif case["case_type"] == "positive_family":
            target = case["expected"]["review_family_id"]
            rank = next(
                (
                    index
                    for index, candidate in enumerate(candidates, 1)
                    if candidate["knowledge_type"] == "review_family"
                    and candidate["knowledge_id"] == target
                ),
                None,
            )
            counts["existing_positive_hits_at_5"] += rank is not None
            counts["existing_positive_hits_at_1"] += rank == 1
            result["target_rank"] = rank
        elif case["case_type"] == "merge_control":
            target = case["expected"]["casting_id"]
            rank = next(
                (
                    index
                    for index, candidate in enumerate(candidates, 1)
                    if candidate["knowledge_type"] == "provisional_variant"
                    and candidate["casting_id"] == target
                ),
                None,
            )
            counts["merge_hits_at_5"] += rank is not None
            forbidden = case["expected"]["forbidden_review_family_id"]
            violations = sum(candidate["knowledge_id"] == forbidden for candidate in candidates)
            counts["existing_forbidden_candidates"] += violations
            result.update(target_rank=rank, forbidden_candidates=violations)
        elif case["case_type"] == "hold_control":
            forbidden = case["expected"]["forbidden_review_family_id"]
            violations = sum(candidate["knowledge_id"] == forbidden for candidate in candidates)
            counts["existing_forbidden_candidates"] += violations
            result["forbidden_candidates"] = violations
        elif case["case_type"] == "unrelated_control":
            counts["unrelated_nonempty"] += bool(candidates)
            result["candidate_count"] = len(candidates)
        else:
            raise ValueError("unexpected development case type")
        case_results.append(result)
    gate_results = [
        {
            "name": name,
            "operator": "=",
            "threshold": expected,
            "actual": counts[name],
            "passed": counts[name] == expected,
        }
        for name, expected in GATES.items()
    ]
    return {
        "counts": counts,
        "metrics": {
            "existing_positive_recall_at_5": counts["existing_positive_hits_at_5"] / 168,
            "existing_positive_recall_at_1": counts["existing_positive_hits_at_1"] / 168,
            "new_required_recall_at_5": counts["new_required_hits_at_5"] / 24,
            "new_forbidden_case_rate_at_5": counts["new_forbidden_hit_cases_at_5"] / 24,
            "new_safety_accuracy_at_5": (24 - counts["new_forbidden_hit_cases_at_5"]) / 24,
        },
        "gates": gate_results,
        "eligible": all(gate["passed"] for gate in gate_results),
        "case_results": case_results,
    }


def score(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    cases = _cases(root)
    summaries = []
    for configuration_id, threshold in CONFIGURATIONS:
        summaries.append(
            {
                "configuration_id": configuration_id,
                "minimum_identity_token_coverage": threshold,
                **summarize(cases, raw["rows"], threshold),
            }
        )
    eligible = [summary for summary in summaries if summary["eligible"]]
    winner = min(
        eligible,
        key=lambda summary: (
            summary["counts"]["new_forbidden_hit_cases_at_5"],
            summary["minimum_identity_token_coverage"],
        ),
        default=None,
    )
    return {
        "summaries": summaries,
        "winner": (
            {
                "configuration_id": winner["configuration_id"],
                "minimum_identity_token_coverage": winner["minimum_identity_token_coverage"],
                "counts": winner["counts"],
                "metrics": winner["metrics"],
                "selection_rule": "eligible_min_forbidden_then_lowest_threshold",
                "status": "selected_development_only_not_runtime",
            }
            if winner is not None
            else None
        ),
    }


def _report(root: Path, raw: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": REPORT_SCHEMA,
        "version": VERSION,
        "status": "development_selection_complete_not_runtime",
        "protocol_sha256": raw["protocol_sha256"],
        "protocol_manifest_sha256": _sha(root / DATA_DIRECTORY / "protocol-manifest.json"),
        "sources": _sources(root),
        "raw": raw,
        "limitations": [
            "development_only_not_final_accuracy",
            "identity_derived_existing_pack_and_manual_related_pairs",
            "top5_post_filter_not_new_retrieval_model",
            "no_private_local_evaluation",
            "selected_policy_not_runtime_activated",
        ],
        **score(root, raw),
    }


def _markdown(report: dict[str, Any]) -> str:
    rows = [
        "# Human Knowledge admission-policy development selection",
        "",
        "This is development selection only; runtime and private final evaluation are unchanged.",
        "",
        "| Configuration | Coverage | Eligible | Existing R@5 | New required | Forbidden cases | Safety |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for summary in report["summaries"]:
        rows.append(
            f"| {summary['configuration_id']} | "
            f"{summary['minimum_identity_token_coverage']:.4f} | "
            f"{'yes' if summary['eligible'] else 'no'} | "
            f"{summary['counts']['existing_positive_hits_at_5']}/168 | "
            f"{summary['counts']['new_required_hits_at_5']}/24 | "
            f"{summary['counts']['new_forbidden_hit_cases_at_5']}/24 | "
            f"{summary['metrics']['new_safety_accuracy_at_5']:.4f} |"
        )
    rows.extend(["", "## Selection", ""])
    winner = report["winner"]
    if winner is None:
        rows.append("No configuration passed every frozen recall and governance gate.")
    else:
        rows.extend(
            [
                f"Selected development configuration: **{winner['configuration_id']}** ",
                f"with minimum identity-token coverage `{winner['minimum_identity_token_coverage']}`.",
                "",
                "The winner is not active in the API or Dual RAG runtime.",
            ]
        )
    rows.append("")
    return "\n".join(rows)


def run(root: Path) -> tuple[dict[str, Any], str]:
    directory = root / REPORT_DIRECTORY
    if directory.exists():
        return check(root), "unchanged"
    report = _report(root, collect(root))
    outputs = {"selection.json": _json(report), "selection.md": _markdown(report)}
    directory.mkdir()
    try:
        for name, content in outputs.items():
            with (directory / name).open("x", encoding="utf-8", newline="\n") as handle:
                handle.write(content)
    except BaseException:
        for path in directory.iterdir():
            path.unlink()
        directory.rmdir()
        raise
    return check(root), "created"


def check(root: Path) -> dict[str, Any]:
    validate_protocol(root)
    directory = root / REPORT_DIRECTORY
    report = _load(directory / "selection.json")
    raw = report.get("raw")
    if (
        not isinstance(raw, dict)
        or report.get("schema_version") != REPORT_SCHEMA
        or raw.get("query_count") != 223
        or raw.get("retrieval_calls") != 223
        or raw.get("protocol_sha256") != _sha(root / DATA_DIRECTORY / "protocol.json")
        or report.get("sources") != _sources(root)
    ):
        raise ValueError("admission selection metadata differs from contract")
    catalog = {str(item.knowledge_uuid): item for item in _catalog(root).documents}
    cases = _cases(root)
    for case, row in zip(cases, raw["rows"], strict=True):
        if row["case_id"] != case["case_id"] or row["query_text"] != case["query_text"]:
            raise ValueError("admission raw row differs from frozen case")
        for rank, candidate in enumerate(row["candidates"], 1):
            document = catalog.get(candidate["knowledge_uuid"])
            if (
                document is None
                or document.knowledge_id != candidate["knowledge_id"]
                or document.knowledge_type != candidate["knowledge_type"]
                or candidate["source_rank"] != rank
                or candidate["identity_token_coverage"]
                != identity_token_coverage(row["query_text"], document)
            ):
                raise ValueError("admission raw candidate differs from corpus or policy")
    rescored = score(root, raw)
    if (
        report.get("summaries") != rescored["summaries"]
        or report.get("winner") != rescored["winner"]
    ):
        raise ValueError("admission selection differs from deterministic scoring")
    _assert_file(directory / "selection.md", _markdown(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Select a development-only admission policy")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--freeze-protocol", action="store_true")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.freeze_protocol:
        operation = freeze_protocol(root)
        output = {"operation": operation, "retrieval_executed": False, "configurations": 5}
    elif arguments.check:
        report = check(root)
        output = {"operation": "valid", "winner": report["winner"]}
    else:
        report, operation = run(root)
        output = {"operation": operation, "winner": report["winner"]}
    print(json.dumps(output, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
