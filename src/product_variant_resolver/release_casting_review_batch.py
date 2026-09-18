"""Prepare the fixed private owner packet for casting review batch 01."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .release_casting_review import check_review
from .release_staging import check_bundle as check_staging_bundle
from .release_staging import digest

SCHEMA_VERSION = "pvr-local-release-casting-review-batch-v1"
PACKET_VERSION = "local-release-casting-review-batch-01-v1"
PUBLIC_SCHEMA_VERSION = "pvr-local-release-casting-review-batch-public-summary-v1"
SELECTED_CLUSTER_IDS = (
    "release-casting-8668bd55fd1689d1ae8c",
    "release-casting-b9f73a5951248c10aedf",
    "release-casting-cd0350720f82607d46b0",
    "release-casting-c9c0e3efd1aad48b705d",
    "release-casting-e5b43dd13d1b8736ab80",
)
ALLOWED_DECISIONS = ("same_review_family", "keep_separate", "unknown")
OBSERVATION_FIELDS = (
    "source_record_id",
    "release_year",
    "toy_number",
    "collector_number",
    "source_model_label",
    "casting_name",
    "variant_note",
    "series",
    "series_position",
)


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"blank or invalid {field}")
    return value.strip()


def _selection_kind(cluster: dict[str, Any]) -> str:
    if cluster.get("match_status") == "exact_both_sources":
        return "cross_source_exact_candidate"
    if cluster.get("normalization_collision") is True:
        return "normalization_collision"
    if cluster.get("match_status") == "exact_canonical_fixture_only":
        return "synthetic_fixture_name_candidate"
    raise ValueError("selected cluster no longer matches the batch-01 selection policy")


def _candidate_summary(cluster: dict[str, Any]) -> dict[str, Any]:
    canonical = cluster.get("canonical_fixture_candidate")
    human = cluster.get("human_draft_candidates")
    if canonical is not None and not isinstance(canonical, dict):
        raise TypeError("canonical fixture candidate must be an object or null")
    if not isinstance(human, list) or not all(isinstance(item, dict) for item in human):
        raise TypeError("human draft candidates must be objects")
    canonical_summary = None
    if canonical is not None:
        canonical_summary = {
            "brand_labels": canonical.get("brand"),
            "casting_labels": canonical.get("casting"),
            "synthetic_product_count": canonical.get("product_count"),
            "canonical_ids": canonical.get("canonical_ids"),
            "authority": canonical.get("authority"),
        }
    return {
        "canonical_fixture": canonical_summary,
        "human_draft": [
            {
                "brand": item.get("brand"),
                "casting": item.get("casting"),
                "casting_id": item.get("casting_id"),
                "authority": item.get("authority"),
            }
            for item in human
        ],
    }


def build_owner_batch(
    queue: dict[str, Any],
    snapshot: dict[str, Any],
    *,
    selected_ids: tuple[str, ...] = SELECTED_CLUSTER_IDS,
) -> dict[str, Any]:
    if len(selected_ids) != 5 or len(set(selected_ids)) != 5:
        raise ValueError("batch 01 must contain five unique predeclared cluster IDs")
    if queue.get("status") != "human_review_required":
        raise ValueError("casting queue is not awaiting human review")
    if queue.get("source_batch_id") != snapshot.get("batch_id"):
        raise ValueError("casting queue and staging snapshot batch IDs differ")
    clusters = queue.get("clusters")
    records = snapshot.get("records")
    if not isinstance(clusters, list) or not isinstance(records, list):
        raise ValueError("queue clusters and staging records are required")
    if not all(isinstance(item, dict) for item in clusters + records):
        raise TypeError("queue clusters and staging records must be objects")
    cluster_map = {
        _required_text(item.get("review_cluster_id"), "review_cluster_id"): item
        for item in clusters
    }
    record_map = {
        _required_text(item.get("source_record_id"), "source_record_id"): item for item in records
    }
    if len(record_map) != len(records):
        raise ValueError("staging snapshot contains duplicate source IDs")

    questions: list[dict[str, Any]] = []
    for ordinal, cluster_id in enumerate(selected_ids, start=1):
        if cluster_id not in cluster_map:
            raise ValueError(f"selected cluster is absent: {cluster_id}")
        cluster = cluster_map[cluster_id]
        if cluster.get("promotion_eligible") is not False:
            raise ValueError("selected cluster is unexpectedly promotion eligible")
        if cluster.get("canonical_uuid") is not None:
            raise ValueError("selected cluster already has a canonical UUID")
        if cluster.get("promotion_decision") != "hold_for_human_review":
            raise ValueError("selected cluster is not held for human review")
        source_ids = cluster.get("source_record_ids")
        if not isinstance(source_ids, list) or not source_ids:
            raise ValueError("selected cluster has no source record IDs")
        observations: list[dict[str, Any]] = []
        for source_id in source_ids:
            source_id = _required_text(source_id, "source_record_id")
            if source_id not in record_map:
                raise ValueError(f"queue source record is absent from staging: {source_id}")
            record = record_map[source_id]
            if record.get("color") is not None:
                raise ValueError("batch 01 cannot accept or infer source color")
            observations.append({field: record.get(field) for field in OBSERVATION_FIELDS})
        observations.sort(
            key=lambda item: (item["release_year"], item["toy_number"], item["source_record_id"])
        )
        labels = cluster.get("observed_casting_labels")
        if not isinstance(labels, list) or not labels:
            raise ValueError("selected cluster has no observed casting labels")
        kind = _selection_kind(cluster)
        questions.append(
            {
                "ordinal": ordinal,
                "review_cluster_id": cluster_id,
                "selection_kind": kind,
                "observed_casting_labels": labels,
                "normalized_key": cluster.get("normalized_key"),
                "source_observations": observations,
                "candidate_evidence": _candidate_summary(cluster),
                "question": (
                    "Should the observed label(s) be treated as the same review-level casting "
                    "family as each other and/or the exact candidate evidence?"
                ),
                "decision_semantics": {
                    "same_review_family": (
                        "record a review-level family relationship only; do not approve a release "
                        "variant, physical color, or canonical product"
                    ),
                    "keep_separate": "do not group the observed label(s) with the candidate evidence",
                    "unknown": "preserve the question without asserting either relationship",
                },
                "allowed_decisions": list(ALLOWED_DECISIONS),
                "decision_status": "pending_owner",
                "decision": None,
                "canonical_uuid": None,
                "color_decision": None,
            }
        )

    kinds = Counter(item["selection_kind"] for item in questions)
    summary = {
        "selected_review_clusters": len(questions),
        "selected_source_observations": sum(len(item["source_observations"]) for item in questions),
        "selection_kind_counts": dict(sorted(kinds.items())),
        "pending_owner_decisions": len(questions),
        "recorded_owner_decisions": 0,
        "approved_casting_links": 0,
        "canonical_promotions": 0,
        "reviewed_colors": 0,
        "postgresql_writes": 0,
        "network_requests": 0,
    }
    body = {
        "schema_version": SCHEMA_VERSION,
        "packet_version": PACKET_VERSION,
        "status": "prepared_awaiting_owner",
        "source_batch_id": snapshot.get("batch_id"),
        "source_queue_sha256": digest(queue),
        "policy": {
            "selection": "fixed five-cluster batch-01 allowlist",
            "allowed_decisions": list(ALLOWED_DECISIONS),
            "prefilled_answers": False,
            "automatic_promotion": False,
            "color_review": False,
        },
        "summary": summary,
        "questions": questions,
    }
    packet_sha256 = digest(body)
    return {
        **body,
        "packet_sha256": packet_sha256,
        "batch_id": f"local-release-casting-review-batch-01-{packet_sha256}",
    }


def build_public_manifest(packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": PUBLIC_SCHEMA_VERSION,
        "packet_version": PACKET_VERSION,
        "status": packet["status"],
        "public_scope": "aggregate_counts_and_hashes_only_no_labels_toy_numbers_or_source_rows",
        "source_batch_id": packet["source_batch_id"],
        "source_queue_sha256": packet["source_queue_sha256"],
        "packet_sha256": packet["packet_sha256"],
        "batch_id": packet["batch_id"],
        "summary": packet["summary"],
    }


def render_private_report(packet: dict[str, Any]) -> str:
    lines = [
        "# Local release casting owner review — batch 01",
        "",
        "Every item is pending. Choose only `same_review_family`, `keep_separate`, or `unknown`.",
        "`same_review_family` does not approve a release variant, color, or canonical product.",
        "",
    ]
    for item in packet["questions"]:
        labels = " / ".join(item["observed_casting_labels"])
        lines.extend(
            [
                f"## {item['ordinal']}. {labels}",
                "",
                f"- Selection reason: `{item['selection_kind']}`",
                f"- Review cluster: `{item['review_cluster_id']}`",
                f"- Source observations: {len(item['source_observations'])}",
                "- Current decision: pending owner",
                "",
                "| Year | Toy # | Collector # | Source label | Series | Variant note |",
                "|---:|---|---|---|---|---|",
            ]
        )
        for row in item["source_observations"]:
            note = row["variant_note"] or "—"
            lines.append(
                f"| {row['release_year']} | {row['toy_number']} | {row['collector_number']} | "
                f"{row['source_model_label']} | {row['series']} | {note} |"
            )
        canonical = item["candidate_evidence"]["canonical_fixture"]
        human = item["candidate_evidence"]["human_draft"]
        lines.extend(["", "Candidate evidence:", ""])
        if canonical is not None:
            lines.append(
                f"- Synthetic fixture: {canonical['casting_labels']} "
                f"({canonical['synthetic_product_count']} synthetic products; not real catalog truth)"
            )
        if human:
            lines.append(
                "- Human draft: " + ", ".join(str(candidate["casting"]) for candidate in human)
            )
        if canonical is None and not human:
            lines.append(
                "- No exact catalog candidate; this question only reviews source spelling grouping."
            )
        lines.extend(
            ["", "Decision: pending (`same_review_family` / `keep_separate` / `unknown`)", ""]
        )
    return "\n".join(lines)


def render_public_report(manifest: dict[str, Any]) -> str:
    summary = manifest["summary"]
    lines = [
        "# Local release casting owner review batch 01 — public summary",
        "",
        "A fixed five-question packet was prepared offline. No answer is prefilled.",
        "The private packet and labels remain local and gitignored.",
        "",
        f"- Selected review clusters: {summary['selected_review_clusters']}",
        f"- Selected source observations: {summary['selected_source_observations']}",
        f"- Pending owner decisions: {summary['pending_owner_decisions']}",
        f"- Recorded owner decisions: {summary['recorded_owner_decisions']}",
        f"- Approved casting links: {summary['approved_casting_links']}",
        f"- Canonical promotions: {summary['canonical_promotions']}",
        f"- Reviewed colors: {summary['reviewed_colors']}",
        "- PostgreSQL writes: 0",
        "- Network requests: 0",
        "",
        "## Selection types",
        "",
    ]
    for kind, count in summary["selection_kind_counts"].items():
        lines.append(f"- `{kind}`: {count}")
    lines.extend(
        [
            "",
            "The next gate is the owner's explicit decision for each frozen question.",
            "No decision may be inferred from packet preparation or exact text matching.",
            "",
        ]
    )
    return "\n".join(lines)


def _stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


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


def build_artifacts(root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    staging_directory = root / "data/external/hot-wheels-wiki/local-export-2023-2026"
    queue_directory = root / "data/external/hot-wheels-wiki/local-release-casting-review-v1"
    queue_public_directory = root / "reports/local-release-casting-review-v1"
    queue, queue_manifest = check_review(
        root, staging_directory, queue_directory, queue_public_directory
    )
    if queue_manifest.get("private_queue_sha256") != digest(queue):
        raise ValueError("private queue checksum differs from its public manifest")
    snapshot = check_staging_bundle(staging_directory, root)
    packet = build_owner_batch(queue, snapshot)
    return packet, build_public_manifest(packet)


def publish_batch(root: Path, private_directory: Path, public_directory: Path) -> dict[str, Any]:
    _safe_directory(
        private_directory, root / "data/external/hot-wheels-wiki", "private batch output"
    )
    _safe_directory(public_directory, root / "reports", "public batch output")
    if private_directory.exists() or public_directory.exists():
        raise FileExistsError("batch output already exists; use --check")
    packet, manifest = build_artifacts(root)
    created: list[Path] = []
    try:
        _write_directory(
            private_directory,
            {
                "packet.json": _stable_json(packet),
                "questions.md": render_private_report(packet),
            },
        )
        created.append(private_directory)
        _write_directory(
            public_directory,
            {"manifest.json": _stable_json(manifest), "report.md": render_public_report(manifest)},
        )
        created.append(public_directory)
    except BaseException:
        for directory in reversed(created):
            for path in directory.iterdir():
                path.unlink()
            directory.rmdir()
        raise
    return packet


def check_batch(root: Path, private_directory: Path, public_directory: Path) -> dict[str, Any]:
    _safe_directory(
        private_directory, root / "data/external/hot-wheels-wiki", "private batch output"
    )
    _safe_directory(public_directory, root / "reports", "public batch output")
    packet, manifest = build_artifacts(root)
    expected = {
        private_directory: {
            "packet.json": _stable_json(packet),
            "questions.md": render_private_report(packet),
        },
        public_directory: {
            "manifest.json": _stable_json(manifest),
            "report.md": render_public_report(manifest),
        },
    }
    for directory, outputs in expected.items():
        if not directory.is_dir() or {path.name for path in directory.iterdir()} != set(outputs):
            raise ValueError(f"{directory.name}: batch bundle files differ from contract")
        for name, content in outputs.items():
            if (directory / name).read_text(encoding="utf-8") != content:
                raise ValueError(f"{directory.name}/{name}: differs from deterministic build")
    return packet


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare local casting owner review batch 01")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--private-output",
        type=Path,
        default=Path("data/external/hot-wheels-wiki/local-release-casting-review-batch-01"),
    )
    parser.add_argument(
        "--public-output",
        type=Path,
        default=Path("reports/local-release-casting-review-batch-01"),
    )
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()

    def within_root(path: Path) -> Path:
        return path if path.is_absolute() else root / path

    operation = check_batch if arguments.check else publish_batch
    packet = operation(
        root,
        within_root(arguments.private_output),
        within_root(arguments.public_output),
    )
    print(
        json.dumps(
            {
                "status": "valid" if arguments.check else "created",
                "batch_id": packet["batch_id"],
                "packet_sha256": packet["packet_sha256"],
                "summary": packet["summary"],
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
