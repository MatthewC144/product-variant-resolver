"""T49.1: deterministic local PLAN only; no database or retrieval adapter."""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, fields
from pathlib import Path
from typing import Any
from uuid import UUID

from product_variant_resolver.human_knowledge import (
    HumanKnowledgeDocument,
    HumanVariantKnowledgeDocument,
    ReviewFamilyKnowledgeDocument,
    load_human_knowledge_catalog,
)

SCHEMA = "pvr-human-knowledge-snapshot-plan-v1"
PILOT = "data/external/hot-wheels-wiki/pilot-2025/"
# Pin the approved local baseline, not merely checksums supplied by a mutable manifest.
# Changing any input requires a new reviewed snapshot version; never relax these v1 pins.
SOURCE_HASHES = {
    "data/human_backed_catalog.json": "d29b69cde8099cb229136a73b893ca99b6313d9652ead5ff4aea48c20242e74f",
    "data/human_backed_catalog_manifest.json": "c79a3bc699d2bfcccae992a672fda79cbb905f1f2252dbfda8fa219ed55e43c7",
    "data/human_labeled_names.json": "68b5dfdb8d0fa4972328d172cc5a56d78ac8bf00bc740083b2bfc07eb2a91188",
    "data/human_labeled_names_manifest.json": "f56cba710a720959d4c535c3353730f012911ab18e5a6054ebef2e5750ada84c",
    "data/review_family_knowledge.json": "8615cbb99b453673599e1f9baf54f6900314d7ba64e53a31ea7891c71810b9d7",
    "data/review_family_knowledge_manifest.json": "0239e272d27276d9a25df2c36edbbe6a7251facce7728ef947b86dcaa417c2ef",
    "data/review_family_registry.json": "3f289b802cc2e8280ed5c3586d87cfabbee7ce37b10ae79504b5aa6b8837367d",
    "data/review_family_registry_manifest.json": "ae9eda741aa2ec7cb9354424e17b789ba73c05890859e73d19cd845c5cab3ff2",
    PILOT + "normalized.json": "e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6",
    PILOT + "manifest.json": "960c639765759d3ab7b610718c026fa784e1995844f4acc9587718d94218f111",
    PILOT + "priority-2-batch-05-adjudicated-queue.json": "989bc914f9493051a071472c9defd352fe1cb8cc217c062e1f479bdcb9c6e4d8",
    PILOT + "priority-2-batch-05-adjudicated-queue-manifest.json": "6b532978c86adf39dbc2f41222d41ca9b765b1c615dce5453a0ba04955a9f6ff",
}


def canonical_bytes(value: Any) -> bytes:
    """Type-sensitive JSON comparison/checksum (True must not equal 1)."""
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def load_object(path: Path) -> dict[str, Any]:
    def unique_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    try:
        value = json.loads(path.read_bytes(), object_pairs_hook=unique_pairs)
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot read JSON: {path.name}") from error
    if not isinstance(value, dict):
        raise ValueError("JSON root must be an object")
    return value


def document_payload(document: HumanKnowledgeDocument) -> dict[str, Any]:
    payload = asdict(document)
    for key, value in payload.items():
        if isinstance(value, UUID):
            payload[key] = str(value)
        elif isinstance(value, tuple):
            payload[key] = list(value)
    return payload


