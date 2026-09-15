#!/usr/bin/env python3
"""Freeze one HSP-4 cost run before collecting any timing output."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE_PROFILE = (
    ROOT / "data/evaluation/human-storage-profile-development-v1/hsp3-run-v4/file-profile.json"
)
OUTPUT = ROOT / "data/evaluation/human-storage-profile-development-v1/hsp4-run-v2"
DB_IMAGE = "pgvector/pgvector:pg16"
DB_IMAGE_ID = "sha256:131dcf7ff6a900545df8e7e092c270aa8c6db2f2c818e408cb45ec21316b74e6"
RUNNER_IMAGE = "product-variant-resolver:ibr-t5-rootfix"
RUNNER_IMAGE_ID = "sha256:7dbae114eb0615fb8582cce3fc79b2f19233edc453672bc5726de937dfec0fee"


def stable(value: Any) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        + "\n"
    ).encode()


def sha_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha(path: Path) -> str:
    return sha_bytes(path.read_bytes())


def git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise ValueError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def runtime_profile(base: dict[str, Any], *, mode: str, database: str) -> dict[str, Any]:
    value = {
        **base,
        "artifact_version": "pending",
        "mode": mode,
        "database": (
            {
                "url_environment": "PVR_HUMAN_STORAGE_TEST_DATABASE_URL",
                "expected_database": database,
            }
            if mode == "postgres_snapshot_experiment"
            else None
        ),
    }
    value["artifact_version"] = (
        "human-storage-profile-development-v1-" + sha_bytes(stable(value))[:12]
    )
    return value


def publish(output: Path, files: dict[str, bytes]) -> None:
    if output.exists() or output.is_symlink() or output.parent != OUTPUT.parent:
        raise ValueError("HSP-4 freeze must be a new versioned evaluation directory")
    temporary = Path(tempfile.mkdtemp(prefix=".hsp4-freeze-", dir=output.parent))
    try:
        for name, raw in files.items():
            path = temporary / name
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(raw)
        os.rename(temporary, output)
    finally:
        if temporary.exists():
            temporary.rmdir()


def freeze(output: Path = OUTPUT) -> dict[str, Any]:
    if git("status", "--porcelain"):
        raise ValueError("commit HSP-4 measurement code before freezing the run")
    commit = git("rev-parse", "HEAD")
    token = sha_bytes((commit + ":HSP-4:authorized").encode())[:12]
    database = "pvr_t49_2_" + token
    base = json.loads(BASE_PROFILE.read_bytes())
    file_raw = stable(runtime_profile(base, mode="file_snapshot_reference", database=database))
    db_raw = stable(runtime_profile(base, mode="postgres_snapshot_experiment", database=database))
    sources = {
        name: sha(ROOT / name)
        for name in (
            "scripts/freeze_human_storage_hsp4_run.py",
            "scripts/run_human_storage_profile_cost.py",
            "scripts/verify_human_storage_profile_cost.py",
            "scripts/score_human_storage_profile_cost.py",
        )
    }
    manifest = {
        "schema_version": "pvr-human-storage-hsp4-run-freeze-v1",
        "status": "frozen_before_cost_outputs",
        "implementation_commit": commit,
        "authorization": {"owner_message": "幫我繼續執行", "scope": "HSP-4 cost run only"},
        "owner_token": token,
        "database": database,
        "network": "pvr-t49-4-" + token,
        "images": {DB_IMAGE: DB_IMAGE_ID, RUNNER_IMAGE: RUNNER_IMAGE_ID},
        "profiles": {
            "file-profile.json": sha_bytes(file_raw),
            "postgres-profile.json": sha_bytes(db_raw),
        },
        "execution_source_sha256": sources,
        "development_pack": {
            "path": "data/evaluation/family-retrieval-development-v1/development-pack.json",
            "sha256": sha(
                ROOT / "data/evaluation/family-retrieval-development-v1/development-pack.json"
            ),
            "cases": 199,
        },
        "protocol": {
            "path": "data/evaluation/human-storage-profile-development-v1/freeze/protocol.json",
            "sha256": sha(
                ROOT / "data/evaluation/human-storage-profile-development-v1/freeze/protocol.json"
            ),
        },
        "constraints": {
            "timed_retries": 0,
            "threshold_changes": False,
            "old_final_105_used": False,
            "production_database_used": False,
        },
    }
    manifest_raw = stable(manifest)
    publish(
        output,
        {
            "file-profile.json": file_raw,
            "postgres-profile.json": db_raw,
            "run-manifest.json": manifest_raw,
            "README.md": b"# HSP-4 run v2\n\nPre-output freeze for the approved 142-document cost protocol.\n",
        },
    )
    return {
        "output": str(output.relative_to(ROOT)),
        "manifest_sha256": sha_bytes(manifest_raw),
        "database": database,
        "owner_token": token,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    print(json.dumps(freeze(args.output), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
