#!/usr/bin/env python3
"""Collect unscored HSP-3 file/PostgreSQL correctness evidence inside its owned network."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import platform
import re
import shutil
import sys
from pathlib import Path
from typing import Any, Callable

import alembic
import psycopg
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from product_variant_resolver.api import create_app as create_default_app  # noqa: E402
from product_variant_resolver.catalog import load_catalog  # noqa: E402
from product_variant_resolver.config import Settings  # noqa: E402
from product_variant_resolver.human_knowledge_persistence import (  # noqa: E402
    PERSISTENCE_NAMESPACE,
    PostgresHumanKnowledgeSnapshotRepository,
)
from product_variant_resolver.human_knowledge_snapshot import (  # noqa: E402
    canonical_bytes,
    check_bundle,
    digest,
)
from product_variant_resolver.human_knowledge_storage_app import (  # noqa: E402
    HumanStorageResolverService,
)
from product_variant_resolver.human_knowledge_storage_app import (
    create_app as create_storage_app,
)
from product_variant_resolver.ingestion import ingest_catalog  # noqa: E402
from product_variant_resolver.postgres_ingestion import PostgresCatalogRepository  # noqa: E402

CANONICAL_ORDER = {
    "product_variant": "canonical_uuid",
    "product_alias": "id",
    "identifier": "id",
    "provenance_record": "id",
    "index_metadata": "index_name",
    "product_search": "canonical_uuid",
    "product_embedding": "canonical_uuid",
}
CANONICAL_FIELDS = (
    "status",
    "canonical_uuid",
    "canonical_id",
    "confidence",
    "reason",
    "product",
    "policy_version",
)


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def object_sha(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def table_snapshot(engine: Any, orders: dict[str, str]) -> dict[str, Any]:
    with engine.connect() as connection:
        return {
            table: [
                [str(value) for value in row]
                for row in connection.execute(
                    sa.text(f"SELECT * FROM public.{table} ORDER BY {order}")
                ).all()
            ]
            for table, order in orders.items()
        }


def settings(*, debug: bool = True) -> Settings:
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
        debug_enabled=debug,
        candidate_limit=25,
    )


def response_view(response: Any, *, debug: bool) -> dict[str, Any]:
    body = response.json()
    canonical = (
        {key: body[key] for key in CANONICAL_FIELDS} if response.status_code == 200 else body
    )
    value: dict[str, Any] = {
        "status": response.status_code,
        "request_id": response.headers.get("x-request-id"),
        "canonical_body": canonical,
    }
    if debug and response.status_code == 200:
        detail = body["debug"]
        value["human"] = {
            "candidates": detail["human_knowledge_candidates"],
            "work": detail.get("human_knowledge_identity_work"),
            "character_index": detail.get("human_knowledge_character_index"),
            "retrieval_artifact_version": detail.get("human_knowledge_retrieval_artifact_version"),
            "retrieval_artifact_sha256": detail.get("human_knowledge_retrieval_artifact_sha256"),
            "model_version": detail["model_versions"].get("human_knowledge"),
        }
    return value


def write_profile(payload: dict[str, Any], name: str) -> Path:
    path = Path("/tmp") / name
    path.write_text(json.dumps(payload, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    return path


def failure_observation(
    name: str, profile_path: Path, *, root: Path = ROOT, environ: dict[str, str] | None = None
) -> dict[str, Any]:
    app = create_storage_app(
        settings(), profile_path=profile_path, root=root, environ=environ or {}
    )
    client = TestClient(app)
    health = client.get("/health", headers={"x-request-id": "hsp3-failure-" + name})
    resolve = client.post(
        "/resolve", json={"title": "Chevy Nomad"}, headers={"x-request-id": "hsp3-failure-" + name}
    )
    return {
        "case": name,
        "health_status": health.status_code,
        "resolve_status": resolve.status_code,
        "resolve_body": resolve.json(),
    }


def role_name(token: str) -> str:
    value = "pvr_hsp3_reader_" + token
    if not re.fullmatch(r"[a-z0-9_]+", value):
        raise ValueError("unsafe generated role name")
    return value


def verify_write_denials(reader_url: str) -> list[dict[str, Any]]:
    statements = {
        "INSERT": "INSERT INTO public.hk_snapshot DEFAULT VALUES",
        "UPDATE": "UPDATE public.hk_snapshot SET document_count = document_count",
        "DELETE": "DELETE FROM public.hk_document",
        "TRUNCATE": "TRUNCATE public.hk_document",
    }
    reader_engine = sa.create_engine(reader_url, poolclass=sa.pool.NullPool)
    observations = []
    for operation, statement in statements.items():
        denied, sqlstate = False, None
        try:
            with reader_engine.begin() as connection:
                connection.execute(sa.text(statement))
        except sa.exc.DBAPIError as error:
            sqlstate = getattr(error.orig, "sqlstate", None)
            denied = sqlstate == "42501"
        observations.append({"operation": operation, "denied": denied, "sqlstate": sqlstate})
    reader_engine.dispose()
    return observations


def count_probes(app: Any, action: Callable[[], Any]) -> tuple[Any, int]:
    service = app.state.service
    if not isinstance(service, HumanStorageResolverService):
        raise ValueError("healthy storage service required")
    original = service.storage.probe
    calls = 0

    def counted() -> float:
        nonlocal calls
        calls += 1
        return original()

    service.storage.probe = counted
    try:
        return action(), calls
    finally:
        service.storage.probe = original


def poststartup_observation(
    name: str, app: Any, break_storage: Callable[[], None], restore_storage: Callable[[], None]
) -> dict[str, Any]:
    client = TestClient(app)
    break_storage()
    first = client.get("/health", headers={"x-request-id": "hsp3-post-" + name})
    restore_storage()
    later_health = client.get("/health")
    later_resolve = client.post("/resolve", json={"title": "Chevy Nomad"})
    return {
        "case": name,
        "first_status": first.status_code,
        "after_restore_health": later_health.status_code,
        "after_restore_resolve": later_resolve.status_code,
    }


def verify() -> dict[str, Any]:
    if os.getenv("PVR_T49_3_ALLOW_DISPOSABLE_DATABASE") != "1":
        raise RuntimeError("explicit HSP-3 disposable database authorization is required")
    database = os.environ["PVR_T49_3_EXPECTED_DATABASE"]
    bootstrap_url = os.environ["PVR_T49_3_BOOTSTRAP_DATABASE_URL"]
    token = os.environ["PVR_T49_3_OWNER_TOKEN"]
    reader_password = os.environ["PVR_T49_3_READER_PASSWORD"]
    file_profile_path = Path(os.environ["PVR_T49_3_FILE_PROFILE"])
    db_profile_path = Path(os.environ["PVR_T49_3_POSTGRES_PROFILE"])
    manifest_path = Path(os.environ["PVR_T49_3_RUN_MANIFEST"])
    manifest = json.loads(manifest_path.read_bytes())
    if manifest["owner_token"] != token or manifest["database"] != database:
        raise ValueError("runtime resources differ from pre-output freeze")
    for tag, expected in manifest["images"].items():
        actual = os.environ[
            "PVR_T49_3_DB_IMAGE_ID" if "pgvector" in tag else "PVR_T49_3_RUNNER_IMAGE_ID"
        ]
        if actual != expected:
            raise ValueError("runtime image differs from pre-output freeze")
    for name, expected in manifest["profiles"].items():
        if sha(manifest_path.parent / name) != expected:
            raise ValueError("runtime profile differs from pre-output freeze")
    admin = PostgresHumanKnowledgeSnapshotRepository.from_url(
        bootstrap_url, expected_database=database, allow_disposable_test=True
    )
    engine = admin.engine
    with engine.connect() as connection:
        admin._guard_database(connection)
        if (
            connection.execute(
                sa.text(
                    "SELECT count(*) FROM information_schema.tables "
                    "WHERE table_schema='public' AND table_type='BASE TABLE'"
                )
            ).scalar_one()
            != 0
        ):
            raise ValueError("HSP-3 requires a genuinely empty disposable database")
        server = connection.execute(sa.text("SELECT version()")).scalar_one()
    configuration = Config(str(ROOT / "alembic.ini"))
    configuration.set_main_option("script_location", str(ROOT / "migrations"))
    configuration.set_main_option("sqlalchemy.url", bootstrap_url.replace("%", "%%"))
    if os.getenv("PVR_DATABASE_URL"):
        raise ValueError("production/default database URL is forbidden")
    command.upgrade(configuration, "0001")
    ingest_catalog(load_catalog(ROOT / "data/catalog.json"), PostgresCatalogRepository(engine))
    canonical_before = table_snapshot(engine, CANONICAL_ORDER)
    if len(canonical_before["product_variant"]) != 120:
        raise ValueError("canonical fixture baseline differs")
    command.upgrade(configuration, "0002")
    plan = check_bundle(ROOT / "reports/human-knowledge-snapshot-v1", ROOT)
    if admin.import_snapshot(plan, root=ROOT) != "inserted":
        raise ValueError("new database did not receive the exact snapshot once")
    reader = role_name(token)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                f"CREATE ROLE {reader} LOGIN PASSWORD :password "
                "NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT"
            ),
            {"password": reader_password},
        )
        connection.execute(sa.text(f"GRANT CONNECT ON DATABASE {database} TO {reader}"))
        connection.execute(sa.text(f"GRANT USAGE ON SCHEMA public TO {reader}"))
        connection.execute(
            sa.text(f"GRANT SELECT ON public.hk_snapshot, public.hk_document TO {reader}")
        )
    reader_url = f"postgresql+psycopg://{reader}:{reader_password}@postgres:5432/{database}"
    runtime_environment = {"PVR_HUMAN_STORAGE_TEST_DATABASE_URL": reader_url}
    with engine.connect() as connection:
        attributes_row = connection.execute(
            sa.text(
                "SELECT rolsuper, rolinherit, rolcreaterole, "
                "rolcreatedb, rolcanlogin FROM pg_roles WHERE rolname=:role"
            ),
            {"role": reader},
        ).one()
        privilege_rows = connection.execute(
            sa.text(
                "SELECT table_name, privilege_type FROM "
                "information_schema.role_table_grants WHERE grantee=:role AND table_schema='public' "
                "ORDER BY table_name, privilege_type"
            ),
            {"role": reader},
        ).all()
    attributes = dict(
        zip(
            ("rolsuper", "rolinherit", "rolcreaterole", "rolcreatedb", "rolcanlogin"),
            attributes_row,
            strict=True,
        )
    )
    table_privileges: dict[str, list[str]] = {}
    for table, privilege in privilege_rows:
        table_privileges.setdefault(table, []).append(privilege)
    write_denials = verify_write_denials(reader_url)

    file_client = TestClient(
        create_storage_app(settings(), profile_path=file_profile_path, root=ROOT, environ={})
    )
    db_client = TestClient(
        create_storage_app(
            settings(), profile_path=db_profile_path, root=ROOT, environ=runtime_environment
        )
    )
    default_client = TestClient(create_default_app(settings()))
    pack = json.loads((ROOT / manifest["development_pack"]["path"]).read_bytes())
    cases = pack["cases"]
    correctness_rows = []
    for index, case in enumerate(cases):
        request_id = "hsp3-%03d-%s" % (
            index,
            hashlib.sha256(case["case_id"].encode()).hexdigest()[:12],
        )
        headers = {"x-request-id": request_id}

        def call(client: TestClient) -> tuple[int, dict[str, Any]]:
            health = client.get("/health", headers=headers)
            response = client.post(
                "/resolve",
                headers=headers,
                json={"title": case["query_text"], "debug": True, "debug_candidate_limit": 5},
            )
            return health.status_code, response_view(response, debug=True)

        if index % 2 == 0:
            file_health, file_value = call(file_client)
            db_health, db_value = call(db_client)
        else:
            db_health, db_value = call(db_client)
            file_health, file_value = call(file_client)
        default_response = default_client.post(
            "/resolve", headers=headers, json={"title": case["query_text"]}
        )
        default_value = response_view(default_response, debug=False)
        correctness_rows.append(
            {
                "case_id": case["case_id"],
                "case_type": case["case_type"],
                "query_text": case["query_text"],
                "request_id": request_id,
                "execution_order": ["file", "postgres"] if index % 2 == 0 else ["postgres", "file"],
                "file_health_status": file_health,
                "postgres_health_status": db_health,
                "file": file_value,
                "postgres": db_value,
                "default": default_value,
            }
        )

    file_payload = json.loads(file_profile_path.read_bytes())
    db_payload = json.loads(db_profile_path.read_bytes())
    startup_failures = []
    startup_failures.append(
        failure_observation("missing_profile", Path("/tmp/does-not-exist.json"))
    )
    malformed = Path("/tmp/hsp3-malformed.json")
    malformed.write_text("{", encoding="utf-8")
    startup_failures.append(failure_observation("malformed_profile", malformed))
    stale = copy.deepcopy(file_payload)
    stale["source_sha256"]["src/product_variant_resolver/api.py"] = "0" * 64
    stale["actual_adapter_source_manifest_sha256"] = object_sha(stale["source_sha256"])
    startup_failures.append(
        failure_observation(
            "stale_profile_source_hash", write_profile(stale, "hsp3-stale-profile.json")
        )
    )
    invalid_file = copy.deepcopy(file_payload)
    invalid_file["snapshot"]["documents"] = 141
    startup_failures.append(
        failure_observation(
            "file_plan_invalid", write_profile(invalid_file, "hsp3-invalid-file-profile.json")
        )
    )
    unavailable = f"postgresql+psycopg://missing:missing@127.0.0.1:1/{database}?connect_timeout=1"
    startup_failures.append(
        failure_observation(
            "db_unavailable",
            db_profile_path,
            environ={"PVR_HUMAN_STORAGE_TEST_DATABASE_URL": unavailable},
        )
    )
    mismatch = copy.deepcopy(db_payload)
    mismatch["database"]["expected_database"] = "pvr_t49_2_000000000000"
    startup_failures.append(
        failure_observation(
            "db_name_mismatch",
            write_profile(mismatch, "hsp3-db-mismatch.json"),
            environ=runtime_environment,
        )
    )

    with engine.begin() as connection:
        connection.execute(
            sa.text("DELETE FROM public.hk_snapshot WHERE snapshot_id=:id"),
            {"id": plan["snapshot_id"]},
        )
    startup_failures.append(
        failure_observation("db_snapshot_missing", db_profile_path, environ=runtime_environment)
    )
    admin.import_snapshot(plan, root=ROOT)
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "UPDATE public.hk_snapshot SET persistence_namespace='wrong' WHERE snapshot_id=:id"
            ),
            {"id": plan["snapshot_id"]},
        )
    startup_failures.append(
        failure_observation("db_namespace_mismatch", db_profile_path, environ=runtime_environment)
    )
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "UPDATE public.hk_snapshot SET persistence_namespace=:value WHERE snapshot_id=:id"
            ),
            {"value": PERSISTENCE_NAMESPACE, "id": plan["snapshot_id"]},
        )
        connection.execute(
            sa.text("DELETE FROM public.hk_document WHERE snapshot_id=:id AND ordinal=141"),
            {"id": plan["snapshot_id"]},
        )
    startup_failures.append(
        failure_observation("db_children_partial", db_profile_path, environ=runtime_environment)
    )
    with engine.begin() as connection:
        admin._insert_document(connection, plan["snapshot_id"], 141, plan["documents"][141])
        connection.execute(
            sa.text(f"REVOKE SELECT ON public.hk_snapshot, public.hk_document FROM {reader}")
        )
    startup_failures.append(
        failure_observation(
            "db_reader_select_permission_missing", db_profile_path, environ=runtime_environment
        )
    )
    with engine.begin() as connection:
        connection.execute(
            sa.text(f"GRANT SELECT ON public.hk_snapshot, public.hk_document TO {reader}")
        )

    poststartup_failures = []
    disconnected_app = create_storage_app(
        settings(), profile_path=db_profile_path, root=ROOT, environ=runtime_environment
    )
    poststartup_failures.append(
        poststartup_observation(
            "db_disconnected",
            disconnected_app,
            lambda: _alter_password(engine, reader, "temporarilywrong"),
            lambda: _alter_password(engine, reader, reader_password),
        )
    )
    header = {key: value for key, value in plan.items() if key != "documents"}
    corrupt_header = copy.deepcopy(header)
    corrupt_header["counts"]["postgresql_writes"] = False
    header_app = create_storage_app(
        settings(), profile_path=db_profile_path, root=ROOT, environ=runtime_environment
    )
    poststartup_failures.append(
        poststartup_observation(
            "db_header_corrupted",
            header_app,
            lambda: _replace_header(engine, plan["snapshot_id"], corrupt_header),
            lambda: _replace_header(engine, plan["snapshot_id"], header),
        )
    )
    child_app = create_storage_app(
        settings(), profile_path=db_profile_path, root=ROOT, environ=runtime_environment
    )
    poststartup_failures.append(
        poststartup_observation(
            "db_child_deleted",
            child_app,
            lambda: _delete_child(engine, plan["snapshot_id"]),
            lambda: _restore_child(engine, admin, plan),
        )
    )
    mutable_root = Path("/tmp/hsp3-file-root")
    for relative in file_payload["source_sha256"]:
        target = mutable_root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    mutable_profile = write_profile(file_payload, "hsp3-mutable-file-profile.json")
    mutable_app = create_storage_app(
        Settings(), profile_path=mutable_profile, root=mutable_root, environ={}
    )
    plan_path = mutable_root / file_payload["snapshot"]["plan_file"]
    original_plan = plan_path.read_bytes()
    poststartup_failures.append(
        poststartup_observation(
            "file_plan_or_source_changed",
            mutable_app,
            lambda: plan_path.write_bytes(original_plan + b"\n"),
            lambda: plan_path.write_bytes(original_plan),
        )
    )

    invalid_app = create_storage_app(
        settings(), profile_path=db_profile_path, root=ROOT, environ=runtime_environment
    )
    invalid_client = TestClient(invalid_app)
    invalid_calls = [
        (
            "malformed_json",
            lambda: invalid_client.post(
                "/resolve", content=b"{", headers={"content-type": "application/json"}
            ),
        ),
        (
            "wrong_content_type",
            lambda: invalid_client.post(
                "/resolve", content=b"{}", headers={"content-type": "text/plain"}
            ),
        ),
        ("blank_title", lambda: invalid_client.post("/resolve", json={"title": "   "})),
        ("title_501", lambda: invalid_client.post("/resolve", json={"title": "x" * 501})),
    ]
    invalid_http = []
    for name, action in invalid_calls:
        response, probes = count_probes(invalid_app, action)
        invalid_http.append(
            {"case": name, "status": response.status_code, "storage_probes": probes}
        )
    disabled_app = create_storage_app(
        settings(debug=False), profile_path=db_profile_path, root=ROOT, environ=runtime_environment
    )
    disabled_client = TestClient(disabled_app)
    response, probes = count_probes(
        disabled_app,
        lambda: disabled_client.post("/resolve", json={"title": "Chevy Nomad", "debug": True}),
    )
    invalid_http.append(
        {"case": "debug_disabled", "status": response.status_code, "storage_probes": probes}
    )

    canonical_after = table_snapshot(engine, CANONICAL_ORDER)
    engine.dispose()
    return {
        "schema_version": "pvr-human-storage-hsp3-runner-raw-v1",
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "uid": os.geteuid(),
            "postgresql_server": server,
            "dependencies": {
                "sqlalchemy": sa.__version__,
                "alembic": alembic.__version__,
                "psycopg": psycopg.__version__,
            },
        },
        "database": database,
        "snapshot_id": plan["snapshot_id"],
        "snapshot_content_sha256": plan["content_sha256"],
        "reader_role": {
            "attributes": attributes,
            "table_privileges": table_privileges,
            "write_denials": write_denials,
        },
        "correctness_rows": correctness_rows,
        "startup_failures": startup_failures,
        "poststartup_failures": poststartup_failures,
        "invalid_http": invalid_http,
        "canonical_before_sha256": digest(canonical_before),
        "canonical_after_sha256": digest(canonical_after),
        "source_and_image_binding": True,
        "retries": 0,
        "parameter_search": False,
        "old_final_105_used": False,
    }


def _alter_password(engine: Any, role: str, password: str) -> None:
    with engine.begin() as connection:
        connection.execute(sa.text(f"ALTER ROLE {role} PASSWORD :password"), {"password": password})


def _replace_header(engine: Any, snapshot_id: str, header: dict[str, Any]) -> None:
    with engine.begin() as connection:
        connection.execute(
            sa.text(
                "UPDATE public.hk_snapshot SET plan_header=CAST(:header AS jsonb) "
                "WHERE snapshot_id=:id"
            ),
            {"header": json.dumps(header, ensure_ascii=False), "id": snapshot_id},
        )


def _delete_child(engine: Any, snapshot_id: str) -> None:
    with engine.begin() as connection:
        connection.execute(
            sa.text("DELETE FROM public.hk_document WHERE snapshot_id=:id AND ordinal=141"),
            {"id": snapshot_id},
        )


def _restore_child(
    engine: Any, repository: PostgresHumanKnowledgeSnapshotRepository, plan: dict[str, Any]
) -> None:
    with engine.begin() as connection:
        repository._insert_document(connection, plan["snapshot_id"], 141, plan["documents"][141])


if __name__ == "__main__":
    try:
        print(json.dumps(verify(), ensure_ascii=False, sort_keys=True, indent=2))
    except Exception as error:
        print(
            json.dumps(
                {
                    "schema_version": "pvr-human-storage-hsp3-runner-raw-v1",
                    "runtime_error": f"{type(error).__name__}: {error}",
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
        raise