def decode_document(entry: dict[str, Any]) -> HumanKnowledgeDocument:
    """Recover the current typed document, without inventing any identity or attributes."""
    kind = entry.get("knowledge_type")
    cls: type[HumanVariantKnowledgeDocument] | type[ReviewFamilyKnowledgeDocument]
    if kind == "provisional_variant":
        cls = HumanVariantKnowledgeDocument
    elif kind == "review_family":
        cls = ReviewFamilyKnowledgeDocument
    else:
        raise ValueError("unsupported knowledge type")
    raw = entry.get("payload")
    if not isinstance(raw, dict) or set(raw) != {field.name for field in fields(cls)}:
        raise ValueError("typed document fields differ from contract")
    values = dict(raw)
    list_fields = {"human_label_names", "pricing_keywords", "initial_names", "source_case_ids",
                   "aliases", "source_record_ids"}
    for key, value in values.items():
        if key.endswith("_uuid"):
            if not isinstance(value, str):
                raise ValueError("UUID must be a string")
            values[key] = UUID(value)
        elif key in list_fields:
            if (not isinstance(value, list) or not all(isinstance(v, str) and v for v in value)
                    or len(value) != len(set(value))):
                raise ValueError("invalid string array")
            values[key] = tuple(value)
        elif value is None and key in {"series_label", "variant_label"}:
            continue
        elif not isinstance(value, str) or not value:
            raise ValueError("invalid string field")
    document = cls(**values)
    if (entry.get("knowledge_uuid") != str(document.knowledge_uuid)
            or entry.get("knowledge_id") != document.knowledge_id
            or entry.get("payload_sha256") != digest(raw)):
        raise ValueError("document identity or checksum mismatch")
    return document


def build_plan(root: Path) -> dict[str, Any]:
    # Validate all bytes before loading documents or attempting any output publication.
    for relative, expected in SOURCE_HASHES.items():
        path = root / relative
        if any(part.is_symlink() for part in (path, *path.parents)):
            raise ValueError(f"symlink source is not allowed: {relative}")
        try:
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as error:
            raise ValueError(f"missing source: {relative}") from error
        if actual != expected:
            raise ValueError(f"source checksum mismatch: {relative}")
    human = load_object(root / "data/human_backed_catalog.json")
    family = load_object(root / "data/review_family_knowledge.json")
    registry = load_object(root / "data/review_family_registry.json")
    catalog = load_human_knowledge_catalog(
        root / "data/human_backed_catalog.json", root / "data/review_family_knowledge.json",
        root / "data/review_family_knowledge_manifest.json")
    accepted = {item["review_family_id"] for item in registry["new_families"]}
    excluded = ({item["review_family_id"] for item in registry["hold_exclusions"]}
                | {item["source_family_review_id"] for item in registry["merge_links"]})
    origins: dict[str, dict[str, Any]] = {}
    for casting in human["castings"]:
        for variant in casting["provisional_variants"]:
            origins[variant["provisional_variant_id"]] = {
                "file": "data/human_backed_catalog.json",
                "casting_id": casting["casting_id"], "raw_casting": casting,
                "raw_variant": variant,
            }
    for item in family["documents"]:
        if item["review_family_id"] not in accepted or item["review_family_id"] in excluded:
            raise ValueError("held/merge-source family cannot be materialized")
        origins[item["review_family_id"]] = {
            "file": "data/review_family_knowledge.json", "raw_document": item,
            "registry_entry": next(row for row in registry["new_families"]
                                   if row["review_family_id"] == item["review_family_id"]),
        }
    entries = []
    for document in sorted(catalog.documents, key=lambda d: (d.knowledge_type, d.knowledge_id)):
        payload = document_payload(document)
        entry = {"knowledge_type": document.knowledge_type,
                 "knowledge_id": document.knowledge_id,
                 "knowledge_uuid": str(document.knowledge_uuid), "payload": payload,
                 "payload_sha256": digest(payload), "origin": origins[document.knowledge_id]}
        if decode_document(entry) != document:
            raise ValueError("typed document roundtrip mismatch")
        entries.append(entry)
    body = {
        "schema_version": SCHEMA, "status": "local_plan_only_not_import_authorization",
        "source_sha256": SOURCE_HASHES,
        "counts": {"documents": 142, "provisional_variant": 100, "review_family": 42,
                   "human_castings": 97, "accepted_family_source_rows": 79,
                   "merge_source_families_excluded": 4, "held_families_excluded": 7,
                   "postgresql_writes": 0, "new_canonical_uuids": 0},
        "source_contracts": {
            "human": {key: value for key, value in human.items() if key != "castings"},
            "family": {key: value for key, value in family.items() if key != "documents"}},
        "documents": entries,
    }
    checksum = digest(body)
    return {**body, "content_sha256": checksum,
            "snapshot_id": "human-knowledge-plan-v1-" + checksum}


