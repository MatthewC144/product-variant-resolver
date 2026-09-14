#!/usr/bin/env python3
"""Freeze the approved v4 execution contract without executing any retrieval."""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from product_variant_resolver.human_knowledge import (  # noqa: E402
    HumanKnowledgeDocument,
    load_human_knowledge_catalog,
)
from product_variant_resolver.human_knowledge_selection import (  # noqa: E402
    SOURCE_PATHS,
    atomic_write,
    load_development,
    sha,
    synthetic_catalog,
)
from product_variant_resolver.identity import normalize_text  # noqa: E402

VERSION = "human-knowledge-identity-development-v1"
DIRECTORY = ROOT / "data/evaluation" / VERSION
SPEC_DIR = "specs/human-knowledge-identity-bounded-retrieval"
APPROVED_COMMIT = "880e4f5b7c556a50e35de900a530e16280bab833"
SPEC_HASHES = {
    "requirements.md": "45bf456d1890e26cbfa9e3afbfa8cce7be1ca9a4d2ddc5a526058b2f111bce62",
    "design.md": "eb2867ad77def038c6d689154f80403d3437a918349441a6c07a0b87da57bc17",
    "tasks.md": "e2e772f5b2e7f95bc4290e07cb6cc40c6b7c8e1917e578deae321a85203cf4f1",
}
NOISE = frozenset("""as blister black blue box boxed cabinet carded car case collectible collector
diecast display estate find from gray green grey hot hotwheels in item light local loose maker
miniature missing model new orange outer package pack piece pictured pickup protective purple red
scale sealed shelf silver small sold storage the toy unopened unknown vehicle wear wheels white
with yellow""".split())
LIMITS = {"query_characters": 512, "query_tokens_before_noise": 64,
          "identity_forms_per_document": 32, "query_forms": 256,
          "posting_entries_per_query": 1_000_000, "source_candidates": 25, "dense_union": 50}
APPROVAL = {
    "schema_version": "pvr-identity-retrieval-owner-approval-v1",
    "authority": "project_owner", "approved_commit": APPROVED_COMMIT,
    "approval_instruction": "執行下一步",
    "approval_basis": "instruction_immediately_after_three_spec_confirmation_handoff",
    "recorded_at_utc": "2026-09-14T01:29:45Z",
    "approved_spec_sha256": SPEC_HASHES,
    "scope": "IBR-T1_only_no_v4_retrieval_or_selection",
}


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n"


def text_sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def core(value: str) -> str:
    return " ".join(token for token in normalize_text(value).split() if token not in NOISE)


def approved_specs(directory: Path, *, from_git: bool = False) -> dict[str, str]:
    result = {}
    for name in SPEC_HASHES:
        if from_git:
            result[name] = subprocess.run(
                ["git", "show", f"{APPROVED_COMMIT}:{SPEC_DIR}/{name}"], cwd=ROOT,
                check=True, capture_output=True, text=True, encoding="utf-8",
            ).stdout
        else:
            result[name] = (directory / "approved-specs" / name).read_text(encoding="utf-8")
    validate_specs(result)
    return result


def validate_specs(specs: dict[str, str]) -> None:
    if set(specs) != set(SPEC_HASHES) or any(text_sha(specs[name]) != checksum
                                           for name, checksum in SPEC_HASHES.items()):
        raise ValueError("approved spec snapshots differ from owner-approved commit")
    policy_section = specs["design.md"].split("## Identity policy", 1)[1]
    policy_text = "\n".join(policy_section.split("```", 2)[1].splitlines()[1:])
    if frozenset(policy_text.split()) != NOISE:
        raise ValueError("noise policy differs from approved design")


