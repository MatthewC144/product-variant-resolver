#!/usr/bin/env python3
"""Own one frozen HSP-3 Docker run, publish raw evidence, and clean only owned resources."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LABEL = "pvr.t49-3.owner"
RUN_FREEZE = ROOT / "data/evaluation/human-storage-profile-development-v1/hsp3-run-v4"
OUTPUT = ROOT / "reports/human-storage-profile-hsp3-raw-v4.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def docker(
    *arguments: str, timeout: int = 60, require_success: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["docker", *arguments], capture_output=True, text=True, timeout=timeout, check=False
    )
    if require_success and result.returncode:
        raise RuntimeError(f"docker {arguments[0]} failed: {result.stderr.strip()}")
    return result


def inspect(kind: str, identity: str) -> dict[str, Any]:
    value = json.loads(docker(kind, "inspect", identity).stdout)
    if not isinstance(value, list) or len(value) != 1:
        raise ValueError("unexpected Docker inspection result")
    return dict(value[0])


def tracked_paths() -> list[Path]:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    paths = [ROOT / name.decode() for name in result.stdout.split(b"\0") if name]
    if any(
        not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT)
        for path in paths
    ):
        raise ValueError("tracked staging set contains a missing/symlinked/outside file")
    return paths


def publish(path: Path, report: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink() or path.parent != ROOT / "reports":
        raise ValueError("raw evidence must be a new exclusive reports/ file")
    descriptor, name = tempfile.mkstemp(prefix=".hsp3-raw-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def check_freeze(manifest: dict[str, Any]) -> None:
    if (
        manifest.get("schema_version") != "pvr-human-storage-hsp3-run-freeze-v1"
        or manifest.get("status") != "frozen_before_real_outputs"
    ):
        raise ValueError("HSP-3 pre-output freeze differs")
    if manifest["constraints"] != {
        "retries": 0,
        "parameter_search": False,
        "old_final_105_used": False,
        "production_database_used": False,
    }:
        raise ValueError("HSP-3 fixed-run constraints differ")
    for name, expected in manifest["profiles"].items():
        if sha(RUN_FREEZE / name) != expected:
            raise ValueError("frozen runtime profile bytes differ")
    for relative, expected in manifest["execution_source_sha256"].items():
        if sha(ROOT / relative) != expected:
            raise ValueError("frozen execution source bytes differ")
    if sha(ROOT / manifest["development_pack"]["path"]) != manifest["development_pack"]["sha256"]:
        raise ValueError("fixed199 development pack differs")
    if sha(ROOT / manifest["protocol"]["path"]) != manifest["protocol"]["sha256"]:
        raise ValueError("approved storage protocol differs")


def run(path: Path) -> dict[str, Any]:
    if path.exists() or path.is_symlink():
        raise ValueError("raw evidence already exists; never rerun/replace it")
    if os.getenv("DOCKER_HOST") and not os.environ["DOCKER_HOST"].startswith("unix://"):
        raise ValueError("HSP-3 requires a local Unix Docker engine")
    endpoint = json.loads(
        docker("context", "inspect", "--format", "{{json .Endpoints.docker.Host}}").stdout
    )
    if not endpoint.startswith("unix://"):
        raise ValueError("remote Docker contexts are forbidden")
    manifest_path = RUN_FREEZE / "run-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    check_freeze(manifest)
    token = manifest["owner_token"]
    database = manifest["database"]
    network_name = manifest["network"]
    if (
        not re.fullmatch(r"[0-9a-f]{12}", token)
        or database != "pvr_t49_2_" + token
        or network_name != "pvr-t49-3-" + token
    ):
        raise ValueError("frozen owned-resource names differ")
    images = manifest["images"]
    for tag, expected in images.items():
        if inspect("image", tag)["Id"] != expected:
            raise ValueError("installed image ID differs from frozen run")
    existing = [
        *docker(
            "ps", "-a", "--filter", f"label={LABEL}={token}", "--format", "{{.ID}}"
        ).stdout.split(),
        *docker(
            "network", "ls", "--filter", f"label={LABEL}={token}", "--format", "{{.ID}}"
        ).stdout.split(),
    ]
    if existing:
        raise ValueError("frozen HSP-3 resource token already exists; do not adopt it")
    resources: dict[str, Any] = {"containers": [], "network": None}
    cleanup: dict[str, Any] = {"removed": [], "errors": [], "remaining_owned_resources": []}
    report: dict[str, Any] = {
        "schema_version": "pvr-human-storage-hsp3-raw-v1",
        "publication_status": "raw_unscored",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_freeze": str(RUN_FREEZE.relative_to(ROOT)),
        "run_manifest_sha256": sha(manifest_path),
        "implementation_commit": manifest["implementation_commit"],
        "owner_token": token,
        "images": images,
        "resources": resources,
        "cleanup": cleanup,
        "runner_result": {
            "schema_version": "pvr-human-storage-hsp3-runner-raw-v1",
            "runtime_error": "runner did not produce parseable raw output",
        },
    }
    try:
        paths = tracked_paths()
        bootstrap_password = secrets.token_hex(24)
        with tempfile.TemporaryDirectory(prefix="pvr-hsp3-") as staging_name:
            stage = Path(staging_name)
            stage.chmod(0o755)
            for source in paths:
                target = stage / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            for relative, expected in manifest["execution_source_sha256"].items():
                if sha(stage / relative) != expected:
                    raise ValueError("staged execution source changed")
            network_id = docker(
                "network", "create", "--internal", "--label", f"{LABEL}={token}", network_name
            ).stdout.strip()
            resources["network"] = network_id
            network = inspect("network", network_id)
            if network["Labels"].get(LABEL) != token or network["Internal"] is not True:
                raise ValueError("owned internal network validation failed")
            db_tag = next(tag for tag in images if "pgvector" in tag)
            db_id = docker(
                "create",
                "--name",
                network_name + "-postgres",
                "--network",
                network_name,
                "--network-alias",
                "postgres",
                "--label",
                f"{LABEL}={token}",
                "--tmpfs",
                "/var/lib/postgresql/data:rw,nosuid,noexec,size=256m",
                "-e",
                f"POSTGRES_DB={database}",
                "-e",
                "POSTGRES_USER=pvr_t49_3",
                "-e",
                f"POSTGRES_PASSWORD={bootstrap_password}",
                images[db_tag],
            ).stdout.strip()
            resources["containers"].append(db_id)
            db_info = inspect("container", db_id)
            if (
                db_info["Config"]["Labels"].get(LABEL) != token
                or db_info["HostConfig"]["PortBindings"]
                or any(mount["Type"] != "tmpfs" for mount in db_info["Mounts"])
                or "/var/lib/postgresql/data" not in db_info["HostConfig"]["Tmpfs"]
            ):
                raise ValueError("owned database isolation validation failed")
            docker("start", db_id)
            deadline = time.monotonic() + 45
            while True:
                ready = docker(
                    "exec",
                    db_id,
                    "pg_isready",
                    "-h",
                    "127.0.0.1",
                    "-U",
                    "pvr_t49_3",
                    "-d",
                    database,
                    timeout=5,
                    require_success=False,
                )
                if ready.returncode == 0:
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError("owned PostgreSQL did not become ready")
                time.sleep(0.2)
            reader_password = secrets.token_hex(24)
            runner_tag = next(tag for tag in images if "product-variant-resolver" in tag)
            runner_id = docker(
                "create",
                "--name",
                network_name + "-runner",
                "--network",
                network_name,
                "--label",
                f"{LABEL}={token}",
                "--read-only",
                "--no-healthcheck",
                "--tmpfs",
                "/tmp:rw,nosuid,noexec,size=64m",
                "--workdir",
                "/workspace",
                "--mount",
                f"type=bind,source={stage},target=/workspace,readonly",
                "-e",
                "PYTHONPATH=/workspace/src",
                "-e",
                "PYTHONDONTWRITEBYTECODE=1",
                "-e",
                "PVR_T49_3_ALLOW_DISPOSABLE_DATABASE=1",
                "-e",
                f"PVR_T49_3_OWNER_TOKEN={token}",
                "-e",
                f"PVR_T49_3_EXPECTED_DATABASE={database}",
                "-e",
                "PVR_T49_3_BOOTSTRAP_DATABASE_URL=postgresql+psycopg://pvr_t49_3:"
                + bootstrap_password
                + "@postgres:5432/"
                + database,
                "-e",
                f"PVR_T49_3_READER_PASSWORD={reader_password}",
                "-e",
                "PVR_T49_3_FILE_PROFILE=/workspace/"
                + str((RUN_FREEZE / "file-profile.json").relative_to(ROOT)),
                "-e",
                "PVR_T49_3_POSTGRES_PROFILE=/workspace/"
                + str((RUN_FREEZE / "postgres-profile.json").relative_to(ROOT)),
                "-e",
                "PVR_T49_3_RUN_MANIFEST=/workspace/" + str(manifest_path.relative_to(ROOT)),
                "-e",
                f"PVR_T49_3_DB_IMAGE_ID={images[db_tag]}",
                "-e",
                f"PVR_T49_3_RUNNER_IMAGE_ID={images[runner_tag]}",
                images[runner_tag],
                "python",
                "scripts/verify_human_storage_profile_sql.py",
            ).stdout.strip()
            resources["containers"].append(runner_id)
            runner_info = inspect("container", runner_id)
            if (
                runner_info["Config"]["Labels"].get(LABEL) != token
                or runner_info["HostConfig"]["PortBindings"]
                or runner_info["HostConfig"]["ReadonlyRootfs"] is not True
                or any(
                    mount["Type"] == "volume"
                    or (mount["Type"] == "bind" and mount["RW"] is not False)
                    for mount in runner_info["Mounts"]
                )
            ):
                raise ValueError("owned runner isolation validation failed")
            execution = docker("start", "--attach", runner_id, timeout=900, require_success=False)
            report["runner_result"] = json.loads(execution.stdout)
            if execution.returncode:
                report["runner_failure"] = {
                    "exit_code": execution.returncode,
                    "stderr_sha256": hashlib.sha256(execution.stderr.encode()).hexdigest(),
                    "stderr_redacted": True,
                }
    except Exception as error:
        report["supervisor_failure"] = f"{type(error).__name__}: {error}"
    finally:
        for container_id in reversed(resources["containers"]):
            try:
                owned = inspect("container", container_id)
                if (
                    not re.fullmatch(r"[0-9a-f]{64}", container_id)
                    or owned["Config"]["Labels"].get(LABEL) != token
                ):
                    raise ValueError("refuse cleanup without exact container ownership")
                docker("rm", "--force", container_id)
                cleanup["removed"].append(container_id)
            except Exception as error:
                cleanup["errors"].append(str(error))
        if resources["network"]:
            try:
                owned_network = inspect("network", resources["network"])
                if owned_network["Labels"].get(LABEL) != token or owned_network.get("Containers"):
                    raise ValueError("refuse cleanup of unowned/nonempty network")
                docker("network", "rm", resources["network"])
                cleanup["removed"].append(resources["network"])
            except Exception as error:
                cleanup["errors"].append(str(error))
        try:
            cleanup["remaining_owned_resources"] = [
                *docker(
                    "ps", "-a", "--filter", f"label={LABEL}={token}", "--format", "{{.ID}}"
                ).stdout.split(),
                *docker(
                    "network", "ls", "--filter", f"label={LABEL}={token}", "--format", "{{.ID}}"
                ).stdout.split(),
            ]
        except Exception as error:
            cleanup["errors"].append(str(error))
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        publish(path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--allow-disposable-test", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if not args.run or not args.allow_disposable_test:
        parser.error("HSP-3 requires --run --allow-disposable-test")
    report = run(args.output)
    failure = bool(
        report.get("supervisor_failure")
        or report.get("runner_failure")
        or report["cleanup"]["errors"]
        or report["cleanup"]["remaining_owned_resources"]
    )
    print(f"HSP-3 raw publication: {'FAIL' if failure else 'UNSCORED'}; evidence={args.output}")
    return 1 if failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
