"""Freeze and measure a public development-only false-positive benchmark."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from .human_knowledge import HumanKnowledgeCatalog, load_human_knowledge_catalog
from .human_knowledge_identity import (
    HumanKnowledgeIdentityRetriever,
    HumanKnowledgeV4Config,
    IdentityCorePolicy,
)
from .retrieval import HashingEmbedding
from .signals import extract_signals

VERSION = "human-knowledge-false-positive-development-v1"
PACK_SCHEMA = "pvr-human-knowledge-false-positive-development-pack-v1"
MANIFEST_SCHEMA = "pvr-human-knowledge-false-positive-development-manifest-v1"
BASELINE_SCHEMA = "pvr-human-knowledge-false-positive-development-baseline-v1"
DATA_DIRECTORY = Path("data/evaluation") / VERSION
REPORT_DIRECTORY = Path("reports") / VERSION
SOURCE = "src/product_variant_resolver/human_knowledge_false_positive_development.py"
INPUTS = (
    "data/human_backed_catalog.json",
    "data/review_family_knowledge.json",
    "data/review_family_knowledge_manifest.json",
)
CANDIDATE_LIMIT = 5
DIMENSIONS = 192
CHARACTER_SCORE_FLOOR = 0.5
CHARACTER_RRF_WEIGHT = 1.0

# Authored before this pack's retriever output was observed. All cases use only the committed
# 142-document corpus; none references a local five-document projection identity or private query.
CASE_SPECS = (
    (
        "fpdev-01-lamborghini",
        "collector listing Lamborghini Sesto Elemento loose miniature",
        "human-hot-wheels-lamborghini-sesto-elemento-mainline-hw-exotics",
        "fandom-family-174efb9bce3a441e",
    ),
    (
        "fpdev-02-mercedes-sprinter",
        "preowned Mercedes Benz Sprinter delivery van miniature",
        "human-hot-wheels-mercedes-benz-sprinter-car-culture-premium-deutschland-design",
        "fandom-family-1b2a4227b4e5decd",
    ),
    (
        "fpdev-03-mercedes-dtm",
        "boxed 1994 AMG Mercedes C Class DTM collector car",
        "human-hot-wheels-1994-amg-mercedes-c-class-dtm-car-culture-premium-deutschland-design",
        "fandom-family-1b2a4227b4e5decd",
    ),
    (
        "fpdev-04-mazda-rx7",
        "loose Mazda RX7 street model from collection",
        "human-hot-wheels-mazda-rx7-mainline-blue",
        "fandom-family-aec11693bfe04245",
    ),
    (
        "fpdev-05-mazda-autozam",
        "carded Mazda Autozam kei vehicle listing",
        "fandom-family-e7d4d8cf1dd8c6e1",
        "fandom-family-aec11693bfe04245",
    ),
    (
        "fpdev-06-ford-escort",
        "used Ford Escort RS2000 red edition model",
        "human-hot-wheels-ford-escort-rs2000-mainline-red-edition",
        "fandom-family-b31d285560d8a242",
    ),
    (
        "fpdev-07-ford-mustang-boss",
        "loose 1969 Ford Mustang Boss 302 collector piece",
        "human-hot-wheels-1969-ford-mustang-boss-302-premium-premium-fast-and-furious",
        "fandom-family-b31d285560d8a242",
    ),
    (
        "fpdev-08-ford-focus",
        "street racers 2008 Ford Focus miniature listing",
        "human-hot-wheels-08-ford-focus-street-racers-street-racers",
        "human-hot-wheels-ford-escort-rs2000-mainline-red-edition",
    ),
    (
        "fpdev-09-honda-civic-eg",
        "premium Honda Civic EG loose vehicle",
        "human-hot-wheels-honda-civic-eg-premium-fast-furious",
        "fandom-family-d114c33db6fa215b",
    ),
    (
        "fpdev-10-honda-crx",
        "silver series Honda CR X collector car",
        "human-hot-wheels-honda-cr-x-silver-series-peanuts",
        "fandom-family-d114c33db6fa215b",
    ),
    (
        "fpdev-11-honda-city",
        "compact king Honda City Turbo loose model",
        "human-hot-wheels-honda-city-turbo-ll-mainline-compact-king",
        "fandom-family-d114c33db6fa215b",
    ),
    (
        "fpdev-12-bugatti",
        "quarter mile Bugatti Veyron display vehicle",
        "human-hot-wheels-bugatti-veyron-1-4-mile-finals-1-4-mile-finals",
        "human-hot-wheels-16-bugatti-chiron-mainline-hw-exotics",
    ),
    (
        "fpdev-13-bmw-m1",
        "red BMW M1 collector listing without package",
        "human-hot-wheels-bmw-m1-walmart-exclusive-walmart-exclusive-red",
        "human-hot-wheels-bmw-m3-gt2-neon-speeders-neon-speeders",
    ),
    (
        "fpdev-14-bmw-m2",
        "matchbox 2023 BMW M2 loose miniature",
        "human-matchbox-2023-bmw-m2-match-box-mainline-red",
        "human-hot-wheels-bmw-m3-gt2-neon-speeders-neon-speeders",
    ),
    (
        "fpdev-15-subaru",
        "off road Subaru Brat pearl yellow model",
        "human-hot-wheels-subaru-brat-hw-off-road-pearl-yellow-kmart-exclusive",
        "human-hot-wheels-subaru-brz-walmart-exclusive-zamac-walmart-exclusive",
    ),
    (
        "fpdev-16-tesla",
        "greetings from space Tesla Roadster loose car",
        "human-hot-wheels-08-tesla-roadster-hot-wheels-tesla-greetings-from-space",
        "human-hot-wheels-tesla-model-s-plaid-mainline-red",
    ),
    (
        "fpdev-17-pontiac",
        "1970 Pontiac Firebird kroger edition listing",
        "human-hot-wheels-1970-pontiac-firebird-mainline-kroger-exclusive",
        "human-hot-wheels-1969-pontiac-gto-hot-wheels-classics-hot-wheels-classics",
    ),
    (
        "fpdev-18-shelby",
        "Gulf Shelby Cobra Daytona Coupe race day model",
        "human-hot-wheels-shelby-cobra-daytona-coupe-mainline-hw-race-day-gulf",
        "human-hot-wheels-shelby-cobra-427-s-c-mainline-yellow",
    ),
    (
        "fpdev-19-nissan-fairlady",
        "blue Nissan Fairlady Z silver series vehicle",
        "human-hot-wheels-nissan-fairlady-z-silver-series-pantone-blue",
        "human-hot-wheels-nissan-300zx-twin-turbo-90s-silver-series-street-scene",
    ),
    (
        "fpdev-20-nissan-leaf",
        "treasure hunt Nissan Leaf Nismo RC miniature",
        "human-hot-wheels-nissan-leaf-nismo-rc-mainline-treasure-hunt",
        "human-hot-wheels-nissan-skyline-rs-the-hot-ones-the-hot-ones",
    ),
    (
        "fpdev-21-cadillac",
        "gold 1935 Cadillac loose collector model",
        "human-hot-wheels-1935-cadillac-mainline-gold",
        "fandom-family-45af5b93f3f6650f",
    ),
    (
        "fpdev-22-chevrolet",
        "premium 1967 Chevrolet Camaro display car",
        "human-hot-wheels-67-chevrolet-camaro-premium-premium-fast-and-furious",
        "human-hot-wheels-1970-chevrolet-chevelle-ss-premium-premium-fast-and-furious",
    ),
    (
        "fpdev-23-twin-mill",
        "electric Twin Mill Gen E loose fantasy casting",
        "fandom-family-39b248ce2f3723cd",
        "fandom-family-d5c83bb87be8cab0",
    ),
    (
        "fpdev-24-ford-truck",
        "red 2020 Ford F 150 Lariat diecast truck",
        "human-auto-world-2020-ford-f-150-lariat-auto-world-red",
        "human-m2-1956-ford-f-100-truck-m2-target-exclusive",
    ),
)


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
    return load_human_knowledge_catalog(
        root / INPUTS[0],
        root / INPUTS[1],
        root / INPUTS[2],
    )


def _sources(root: Path) -> dict[str, str]:
    return {name: _sha(root / name) for name in (*INPUTS, SOURCE)}


def build_pack(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    catalog = _catalog(root)
    documents = {document.knowledge_id: document for document in catalog.documents}
    if len(documents) != 142:
        raise ValueError("development source corpus must contain exactly 142 documents")
    policy = IdentityCorePolicy()
    cases: list[dict[str, Any]] = []
    seen_queries: set[str] = set()
    seen_ids: set[str] = set()
    for case_id, query, required_id, forbidden_id in CASE_SPECS:
        required = documents.get(required_id)
        forbidden = documents.get(forbidden_id)
        if required is None or forbidden is None or required_id == forbidden_id:
            raise ValueError("development pair does not resolve to two corpus documents")
        query_normalized = extract_signals(query).normalized_title
        identities = {
            extract_signals(value).normalized_title
            for document in (required, forbidden)
            for value in (document.casting, *getattr(document, "aliases", ()))
        }
        if query_normalized in identities:
            raise ValueError("development query must not equal either identity")
        required_tokens = set(policy.core(required.casting).split())
        forbidden_tokens = set(policy.core(forbidden.casting).split())
        shared = sorted(required_tokens & forbidden_tokens)
        if not shared:
            raise ValueError("development pair must share an identity-core token")
        if case_id in seen_ids or query_normalized in seen_queries:
            raise ValueError("development case IDs and normalized queries must be unique")
        seen_ids.add(case_id)
        seen_queries.add(query_normalized)
        cases.append(
            {
                "case_id": case_id,
                "case_type": "required_plus_forbidden",
                "query_text": query,
                "split": "dev",
                "shared_identity_core_tokens": shared,
                "expected": {
                    "required": {
                        "knowledge_id": required.knowledge_id,
                        "knowledge_uuid": str(required.knowledge_uuid),
                        "knowledge_type": required.knowledge_type,
                    },
                    "forbidden": {
                        "knowledge_id": forbidden.knowledge_id,
                        "knowledge_uuid": str(forbidden.knowledge_uuid),
                        "knowledge_type": forbidden.knowledge_type,
                    },
                },
            }
        )
    if len(cases) != 24:
        raise ValueError("false-positive development pack must contain exactly 24 cases")
    pack = {
        "schema_version": PACK_SCHEMA,
        "version": VERSION,
        "status": "development_only_frozen_before_baseline",
        "split": "dev",
        "case_count": 24,
        "candidate_limit": CANDIDATE_LIMIT,
        "corpus_document_count": 142,
        "configuration": {
            "retriever_version": "human-knowledge-hybrid-v4",
            "character_score_floor": CHARACTER_SCORE_FLOOR,
            "character_rrf_weight": CHARACTER_RRF_WEIGHT,
            "dense_embedding": "hashing-v1",
            "dense_dimensions": DIMENSIONS,
        },
        "authorship": {
            "method": "manual_related_identity_pairs_before_pack_baseline",
            "retriever_output_viewed_for_this_pack": False,
            "private_local_evaluation_loaded": False,
            "eligible_for_final_accuracy": False,
            "eligible_for_development": True,
        },
        "excluded_from": [
            "final_accuracy",
            "runtime_activation",
            "canonical_truth",
            "release_variant_truth",
            "color_truth",
            "private_local_evaluation_tuning",
        ],
        "cases": cases,
    }
    manifest = {
        "schema_version": MANIFEST_SCHEMA,
        "version": VERSION,
        "source_sha256": _sources(root),
        "pack_sha256": hashlib.sha256(_json(pack).encode()).hexdigest(),
        "case_count": 24,
        "retrieval_executed": False,
        "private_local_artifacts_read": False,
    }
    return pack, manifest


def _assert_file(path: Path, content: str) -> None:
    if not path.is_file() or path.read_text(encoding="utf-8") != content:
        raise ValueError(f"{path} differs from deterministic artifact")


def freeze_pack(root: Path) -> str:
    directory = root / DATA_DIRECTORY
    pack, manifest = build_pack(root)
    outputs = {
        "development-pack.json": _json(pack),
        "development-pack-manifest.json": _json(manifest),
    }
    if directory.exists():
        if {path.name for path in directory.iterdir()} != set(outputs):
            raise ValueError("development pack directory is partial or conflicting")
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


def validate_pack(root: Path) -> dict[str, Any]:
    expected_pack, expected_manifest = build_pack(root)
    directory = root / DATA_DIRECTORY
    _assert_file(directory / "development-pack.json", _json(expected_pack))
    _assert_file(directory / "development-pack-manifest.json", _json(expected_manifest))
    return expected_pack


def _candidate(candidate: Any) -> dict[str, Any]:
    return {
        "knowledge_id": candidate.document.knowledge_id,
        "knowledge_uuid": str(candidate.document.knowledge_uuid),
        "knowledge_type": candidate.document.knowledge_type,
        "rank": candidate.rrf_rank,
    }


def collect(root: Path) -> dict[str, Any]:
    pack = validate_pack(root)
    catalog = _catalog(root)
    retriever = HumanKnowledgeIdentityRetriever(
        catalog,
        HashingEmbedding(DIMENSIONS),
        HumanKnowledgeV4Config(
            CHARACTER_SCORE_FLOOR,
            CHARACTER_RRF_WEIGHT,
            artifact_version=f"{VERSION}-baseline",
            artifact_sha256=_sha(root / DATA_DIRECTORY / "development-pack.json"),
        ),
    )
    rows: list[dict[str, Any]] = []
    for case in pack["cases"]:
        try:
            candidates, work = retriever.retrieve_with_work(
                extract_signals(case["query_text"]), CANDIDATE_LIMIT
            )
            row = {
                "candidates": [_candidate(candidate) for candidate in candidates],
                "work": work.as_dict(),
                "error": None,
            }
        except Exception as error:  # noqa: BLE001 - preserve each development failure once
            row = {
                "candidates": [],
                "work": None,
                "error": {"type": type(error).__name__, "message": str(error)},
            }
        rows.append({"case_id": case["case_id"], "query_text": case["query_text"], **row})
    return {
        "schema_version": BASELINE_SCHEMA,
        "version": VERSION,
        "status": "baseline_recorded_no_mitigation_selected",
        "pack_sha256": _sha(root / DATA_DIRECTORY / "development-pack.json"),
        "corpus_document_count": 142,
        "candidate_limit": CANDIDATE_LIMIT,
        "configuration": pack["configuration"],
        "rows": rows,
    }


def score(pack: dict[str, Any], baseline: dict[str, Any]) -> dict[str, Any]:
    rows = baseline.get("rows")
    if not isinstance(rows, list) or len(rows) != 24:
        raise ValueError("baseline must contain exactly 24 rows")
    required_hits = 0
    forbidden_cases = 0
    forbidden_candidates = 0
    errors = 0
    results: list[dict[str, Any]] = []
    for case, row in zip(pack["cases"], rows, strict=True):
        if row.get("case_id") != case["case_id"] or row.get("query_text") != case["query_text"]:
            raise ValueError("baseline row differs from frozen development case")
        candidates = row.get("candidates")
        if not isinstance(candidates, list):
            raise TypeError("baseline candidates must be a list")
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
        required_hits += required_rank is not None
        forbidden_cases += bool(forbidden_ranks)
        forbidden_candidates += len(forbidden_ranks)
        errors += row.get("error") is not None
        results.append(
            {
                "case_id": case["case_id"],
                "required_rank": required_rank,
                "forbidden_ranks": forbidden_ranks,
            }
        )
    return {
        "counts": {
            "cases": 24,
            "required_hits_at_5": required_hits,
            "forbidden_hit_cases_at_5": forbidden_cases,
            "forbidden_candidates_at_5": forbidden_candidates,
            "retrieval_errors": errors,
        },
        "metrics": {
            "required_recall_at_5": required_hits / 24,
            "forbidden_case_rate_at_5": forbidden_cases / 24,
            "safety_accuracy_at_5": (24 - forbidden_cases) / 24,
        },
        "case_results": results,
    }


def _complete(root: Path, baseline: dict[str, Any]) -> dict[str, Any]:
    pack = validate_pack(root)
    return {
        **baseline,
        "source_sha256": _sources(root),
        "pack_manifest_sha256": _sha(root / DATA_DIRECTORY / "development-pack-manifest.json"),
        "limitations": [
            "development_only_not_final_accuracy",
            "manually_authored_related_pairs_not_population_sample",
            "current_142_document_corpus_only",
            "no_local_five_document_evaluation",
            "no_mitigation_or_runtime_selection",
        ],
        **score(pack, baseline),
    }


def _markdown(report: dict[str, Any]) -> str:
    counts = report["counts"]
    metrics = report["metrics"]
    return "\n".join(
        [
            "# Human Knowledge false-positive development baseline",
            "",
            "Status: **BASELINE RECORDED — no mitigation selected**.",
            "",
            f"- Development cases: {counts['cases']}",
            f"- Required targets retrieved at 5: {counts['required_hits_at_5']}/24",
            f"- Cases with forbidden candidate at 5: {counts['forbidden_hit_cases_at_5']}/24",
            f"- Forbidden candidates at 5: {counts['forbidden_candidates_at_5']}",
            f"- Required Recall@5: {metrics['required_recall_at_5']:.4f}",
            f"- Safety accuracy@5: {metrics['safety_accuracy_at_5']:.4f}",
            f"- Retrieval errors: {counts['retrieval_errors']}",
            "",
            "This is development evidence, not final accuracy or permission to change runtime.",
            "The private local-family evaluation was not loaded or rerun.",
            "",
        ]
    )


def evaluate(root: Path) -> tuple[dict[str, Any], str]:
    directory = root / REPORT_DIRECTORY
    if directory.exists():
        return check(root), "unchanged"
    baseline = _complete(root, collect(root))
    outputs = {"baseline.json": _json(baseline), "baseline.md": _markdown(baseline)}
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
    pack = validate_pack(root)
    directory = root / REPORT_DIRECTORY
    report = _load(directory / "baseline.json")
    if (
        report.get("schema_version") != BASELINE_SCHEMA
        or report.get("pack_sha256") != _sha(root / DATA_DIRECTORY / "development-pack.json")
        or report.get("corpus_document_count") != 142
        or report.get("candidate_limit") != CANDIDATE_LIMIT
    ):
        raise ValueError("development baseline metadata differs from contract")
    expected_score = score(pack, report)
    for name, value in expected_score.items():
        if report.get(name) != value:
            raise ValueError("development baseline score differs from raw rows")
    if report.get("source_sha256") != _sources(root):
        raise ValueError("development baseline source hashes are stale")
    if report.get("pack_manifest_sha256") != _sha(
        root / DATA_DIRECTORY / "development-pack-manifest.json"
    ):
        raise ValueError("development baseline manifest hash is stale")
    catalog = {str(item.knowledge_uuid): item for item in _catalog(root).documents}
    for row in report["rows"]:
        if row["error"] is None and not isinstance(row["work"], dict):
            raise TypeError("successful development row must contain work counters")
        if row["error"] is not None and (row["candidates"] or row["work"] is not None):
            raise ValueError("failed development row contains partial candidates")
        for rank, candidate in enumerate(row["candidates"], 1):
            document = catalog.get(candidate.get("knowledge_uuid"))
            if (
                set(candidate) != {"knowledge_id", "knowledge_uuid", "knowledge_type", "rank"}
                or candidate["rank"] != rank
                or document is None
                or document.knowledge_id != candidate["knowledge_id"]
                or document.knowledge_type != candidate["knowledge_type"]
            ):
                raise ValueError("development candidate differs from the source corpus")
    _assert_file(directory / "baseline.md", _markdown(report))
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Develop Human Knowledge admission safety")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--freeze-pack", action="store_true")
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    if arguments.freeze_pack:
        operation = freeze_pack(root)
        payload = {"operation": operation, "case_count": 24, "retrieval_executed": False}
    elif arguments.check:
        report = check(root)
        payload = {"operation": "valid", **report["counts"], **report["metrics"]}
    else:
        report, operation = evaluate(root)
        payload = {"operation": operation, **report["counts"], **report["metrics"]}
    print(json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