def identity_audit(documents: tuple[HumanKnowledgeDocument, ...]) -> dict[str, Any]:
    if len({item.knowledge_uuid for item in documents}) != len(documents):
        raise ValueError("duplicate knowledge UUID")
    if len({item.knowledge_id for item in documents}) != len(documents):
        raise ValueError("duplicate knowledge ID")
    collisions: dict[str, dict[str, str]] = defaultdict(dict)
    rows: list[dict[str, Any]] = []
    gram_keys: set[tuple[str, str]] = set()
    posting_entries = 0
    lengths = set()
    for document in sorted(documents, key=lambda item: str(item.knowledge_uuid)):
        values = ((document.casting,) if document.knowledge_type == "provisional_variant"
                  else (document.casting, *getattr(document, "aliases")))
        forms: dict[tuple[str, str], dict[str, Any]] = {}
        for value in values:
            identity = core(value)
            if not identity:
                raise ValueError(f"empty identity core: {document.knowledge_id}")
            collisions[identity][document.knowledge_id] = document.casting
            lengths.add(len(identity.split()))
            for mode, text in (("spaced", identity), ("compact", identity.replace(" ", ""))):
                grams = {text[index:index + size] for size in (2, 3)
                         for index in range(max(0, len(text) - size + 1))}
                if not grams:
                    raise ValueError(f"identity too short for grams: {document.knowledge_id}")
                key = (mode, text)
                if key not in forms:
                    form_id = text_sha(f"{document.knowledge_uuid}\x1f{mode}\x1f{text}")
                    forms[key] = {"form_id": form_id, "mode": mode, "text": text,
                                  "token_count": len(identity.split()), "gram_count": len(grams)}
                    gram_keys.update((mode, gram) for gram in grams)
                    posting_entries += len(grams)
        if len(forms) > LIMITS["identity_forms_per_document"]:
            raise ValueError(f"identity form limit exceeded: {document.knowledge_id}")
        rows.append({"knowledge_id": document.knowledge_id,
                     "knowledge_uuid": str(document.knowledge_uuid),
                     "knowledge_type": document.knowledge_type, "casting": document.casting,
                     "forms": [forms[key] for key in sorted(forms)]})
    groups = [{"core": identity, "knowledge_ids": sorted(ids),
               "original_castings": sorted(set(ids.values())),
               "cross_casting_collision": len(set(ids.values())) > 1}
              for identity, ids in sorted(collisions.items()) if len(ids) > 1]
    return {"documents": rows, "document_count": len(rows),
            "knowledge_type_counts": dict(sorted(Counter(row["knowledge_type"] for row in rows).items())),
            "form_count": sum(len(row["forms"]) for row in rows),
            "max_forms_per_document": max(len(row["forms"]) for row in rows),
            "identity_token_lengths": sorted(lengths), "gram_posting_key_count": len(gram_keys),
            "form_posting_entry_count": posting_entries, "collisions": groups,
            "collision_group_count": len(groups),
            "cross_casting_collision_group_count": sum(row["cross_casting_collision"] for row in groups)}


def query_form_count(query: str, lengths: list[int]) -> int:
    normalized = normalize_text(query)
    if len(normalized) > LIMITS["query_characters"] or len(normalized.split()) > LIMITS["query_tokens_before_noise"]:
        raise ValueError("protocol workload query exceeds proposed query limits")
    tokens = core(query).split()
    forms: set[tuple[str, str]] = set()
    for length in lengths:
        for size in range(max(1, length - 1), length + 2):
            for start in range(max(0, len(tokens) - size + 1)):
                text = " ".join(tokens[start:start + size])
                forms.update((("spaced", text), ("compact", text.replace(" ", ""))))
    if len(forms) > LIMITS["query_forms"]:
        raise ValueError("protocol workload query exceeds proposed window limit")
    return len(forms)


