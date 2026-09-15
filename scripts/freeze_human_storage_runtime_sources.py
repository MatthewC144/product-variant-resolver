#!/usr/bin/env python3
"""Freeze/check HSP-2 adapter sources; never build images, contact SQL, or run retrieval."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from product_variant_resolver.human_knowledge_snapshot import canonical_bytes  # noqa: E402
from product_variant_resolver.human_knowledge_storage_profile import (  # noqa: E402
    MATH_ARTIFACT,
    MATH_ARTIFACT_SHA256,
    MATH_PROTOCOL_SHA256,
    PLAN,
    PLAN_SHA256,
    PROFILE_SCHEMA,
    PROFILE_VERSION,
    REQUIRED_RUNTIME_SOURCES,
    SNAPSHOT_ID,
    SNAPSHOT_SHA256,
    STORAGE_PROTOCOL,
    STORAGE_PROTOCOL_SHA256,
)

PRODUCER = "scripts/freeze_human_storage_runtime_sources.py"
OUTPUT = "data/evaluation/human-storage-profile-development-v1/runtime-source-freeze"


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def encode(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                       allow_nan=False) + "\n").encode()


def read(root: Path, relative: str) -> bytes:
    path = root / relative
    if Path(relative).is_absolute() or ".." in Path(relative).parts:
        raise ValueError("invalid source path")
    if any(part.is_symlink() for part in (path, *path.parents)):
        raise ValueError(f"symlink source rejected: {relative}")
    try:
        resolved = path.resolve(strict=True)
    except OSError as error:
        raise ValueError(f"missing source: {relative}") from error
    if not resolved.is_file() or not resolved.is_relative_to(root.resolve()):
        raise ValueError(f"source escapes project: {relative}")
    return resolved.read_bytes()


def git_bytes(root: Path, commit: str, relative: str) -> bytes:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("invalid committed producer reference")
    result = subprocess.run(["git", "show", f"{commit}:{relative}"], cwd=root,
                            capture_output=True, check=False)
    if result.returncode:
        raise ValueError("committed producer is unavailable")
    return result.stdout


def build_bundle(root: Path, producer_commit: str) -> dict[str, bytes]:
    producer = read(root, PRODUCER)
    if producer != git_bytes(root, producer_commit, PRODUCER):
        raise ValueError("runtime-source producer must match committed bytes")
    plan = json.loads(read(root, PLAN))
    if (sha(read(root, PLAN)) != PLAN_SHA256 or plan.get("snapshot_id") != SNAPSHOT_ID
            or plan.get("content_sha256") != SNAPSHOT_SHA256
            or len(plan.get("documents", [])) != 142 or len(plan.get("source_sha256", {})) != 12):
        raise ValueError("pinned snapshot plan differs")
    paths = set(REQUIRED_RUNTIME_SOURCES) | set(plan["source_sha256"]) | {
        PRODUCER, STORAGE_PROTOCOL,
    }
    sources = {}
    for relative in sorted(paths):
        raw = read(root, relative)
        if raw != git_bytes(root, producer_commit, relative):
            raise ValueError(f"runtime source must match committed bytes: {relative}")
        sources[relative] = sha(raw)
    if (sources[STORAGE_PROTOCOL] != STORAGE_PROTOCOL_SHA256
            or sources[MATH_ARTIFACT] != MATH_ARTIFACT_SHA256):
        raise ValueError("approved storage/math protocol binding differs")
    source_digest = sha(canonical_bytes(sources))
    manifest = {
        "schema_version": "pvr-human-storage-runtime-source-manifest-v1",
        "status": "adapter_mock_verified_pending_runtime_images_and_sql_approval",
        "producer": {"commit": producer_commit, "path": PRODUCER, "sha256": sha(producer)},
        "source_sha256": sources,
        "actual_adapter_source_manifest_sha256": source_digest,
        "source_count": len(sources),
        "new_storage_profile_retrieval_executed": False,
        "real_sql_executed": False,
        "runtime_image_ids": None,
    }
    files: dict[str, bytes] = {"manifest.json": encode(manifest)}
    template = {
        "schema_version": "pvr-human-storage-runtime-profile-template-v1",
        "target_schema_version": PROFILE_SCHEMA,
        "profile_version": PROFILE_VERSION,
        "storage_protocol": {"file": STORAGE_PROTOCOL, "sha256": STORAGE_PROTOCOL_SHA256},
        "snapshot": {"id": SNAPSHOT_ID, "content_sha256": SNAPSHOT_SHA256,
            "plan_file": PLAN, "plan_byte_sha256": PLAN_SHA256, "documents": 142,
            "provisional_variant": 100, "review_family": 42},
        "math": {"artifact_file": MATH_ARTIFACT, "artifact_sha256": MATH_ARTIFACT_SHA256,
                 "protocol_sha256": MATH_PROTOCOL_SHA256},
        "source_sha256": sources,
        "actual_adapter_source_manifest_sha256": source_digest,
        "human_authority": "debug_only_canonical_unchanged",
        "automatic_fallback": False,
        "required_later_fields": ["artifact_version", "status", "mode", "database",
                                  "ready_for_real_outputs", "runtime_image_ids"],
        "not_a_runnable_profile": True,
    }
    files["profile-template.json"] = encode(template)
    approved = json.loads(read(root, STORAGE_PROTOCOL))
    approved.update({
        "status": "adapter_sources_frozen_mock_verified_pending_runtime_and_sql",
        "actual_adapter_source_manifest_sha256": source_digest,
        "runtime_source_manifest_file": OUTPUT + "/manifest.json",
        "runtime_source_manifest_sha256": sha(files["manifest.json"]),
        "runtime_profile_template_sha256": sha(files["profile-template.json"]),
        "runtime_image_ids": None,
        "ready_for_real_outputs": False,
        "new_storage_profile_outputs_viewed": False,
        "new_storage_profile_retrieval_executed": False,
    })
    files["protocol-binding.json"] = encode(approved)
    report = (
        "# T49.3 HSP-2 runtime-source freeze\n\n"
        f"Adapter source manifest: `{source_digest}` ({len(sources)} inputs).\n\n"
        "Source/mock contract is frozen. Runtime image IDs, runnable profile, isolated SQL "
        "authorization, real199 outputs and cost results remain absent.\n"
    ).encode()
    files["report.md"] = report
    return files


def publish(root: Path, commit: str) -> None:
    files = build_bundle(root, commit)
    directory = root / OUTPUT
    if directory.exists() or directory.is_symlink():
        raise ValueError("runtime-source freeze exists; refusing overwrite")
    directory.parent.mkdir(parents=True, exist_ok=True)
    directory.mkdir()
    for name, raw in files.items():
        with (directory / name).open("xb") as stream:
            stream.write(raw)


def check(root: Path) -> None:
    directory = root / OUTPUT
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError("runtime-source freeze is unavailable")
    manifest = json.loads((directory / "manifest.json").read_bytes())
    expected = build_bundle(root, manifest["producer"]["commit"])
    if {path.name for path in directory.iterdir()} != set(expected):
        raise ValueError("partial or unexpected runtime-source freeze")
    for name, raw in expected.items():
        path = directory / name
        if path.is_symlink() or path.read_bytes() != raw:
            raise ValueError(f"runtime-source freeze differs: {name}")


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
            publish(ROOT, commit)
        else:
            check(ROOT)
    except (ValueError, OSError, KeyError, TypeError, json.JSONDecodeError,
            subprocess.SubprocessError) as error:
        parser.exit(1, f"HSP-2 FREEZE FAIL: {error}\n")
    print("HSP-2 source freeze PASS; runtime images/SQL/real outputs remain pending")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
