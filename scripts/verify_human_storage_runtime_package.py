#!/usr/bin/env python3
"""Run one isolated T49.4 default/file-profile Compose packaging smoke."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / "runtime/human-storage-file-v1"
OUTPUT = ROOT / "reports/human-storage-runtime-package-v1.json"


def command(
    arguments: list[str], *, environment: dict[str, str], required: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        arguments,
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=600,
        check=False,
    )
    if required and result.returncode:
        raise RuntimeError(
            f"command failed: {arguments[:3]}; stderr_sha256="
            + hashlib.sha256(result.stderr.encode()).hexdigest()
        )
    return result


def docker(
    *arguments: str, environment: dict[str, str], required: bool = True
) -> subprocess.CompletedProcess[str]:
    return command(["docker", *arguments], environment=environment, required=required)


def compose(
    project: str,
    *arguments: str,
    environment: dict[str, str],
    required: bool = True,
) -> subprocess.CompletedProcess[str]:
    return command(
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.human-storage.yml",
            "-p",
            project,
            "--profile",
            "human-storage",
            *arguments,
        ],
        environment=environment,
        required=required,
    )


def request(
    port: int,
    path: str,
    body: dict[str, Any] | None = None,
    request_id: str = "",
) -> tuple[int, dict[str, Any]]:
    data = None if body is None else json.dumps(body).encode()
    headers = {"content-type": "application/json"}
    if request_id:
        headers["x-request-id"] = request_id
    item = urllib.request.Request(f"http://127.0.0.1:{port}{path}", data=data, headers=headers)
    try:
        with urllib.request.urlopen(item, timeout=15) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as error:
        return error.code, json.loads(error.read())


def publish(path: Path, payload: dict[str, Any]) -> None:
    if path.exists() or path.is_symlink() or path.parent != ROOT / "reports":
        raise ValueError("runtime report must be a new exclusive reports file")
    descriptor, name = tempfile.mkstemp(prefix=".runtime-package-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def inspect_container(identity: str, image_id: str) -> dict[str, Any]:
    value = json.loads(
        subprocess.run(
            ["docker", "container", "inspect", identity],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        ).stdout
    )[0]
    bindings = value["HostConfig"]["PortBindings"] or {}
    if (
        value["Image"] != image_id
        or value["Config"]["User"] != "pvr"
        or value["HostConfig"]["ReadonlyRootfs"] is not True
        or any(binding["HostIp"] != "127.0.0.1" for rows in bindings.values() for binding in rows)
        or any(mount["RW"] for mount in value["Mounts"] if mount["Type"] != "tmpfs")
    ):
        raise ValueError("runtime container safety boundary differs")
    return {
        "image_id": value["Image"],
        "user": value["Config"]["User"],
        "read_only_root": value["HostConfig"]["ReadonlyRootfs"],
        "port_bindings": bindings,
        "mounts": [
            {"type": item["Type"], "destination": item["Destination"], "rw": item["RW"]}
            for item in value["Mounts"]
        ],
    }


def stable_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def run(output: Path = OUTPUT) -> dict[str, Any]:
    if output.exists() or output.is_symlink():
        raise ValueError("runtime report exists; do not overwrite or rerun")
    sys.path.insert(0, str(ROOT / "scripts"))
    from freeze_human_storage_runtime_package import check

    manifest = check(PACKAGE, check_image=True)
    project = manifest["owner_project"]
    if not re.fullmatch(r"pvr-t49-4-runtime-[0-9a-f]{12}", project):
        raise ValueError("runtime package owner project differs")
    environment = dict(os.environ)
    environment.update(
        {
            "PVR_DEFAULT_REFERENCE_PORT": "18080",
            "PVR_HUMAN_STORAGE_PORT": "18081",
            "PVR_HUMAN_STORAGE_PROFILE_HOST_PATH": str(PACKAGE / "profile.json"),
        }
    )
    report: dict[str, Any] = {
        "schema_version": "pvr-human-storage-runtime-package-report-v1",
        "started_at_utc": datetime.now(UTC).isoformat(),
        "verdict": "FAIL",
        "package_manifest_sha256": hashlib.sha256(
            (PACKAGE / "manifest.json").read_bytes()
        ).hexdigest(),
        "image": manifest["image"],
        "project": project,
        "checks": {},
        "cleanup": {"errors": [], "remaining": []},
    }
    try:
        endpoint = json.loads(
            docker(
                "context",
                "inspect",
                "--format",
                "{{json .Endpoints.docker.Host}}",
                environment=environment,
            ).stdout
        )
        if not endpoint.startswith("unix://"):
            raise ValueError("remote Docker context is forbidden")
        existing = docker(
            "ps",
            "-a",
            "--filter",
            f"label=com.docker.compose.project={project}",
            "--format",
            "{{.ID}}",
            environment=environment,
        ).stdout.split()
        if existing:
            raise ValueError("owned Compose project already exists")
        compose(project, "config", "--quiet", environment=environment)

        missing_path = PACKAGE / "missing-profile.json"
        missing_environment = {
            **environment,
            "PVR_HUMAN_STORAGE_PROFILE_HOST_PATH": str(missing_path),
        }
        missing = compose(
            project,
            "create",
            "--no-build",
            "human-storage-file",
            environment=missing_environment,
            required=False,
        )
        report["checks"]["missing_profile"] = {
            "rejected": missing.returncode != 0,
            "exit_code": missing.returncode,
            "stderr_sha256": hashlib.sha256(missing.stderr.encode()).hexdigest(),
            "path_created": missing_path.exists(),
        }
        if missing.returncode == 0 or missing_path.exists():
            raise ValueError("missing profile did not fail before startup")
        compose(project, "down", "--remove-orphans", environment=environment, required=False)

        compose(
            project,
            "up",
            "--detach",
            "--no-build",
            "--wait",
            "default-reference",
            "human-storage-file",
            environment=environment,
        )
        default_id = compose(
            project, "ps", "-q", "default-reference", environment=environment
        ).stdout.strip()
        storage_id = compose(
            project, "ps", "-q", "human-storage-file", environment=environment
        ).stdout.strip()
        containers = {
            "default_reference": inspect_container(default_id, manifest["image"]["id"]),
            "human_storage_file": inspect_container(storage_id, manifest["image"]["id"]),
        }
        default_health_status, _default_health = request(18080, "/health")
        storage_health_status, storage_health = request(18081, "/health")
        storage_dependency = storage_health["dependencies"]["human_knowledge_storage"]
        profile_version = json.loads((PACKAGE / "profile.json").read_bytes())["artifact_version"]
        if (
            default_health_status != 200
            or storage_health_status != 200
            or storage_dependency["ready"] is not True
            or storage_dependency["version"] != profile_version
        ):
            raise ValueError("runtime health contract differs")

        cases = ["2022 Chevy Nomad Red #101", "Toyota Supra", "Chevy Nomad", "red toy boxed"]
        comparisons = []
        for index, title in enumerate(cases):
            request_id = f"t49-4-runtime-{index}"
            left_status, left = request(18080, "/resolve", {"title": title}, request_id)
            right_status, right = request(18081, "/resolve", {"title": title}, request_id)
            same = left == right
            comparisons.append(
                {
                    "title": title,
                    "status": [left_status, right_status],
                    "same": same,
                    "response_sha256": hashlib.sha256(stable_json(left)).hexdigest(),
                }
            )
            if left_status != 200 or right_status != 200 or not same:
                raise ValueError("default/storage canonical response differs")

        debug_status, debug = request(
            18081,
            "/resolve",
            {"title": cases[0], "debug": True},
            "t49-4-runtime-debug",
        )
        model_versions = debug.get("debug", {}).get("model_versions", {})
        if (
            debug_status != 200
            or "human_knowledge_storage" not in model_versions
            or "human_storage_integrity" not in debug.get("debug", {}).get("timings_ms", {})
        ):
            raise ValueError("debug-only storage evidence differs")
        report["checks"].update(
            {
                "health": {
                    "default_status": default_health_status,
                    "storage_status": storage_health_status,
                    "storage_dependency": storage_dependency,
                },
                "canonical_comparisons": comparisons,
                "debug": {
                    "status": debug_status,
                    "storage_version": model_versions["human_knowledge_storage"],
                    "storage_sha256": model_versions["human_knowledge_storage_sha256"],
                    "integrity_ms_present": True,
                },
                "containers": containers,
            }
        )
        report["verdict"] = "PASS"
    except Exception as error:
        report["failure"] = {
            "type": type(error).__name__,
            "detail": "runtime package verification failed",
        }
    finally:
        cleanup = compose(
            project, "down", "--remove-orphans", environment=environment, required=False
        )
        if cleanup.returncode:
            report["cleanup"]["errors"].append(
                {
                    "exit_code": cleanup.returncode,
                    "stderr_sha256": hashlib.sha256(cleanup.stderr.encode()).hexdigest(),
                }
            )
        report["cleanup"]["remaining"] = [
            *docker(
                "ps",
                "-a",
                "--filter",
                f"label=com.docker.compose.project={project}",
                "--format",
                "{{.ID}}",
                environment=environment,
                required=False,
            ).stdout.split(),
            *docker(
                "network",
                "ls",
                "--filter",
                f"label=com.docker.compose.project={project}",
                "--format",
                "{{.ID}}",
                environment=environment,
                required=False,
            ).stdout.split(),
        ]
        if report["cleanup"]["errors"] or report["cleanup"]["remaining"]:
            report["verdict"] = "FAIL"
        report["finished_at_utc"] = datetime.now(UTC).isoformat()
        publish(output, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    if not args.run:
        parser.error("explicit --run is required")
    result = run(args.output)
    print(f"T49.4 runtime package: {result['verdict']}; evidence={args.output}")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
