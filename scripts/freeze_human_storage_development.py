#!/usr/bin/env python3
"""Freeze/check HSP-1 inputs only: no database, HTTP or retrieval execution."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SPEC = "specs/human-storage-profile-development/"
OUTPUT = "data/evaluation/human-storage-profile-development-v1/freeze"
PRODUCER = "scripts/freeze_human_storage_development.py"
TASK_COMMIT = "10ee18aca16c85d349ecc56d09abf2615c6a10e8"
APPROVED = {
    "requirements.md": (
        "c197d0fbca1a6d16803ba9809933a9c194ca8046",
        "54dfd2dd31fe51a628344832c3eae3463dac811a9cd489347204ecaac47df918",
    ),
    "design.md": (
        "7a90be004a017493c61bf52a364a89ef4fb6477e",
        "26037641051b08799c99d079d4d43b6ffc33b6a6308ba446669d7ff78736a5dd",
    ),
    "tasks.md": (
        TASK_COMMIT, "26aa54b33e8ef54c0de0242c17d0960dfc510f49d986e580d7518d9eb5a91fb9",
    ),
    "protocol-draft.json": (
        TASK_COMMIT, "e23678bd02f7ad00871a2eca43f05ad1ae2d4139adfe39a1c92e155567d5b235",
    ),
}


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode()


def git_bytes(root: Path, commit: str, relative: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("invalid committed source reference")
    result = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=root,
                            capture_output=True, check=False)
    if result.returncode:
        raise ValueError(f"committed source unavailable: {relative}")
    return result.stdout


def read_source(root: Path, relative: str) -> bytes:
    path = root / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("invalid source path")
    if path.is_symlink() or not path.resolve().is_relative_to(root.resolve()):
        raise ValueError("source must remain inside project")
    return path.read_bytes()


def build_bundle(root: Path, producer_commit: str) -> dict[str, bytes]:
    files: dict[str, bytes] = {}
    spec_bindings = {}
    for name, (commit, expected) in APPROVED.items():
        raw = git_bytes(root, commit, SPEC + name)
        if sha(raw) != expected:
            raise ValueError(f"approved specification hash mismatch: {name}")
        files[name] = raw
        spec_bindings[name] = {"commit": commit, "path": SPEC + name, "sha256": expected}
    draft = json.loads(files["protocol-draft.json"])
    bindings = dict(draft["baseline_source_sha256"])
    snapshot = draft["snapshot"]
    bindings[snapshot["plan_file"]] = snapshot["plan_byte_sha256"]
    plan_raw = read_source(root, snapshot["plan_file"])
    if sha(plan_raw) != snapshot["plan_byte_sha256"]:
        raise ValueError("snapshot plan hash mismatch")
    plan = json.loads(plan_raw)
    if (plan["snapshot_id"] != snapshot["id"]
            or plan["content_sha256"] != snapshot["content_sha256"]
            or len(plan["documents"]) != 142 or len(plan["source_sha256"]) != 12):
        raise ValueError("snapshot identity/count mismatch")
    bindings.update(plan["source_sha256"])
    dev = draft["development"]
    bindings[dev["pack"]] = dev["pack_sha256"]
    bindings[dev["manifest"]] = dev["manifest_sha256"]
    for relative, expected in bindings.items():
        if sha(read_source(root, relative)) != expected:
            raise ValueError(f"frozen input hash mismatch: {relative}")
    producer = read_source(root, PRODUCER)
    if producer != git_bytes(root, producer_commit, PRODUCER):
        raise ValueError("freeze producer must match committed bytes")

    approval = {
        "schema_version": "pvr-human-storage-approval-v1",
        "mode": "Lite",
        "requirements": {"confirmed": True, "owner_message": "確認完成，請繼續執行"},
        "design": {"confirmed": True, "owner_message": "確認 繼續下一步"},
        "tasks_and_budgets": {"confirmed": True, "owner_message": "開始執行"},
        "confirmation_context": "three sequential requirements/design/tasks confirmation questions",
        "approved_spec_bindings": spec_bindings,
        "execution_scope": "HSP-1 local input freeze only",
        "new_isolated_sql_run_authorized": False,
        "production_rollout_authorized": False,
    }
    files["approval.json"] = encode(approval)
    profiles = {
        "schema_version": "pvr-human-storage-declared-profile-v1",
        "profile_version": "human-storage-hydration-development-v1",
        "status": "declared_contract_not_runtime_artifact",
        "modes": draft["profiles"],
        "snapshot": snapshot,
        "legacy_math_protocol_sha256": draft["fixed_mathematics"]["legacy_math_protocol_sha256"],
        "mathematics": draft["fixed_mathematics"],
        "readiness": draft["readiness"],
        "planned_entrypoint": "product_variant_resolver.human_knowledge_storage_app:create_app",
        "planned_modules": ["src/product_variant_resolver/human_knowledge_storage_profile.py",
                            "src/product_variant_resolver/human_knowledge_storage_app.py"],
        "human_authority": "debug_only_canonical_unchanged",
        "credentials": "temporary_external_environment_only_not_in_artifacts",
        "actual_adapter_source_manifest_sha256": None,
        "runtime_image_ids": None,
        "ready_for_real_outputs": False,
    }
    files["declared-profile.json"] = encode(profiles)
    protocol = dict(draft)
    protocol.update({
        "schema_version": "pvr-human-storage-development-protocol-v1",
        "status": "approved_inputs_frozen_pending_adapter_and_runtime",
        "owner_tasks_and_budgets_confirmed": True,
        "approved_spec_sha256": sha(encode(spec_bindings)),
        "approval_sha256": sha(files["approval.json"]),
        "declared_profile_sha256": sha(files["declared-profile.json"]),
        "ready_for_real_outputs": False,
    })
    protocol["cost"] = dict(draft["cost"], budgets_status="owner_approved_not_measured_sla")
    files["protocol.json"] = encode(protocol)
    manifest = {
        "schema_version": "pvr-human-storage-input-freeze-v1",
        "status": "HSP-1_inputs_only_no_runtime_results",
        "producer": {"path": PRODUCER, "commit": producer_commit, "sha256": sha(producer)},
        "source_sha256": bindings,
        "bundle_sha256": {name: sha(raw) for name, raw in files.items()},
        "source_binding_scope": "approved_inputs_and_freeze_producer_not_all_future_runtime_imports",
        "pending_before_real_outputs": ["committed_actual_adapter_and_all_imported_sources",
                                        "runtime_image_ids", "separate_isolated_sql_run_approval"],
        "new_storage_profile_retrieval_executed": False,
    }
    files["manifest.json"] = encode(manifest)
    return files


def publish_bundle(root: Path, producer_commit: str) -> None:
    files = build_bundle(root, producer_commit)  # Validate all inputs before creating output.
    directory = root / OUTPUT
    if directory.exists() or directory.is_symlink():
        raise ValueError("freeze exists; refusing overwrite or retry")
    if not directory.parent.resolve().is_relative_to(root.resolve()):
        raise ValueError("output must remain inside project")
    directory.parent.mkdir(parents=True, exist_ok=True)
    directory.mkdir()
    # Exclusive files; a killed/failed publication remains inspectable and is never overwritten.
    for name, raw in files.items():
        with (directory / name).open("xb") as stream:
            stream.write(raw)


def check_bundle(root: Path) -> None:
    directory = root / OUTPUT
    if directory.is_symlink() or not directory.resolve().is_relative_to(root.resolve()):
        raise ValueError("invalid frozen bundle directory")
    manifest_path = directory / "manifest.json"
    if manifest_path.is_symlink():
        raise ValueError("symlinked manifest rejected")
    manifest = json.loads(manifest_path.read_bytes())
    expected = build_bundle(root, manifest["producer"]["commit"])
    if {path.name for path in directory.iterdir()} != set(expected):
        raise ValueError("partial or unexpected frozen bundle files")
    for name, raw in expected.items():
        path = directory / name
        if path.is_symlink() or path.read_bytes() != raw:
            raise ValueError(f"frozen bundle mismatch: {name}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--freeze", action="store_true")
    group.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        if args.freeze:
            commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                                    capture_output=True, text=True).stdout.strip()
            publish_bundle(ROOT, commit)
        else:
            check_bundle(ROOT)
    except (ValueError, OSError, KeyError, TypeError, subprocess.SubprocessError) as error:
        parser.exit(1, f"HSP-1 FAIL: {error}\n")
    print("HSP-1 input freeze PASS; adapter/runtime/SQL/results remain pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
