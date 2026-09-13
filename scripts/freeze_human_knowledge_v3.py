#!/usr/bin/env python3
"""Freeze a qualifying development winner; FAIL never touches a runtime artifact."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from product_variant_resolver.human_knowledge import (  # noqa: E402
    FAMILY_KNOWLEDGE_VERSION,
    HUMAN_KNOWLEDGE_CHARACTER_INDEX_VERSION,
    HUMAN_KNOWLEDGE_DEVELOPMENT_VERSION,
    HUMAN_KNOWLEDGE_V3_ALLOWED_FIELDS,
    HUMAN_KNOWLEDGE_V3_ARTIFACT_SCHEMA,
    HUMAN_KNOWLEDGE_V3_ELIGIBLE_FOR,
    HUMAN_KNOWLEDGE_V3_EXCLUDED_FROM,
    HUMAN_KNOWLEDGE_V3_RETRIEVER_VERSION,
)
from product_variant_resolver.human_knowledge_selection import (  # noqa: E402
    DEV,
    REPORT,
    load_object,
    sha,
    validate_report,
    write_json,
)


def freeze(selection: Path, output: Path) -> bool:
    payload = load_object(selection)
    validate_report(payload)
    if payload["verdict"] != "PASS" or payload["winner"] is None:
        return False
    if selection.resolve().parent != REPORT.parent.resolve():
        raise ValueError("selection must be frozen inside development reports")
    # Refuse destructive replacement, even for a new qualifying experiment.
    if output.exists():
        raise ValueError("runtime artifact already exists; use a new versioned path")
    references = {
        "human_catalog": (ROOT / "data/human_backed_catalog.json", "human-backed-catalog-v1"),
        "review_family_knowledge": (ROOT / "data/review_family_knowledge.json", FAMILY_KNOWLEDGE_VERSION),
        "development_pack": (DEV / "development-pack.json", HUMAN_KNOWLEDGE_DEVELOPMENT_VERSION),
        "development_manifest": (DEV / "development-pack-manifest.json", HUMAN_KNOWLEDGE_DEVELOPMENT_VERSION),
    }
    configuration = dict(payload["winner"])
    configuration.update(dense_dimensions=192, dense_rrf_weight=1.0, rrf_k=60,
                         selection_candidate_limit=5, source_candidate_limit=25,
                         sparse_rrf_weight=1.0)
    evidence = [{key: entry[key] for key in ("configuration", "metrics", "rejection_reasons")}
                for entry in payload["configurations"]]
    artifact = {
        "schema_version": HUMAN_KNOWLEDGE_V3_ARTIFACT_SCHEMA,
        "artifact_version": f"human-knowledge-retrieval-v3-dev-{sha(selection)[:12]}",
        "retriever_version": HUMAN_KNOWLEDGE_V3_RETRIEVER_VERSION,
        "status": "selected_development_configuration", "configuration": configuration,
        "character_index": {"allowed_fields": HUMAN_KNOWLEDGE_V3_ALLOWED_FIELDS,
                            "gram_sizes": [2, 3], "modes": ["spaced", "compact"],
                            "stable_tie_break": "knowledge_uuid",
                            "version": HUMAN_KNOWLEDGE_CHARACTER_INDEX_VERSION,
                            "window_token_radius": 1},
        "sources": {key: {"file": path.name, "sha256": sha(path), "version": version}
                    for key, (path, version) in references.items()},
        "implementation": {"file": "human_knowledge.py",
                           "sha256": sha(ROOT / "src/product_variant_resolver/human_knowledge.py")},
        "selection_evidence": {"file": str(selection.resolve().relative_to(ROOT)),
                               "sha256": sha(selection), "configurations": evidence},
        "eligible_for": HUMAN_KNOWLEDGE_V3_ELIGIBLE_FOR,
        "excluded_from": HUMAN_KNOWLEDGE_V3_EXCLUDED_FROM,
    }
    write_json(output, artifact)
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection", type=Path, default=REPORT)
    parser.add_argument("--output", type=Path, default=ROOT / "artifacts/human-knowledge-retrieval-v3.json")
    args = parser.parse_args()
    if freeze(args.selection, args.output):
        print("froze qualifying v3 artifact; commit before final holdout authoring")
    else:
        print("selection FAIL: runtime artifact untouched, v2 stays active")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