def scale_workload(development: dict[str, Any]) -> list[dict[str, Any]]:
    scale = synthetic_catalog()
    rows = [{"case_id": f"scale-original-{case['case_id']}", "group": "original_dev_20",
             "source_case_id": case["case_id"], "query_text": case["query_text"],
             "correctness_eligible": False, "target_knowledge_id": None,
             "target_knowledge_uuid": None} for case in development["cases"][:20]]
    for index in range(100):
        document = scale.documents[index]
        group = "exact_identity" if index < 60 else "single_edit" if index < 80 else "contextual_identity"
        query = document.casting
        if group == "single_edit":
            query = query.replace("Scale", "Scxle", 1)
        elif group == "contextual_identity":
            query = f"listing {query} local pickup"
        rows.append({"case_id": f"scale-{group}-{index:04d}", "group": group,
                     "source_case_id": None, "query_text": query, "correctness_eligible": True,
                     "target_knowledge_id": document.knowledge_id,
                     "target_knowledge_uuid": str(document.knowledge_uuid)})
    if Counter(row["group"] for row in rows) != {
            "original_dev_20": 20, "exact_identity": 60, "single_edit": 20, "contextual_identity": 20}:
        raise ValueError("scale workload count differs")
    if len({normalize_text(row["query_text"]) for row in rows}) != 120:
        raise ValueError("scale queries duplicate")
    return rows


