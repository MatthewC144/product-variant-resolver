#!/usr/bin/env python3
"""Own one frozen HSP-4 cost run and clean only its labeled Docker resources."""

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
LABEL = "pvr.t49-4.owner"
FREEZE = ROOT / "data/evaluation/human-storage-profile-development-v1/hsp4-run-v2"
OUTPUT = ROOT / "reports/human-storage-profile-hsp4-raw-v2.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def docker(
    *args: str, timeout: int = 60, required: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["docker", *args], capture_output=True, text=True, timeout=timeout, check=False
    )
    if required and result.returncode:
        raise RuntimeError(f"docker {args[0]} failed: {result.stderr.strip()}")
    return result


def inspect(kind: str, identity: str) -> dict[str, Any]:
    value = json.loads(docker(kind, "inspect", identity).stdout)
    if not isinstance(value, list) or len(value) != 1:
        raise ValueError("unexpected Docker inspect output")
    return dict(value[0])


def tracked() -> list[Path]:
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT, capture_output=True, check=True)
    paths = [ROOT / value.decode() for value in result.stdout.split(b"\0") if value]
    if any(
        not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(ROOT)
        for path in paths
    ):
        raise ValueError("tracked staging input differs")
    return paths


def publish(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink() or path.parent != ROOT / "reports":
        raise ValueError("HSP-4 raw evidence must be a new exclusive reports file")
    descriptor, name = tempfile.mkstemp(prefix=".hsp4-raw-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def validate_freeze(manifest: dict[str, Any]) -> None:
    if (
        manifest.get("schema_version") != "pvr-human-storage-hsp4-run-freeze-v1"
        or manifest.get("status") != "frozen_before_cost_outputs"
        or manifest["constraints"]
        != {
            "timed_retries": 0,
            "threshold_changes": False,
            "old_final_105_used": False,
            "production_database_used": False,
        }
    ):
        raise ValueError("HSP-4 freeze identity/constraints differ")
    for name, expected in manifest["profiles"].items():
        if sha(FREEZE / name) != expected:
            raise ValueError("frozen HSP-4 profile differs")
    for relative, expected in manifest["execution_source_sha256"].items():
        if sha(ROOT / relative) != expected:
            raise ValueError("frozen HSP-4 execution source differs")
    for item in ("protocol", "development_pack"):
        if sha(ROOT / manifest[item]["path"]) != manifest[item]["sha256"]:
            raise ValueError(f"frozen HSP-4 {item} differs")


def run(output: Path) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise ValueError("HSP-4 raw report exists; never replace or rerun it")
    if os.getenv("DOCKER_HOST") and not os.environ["DOCKER_HOST"].startswith("unix://"):
        raise ValueError("only a local Unix Docker engine is allowed")
    endpoint = json.loads(
        docker("context", "inspect", "--format", "{{json .Endpoints.docker.Host}}").stdout
    )
    if not endpoint.startswith("unix://"):
        raise ValueError("remote Docker context is forbidden")
    manifest_path = FREEZE / "run-manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    validate_freeze(manifest)
    token, database, network_name = (
        manifest["owner_token"],
        manifest["database"],
        manifest["network"],
    )
    if (
        not re.fullmatch(r"[0-9a-f]{12}", token)
        or database != "pvr_t49_2_" + token
        or network_name != "pvr-t49-4-" + token
    ):
        raise ValueError("frozen HSP-4 resource names differ")
    images = manifest["images"]
    for tag, expected in images.items():
        if inspect("image", tag)["Id"] != expected:
            raise ValueError("installed image differs from HSP-4 freeze")
    if (
        docker(
            "ps", "-a", "--filter", f"label={LABEL}={token}", "--format", "{{.ID}}"
        ).stdout.split()
        or docker(
            "network", "ls", "--filter", f"label={LABEL}={token}", "--format", "{{.ID}}"
        ).stdout.split()
    ):
        raise ValueError("HSP-4 owned token already exists")
    resources: dict[str, Any] = {"containers": [], "network": None}
    cleanup: dict[str, Any] = {"removed": [], "errors": [], "remaining_owned_resources": []}
    report: dict[str, Any] = {
        "schema_version": "pvr-human-storage-hsp4-raw-v1",
        "publication_status": "raw_unscored",
        "started_at_utc": datetime.now(timezone.utc).isoformat(),
        "run_freeze": str(FREEZE.relative_to(ROOT)),
        "run_manifest_sha256": sha(manifest_path),
        "implementation_commit": manifest["implementation_commit"],
        "owner_token": token,
        "images": images,
        "resources": resources,
        "cleanup": cleanup,
        "runner_result": {
            "schema_version": "pvr-human-storage-hsp4-runner-raw-v1",
            "runtime_error": "collector did not produce parseable output",
        },
    }
    try:
        bootstrap_password, reader_password = secrets.token_hex(24), secrets.token_hex(24)
        with tempfile.TemporaryDirectory(prefix="pvr-hsp4-") as directory:
            stage = Path(directory)
            stage.chmod(0o755)
            for source in tracked():
                target = stage / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
            for relative, expected in manifest["execution_source_sha256"].items():
                if sha(stage / relative) != expected:
                    raise ValueError("staged HSP-4 execution source changed")
            network_id = docker(
                "network", "create", "--internal", "--label", f"{LABEL}={token}", network_name
            ).stdout.strip()
            resources["network"] = network_id
            network = inspect("network", network_id)
            if network["Labels"].get(LABEL) != token or network["Internal"] is not True:
                raise ValueError("HSP-4 network isolation differs")
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
                "POSTGRES_USER=pvr_t49_4",
                "-e",
                f"POSTGRES_PASSWORD={bootstrap_password}",
                images[db_tag],
            ).stdout.strip()
            resources["containers"].append(db_id)
            db = inspect("container", db_id)
            if (
                db["Config"]["Labels"].get(LABEL) != token
                or db["HostConfig"]["PortBindings"]
                or any(mount["Type"] != "tmpfs" for mount in db["Mounts"])
            ):
                raise ValueError("HSP-4 database isolation differs")
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
                    "pvr_t49_4",
                    "-d",
                    database,
                    timeout=5,
                    required=False,
                )
                if ready.returncode == 0:
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError("HSP-4 PostgreSQL did not become ready")
                time.sleep(0.2)
            runner_tag = next(tag for tag in images if "product-variant-resolver" in tag)
            relative = lambda path: "/workspace/" + str(path.relative_to(ROOT))
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
                "PVR_T49_4_ALLOW_DISPOSABLE_DATABASE=1",
                "-e",
                f"PVR_T49_4_OWNER_TOKEN={token}",
                "-e",
                f"PVR_T49_4_EXPECTED_DATABASE={database}",
                "-e",
                "PVR_T49_4_BOOTSTRAP_DATABASE_URL=postgresql+psycopg://pvr_t49_4:"
                + bootstrap_password
                + "@postgres:5432/"
                + database,
                "-e",
                f"PVR_T49_4_READER_PASSWORD={reader_password}",
                "-e",
                "PVR_T49_4_FILE_PROFILE=" + relative(FREEZE / "file-profile.json"),
                "-e",
                "PVR_T49_4_POSTGRES_PROFILE=" + relative(FREEZE / "postgres-profile.json"),
                "-e",
                "PVR_T49_4_RUN_MANIFEST=" + relative(manifest_path),
                "-e",
                f"PVR_T49_4_DB_IMAGE_ID={images[db_tag]}",
                "-e",
                f"PVR_T49_4_RUNNER_IMAGE_ID={images[runner_tag]}",
                images[runner_tag],
                "python",
                "scripts/verify_human_storage_profile_cost.py",
            ).stdout.strip()
            resources["containers"].append(runner_id)
            runner = inspect("container", runner_id)
            if (
                runner["Config"]["Labels"].get(LABEL) != token
                or runner["HostConfig"]["PortBindings"]
                or runner["HostConfig"]["ReadonlyRootfs"] is not True
                or any(
                    mount["Type"] == "volume"
                    or (mount["Type"] == "bind" and mount["RW"] is not False)
                    for mount in runner["Mounts"]
                )
            ):
                raise ValueError("HSP-4 runner isolation differs")
            execution = docker("start", "--attach", runner_id, timeout=1200, required=False)
            try:
                report["runner_result"] = json.loads(execution.stdout)
            except json.JSONDecodeError:
                report["runner_result"] = {
                    "schema_version": "pvr-human-storage-hsp4-runner-raw-v1",
                    "runtime_error": {
                        "type": "UnparseableRunnerOutput",
                        "detail": "redacted collector failure",
                    },
                }
            if execution.returncode or "runtime_error" in report["runner_result"]:
                report["runner_failure"] = {
                    "exit_code": execution.returncode,
                    "stdout_sha256": hashlib.sha256(execution.stdout.encode()).hexdigest(),
                    "stderr_sha256": hashlib.sha256(execution.stderr.encode()).hexdigest(),
                    "stderr_redacted": True,
                }
    except Exception as error:
        report["supervisor_failure"] = f"{type(error).__name__}: {error}"
    finally:
        for container_id in reversed(resources["containers"]):
            try:
                value = inspect("container", container_id)
                if (
                    not re.fullmatch(r"[0-9a-f]{64}", container_id)
                    or value["Config"]["Labels"].get(LABEL) != token
                ):
                    raise ValueError("refuse cleanup without exact HSP-4 container ownership")
                docker("rm", "--force", container_id)
                cleanup["removed"].append(container_id)
            except Exception as error:
                cleanup["errors"].append(str(error))
        if resources["network"]:
            try:
                value = inspect("network", resources["network"])
                if value["Labels"].get(LABEL) != token or value.get("Containers"):
                    raise ValueError("refuse cleanup of unowned/nonempty HSP-4 network")
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
        publish(output, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--allow-disposable-test", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if not args.run or not args.allow_disposable_test:
        parser.error("HSP-4 requires --run --allow-disposable-test")
    report = run(args.output)
    failure = bool(
        report.get("supervisor_failure")
        or report.get("runner_failure")
        or report["cleanup"]["errors"]
        or report["cleanup"]["remaining_owned_resources"]
    )
    print(f"HSP-4 raw publication: {'FAIL' if failure else 'UNSCORED'}; evidence={args.output}")
    return 1 if failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
