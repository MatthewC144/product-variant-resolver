#!/usr/bin/env python3
"""Collect raw HSP-4 startup, Uvicorn HTTP, integrity, and human-core durations."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import alembic
import httpx
import psycopg
import sqlalchemy as sa
import uvicorn
from alembic import command
from alembic.config import Config

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from product_variant_resolver.config import Settings  # noqa: E402
from product_variant_resolver.human_knowledge_persistence import (  # noqa: E402
    PostgresHumanKnowledgeSnapshotRepository,
)
from product_variant_resolver.human_knowledge_snapshot import check_bundle  # noqa: E402
from product_variant_resolver.human_knowledge_storage_app import (  # noqa: E402
    build_service,
    create_app,
)
from product_variant_resolver.signals import extract_signals  # noqa: E402


def settings() -> Settings:
    return Settings(
        catalog_path=ROOT / "data/catalog.json",
        human_catalog_path=ROOT / "data/human_backed_catalog.json",
        review_family_knowledge_path=ROOT / "data/review_family_knowledge.json",
        review_family_knowledge_manifest_path=ROOT / "data/review_family_knowledge_manifest.json",
        human_knowledge_development_path=(
            ROOT / "data/evaluation/family-retrieval-development-v1/development-pack.json"
        ),
        human_knowledge_development_manifest_path=(
            ROOT / "data/evaluation/family-retrieval-development-v1/development-pack-manifest.json"
        ),
        ui_path=ROOT / "ui",
        candidate_limit=25,
        debug_enabled=True,
    )


def environment() -> dict[str, str]:
    value = os.environ.get("PVR_HUMAN_STORAGE_TEST_DATABASE_URL", "")
    return {"PVR_HUMAN_STORAGE_TEST_DATABASE_URL": value} if value else {}


def duration_ms(started: int) -> float:
    return round((time.perf_counter_ns() - started) / 1_000_000, 6)


def startup_worker(profile: Path) -> dict[str, Any]:
    started = time.perf_counter_ns()
    service = build_service(settings(), profile_path=profile, root=ROOT, environ=environment())
    elapsed = duration_ms(started)
    return {
        "duration_ms": elapsed,
        "documents": len(service.human_catalog.documents),
        "profile_version": service.storage_profile.artifact_version,
        "storage_mode": service.storage_profile.mode,
        "error": None,
    }


def serve(profile: Path, port: int) -> None:
    app = create_app(settings(), profile_path=profile, root=ROOT, environ=environment())
    uvicorn.run(app, host="127.0.0.1", port=port, workers=1, log_level="warning", access_log=False)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def validate_inputs(manifest: dict[str, Any], manifest_path: Path) -> None:
    if manifest.get("schema_version") != "pvr-human-storage-hsp4-run-freeze-v1":
        raise ValueError("HSP-4 run manifest differs")
    if sha(ROOT / manifest["protocol"]["path"]) != manifest["protocol"]["sha256"]:
        raise ValueError("approved cost protocol differs")
    if sha(ROOT / manifest["development_pack"]["path"]) != manifest["development_pack"]["sha256"]:
        raise ValueError("fixed199 development pack differs")
    for name, expected in manifest["profiles"].items():
        if sha(manifest_path.parent / name) != expected:
            raise ValueError("HSP-4 profile differs from pre-output freeze")
    for tag, expected in manifest["images"].items():
        actual = os.environ[
            "PVR_T49_4_DB_IMAGE_ID" if "pgvector" in tag else "PVR_T49_4_RUNNER_IMAGE_ID"
        ]
        if actual != expected:
            raise ValueError("runtime image differs from HSP-4 freeze")


def create_reader(engine: Any, *, database: str, token: str, password: str) -> tuple[str, str]:
    role = "pvr_hsp4_reader_" + token
    if not re.fullmatch(r"[a-z0-9_]+", role) or not re.fullmatch(r"[0-9a-f]{48}", password):
        raise ValueError("unsafe generated reader credential shape")
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                f"CREATE ROLE {role} LOGIN PASSWORD '{password}' "
                "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT"
            )
        )
        connection.execute(sa.text(f"GRANT CONNECT ON DATABASE {database} TO {role}"))
        connection.execute(sa.text(f"GRANT USAGE ON SCHEMA public TO {role}"))
        connection.execute(
            sa.text(f"GRANT SELECT ON public.hk_snapshot, public.hk_document TO {role}")
        )
    url = f"postgresql+psycopg://{role}:{password}@postgres:5432/{database}"
    return role, url


def collect_startups(profile: Path, samples: int) -> list[dict[str, Any]]:
    rows = []
    for index in range(samples):
        result = subprocess.run(
            [sys.executable, str(Path(__file__)), "--startup-worker", str(profile)],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if result.returncode:
            rows.append(
                {
                    "sample": index,
                    "duration_ms": None,
                    "error": {
                        "exit_code": result.returncode,
                        "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest(),
                    },
                }
            )
            continue
        value = json.loads(result.stdout)
        rows.append({"sample": index, **value})
    return rows


def wait_ready(url: str) -> None:
    deadline = time.monotonic() + 30
    with httpx.Client(timeout=3) as client:
        while True:
            try:
                if client.get(url + "/health").status_code == 200:
                    return
            except httpx.HTTPError:
                pass
            if time.monotonic() >= deadline:
                raise RuntimeError("Uvicorn profile server did not become ready")
            time.sleep(0.05)


def http_call(
    client: httpx.Client, base: str, case: dict[str, Any], request_id: str, *, warmup: bool
) -> dict[str, Any]:
    started = time.perf_counter_ns()
    try:
        response = client.post(
            base + "/resolve",
            headers={"x-request-id": request_id},
            json={"title": case["query_text"], "debug": True, "debug_candidate_limit": 5},
        )
        body = response.json()
        elapsed = duration_ms(started)
        return {
            "duration_ms": elapsed,
            "status": response.status_code,
            "error": None if response.status_code == 200 else body,
            "abstention": body.get("status") if response.status_code == 200 else None,
            "candidate_count": len(body.get("debug", {}).get("human_knowledge_candidates", [])),
            "integrity_ms": body.get("debug", {})
            .get("timings_ms", {})
            .get("human_storage_integrity"),
            "warmup": warmup,
        }
    except Exception as error:
        return {
            "duration_ms": duration_ms(started),
            "status": None,
            "error": {"type": type(error).__name__, "detail": "request failed"},
            "abstention": None,
            "candidate_count": None,
            "integrity_ms": None,
            "warmup": warmup,
        }


def core_call(service: Any, signal: Any, *, warmup: bool) -> dict[str, Any]:
    started = time.perf_counter_ns()
    try:
        candidates, work = service.human_knowledge.retrieve_with_work(signal, 5)
        elapsed = duration_ms(started)
        return {
            "duration_ms": elapsed,
            "status": "ok",
            "error": None,
            "abstention": work.abstention_reason,
            "candidate_count": len(candidates),
            "work": work.as_dict(),
            "warmup": warmup,
        }
    except Exception as error:
        return {
            "duration_ms": duration_ms(started),
            "status": "error",
            "error": {"type": type(error).__name__, "detail": "core retrieval failed"},
            "abstention": None,
            "candidate_count": None,
            "work": None,
            "warmup": warmup,
        }


def collect() -> dict[str, Any]:
    if os.getenv("PVR_T49_4_ALLOW_DISPOSABLE_DATABASE") != "1":
        raise RuntimeError("explicit HSP-4 disposable database authorization is required")
    database = os.environ["PVR_T49_4_EXPECTED_DATABASE"]
    token = os.environ["PVR_T49_4_OWNER_TOKEN"]
    bootstrap_url = os.environ["PVR_T49_4_BOOTSTRAP_DATABASE_URL"]
    reader_password = os.environ["PVR_T49_4_READER_PASSWORD"]
    file_profile = Path(os.environ["PVR_T49_4_FILE_PROFILE"])
    db_profile = Path(os.environ["PVR_T49_4_POSTGRES_PROFILE"])
    manifest_path = Path(os.environ["PVR_T49_4_RUN_MANIFEST"])
    manifest = json.loads(manifest_path.read_bytes())
    validate_inputs(manifest, manifest_path)
    if manifest["database"] != database or manifest["owner_token"] != token:
        raise ValueError("owned HSP-4 resources differ from freeze")
    repo = PostgresHumanKnowledgeSnapshotRepository.from_url(
        bootstrap_url, expected_database=database, allow_disposable_test=True
    )
    engine = repo.engine
    with engine.connect() as connection:
        repo._guard_database(connection)
        if (
            connection.execute(
                sa.text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_type='BASE TABLE'"
                )
            ).scalar_one()
            != 0
        ):
            raise ValueError("HSP-4 requires a fresh empty database")
        server = connection.execute(sa.text("SELECT version()")).scalar_one()
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("script_location", str(ROOT / "migrations"))
    config.set_main_option("sqlalchemy.url", bootstrap_url.replace("%", "%%"))
    command.upgrade(config, "0002")
    plan = check_bundle(ROOT / "reports/human-knowledge-snapshot-v1", ROOT)
    if repo.import_snapshot(plan, root=ROOT) != "inserted":
        raise ValueError("fresh HSP-4 snapshot import differs")
    reader, reader_url = create_reader(
        engine, database=database, token=token, password=reader_password
    )
    os.environ["PVR_HUMAN_STORAGE_TEST_DATABASE_URL"] = reader_url
    protocol = json.loads((ROOT / manifest["protocol"]["path"]).read_bytes())
    cost = protocol["cost"]
    startup = {
        "file": collect_startups(file_profile, cost["fresh_startup_samples_per_profile"]),
        "postgres": collect_startups(db_profile, cost["fresh_startup_samples_per_profile"]),
    }
    pack = json.loads((ROOT / manifest["development_pack"]["path"]).read_bytes())
    cases = pack["cases"]
    ports = {"file": 18101, "postgres": 18102}
    processes = {
        "file": subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__)),
                "--serve",
                str(file_profile),
                "--port",
                str(ports["file"]),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ),
        "postgres": subprocess.Popen(
            [
                sys.executable,
                str(Path(__file__)),
                "--serve",
                str(db_profile),
                "--port",
                str(ports["postgres"]),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        ),
    }
    bases = {name: f"http://127.0.0.1:{port}" for name, port in ports.items()}
    http_warmups: dict[str, list[dict[str, Any]]] = {"file": [], "postgres": []}
    http_rows: list[dict[str, Any]] = []
    try:
        for base in bases.values():
            wait_ready(base)
        with httpx.Client(timeout=30) as client:
            for name in ("file", "postgres"):
                for index in range(cost["warmups_before_http_per_profile"]):
                    http_warmups[name].append(
                        http_call(
                            client,
                            bases[name],
                            cases[0],
                            f"hsp4-http-warmup-{name}-{index}",
                            warmup=True,
                        )
                    )
            for index, case in enumerate(cases):
                order = ("file", "postgres") if index % 2 == 0 else ("postgres", "file")
                values = {}
                for name in order:
                    values[name] = http_call(
                        client, bases[name], case, f"hsp4-http-{index:03d}-{name}", warmup=False
                    )
                http_rows.append(
                    {
                        "case_id": case["case_id"],
                        "case_type": case["case_type"],
                        "order": list(order),
                        **values,
                    }
                )
    finally:
        for process in processes.values():
            process.terminate()
        for process in processes.values():
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
    file_service = build_service(
        settings(), profile_path=file_profile, root=ROOT, environ=environment()
    )
    db_service = build_service(
        settings(), profile_path=db_profile, root=ROOT, environ=environment()
    )
    services = {"file": file_service, "postgres": db_service}
    signals = [
        extract_signals(
            case["query_text"], file_service.color_vocabulary, file_service.series_vocabulary
        )
        for case in cases
    ]
    core_warmups: dict[str, list[dict[str, Any]]] = {"file": [], "postgres": []}
    for name in ("file", "postgres"):
        for _index in range(cost["warmups_before_core_per_profile"]):
            core_warmups[name].append(core_call(services[name], signals[0], warmup=True))
    core_rows = []
    for index, (case, signal) in enumerate(zip(cases, signals, strict=True)):
        order = ("file", "postgres") if index % 2 == 0 else ("postgres", "file")
        values = {name: core_call(services[name], signal, warmup=False) for name in order}
        core_rows.append(
            {
                "case_id": case["case_id"],
                "case_type": case["case_type"],
                "order": list(order),
                **values,
            }
        )
    with engine.connect() as connection:
        role_row = connection.execute(
            sa.text(
                "SELECT rolsuper,rolinherit,rolcreaterole,rolcreatedb,"
                "rolcanlogin FROM pg_roles WHERE rolname=:role"
            ),
            {"role": reader},
        ).one()
    engine.dispose()
    return {
        "schema_version": "pvr-human-storage-hsp4-runner-raw-v1",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "uid": os.geteuid(),
            "postgresql_server": server,
            "dependencies": {
                "sqlalchemy": sa.__version__,
                "alembic": alembic.__version__,
                "psycopg": psycopg.__version__,
                "uvicorn": uvicorn.__version__,
                "httpx": httpx.__version__,
            },
        },
        "measurement_contract": cost,
        "startup_samples": startup,
        "http_warmups": http_warmups,
        "http_samples": http_rows,
        "core_warmups": core_warmups,
        "core_samples": core_rows,
        "corpus": {"documents": 142, "provisional_variant": 100, "review_family": 42},
        "reader_role_attributes": dict(
            zip(
                ("rolsuper", "rolinherit", "rolcreaterole", "rolcreatedb", "rolcanlogin"),
                role_row,
                strict=True,
            )
        ),
        "timed_retries": 0,
        "old_final_105_used": False,
        "real_3000_claim": False,
        "serving_and_core_initialization_timed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--startup-worker", type=Path)
    parser.add_argument("--serve", type=Path)
    parser.add_argument("--port", type=int)
    args = parser.parse_args()
    if args.startup_worker:
        print(json.dumps(startup_worker(args.startup_worker), sort_keys=True))
        return 0
    if args.serve:
        if args.port is None:
            parser.error("--serve requires --port")
        serve(args.serve, args.port)
        return 0
    try:
        print(json.dumps(collect(), ensure_ascii=False, sort_keys=True, indent=2))
        return 0
    except Exception as error:
        print(
            json.dumps(
                {
                    "schema_version": "pvr-human-storage-hsp4-runner-raw-v1",
                    "runtime_error": {
                        "type": type(error).__name__,
                        "detail": "redacted collector failure",
                    },
                },
                sort_keys=True,
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