def build(specs: dict[str, str], *, root: Path = ROOT) -> dict[str, str]:
    validate_specs(specs)
    pack, manifest = load_development(root)
    catalog = load_human_knowledge_catalog(root / "data/human_backed_catalog.json",
                                          root / "data/review_family_knowledge.json",
                                          root / "data/review_family_knowledge_manifest.json")
    real = identity_audit(catalog.documents)
    large = identity_audit(synthetic_catalog().documents)
    workload = scale_workload(pack)
    real_forms = [query_form_count(case["query_text"], real["identity_token_lengths"])
                  for case in pack["cases"]]
    scale_forms = [query_form_count(case["query_text"], large["identity_token_lengths"])
                   for case in workload]
    protocol = {
        "schema_version": "pvr-human-knowledge-identity-protocol-v1", "protocol_version": VERSION,
        "retriever_version": "human-knowledge-hybrid-v4", "split": "dev",
        "status": "frozen_before_v4_configuration_execution", "v4_retrieval_executed": False,
        "v4_configuration_output_viewed": False, "owner_approval": APPROVAL,
        "approved_spec_sha256": SPEC_HASHES,
        "identity_policy": {"version": "identity-core-policy-v1", "normalization": "NFKC_casefold_word_tokens",
                            "noise_tokens": sorted(NOISE), "removal": "whole_tokens",
                            "admission_fields": {"provisional_variant": ["casting"],
                                                 "review_family": ["casting", "aliases"]},
                            "token_admission": "all_tokens_of_one_complete_nonempty_identity_core"},
        "character_score": {"index_version": "human-knowledge-identity-postings-v1",
                            "gram_sizes": [2, 3], "modes": ["spaced", "compact"],
                            "idf": "log((N+1)/(document_df+1))+1",
                            "unknown_query_idf": "log(N+1)+1", "tf": "raw_count",
                            "form_normalization": "L2", "dot_method": "weighted_form_posting_accumulation",
                            "document_score": "max_matching_mode_form_window_cosine",
                            "query_window_token_radius": 1, "tie_break": "knowledge_uuid"},
        "limits": LIMITS, "limit_failure": "discard_all_human_candidates_no_partial_ranks",
        "selection_contract": manifest["selection_contract"],
        "cost_protocol": {"candidate_k": 5, "warmups_per_corpus_configuration": 3,
                          "clock": "perf_counter_ns", "percentile_method": "nearest_rank",
                          "process_count": 1, "real_sample_count": 199, "scale_sample_count": 120,
                          "real_p95_max_ms": 25, "scale_p95_max_ms": 150,
                          "scale_exact_hits_required": 60, "scale_context_hits_required": 20,
                          "scale_single_edit_hits_required": 17,
                          "original_20_subgroup_report_required": True,
                          "positive_abstentions_count_as_misses": True,
                          "excluded": ["index_build", "serialization", "HTTP", "SQL", "network", "concurrency", "production"]},
        "real_query_case_ids": [case["case_id"] for case in pack["cases"]],
        "scale_workload": workload,
        "audit_summary": {"real": {key: value for key, value in real.items() if key != "documents"},
                          "synthetic": {key: value for key, value in large.items() if key != "documents"},
                          "max_real_query_forms": max(real_forms), "max_scale_query_forms": max(scale_forms)},
        "limitations": ["viewed_identity_derived_199_development_cases_reused_not_blind",
                        "v3_report_diagnostic_only_not_final_accuracy", "no_v1_final_selection_access",
                        "synthetic_scale_not_real_database_growth", "synthetic_casting_cores_are_numeric_only",
                        "scale_single_edit_changes_noise_token_not_numeric_target_identity",
                        "no_v4_quality_or_latency_result_yet", "human_debug_only_no_canonical_authority"],
        "excluded_from": ["canonical_resolution", "final_accuracy_claim", "postgresql_ingestion", "default_deployment"],
    }
    # Keep complete core audit for review; no query scoring/candidate output is produced.
    audit = {"schema_version": "pvr-human-knowledge-identity-core-audit-v1",
             "protocol_version": VERSION, "real": real,
             "synthetic_summary": {key: value for key, value in large.items() if key != "documents"},
             "synthetic_documents_sha256": text_sha(stable_json([
                 {"knowledge_id": item.knowledge_id, "knowledge_uuid": str(item.knowledge_uuid),
                  "casting": item.casting, "aliases": list(getattr(item, "aliases"))}
                 for item in synthetic_catalog().documents]))}
    files = {"protocol.json": stable_json(protocol), "identity-core-audit.json": stable_json(audit),
             "owner-approval.json": stable_json(APPROVAL),
             **{f"approved-specs/{name}": text for name, text in specs.items()}}
    source_names = [*SOURCE_PATHS, "scripts/build_human_knowledge_identity_protocol.py",
                    "data/review_family_knowledge_manifest.json", "data/review_family_registry.json",
                    "data/review_family_registry_manifest.json", "data/human_backed_catalog_manifest.json",
                    "reports/family-retrieval-development-v1/selection.json",
                    "reports/family-retrieval-development-v1/selection.md"]
    source_refs = {name: sha(root / name) for name in source_names}
    if source_refs["reports/family-retrieval-development-v1/selection.json"] != "dcc0cd4e09ec5b20862cfee39b90d65a12bbd48a80f7da29c0fbacb0da267853":
        raise ValueError("historical v3 diagnostic report changed")
    frozen_manifest = {"schema_version": "pvr-human-knowledge-identity-protocol-manifest-v1",
                       "protocol_version": VERSION, "status": "frozen_before_v4_configuration_execution",
                       "v4_retrieval_executed": False, "v4_configuration_output_viewed": False,
                       "input_sha256": source_refs,
                       "file_sha256": {name: text_sha(text) for name, text in files.items()}}
    files["protocol-manifest.json"] = stable_json(frozen_manifest)
    return files


def freeze(directory: Path, specs: dict[str, str]) -> None:
    expected = build(specs)
    # Validate all artifacts and existing outputs before replacing any path.
    for name, text in expected.items():
        path = directory / name
        if path.exists() and path.read_text(encoding="utf-8") != text:
            raise ValueError(f"refusing to overwrite a different frozen {name}")
    for name, text in expected.items():
        if not (directory / name).exists():
            atomic_write(directory / name, text)


def check(directory: Path) -> None:
    expected = build(approved_specs(directory))
    for name, text in expected.items():
        if (directory / name).read_text(encoding="utf-8") != text:
            raise ValueError(f"frozen {name} is stale or changed")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--freeze", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--output-dir", type=Path, default=DIRECTORY)
    args = parser.parse_args()
    try:
        if args.freeze:
            freeze(args.output_dir, approved_specs(args.output_dir, from_git=True))
        else:
            check(args.output_dir)
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        print(f"identity protocol ERROR: {error}", file=sys.stderr)
        return 1
    print(f"{'froze' if args.freeze else 'verified'} {VERSION}: 142 real / 3000 synthetic; 199 / 120 queries; no v4 retrieval")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
