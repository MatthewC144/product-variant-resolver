"""Audit RHB-v1 exact-authority eligibility without network or resolver output."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from product_variant_resolver.representative_benchmark import (
    AuthorityEligibility,
    SourceDecisionUse,
    content_sha256,
    stable_json_bytes,
    validate_canonical_authority_manifest,
    validate_source_decisions,
    validate_t1_inventory_files,
)

ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "evaluation" / "representative-hard-benchmark-v1"
AUTHORITY_PATH = OUTPUT_DIR / "canonical-authority.json"
MANIFEST_PATH = OUTPUT_DIR / "canonical-authority-manifest.json"
INVENTORY_PATH = OUTPUT_DIR / "source-inventory.json"
INVENTORY_MANIFEST_PATH = OUTPUT_DIR / "source-inventory-manifest.json"
DECISIONS_PATH = OUTPUT_DIR / "source-decisions.json"
CATALOG_PATH = ROOT / "data" / "catalog.json"
HUMAN_CATALOG_PATH = ROOT / "data" / "human_backed_catalog.json"
HUMAN_CATALOG_MANIFEST_PATH = ROOT / "data" / "human_backed_catalog_manifest.json"
WIKI_PATH = ROOT / "data" / "external" / "hot-wheels-wiki" / "pilot-2025" / "normalized.json"
GENERATOR_PATH = ROOT / "scripts" / "build_representative_hard_benchmark_canonical_authority.py"

AUTHORITY_VERSION = "representative-hard-benchmark-canonical-authority-v1"
MANIFEST_VERSION = "representative-hard-benchmark-canonical-authority-audit-v1"
GENERATED_AT = "2026-09-27T02:30:00Z"
MIN_EXACT_VARIANTS = 20
MIN_MULTI_RELEASE_FAMILIES = 4


class AuthorityAuditError(ValueError):
    """Raised when an audit input is stale, partial, or no longer safely excluded."""


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise AuthorityAuditError(f"{path}: could not read valid JSON") from error
    if not isinstance(value, dict):
        raise AuthorityAuditError(f"{path}: root must be an object")
    return value


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError as error:
        raise AuthorityAuditError(f"{path}: could not compute SHA-256") from error


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _expect(condition: bool, message: str) -> None:
    if not condition:
        raise AuthorityAuditError(message)


def _require_list(value: Any, message: str) -> list[Any]:
    if not isinstance(value, list):
        raise AuthorityAuditError(message)
    return value


def _source_exclusion_reasons(source: Any) -> list[str]:
    exact_cell = next(
        cell for cell in source.decisions if cell.use == SourceDecisionUse.exact_variant_authority
    )
    reasons = list(exact_cell.conditions)
    if source.authority_eligibility == AuthorityEligibility.synthetic_regression_only:
        reasons.insert(0, "synthetic_regression_only")
    else:
        reasons.insert(0, "authority_eligibility_prohibited")
    return sorted(set(reasons))


def _input_sha256(root: Path) -> dict[str, str]:
    paths = (
        root / "data" / "catalog.json",
        root / "data" / "human_backed_catalog.json",
        root / "data" / "human_backed_catalog_manifest.json",
        root / "data" / "evaluation" / "representative-hard-benchmark-v1" / "source-decisions.json",
        root
        / "data"
        / "evaluation"
        / "representative-hard-benchmark-v1"
        / "source-inventory-manifest.json",
        root / "data" / "evaluation" / "representative-hard-benchmark-v1" / "source-inventory.json",
        root / "scripts" / "build_representative_hard_benchmark_canonical_authority.py",
    )
    return {_relative(path, root): _sha256(path) for path in sorted(paths)}


def build_audit(root: Path = ROOT) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build an empty authority set plus a complete machine-checkable blocked Gate."""

    output_dir = root / "data" / "evaluation" / "representative-hard-benchmark-v1"
    inventory_payload = _load(output_dir / "source-inventory.json")
    inventory_manifest_payload = _load(output_dir / "source-inventory-manifest.json")
    decisions_payload = _load(output_dir / "source-decisions.json")
    catalog_payload = _load(root / "data" / "catalog.json")
    human_catalog_payload = _load(root / "data" / "human_backed_catalog.json")
    human_catalog_manifest = _load(root / "data" / "human_backed_catalog_manifest.json")
    wiki_payload = _load(
        root / "data" / "external" / "hot-wheels-wiki" / "pilot-2025" / "normalized.json"
    )

    inventory, _ = validate_t1_inventory_files(inventory_payload, inventory_manifest_payload)
    decisions = validate_source_decisions(
        decisions_payload,
        inventory_payload=inventory_payload,
        wiki_source_payload=wiki_payload,
    )

    products = _require_list(catalog_payload.get("products"), "canonical catalog lacks products[]")
    _expect(catalog_payload.get("catalog_version") == "fixture-v1", "unexpected catalog version")
    _expect(len(products) == 120, "fixture catalog count changed")
    for index, product in enumerate(products):
        _expect(isinstance(product, Mapping), f"catalog product {index} must be an object")
        provenance = _require_list(
            product.get("provenance"), f"catalog product {index} lacks provenance"
        )
        _expect(bool(provenance), f"catalog product {index} has empty provenance")
        _expect(
            all(
                isinstance(item, Mapping)
                and item.get("source_name") == "synthetic_fixture"
                and str(item.get("source_reference", "")).startswith("synthetic://fixture-v1/")
                for item in provenance
            ),
            f"catalog product {index} is not wholly synthetic regression data",
        )

    fixture_source = next(
        entry for entry in inventory.entries if entry.source_id == "fixture-v1-catalog"
    )
    _expect(
        fixture_source.local_sha256 == content_sha256(catalog_payload),
        "catalog inventory hash drift",
    )
    _expect(
        fixture_source.authority_eligibility == AuthorityEligibility.synthetic_regression_only,
        "fixture catalog authority boundary changed",
    )

    castings = _require_list(
        human_catalog_payload.get("castings"), "human-backed catalog lacks castings[]"
    )
    provisional_variants = []
    for index, casting in enumerate(castings):
        _expect(isinstance(casting, Mapping), f"human-backed casting {index} must be an object")
        provisional_variants.extend(
            _require_list(
                casting.get("provisional_variants"),
                f"human-backed casting {index} lacks provisional_variants[]",
            )
        )
    _expect(
        human_catalog_payload.get("identity_level") == "casting_with_provisional_variants",
        "human-backed catalog identity level changed",
    )
    _expect(
        "canonical_variant_response" in human_catalog_payload.get("excluded_from", []),
        "human-backed catalog no longer excludes canonical variant responses",
    )
    _expect(
        all(
            isinstance(variant, Mapping)
            and variant.get("identity_status") == "needs_canonical_review"
            and "canonical_uuid" not in variant
            for variant in provisional_variants
        ),
        "human-backed provisional variants gained unreviewed canonical identity",
    )
    _expect(
        human_catalog_manifest.get("catalog_sha256") == content_sha256(human_catalog_payload),
        "human-backed catalog manifest hash drift",
    )
    _expect(
        human_catalog_manifest.get("provisional_variant_count") == len(provisional_variants),
        "human-backed provisional count drift",
    )

    authority: dict[str, Any] = {
        "authority_version": AUTHORITY_VERSION,
        "publication_scope": "public",
        "records": [],
        "schema_version": "pvr-representative-hard-benchmark-canonical-authority-v1",
    }
    input_sha256 = _input_sha256(root)
    source_audit = [
        {
            "authority_eligibility": source.authority_eligibility.value,
            "eligible_exact_variant_count": 0,
            "exact_authority_decision": "rejected",
            "exclusion_reasons": _source_exclusion_reasons(source),
            "source_id": source.source_id,
        }
        for source in sorted(decisions.sources, key=lambda item: item.source_id)
    ]
    manifest: dict[str, Any] = {
        "authority_file": "canonical-authority.json",
        "authority_record_order": [],
        "authority_sha256": content_sha256(authority),
        "authority_version": AUTHORITY_VERSION,
        "benchmark_labels_consulted": False,
        "canonical_catalog": {
            "catalog_path": "data/catalog.json",
            "catalog_sha256": content_sha256(catalog_payload),
            "catalog_version": catalog_payload["catalog_version"],
            "independently_supported_exact_count": 0,
            "product_count": len(products),
            "synthetic_regression_only_excluded_count": len(products),
        },
        "current_source_count": len(source_audit),
        "current_source_exact_authority_rejected_count": len(source_audit),
        "eligible_exact_variant_count": 0,
        "exclusion_summary": [
            "120 fixture-v1 products are synthetic regression data, not real release truth",
            "100 human-backed variants are provisional and need canonical review",
            "all 11 owner-confirmed sources reject exact_variant_authority",
            "family, staging, Wiki, candidate, and resolver outputs cannot infer UUIDs",
        ],
        "gate_result": "blocked_insufficient_exact_authority",
        "generated_at": GENERATED_AT,
        "generated_by": "scripts/build_representative_hard_benchmark_canonical_authority.py",
        "input_artifacts": [
            {"path": path, "sha256": sha256} for path, sha256 in input_sha256.items()
        ],
        "manifest_version": MANIFEST_VERSION,
        "network_requests": 0,
        "next_allowed_step": "obtain_new_authorized_exact_variant_evidence",
        "pilot_usable_exact_variant_count": 0,
        "prohibited_next_steps": [
            "RHB_T5",
            "canonical_uuid_inference",
            "label_authoring",
            "matched_pilot_construction",
            "network_collection",
            "query_pack_authoring",
        ],
        "resolver_output_consulted": False,
        "same_casting_multi_release_family_count": 0,
        "schema_version": "pvr-representative-hard-benchmark-canonical-authority-manifest-v1",
        "source_audit": source_audit,
        "status": "complete",
        "supporting_human_catalog": {
            "catalog_path": "data/human_backed_catalog.json",
            "catalog_sha256": content_sha256(human_catalog_payload),
            "catalog_version": human_catalog_payload["catalog_version"],
            "casting_count": len(castings),
            "exact_variant_count": 0,
            "exclusion_reasons": [
                "identity_level_is_casting_with_provisional_variants",
                "all_variants_need_canonical_review",
                "canonical_variant_response_is_explicitly_excluded",
            ],
            "provisional_variant_count": len(provisional_variants),
        },
        "thresholds": {
            "exact_variant_shortfall": MIN_EXACT_VARIANTS,
            "family_shortfall": MIN_MULTI_RELEASE_FAMILIES,
            "minimum_pilot_usable_exact_variants": MIN_EXACT_VARIANTS,
            "minimum_same_casting_multi_release_families": MIN_MULTI_RELEASE_FAMILIES,
            "observed_pilot_usable_exact_variants": 0,
            "observed_same_casting_multi_release_families": 0,
        },
    }
    validate_canonical_authority_manifest(
        manifest,
        authority_payload=authority,
        catalog_payload=catalog_payload,
        human_catalog_payload=human_catalog_payload,
        inventory=inventory,
        source_decisions=decisions,
        input_sha256=input_sha256,
    )
    return authority, manifest


def _atomic_write(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except BaseException:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def _check(path: Path, expected: bytes) -> None:
    if not path.is_file():
        raise AuthorityAuditError(f"missing frozen output: {path}")
    if path.read_bytes() != expected:
        raise AuthorityAuditError(f"stale or modified frozen output: {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="fail unless frozen outputs are exact")
    args = parser.parse_args(argv)
    try:
        authority, manifest = build_audit(ROOT)
        authority_bytes = stable_json_bytes(authority)
        manifest_bytes = stable_json_bytes(manifest)
        if args.check:
            _check(AUTHORITY_PATH, authority_bytes)
            _check(MANIFEST_PATH, manifest_bytes)
            print("unchanged")
            return 0
        unchanged = (
            AUTHORITY_PATH.is_file()
            and MANIFEST_PATH.is_file()
            and AUTHORITY_PATH.read_bytes() == authority_bytes
            and MANIFEST_PATH.read_bytes() == manifest_bytes
        )
        if not unchanged:
            _atomic_write(AUTHORITY_PATH, authority_bytes)
            _atomic_write(MANIFEST_PATH, manifest_bytes)
        print("unchanged" if unchanged else "written")
        return 0
    except (AuthorityAuditError, ValueError) as error:
        print(f"authority audit failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
