"""Strict offline normalization for owner-supplied Hot Wheels release workbooks."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import json
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "pvr-local-release-staging-v1"
IMPORT_VERSION = "local-xlsx-openpyxl-v1"
REVIEW_STATUS = "needs_canonical_review"
USAGE = "staging_only_not_evaluation_or_canonical"
SOURCE_RIGHTS_STATE = "access_permission_and_republication_rights_not_provided"
INPUTS = {
    2023: ("catalog-2023.xlsx", 445),
    2024: ("catalog-2024.xlsx", 441),
    2025: ("catalog-2025.xlsx", 440),
    2026: ("catalog-2026.xlsx", 437),
}
HEADERS = (
    "Source record ID",
    "Release year",
    "Brand",
    "Toy number",
    "Collector number",
    "Source model label",
    "Casting name",
    "Variant note",
    "Series",
    "Series position",
    "Color",
    "Source page title",
    "Source page URL",
    "Source table",
    "Source row",
    "Parse status",
    "Parse error",
    "Collected at (UTC)",
    "Raw fields (JSON)",
)
FIELD_NAMES = (
    "source_record_id",
    "release_year",
    "brand",
    "toy_number",
    "collector_number",
    "source_model_label",
    "casting_name",
    "variant_note",
    "series",
    "series_position",
    "color",
    "source_page_title",
    "source_page_url",
    "source_table",
    "source_row",
    "parse_status",
    "parse_error",
    "collected_at",
    "raw_fields",
)
REQUIRED_TEXT_FIELDS = {
    "source_record_id",
    "brand",
    "toy_number",
    "collector_number",
    "source_model_label",
    "casting_name",
    "series",
    "series_position",
    "source_page_title",
    "source_page_url",
    "parse_status",
    "collected_at",
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _openpyxl() -> Any:
    try:
        return importlib.import_module("openpyxl")
    except ImportError as error:
        raise RuntimeError("release staging requires openpyxl") from error


def _safe_source(path: Path, root: Path) -> None:
    expected_parent = (root / "HW data").absolute()
    if path.absolute().parent != expected_parent:
        raise ValueError("release input must be a direct member of HW data/")
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError(f"symlink input is not allowed: {path.name}")
    if not path.is_file():
        raise ValueError(f"missing release input: {path.name}")


def _clean_optional_text(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise TypeError("expected a text cell")
    cleaned = value.strip()
    return cleaned or None


def _required_text(value: Any, field: str, *, filename: str, row_number: int) -> str:
    cleaned = _clean_optional_text(value)
    if cleaned is None:
        raise ValueError(f"{filename} row {row_number}: blank {field}")
    return cleaned


def _integer(value: Any, field: str, *, filename: str, row_number: int) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{filename} row {row_number}: invalid {field}")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    raise ValueError(f"{filename} row {row_number}: invalid {field}")


def _timestamp(value: str, *, filename: str, row_number: int) -> str:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{filename} row {row_number}: malformed collected_at") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{filename} row {row_number}: collected_at must include timezone")
    return parsed.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _raw_object(value: str, *, filename: str, row_number: int) -> dict[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as error:
        raise ValueError(f"{filename} row {row_number}: malformed raw_fields JSON") from error
    if not isinstance(parsed, dict):
        raise TypeError(f"{filename} row {row_number}: raw_fields must be a JSON object")
    return parsed


def _reject_formulas(path: Path) -> None:
    workbook = _openpyxl().load_workbook(path, read_only=True, data_only=False)
    try:
        if "Releases" not in workbook.sheetnames:
            raise ValueError(f"{path.name}: missing Releases sheet")
        sheet = workbook["Releases"]
        for row in sheet.iter_rows(min_row=6):
            for column_index, cell in enumerate(row, start=1):
                if cell.data_type == "f":
                    raise ValueError(
                        f"{path.name}: formula cell is not allowed at {cell.coordinate}"
                    )
                if column_index > len(HEADERS) and cell.value is not None:
                    raise ValueError(
                        f"{path.name}: extra column content is not allowed at {cell.coordinate}"
                    )
    finally:
        workbook.close()


def _normalize_row(
    values: tuple[Any, ...], *, year: int, filename: str, file_sha256: str, row_number: int
) -> dict[str, Any]:
    if len(values) != len(HEADERS):
        raise ValueError(f"{filename} row {row_number}: expected 19 columns")
    raw = dict(zip(FIELD_NAMES, values, strict=True))
    record: dict[str, Any] = {}
    for field in REQUIRED_TEXT_FIELDS:
        record[field] = _required_text(raw[field], field, filename=filename, row_number=row_number)
    for field in ("variant_note", "color", "parse_error"):
        record[field] = _clean_optional_text(raw[field])
    record["release_year"] = _integer(
        raw["release_year"], "release_year", filename=filename, row_number=row_number
    )
    record["source_table"] = _integer(
        raw["source_table"], "source_table", filename=filename, row_number=row_number
    )
    record["source_row"] = _integer(
        raw["source_row"], "source_row", filename=filename, row_number=row_number
    )
    if record["release_year"] != year:
        raise ValueError(f"{filename} row {row_number}: release year mismatch")
    if record["parse_status"] != "parsed" or record["parse_error"] is not None:
        raise ValueError(f"{filename} row {row_number}: only clean parsed rows are accepted")
    if record["color"] is not None:
        raise ValueError(f"{filename} row {row_number}: color must remain unknown for this batch")
    record["collected_at"] = _timestamp(
        record["collected_at"], filename=filename, row_number=row_number
    )
    record["raw_fields"] = _raw_object(
        _required_text(raw["raw_fields"], "raw_fields", filename=filename, row_number=row_number),
        filename=filename,
        row_number=row_number,
    )
    record["input_filename"] = filename
    record["input_sha256"] = file_sha256
    record["review_status"] = REVIEW_STATUS
    record["usage"] = USAGE
    record["canonical_uuid"] = None
    return {
        field: record[field]
        for field in (
            *FIELD_NAMES[:-1],
            "raw_fields",
            "input_filename",
            "input_sha256",
            "review_status",
            "usage",
            "canonical_uuid",
        )
    }


def parse_workbook(
    path: Path, *, year: int, expected_count: int, root: Path
) -> list[dict[str, Any]]:
    _safe_source(path, root)
    file_sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
    _reject_formulas(path)
    workbook = _openpyxl().load_workbook(path, read_only=True, data_only=True)
    try:
        if "Releases" not in workbook.sheetnames:
            raise ValueError(f"{path.name}: missing Releases sheet")
        sheet = workbook["Releases"]
        header = tuple(cell.value for cell in sheet[6][: len(HEADERS)])
        if header != HEADERS:
            raise ValueError(f"{path.name}: Releases row 6 header differs from contract")
        records: list[dict[str, Any]] = []
        for row_number, row in enumerate(
            sheet.iter_rows(min_row=7, max_col=len(HEADERS), values_only=True), start=7
        ):
            values = tuple(row)
            if not any(value is not None and str(value).strip() for value in values):
                continue
            records.append(
                _normalize_row(
                    values,
                    year=year,
                    filename=path.name,
                    file_sha256=file_sha256,
                    row_number=row_number,
                )
            )
    finally:
        workbook.close()
    if len(records) != expected_count:
        raise ValueError(f"{path.name}: expected {expected_count} rows, found {len(records)}")
    if [record["source_row"] for record in records] != list(range(1, expected_count + 1)):
        raise ValueError(f"{path.name}: source rows must be ordered and contiguous")
    return records


def _duplicates(values: Iterable[str]) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    return duplicates


def build_snapshot(root: Path) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    files: list[dict[str, Any]] = []
    for year, (filename, expected_count) in INPUTS.items():
        path = root / "HW data" / filename
        parsed = parse_workbook(path, year=year, expected_count=expected_count, root=root)
        records.extend(parsed)
        files.append(
            {
                "filename": filename,
                "release_year": year,
                "row_count": len(parsed),
                "sha256": parsed[0]["input_sha256"],
            }
        )
    source_ids = [str(record["source_record_id"]) for record in records]
    toy_numbers = [str(record["toy_number"]) for record in records]
    if duplicate_ids := _duplicates(source_ids):
        raise ValueError(f"duplicate source record IDs: {sorted(duplicate_ids)[:3]}")
    if duplicate_toys := _duplicates(toy_numbers):
        raise ValueError(f"duplicate toy numbers: {sorted(duplicate_toys)[:3]}")
    if len(records) != 1763:
        raise ValueError("combined row count must be 1,763")
    counts = {
        "staged_observations": len(records),
        "unique_source_record_ids": len(set(source_ids)),
        "unique_toy_numbers": len(set(toy_numbers)),
        "unique_casting_names": len({str(record["casting_name"]) for record in records}),
        "unknown_colors": sum(record["color"] is None for record in records),
        "variant_note_observations": sum(record["variant_note"] is not None for record in records),
        "parse_errors": sum(record["parse_error"] is not None for record in records),
        "reviewed_variants": 0,
        "canonical_products": 0,
        "postgresql_rows_written": 0,
        "network_requests": 0,
    }
    if counts["unique_casting_names"] != 678 or counts["unknown_colors"] != 1763:
        raise ValueError("combined casting/color counts differ from the approved batch")
    body = {
        "schema_version": SCHEMA_VERSION,
        "import_version": IMPORT_VERSION,
        "status": "review_only_local_staging_snapshot",
        "source_rights_state": SOURCE_RIGHTS_STATE,
        "files": files,
        "counts": counts,
        "records": records,
    }
    content_sha256 = digest(body)
    return {
        **body,
        "content_sha256": content_sha256,
        "batch_id": f"local-release-staging-v1-{content_sha256}",
    }


def validate_snapshot(snapshot: dict[str, Any], root: Path) -> None:
    if canonical_bytes(snapshot) != canonical_bytes(build_snapshot(root)):
        raise ValueError("release staging snapshot differs from the complete local inputs")


def render_report(snapshot: dict[str, Any]) -> str:
    counts = snapshot["counts"]
    lines = [
        "# Local release staging snapshot — 2023–2026",
        "",
        f"Batch: `{snapshot['batch_id']}`",
        "",
        "這是待人工 canonical review 的來源觀測資料，不是已驗證商品，也不會進入 Dual RAG。",
        "顏色沒有從名稱、variant note、網址或常識推測；本批 1,763 筆皆保留為 NULL。",
        "",
        "## 結果",
        "",
        f"- Staged observations: {counts['staged_observations']}",
        f"- Unique source record IDs: {counts['unique_source_record_ids']}",
        f"- Unique toy numbers: {counts['unique_toy_numbers']}",
        f"- Cross-year casting names: {counts['unique_casting_names']}",
        f"- Unknown colors: {counts['unknown_colors']}",
        f"- Rows with a variant note: {counts['variant_note_observations']}",
        f"- Reviewed variants: {counts['reviewed_variants']}",
        f"- Canonical products: {counts['canonical_products']}",
        f"- Parse errors: {counts['parse_errors']}",
        "- Network requests: 0",
        "- PostgreSQL rows written while building this snapshot: 0",
        "",
        "## Source boundary",
        "",
        "這些檔案由 owner 在本機提供；未提供網站存取許可或再發布權證明。",
        "本機持有檔案不代表可重新爬取，也不代表可公開發布原始 XLSX。",
        "",
    ]
    for item in snapshot["files"]:
        lines.append(
            f"- `{item['filename']}`: {item['row_count']} rows, SHA-256 `{item['sha256']}`"
        )
    lines.append("")
    return "\n".join(lines)


def check_bundle(directory: Path, root: Path) -> dict[str, Any]:
    expected_names = {"normalized.json", "manifest.json", "report.md"}
    if any(part.is_symlink() for part in (directory, *directory.parents)):
        raise ValueError("symlink bundle is not allowed")
    if not directory.is_dir() or {path.name for path in directory.iterdir()} != expected_names:
        raise ValueError("release bundle must contain normalized.json, manifest.json and report.md")
    snapshot = json.loads((directory / "normalized.json").read_text(encoding="utf-8"))
    if not isinstance(snapshot, dict):
        raise TypeError("normalized snapshot must be an object")
    validate_snapshot(snapshot, root)
    manifest = {key: value for key, value in snapshot.items() if key != "records"}
    stored_manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    if canonical_bytes(stored_manifest) != canonical_bytes(manifest):
        raise ValueError("manifest differs from normalized snapshot")
    if (directory / "report.md").read_text(encoding="utf-8") != render_report(snapshot):
        raise ValueError("report differs from normalized snapshot")
    return snapshot


def publish_bundle(directory: Path, root: Path) -> dict[str, Any]:
    parent = root / "data" / "external" / "hot-wheels-wiki"
    if directory.absolute().parent != parent.absolute():
        raise ValueError("output must be a direct child of data/external/hot-wheels-wiki/")
    if any(part.is_symlink() for part in (directory, *directory.parents)):
        raise ValueError("symlink output is not allowed")
    snapshot = build_snapshot(root)
    manifest = {key: value for key, value in snapshot.items() if key != "records"}
    outputs = {
        "normalized.json": json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=2)
        + "\n",
        "manifest.json": json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        "report.md": render_report(snapshot),
    }
    directory.mkdir()
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
        try:
            directory.rmdir()
        except OSError:
            pass
        raise
    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build a deterministic local release staging bundle"
    )
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/external/hot-wheels-wiki/local-export-2023-2026"),
    )
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args()
    root = arguments.root.resolve()
    output = arguments.output if arguments.output.is_absolute() else root / arguments.output
    snapshot = check_bundle(output, root) if arguments.check else publish_bundle(output, root)
    print(
        json.dumps(
            {
                "status": "valid" if arguments.check else "created",
                "batch_id": snapshot["batch_id"],
                "content_sha256": snapshot["content_sha256"],
                "counts": snapshot["counts"],
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
