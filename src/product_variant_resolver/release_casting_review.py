"""Build a private, review-only casting queue from local release staging."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .release_staging import (
    REVIEW_STATUS,
    SOURCE_RIGHTS_STATE,
    USAGE,
    digest,
)
from .release_staging import check_bundle as check_staging_bundle

SCHEMA_VERSION = "pvr-local-release-casting-review-v1"
REVIEW_VERSION = "local-release-casting-review-v1"
PUBLIC_SCHEMA_VERSION = "pvr-local-release-casting-review-public-summary-v1"
STATUSES = (
    "exact_both_sources",
    "exact_canonical_fixture_only",
    "exact_human_draft_only",
    "no_exact_candidate",
)
PRIORITY = {
    "exact_both_sources": 1,
    "exact_canonical_fixture_only": 2,
    "exact_human_draft_only": 3,
    "no_exact_candidate": 5,
}


def _load_object(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError(f"{path.name}: could not read a JSON object") from error
    if not isinstance(payload, dict):
        raise TypeError(f"{path.name}: root must be an object")
    return payload


def normalize_review_text(value: str) -> str:
    ascii_value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii").casefold()
    )
    return " ".join(re.findall(r"[a-z0-9]+", ascii_value))


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"blank or invalid {field}")
    return value.strip()


def _records(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    records = snapshot.get("records")
    if not isinstance(records, list) or not records:
        raise ValueError("staging snapshot must contain records[]")
    checked: list[dict[str, Any]] = []
    source_ids: set[str] = set()
    for index, item in enumerate(records):
        if not isinstance(item, dict):
            raise TypeError(f"staging record {index} must be an object")
        source_id = _required_text(item.get("source_record_id"), "source_record_id")
        if source_id in source_ids:
            raise ValueError(f"duplicate source_record_id: {source_id}")
        source_ids.add(source_id)
        if item.get("review_status") != REVIEW_STATUS:
            raise ValueError("staging row bypasses needs_canonical_review")
        if item.get("usage") != USAGE:
            raise ValueError("staging row has non-staging usage")
        if item.get("canonical_uuid") is not None:
            raise ValueError("staging row already asserts a canonical UUID")
        if item.get("color") is not None:
            raise ValueError("casting review cannot infer or accept color")
        _required_text(item.get("brand"), "brand")
        _required_text(item.get("casting_name"), "casting_name")
        checked.append(item)
    return checked


def _catalog_lists(
    canonical_catalog: dict[str, Any], human_catalog: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    products = canonical_catalog.get("products")
    castings = human_catalog.get("castings")
    if not isinstance(products, list) or not products:
        raise ValueError("canonical catalog must contain products[]")
    if not isinstance(castings, list) or not castings:
        raise ValueError("human catalog must contain castings[]")
    if not all(isinstance(item, dict) for item in products + castings):
        raise TypeError("catalog entries must be objects")
    return products, castings


def _key(brand: Any, casting: Any) -> tuple[str, str]:
    normalized = (
        normalize_review_text(_required_text(brand, "brand")),
        normalize_review_text(_required_text(casting, "casting")),
    )
    if not all(normalized):
        raise ValueError("brand/casting normalization produced a blank key")
    return normalized


def _canonical_index(products: list[dict[str, Any]]) -> dict[tuple[str, str], dict[str, Any]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for product in products:
        grouped[_key(product.get("brand"), product.get("casting"))].append(product)
    result: dict[tuple[str, str], dict[str, Any]] = {}
    for key, members in grouped.items():
        ids = sorted(_required_text(item.get("canonical_id"), "canonical_id") for item in members)
        uuids = sorted(
            _required_text(item.get("canonical_uuid"), "canonical_uuid") for item in members
        )
        result[key] = {
            "brand": sorted({_required_text(item.get("brand"), "brand") for item in members}),
            "casting": sorted({_required_text(item.get("casting"), "casting") for item in members}),
            "product_count": len(members),
            "canonical_ids": ids,
            "canonical_uuids": uuids,
            "authority": "synthetic_fixture_not_real_catalog_truth",
        }
    return result


def _human_index(castings: list[dict[str, Any]]) -> dict[tuple[str, str], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for casting in castings:
        grouped[_key(casting.get("brand"), casting.get("casting"))].append(casting)
    result: dict[tuple[str, str], list[dict[str, Any]]] = {}
    for key, members in grouped.items():
        result[key] = sorted(
            [
                {
                    "brand": _required_text(item.get("brand"), "brand"),
                    "casting": _required_text(item.get("casting"), "casting"),
                    "casting_id": _required_text(item.get("casting_id"), "casting_id"),
                    "casting_uuid": _required_text(item.get("casting_uuid"), "casting_uuid"),
                    "authority": "human_backed_draft_not_canonical_truth",
                }
                for item in members
            ],
            key=lambda item: item["casting_id"],
        )
    return result


def _status(has_canonical: bool, has_human: bool) -> tuple[str, str]:
    if has_canonical and has_human:
        return "exact_both_sources", "compare_fixture_and_human_evidence"
    if has_canonical:
        return (
            "exact_canonical_fixture_only",
            "review_synthetic_fixture_family_without_promoting_variant",
        )
    if has_human:
        return "exact_human_draft_only", "review_human_draft_family"
    return "no_exact_candidate", "research_or_create_family_after_source_review"


def build_review_queue(
    snapshot: dict[str, Any],
    canonical_catalog: dict[str, Any],
    human_catalog: dict[str, Any],
) -> dict[str, Any]:
    if snapshot.get("source_rights_state") != SOURCE_RIGHTS_STATE:
        raise ValueError("staging source-rights state differs from the approved boundary")
    source_batch_id = _required_text(snapshot.get("batch_id"), "batch_id")
    records = _records(snapshot)
    products, human_castings = _catalog_lists(canonical_catalog, human_catalog)
    canonical = _canonical_index(products)
    human = _human_index(human_castings)

    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[_key(record.get("brand"), record.get("casting_name"))].append(record)

    clusters: list[dict[str, Any]] = []
    for key, members in grouped.items():
        canonical_candidate = canonical.get(key)
        human_candidates = human.get(key, [])
        status, action = _status(canonical_candidate is not None, bool(human_candidates))
        observed_brands = sorted({_required_text(item.get("brand"), "brand") for item in members})
        observed_labels = sorted(
            {_required_text(item.get("casting_name"), "casting_name") for item in members}
        )
        collision = len(observed_brands) > 1 or len(observed_labels) > 1
        priority = 4 if status == "no_exact_candidate" and collision else PRIORITY[status]
        source_ids = sorted(
            _required_text(item.get("source_record_id"), "source_record_id") for item in members
        )
        toy_numbers = sorted(
            _required_text(item.get("toy_number"), "toy_number") for item in members
        )
        year_values: set[int] = set()
        for item in members:
            year = item.get("release_year")
            if not isinstance(year, int) or isinstance(year, bool):
                raise ValueError("release years must be integers")
            year_values.add(year)
        years = sorted(year_values)
        clusters.append(
            {
                "review_cluster_id": "release-casting-" + digest({"key": key})[:20],
                "normalized_key": {"brand": key[0], "casting": key[1]},
                "observed_brands": observed_brands,
                "observed_casting_labels": observed_labels,
                "normalization_collision": collision,
                "observation_count": len(members),
                "release_years": years,
                "source_record_ids": source_ids,
                "toy_numbers": toy_numbers,
                "match_status": status,
                "canonical_fixture_candidate": canonical_candidate,
                "human_draft_candidates": human_candidates,
                "review_priority": priority,
                "recommended_action": action,
                "promotion_decision": "hold_for_human_review",
                "promotion_eligible": False,
                "canonical_uuid": None,
                "review_requirements": [
                    "confirm_casting_identity_from_attributable_evidence",
                    "decide_existing_or_new_family",
                    "keep_release_variant_and_color_separate",
                ],
            }
        )
    clusters.sort(
        key=lambda item: (
            item["review_priority"],
            item["normalized_key"]["brand"],
            item["normalized_key"]["casting"],
        )
    )
    status_clusters = Counter(item["match_status"] for item in clusters)
    status_observations = Counter(
        {
            status: sum(
                item["observation_count"] for item in clusters if item["match_status"] == status
            )
            for status in STATUSES
        }
    )
    summary = {
        "staged_observations": len(records),
        "raw_casting_labels": len(
            {
                (
                    _required_text(item.get("brand"), "brand"),
                    _required_text(item.get("casting_name"), "casting_name"),
                )
                for item in records
            }
        ),
        "normalized_review_clusters": len(clusters),
        "normalization_collision_clusters": sum(
            bool(item["normalization_collision"]) for item in clusters
        ),
        "candidate_cluster_counts": {status: status_clusters[status] for status in STATUSES},
        "candidate_observation_counts": {
            status: status_observations[status] for status in STATUSES
        },
        "unresolved_review_clusters": len(clusters),
        "approved_casting_links": 0,
        "canonical_promotions": 0,
        "reviewed_colors": 0,
        "network_requests": 0,
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "review_version": REVIEW_VERSION,
        "status": "human_review_required",
        "source_batch_id": source_batch_id,
        "source_rights_state": SOURCE_RIGHTS_STATE,
        "policy": {
            "grouping": "NFKD ASCII, casefold, alphanumeric normalized brand/casting",
            "candidate_matching": "exact normalized key only",
            "fuzzy_matching": False,
            "automatic_linking": False,
            "automatic_promotion": False,
            "color_review": False,
            "meaning_of_match": "review candidate only",
        },
        "summary": summary,
        "clusters": clusters,
    }


def build_public_manifest(
    queue: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    canonical_sha256: str,
    human_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "review_version": REVIEW_VERSION,
        "status": "human_review_required",
        "public_scope": "aggregate_counts_and_hashes_only_no_source_rows_or_casting_labels",
        "source_rights_state": SOURCE_RIGHTS_STATE,
        "source_batch_id": queue["source_batch_id"],
        "source_content_sha256": snapshot["content_sha256"],
        "canonical_catalog_sha256": canonical_sha256,
        "human_catalog_sha256": human_sha256,
        "private_queue_sha256": digest(queue),
        "summary": queue["summary"],
    }


def render_public_report(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    cluster_counts = summary["candidate_cluster_counts"]
    observation_counts = summary["candidate_observation_counts"]
    lines = [
        "# Local release casting review — public summary",
        "",
        "The private review queue was built offline from the owner-supplied staging snapshot.",
        "Exact matches are review candidates only; no identity, variant, color, or runtime truth was promoted.",
        "",
        f"- Staged observations: {summary['staged_observations']}",
        f"- Raw casting labels: {summary['raw_casting_labels']}",
        f"- Normalized review clusters: {summary['normalized_review_clusters']}",
        f"- Normalization-collision clusters: {summary['normalization_collision_clusters']}",
        f"- Unresolved review clusters: {summary['unresolved_review_clusters']}",
        f"- Approved casting links: {summary['approved_casting_links']}",
        f"- Canonical promotions: {summary['canonical_promotions']}",
        f"- Reviewed colors: {summary['reviewed_colors']}",
        "- Network requests: 0",
        "",
        "## Exact candidate classes",
        "",
    ]
    for status in STATUSES:
        lines.append(
            f"- `{status}`: {cluster_counts[status]} clusters / "
            f"{observation_counts[status]} observations"
        )
    lines.extend(
        [
            "",
            "The complete queue, source record references, and casting labels remain local and gitignored.",
            "The committed manifest contains only aggregate counts and input/private-artifact hashes.",
            "",
        ]
    )
    return "\n".join(lines)


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def build_artifacts(root: Path, staging_directory: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    snapshot = check_staging_bundle(staging_directory, root)
    canonical_path = root / "data" / "catalog.json"
    human_path = root / "data" / "human_backed_catalog.json"
    canonical_catalog = _load_object(canonical_path)
    human_catalog = _load_object(human_path)
    queue = build_review_queue(snapshot, canonical_catalog, human_catalog)
    manifest = build_public_manifest(
        queue,
        snapshot,
        canonical_sha256=hashlib.sha256(canonical_path.read_bytes()).hexdigest(),
        human_sha256=hashlib.sha256(human_path.read_bytes()).hexdigest(),
    )
    return queue, manifest


def _safe_directory(directory: Path, expected_parent: Path, label: str) -> None:
    if directory.absolute().parent != expected_parent.absolute():
        raise ValueError(f"{label} must be a direct child of {expected_parent}")
    if any(part.is_symlink() for part in (directory, *directory.parents)):
        raise ValueError(f"symlink {label} is not allowed")


def _write_directory(directory: Path, outputs: dict[str, str]) -> None:
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


def publish_review(
    root: Path,
    staging_directory: Path,
    private_directory: Path,
    public_directory: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _safe_directory(
        private_directory, root / "data" / "external" / "hot-wheels-wiki", "private output"
    )
    _safe_directory(public_directory, root / "reports", "public output")
    if private_directory.exists() or public_directory.exists():
        raise FileExistsError("review output already exists; use --check")
    queue, manifest = build_artifacts(root, staging_directory)
    report = render_public_report(manifest)
    created: list[Path] = []
    try:
        _write_directory(
            private_directory,
            {
                "queue.json": _stable_json(queue),
                "manifest.json": _stable_json(manifest),
                "report.md": report,
            },
        )
        created.append(private_directory)
        _write_directory(
            public_directory,
            {"manifest.json": _stable_json(manifest), "report.md": report},
        )
        created.append(public_directory)
    except BaseException:
        for directory in reversed(created):
            for path in directory.iterdir():
                path.unlink()
            directory.rmdir()
        raise
    return queue, manifest


def check_review(
    root: Path,
    staging_directory: Path,
    private_directory: Path,
    public_directory: Path,
) -> tuple[dict[str, Any], dict[str, Any]]:
    _safe_directory(
        private_directory, root / "data" / "external" / "hot-wheels-wiki", "private output"
    )
    _safe_directory(public_directory, root / "reports", "public output")
    queue, manifest = build_artifacts(root, staging_directory)
    report = render_public_report(manifest)
    expected = {
        private_directory: {
            "queue.json": _stable_json(queue),
            "manifest.json": _stable_json(manifest),
            "report.md": report,
        },
        public_directory: {"manifest.json": _stable_json(manifest), "report.md": report},
    }
    for directory, outputs in expected.items():
        if not directory.is_dir() or {path.name for path in directory.iterdir()} != set(outputs):
            raise ValueError(f"{directory.name}: review bundle files differ from contract")
        for name, content in outputs.items():
            if (directory / name).read_text(encoding="utf-8") != content:
                raise ValueError(f"{directory.name}/{name}: differs from deterministic build")
    return queue, manifest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build the private local casting review queue")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--staging",
        type=Path,
        default=Path("data/external/hot-wheels-wiki/local-export-2023-2026"),
    )
    parser.add_argument(
        "--private-output",
        type=Path,
        default=Path("data/external/hot-wheels-wiki/local-release-casting-review-v1"),
    )
    parser.add_argument(
        "--public-output", type=Path, default=Path("reports/local-release-casting-review-v1")
    )
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()

    def within_root(path: Path) -> Path:
        return path if path.is_absolute() else root / path

    operation = check_review if arguments.check else publish_review
    queue, manifest = operation(
        root,
        within_root(arguments.staging),
        within_root(arguments.private_output),
        within_root(arguments.public_output),
    )
    print(
        json.dumps(
            {
                "status": "valid" if arguments.check else "created",
                "private_queue_sha256": manifest["private_queue_sha256"],
                "summary": queue["summary"],
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
