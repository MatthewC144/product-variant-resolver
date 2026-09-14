#!/usr/bin/env python3
"""Own a disposable internal Docker SQL test, publish evidence, clean only owned resources."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
LABEL = "pvr.t49-2.owner"
REPORT_SCHEMA = "pvr-human-knowledge-postgres-test-v1"
DB_IMAGE = "pgvector/pgvector:pg16"
RUNNER_IMAGE = "product-variant-resolver:ibr-t5-rootfix"


def docker(*arguments: str, timeout: int = 60, require_success: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(["docker", *arguments], capture_output=True, text=True,
                            timeout=timeout, check=False)
    if require_success and result.returncode:
        raise RuntimeError(f"docker {arguments[0]} failed: {result.stderr.strip()}")
    return result


def inspect(kind: str, identity: str) -> dict[str, Any]:
    value = json.loads(docker(kind, "inspect", identity).stdout)
    if not isinstance(value, list) or len(value) != 1:
        raise ValueError("unexpected Docker inspection result")
    return dict(value[0])


def source_paths() -> list[Path]:
    # Runtime staging only; copy bytes with new readable modes, never chmod original600files.
    import sys
    sys.path.insert(0, str(ROOT / "src"))
    from product_variant_resolver.human_knowledge_snapshot import SOURCE_HASHES

    paths = [*ROOT.joinpath("src").rglob("*.py"), *ROOT.joinpath("migrations").rglob("*.py"),
             ROOT / "alembic.ini", ROOT / "data/catalog.json",
             ROOT / "scripts/verify_human_knowledge_postgres.py",
             ROOT / "scripts/run_human_knowledge_postgres_test.py",
             ROOT / "reports/human-knowledge-snapshot-v1/plan.json",
             ROOT / "reports/human-knowledge-snapshot-v1/report.md",
             *(ROOT / name for name in SOURCE_HASHES)]
    return sorted(set(paths))


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def check_report(path: Path) -> dict[str, Any]:
    report = json.loads(path.read_bytes())
    if report.get("schema_version") != REPORT_SCHEMA or report.get("verdict") != "PASS":
        raise ValueError("stored SQL test is not a passing v1 report")
    result = report["sql_result"]
    if (result["verdict"] != "PASS" or result["uid"] == 0
            or result["counts"] != {"snapshots": 1, "documents": 142,
                "provisional_variant": 100, "review_family": 42}
            or result["canonical_before_sha256"] != result["canonical_after_sha256"]
            or report["cleanup"]["errors"] or report["cleanup"]["remaining_owned_resources"]):
        raise ValueError("stored counts/canonical/cleanup gate is invalid")
    for relative, expected in report["source_sha256"].items():
        candidate = ROOT / relative
        if (candidate.resolve() != candidate.absolute() or not candidate.is_relative_to(ROOT)
                or sha(candidate) != expected):
            raise ValueError(f"stored source no longer matches: {relative}")
    gates = result["gates"]
    if (gates["sql_fault_visible_documents_before_abort"] != 71
            or any(value is not True for key, value in gates.items()
                   if key not in {"sql_fault_visible_documents_before_abort", "invalid_input_no_overwrite"})
            or any(value is not True for value in gates["invalid_input_no_overwrite"].values())):
        raise ValueError("stored SQL correctness gate failed")
    return dict(report)


def publish(path: Path, report: dict[str, Any]) -> None:
    if path.absolute().parent != ROOT / "reports" or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError("report must be an exclusive project reports/ file")
    descriptor, name = tempfile.mkstemp(prefix=".t49-2-report-", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, sort_keys=True, indent=2)
            handle.write("\n")
        os.link(temporary, path)  # never overwrite existing evidence, even on concurrent publication
    finally:
        temporary.unlink(missing_ok=True)


def run(path: Path) -> dict[str, Any]:
    if path.exists() or path.is_symlink():
        raise ValueError("report already exists; check it, never replace it")
    if path.absolute().parent != ROOT / "reports":
        raise ValueError("report must remain in project reports/")
    if os.getenv("DOCKER_HOST") and not os.environ["DOCKER_HOST"].startswith("unix://"):
        raise ValueError("test must use a local Unix Docker engine, not a remote host")
    endpoint = json.loads(docker("context", "inspect", "--format", "{{json .Endpoints.docker.Host}}").stdout)
    if not endpoint.startswith("unix://"):
        raise ValueError("only the local Unix Docker context is allowed")
    token = uuid.uuid4().hex[:12]
    network_name = "pvr-t49-2-" + token
    database = "pvr_t49_2_" + token
    paths = source_paths()
    report: dict[str, Any] = {"schema_version": REPORT_SCHEMA, "verdict": "FAIL",
        "started_at_utc": datetime.now(timezone.utc).isoformat(), "owner_token": token,
        "source_sha256": {str(p.relative_to(ROOT)): sha(p) for p in paths},
        "images": {name: inspect("image", name)["Id"] for name in (DB_IMAGE, RUNNER_IMAGE)},
        "resources": {"containers": [], "network": None},
        "cleanup": {"removed": [], "errors": [], "remaining_owned_resources": []}}
    resources = report["resources"]
    try:
        with tempfile.TemporaryDirectory(prefix="pvr-t49-2-") as staging_name:
            stage = Path(staging_name)
            stage.chmod(0o755)
            for source in paths:
                target = stage / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
                if sha(target) != report["source_sha256"][str(source.relative_to(ROOT))]:
                    raise ValueError("staged source changed during copy")
            network_id = docker("network", "create", "--internal", "--label", f"{LABEL}={token}", network_name).stdout.strip()
            resources["network"] = network_id
            network = inspect("network", network_id)
            if network["Labels"].get(LABEL) != token or network["Internal"] is not True:
                raise ValueError("new network ownership/isolation failed")
            db_id = docker("create", "--name", network_name + "-postgres", "--network", network_name,
                "--network-alias", "postgres", "--label", f"{LABEL}={token}",
                "--tmpfs", "/var/lib/postgresql/data:rw,nosuid,noexec,size=256m",
                "-e", f"POSTGRES_DB={database}", "-e", "POSTGRES_USER=pvr_t49_2",
                "-e", "POSTGRES_PASSWORD=pvr-disposable-test-only", report["images"][DB_IMAGE]).stdout.strip()
            resources["containers"].append(db_id)
            db_info = inspect("container", db_id)
            if (db_info["Config"]["Labels"].get(LABEL) != token
                    or db_info["HostConfig"]["PortBindings"]
                    or any(m["Type"] != "tmpfs" for m in db_info["Mounts"])
                    or "/var/lib/postgresql/data" not in db_info["HostConfig"]["Tmpfs"]):
                raise ValueError("new database mounts/ports/ownership are unsafe")
            docker("start", db_id)
            deadline = time.monotonic() + 45
            while True:
                ready = docker("exec", db_id, "pg_isready", "-h", "127.0.0.1", "-U", "pvr_t49_2", "-d", database,
                               timeout=5, require_success=False)
                if ready.returncode == 0:
                    break
                if time.monotonic() >= deadline:
                    raise RuntimeError("new isolated PostgreSQL did not become ready")
                time.sleep(0.2)
            runner_id = docker("create", "--name", network_name + "-runner", "--network", network_name,
                "--label", f"{LABEL}={token}", "--read-only", "--no-healthcheck",
                "--tmpfs", "/tmp:rw,nosuid,noexec,size=16m", "--workdir", "/workspace",
                "--mount", f"type=bind,source={stage},target=/workspace,readonly",
                "-e", "PYTHONPATH=/workspace/src", "-e", "PYTHONDONTWRITEBYTECODE=1",
                "-e", "PVR_T49_2_ALLOW_DISPOSABLE_DATABASE=1", "-e", f"PVR_T49_2_EXPECTED_DATABASE={database}",
                "-e", f"PVR_T49_2_DATABASE_URL=postgresql+psycopg://pvr_t49_2:pvr-disposable-test-only@postgres:5432/{database}",
                report["images"][RUNNER_IMAGE], "python", "scripts/verify_human_knowledge_postgres.py").stdout.strip()
            resources["containers"].append(runner_id)
            runner = inspect("container", runner_id)
            if (runner["Config"]["Labels"].get(LABEL) != token or runner["HostConfig"]["PortBindings"]
                    or runner["HostConfig"]["ReadonlyRootfs"] is not True
                    or any(m["Type"] == "volume" or (m["Type"] == "bind" and not m["RW"] is False)
                           for m in runner["Mounts"])):
                raise ValueError("new runner isolation failed")
            execution = docker("start", "--attach", runner_id, timeout=180, require_success=False)
            report["runner_stdout"] = execution.stdout
            report["runner_stderr"] = execution.stderr
            if execution.returncode:
                raise RuntimeError("SQL verifier failed; full stdout/stderr preserved")
            report["sql_result"] = json.loads(execution.stdout)
            if report["sql_result"]["verdict"] != "PASS":
                raise ValueError("SQL correctness did not pass")
            report["verdict"] = "PASS"
    except Exception as error:
        report["failure"] = f"{type(error).__name__}: {error}"
    finally:
        cleanup = report["cleanup"]
        for container_id in reversed(resources["containers"]):
            try:
                owned = inspect("container", container_id)
                if not re.fullmatch(r"[0-9a-f]{64}", container_id) or owned["Config"]["Labels"].get(LABEL) != token:
                    raise ValueError("refuse cleanup without exact new-container ownership")
                docker("rm", "--force", container_id)
                cleanup["removed"].append(container_id)
            except Exception as error:
                cleanup["errors"].append(str(error))
        if resources["network"]:
            try:
                network = inspect("network", resources["network"])
                if network["Labels"].get(LABEL) != token or network.get("Containers"):
                    raise ValueError("refuse cleanup of unowned/nonempty network")
                docker("network", "rm", resources["network"])
                cleanup["removed"].append(resources["network"])
            except Exception as error:
                cleanup["errors"].append(str(error))
        try:
            cleanup["remaining_owned_resources"] = [*docker("ps", "-a", "--filter", f"label={LABEL}={token}",
                "--format", "{{.ID}}").stdout.split(), *docker("network", "ls", "--filter", f"label={LABEL}={token}",
                "--format", "{{.ID}}").stdout.split()]
        except Exception as error:
            cleanup["errors"].append(str(error))
        if cleanup["errors"] or cleanup["remaining_owned_resources"]:
            report["verdict"] = "FAIL"
        report["finished_at_utc"] = datetime.now(timezone.utc).isoformat()
        publish(path, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--run", action="store_true")
    mode.add_argument("--check", action="store_true")
    parser.add_argument("--allow-disposable-test", action="store_true")
    parser.add_argument("--output", type=Path, default=ROOT / "reports/human-knowledge-postgres-t49-2.json")
    args = parser.parse_args()
    if args.run and not args.allow_disposable_test:
        parser.error("--run requires --allow-disposable-test for the approved isolated environment")
    report = run(args.output) if args.run else check_report(args.output)
    print(f"T49.2 isolated SQL: {report['verdict']}; evidence={args.output}")
    return 0 if report["verdict"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
