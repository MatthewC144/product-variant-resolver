#!/usr/bin/env python3
"""Freeze the one authorized HSP-3 run before any real output is produced."""

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
TEMPLATE = (
    ROOT
    / "data/evaluation/human-storage-profile-development-v1/runtime-source-freeze-v2/profile-template.json"
)
DEFAULT_OUTPUT = ROOT / "data/evaluation/human-storage-profile-development-v1/hsp3-run-v2"
DB_IMAGE = "pgvector/pgvector:pg16"
DB_IMAGE_ID = "sha256:131dcf7ff6a900545df8e7e092c270aa8c6db2f2c818e408cb45ec21316b74e6"
RUNNER_IMAGE = "product-variant-resolver:ibr-t5-rootfix"
RUNNER_IMAGE_ID = "sha256:7dbae114eb0615fb8582cce3fc79b2f19233edc453672bc5726de937dfec0fee"
PRODUCER_COMMIT = "bd2a8387385a960add42d9669a77f33132bccdec"
APPROVAL_TEXT = "繼續執行下一步"


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


def profile(template: dict[str, Any], *, mode: str, database: str) -> dict[str, Any]:
    payload = {
        key: value
        for key, value in template.items()
        if key not in {"not_a_runnable_profile", "required_later_fields", "target_schema_version"}
    }
    payload.update(
        {
            "schema_version": template["target_schema_version"],
            "status": "source_and_runtime_frozen_for_authorized_isolated_run",
            "mode": mode,
            "database": (
                {
                    "url_environment": "PVR_HUMAN_STORAGE_TEST_DATABASE_URL",
                    "expected_database": database,
                }
                if mode == "postgres_snapshot_experiment"
                else None
            ),
            "ready_for_real_outputs": True,
            "runtime_image_ids": [DB_IMAGE_ID, RUNNER_IMAGE_ID],
        }
    )
    payload["artifact_version"] = (
        "human-storage-profile-development-v1-" + sha_bytes(stable(payload))[:12]
    )
    return payload


def publish_directory(output: Path, files: dict[str, bytes]) -> None:
    if output.exists() or output.is_symlink():
        raise ValueError("HSP-3 run freeze already exists; never overwrite it")
    if output.parent != DEFAULT_OUTPUT.parent:
        raise ValueError("run freeze must stay in the versioned evaluation directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".hsp3-freeze-", dir=output.parent))
    try:
        for name, raw in files.items():
            path = temporary / name
            path.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(raw)
        os.rename(temporary, output)
    finally:
        if temporary.exists():
            temporary.rmdir()


def freeze(output: Path = DEFAULT_OUTPUT) -> dict[str, Any]:
    if git("status", "--porcelain"):
        raise ValueError("commit the HSP-3 implementation before freezing the run")
    implementation_commit = git("rev-parse", "HEAD")
    template = json.loads(TEMPLATE.read_bytes())
    token = sha_bytes((implementation_commit + ":HSP-3:authorized").encode())[:12]
    database = "pvr_t49_2_" + token
    file_profile = profile(template, mode="file_snapshot_reference", database=database)
    db_profile = profile(template, mode="postgres_snapshot_experiment", database=database)
    file_raw, db_raw = stable(file_profile), stable(db_profile)
    execution_sources = {
        name: sha(ROOT / name)
        for name in (
            "scripts/freeze_human_storage_hsp3_run.py",
            "scripts/run_human_storage_profile_sql.py",
            "scripts/verify_human_storage_profile_sql.py",
            "scripts/score_human_storage_profile_sql.py",
        )
    }
    manifest = {
        "schema_version": "pvr-human-storage-hsp3-run-freeze-v1",
        "status": "frozen_before_real_outputs",
        "authorization": {
            "owner_message": APPROVAL_TEXT,
            "scope": "HSP-3 disposable SQL correctness run only",
        },
        "implementation_commit": implementation_commit,
        "adapter_source_commit": PRODUCER_COMMIT,
        "owner_token": token,
        "database": database,
        "network": "pvr-t49-3-" + token,
        "images": {DB_IMAGE: DB_IMAGE_ID, RUNNER_IMAGE: RUNNER_IMAGE_ID},
        "profiles": {
            "file-profile.json": sha_bytes(file_raw),
            "postgres-profile.json": sha_bytes(db_raw),
        },
        "execution_source_sha256": execution_sources,
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
            "retries": 0,
            "parameter_search": False,
            "old_final_105_used": False,
            "production_database_used": False,
        },
    }
    manifest_raw = stable(manifest)
    files = {
        "file-profile.json": file_raw,
        "postgres-profile.json": db_raw,
        "run-manifest.json": manifest_raw,
        "README.md": (
            f"# HSP-3 {output.name} freeze\n\nThis directory was published before real SQL/dev outputs. "
            "It binds the approved disposable database name, exact image IDs, two runtime "
            "profiles, fixed 199-case pack, protocol, and execution code. It contains no "
            "credential or database URL.\n"
        ).encode(),
    }
    publish_directory(output, files)
    return {
        "output": str(output.relative_to(ROOT)),
        "manifest_sha256": sha_bytes(manifest_raw),
        "owner_token": token,
        "database": database,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    print(json.dumps(freeze(args.output), ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
