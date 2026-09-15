#!/usr/bin/env python3
"""Freeze an image-bound file-profile package before T49.4 runtime output."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "data/evaluation/human-storage-profile-development-v1/hsp4-run-v2/file-profile.json"
OUTPUT = ROOT / "runtime/human-storage-file-v2"
IMAGE = "product-variant-resolver:human-storage-lite"
PACKAGE_SOURCES = (
    "Dockerfile.human-storage",
    "Dockerfile.human-storage.dockerignore",
    "docker-compose.human-storage.yml",
    "scripts/freeze_human_storage_runtime_package.py",
    "scripts/verify_human_storage_runtime_package.py",
)


def stable(value: Any) -> bytes:
    return (
        json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
        )
        + "\n"
    ).encode()


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def git(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments], cwd=ROOT, capture_output=True, text=True, check=False
    )
    if result.returncode:
        raise ValueError(result.stderr.strip() or "git command failed")
    return result.stdout.strip()


def installed_image_id(image: str = IMAGE) -> str:
    result = subprocess.run(
        ["docker", "image", "inspect", "--format", "{{.Id}}", image],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise ValueError("required T49.4 runtime image is unavailable")
    value = result.stdout.strip()
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", value):
        raise ValueError("runtime image ID is not content-addressed")
    return value


def package_payloads(image_id: str, commit: str) -> tuple[bytes, bytes, bytes]:
    if not re.fullmatch(r"sha256:[0-9a-f]{64}", image_id):
        raise ValueError("runtime image ID is not content-addressed")
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("implementation commit must be a full Git object ID")
    base = json.loads(BASE.read_bytes())
    if (
        base.get("mode") != "file_snapshot_reference"
        or base.get("ready_for_real_outputs") is not True
    ):
        raise ValueError("base file profile is not runtime-ready")
    profile = {
        **base,
        "artifact_version": "pending",
        "runtime_image_ids": [base["runtime_image_ids"][0], image_id],
    }
    profile["artifact_version"] = (
        "human-storage-profile-development-v1-" + hashlib.sha256(stable(profile)).hexdigest()[:12]
    )
    profile_raw = stable(profile)
    token = hashlib.sha256((commit + image_id + ":T49.4").encode()).hexdigest()[:12]
    manifest = {
        "schema_version": "pvr-human-storage-runtime-package-v1",
        "status": "frozen_before_runtime_output",
        "implementation_commit": commit,
        "owner_authorization": "請幫我執行下一步",
        "owner_project": "pvr-t49-4-runtime-" + token,
        "image": {"reference": IMAGE, "id": image_id},
        "profile": {
            "path": "runtime/human-storage-file-v2/profile.json",
            "sha256": hashlib.sha256(profile_raw).hexdigest(),
            "mode": "file_snapshot_reference",
        },
        "base_profile": {
            "path": str(BASE.relative_to(ROOT)),
            "sha256": sha(BASE),
        },
        "compose": {
            "profile": "human-storage",
            "service": "human-storage-file",
            "entrypoint": "product_variant_resolver.human_knowledge_storage_app:app",
            "container_profile_path": "/runtime/profile.json",
        },
        "package_source_sha256": {name: sha(ROOT / name) for name in PACKAGE_SOURCES},
        "constraints": {
            "default_api_unchanged": True,
            "database_used": False,
            "persistent_volume_used": False,
            "production_rollout": False,
            "real_3000_claim": False,
        },
    }
    readme = (
        "# Human storage file runtime v2\n\n"
        "Image-bound opt-in T49.4 package. Default API and PostgreSQL rollout remain unchanged.\n"
    ).encode()
    return profile_raw, stable(manifest), readme


def publish(output: Path, files: dict[str, bytes]) -> None:
    if output.exists() or output.is_symlink() or output.parent != OUTPUT.parent:
        raise ValueError("runtime package must be a new exclusive directory")
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix=".human-storage-package-", dir=output.parent))
    try:
        for name, raw in files.items():
            descriptor = os.open(temporary / name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(raw)
        os.rename(temporary, output)
    finally:
        if temporary.exists():
            temporary.rmdir()


def freeze(output: Path = OUTPUT, image: str = IMAGE) -> dict[str, Any]:
    if git("status", "--porcelain"):
        raise ValueError("commit T49.4 packaging sources before freezing")
    commit = git("rev-parse", "HEAD")
    image_id = installed_image_id(image)
    profile, manifest, readme = package_payloads(image_id, commit)
    publish(output, {"profile.json": profile, "manifest.json": manifest, "README.md": readme})
    return {
        "output": str(output.relative_to(ROOT)),
        "image_id": image_id,
        "profile_sha256": hashlib.sha256(profile).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
    }


def check(output: Path = OUTPUT, *, check_image: bool = False) -> dict[str, Any]:
    if output.is_symlink() or not output.is_dir():
        raise ValueError("runtime package directory is unavailable")
    expected = {"README.md", "manifest.json", "profile.json"}
    if {path.name for path in output.iterdir()} != expected:
        raise ValueError("runtime package files differ")
    manifest: dict[str, Any] = json.loads((output / "manifest.json").read_bytes())
    if (
        manifest.get("schema_version") != "pvr-human-storage-runtime-package-v1"
        or manifest.get("status") != "frozen_before_runtime_output"
        or manifest["profile"]["sha256"] != sha(output / "profile.json")
        or manifest["base_profile"]["sha256"] != sha(ROOT / manifest["base_profile"]["path"])
    ):
        raise ValueError("runtime package identity differs")
    for name, expected_sha in manifest["package_source_sha256"].items():
        if sha(ROOT / name) != expected_sha:
            raise ValueError(f"runtime package source differs: {name}")
    profile = json.loads((output / "profile.json").read_bytes())
    if profile["runtime_image_ids"][1] != manifest["image"]["id"]:
        raise ValueError("profile is not bound to packaged image")
    if (
        check_image
        and installed_image_id(manifest["image"]["reference"]) != manifest["image"]["id"]
    ):
        raise ValueError("installed image differs from runtime package")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--freeze", action="store_true")
    action.add_argument("--check", action="store_true")
    parser.add_argument("--check-image", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--image", default=IMAGE)
    args = parser.parse_args()
    result = (
        freeze(args.output, args.image)
        if args.freeze
        else check(args.output, check_image=args.check_image)
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