def validate_plan(plan: dict[str, Any], root: Path) -> None:
    expected = build_plan(root)
    # Reconstruction checks every field/origin/order/exclusion, including correctly rehashed
    # malicious edits. A self-consistent checksum alone is not source authenticity.
    if canonical_bytes(plan) != canonical_bytes(expected):
        raise ValueError("plan differs from the complete pinned local snapshot")


def render_report(plan: dict[str, Any]) -> str:
    lines = ["# T49.1 — 本機人工知識匯入計畫", "",
             f"Snapshot: `{plan['snapshot_id']}`", "",
             "驗證結果：142 筆完整人工知識，100 筆 provisional variant + 42 筆 review family。",
             "這是匯入前的計畫，不是 PostgreSQL 匯入、正式商品確認或檢索上線。",
             "原有 ID／UUID／typed payload 可完整還原；原始內容、來源及限制一併保留。",
             "4 個 merge-source family、7 個 held family 未另建知識文件；79 筆 accepted source rows。",
             "來源仍排除 canonical authority／variant identity／PostgreSQL ingestion；本計畫不解除限制。",
             "SQL 寫入 0；網站請求 0；新增 canonical UUID 0；未重跑已封存的 final 評估。", "",
             "## 來源檔案指紋（12 個本機輸入；非整個歷史 evidence tree 的重新驗證）", ""]
    for path, checksum in sorted(plan["source_sha256"].items()):
        lines.append(f"- `{path}`：`{checksum}`")
    lines.extend(["", "## 後續界線", "",
                  "T49.2 必須先指定並確認隔離測試資料庫；未授權操作既有資料庫或收集新網站資料。",
                  "這份 plan 不包含 embedding／SQL schema，也不決定 release equivalence。", ""])
    return "\n".join(lines)


def check_bundle(directory: Path, root: Path) -> dict[str, Any]:
    if any(part.is_symlink() for part in (directory, *directory.parents)):
        raise ValueError("symlink bundle is not allowed")
    if not directory.is_dir() or {p.name for p in directory.iterdir()} != {"plan.json", "report.md"}:
        raise ValueError("bundle must contain exactly plan.json and report.md")
    if any(path.is_symlink() for path in directory.iterdir()):
        raise ValueError("symlink bundle member is not allowed")
    plan = load_object(directory / "plan.json")
    validate_plan(plan, root)
    if (directory / "report.md").read_bytes() != render_report(plan).encode("utf-8"):
        raise ValueError("readable report differs from validated plan")
    return plan


def publish_bundle(directory: Path, root: Path) -> dict[str, Any]:
    plan = build_plan(root)
    outputs = {"plan.json": json.dumps(plan, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
               "report.md": render_report(plan)}
    # Resolve containment only after explicitly rejecting symlink components.
    if any(part.is_symlink() for part in (directory, *directory.parents)):
        raise ValueError("symlink output is not allowed")
    if directory.absolute().parent != (root / "reports").absolute():
        raise ValueError("output must be a new direct child of project reports/")
    if not directory.parent.is_dir():
        raise ValueError("reports parent must already exist")
    directory.mkdir()  # exclusive: repeated or concurrent publication never overwrites a bundle
    owned: list[Path] = []
    try:
        for name, content in outputs.items():
            path = directory / name
            with path.open("x", encoding="utf-8", newline="\n") as handle:
                owned.append(path)
                handle.write(content)
        check_bundle(directory, root)
    except BaseException:
        for path in owned:
            path.unlink(missing_ok=True)
        # Remove only the exact new directory if empty; never recursively delete unknown files.
        try:
            directory.rmdir()
        except OSError:
            pass
        raise
    # A process kill may leave an incomplete directory; checking rejects it and repeats refuse it.
    # This is exclusive file publication, not a crash-atomic database transaction.
    return plan
