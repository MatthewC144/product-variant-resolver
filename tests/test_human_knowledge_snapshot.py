from __future__ import annotations

import copy
import hashlib
import json
import shutil
import socket
import subprocess
import sys
from pathlib import Path

import pytest

from product_variant_resolver.human_knowledge import load_human_knowledge_catalog
from product_variant_resolver.human_knowledge_snapshot import (
    SOURCE_HASHES,
    build_plan,
    check_bundle,
    decode_document,
    digest,
    load_object,
    publish_bundle,
    render_report,
    validate_plan,
)

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def local_root(tmp_path: Path) -> Path:
    for relative in SOURCE_HASHES:
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / relative, target)
    (tmp_path / "reports").mkdir()
    return tmp_path


def test_exact_typed_roundtrip_and_source_boundaries(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("network/subprocess is forbidden")

    monkeypatch.setattr(socket, "socket", forbidden)
    monkeypatch.setattr(subprocess, "run", forbidden)
    plan = build_plan(ROOT)
    assert plan == build_plan(ROOT)
    assert plan["counts"]["documents"] == 142
    assert plan["counts"]["postgresql_writes"] == plan["counts"]["new_canonical_uuids"] == 0
    catalog = load_human_knowledge_catalog(ROOT / "data/human_backed_catalog.json",
        ROOT / "data/review_family_knowledge.json", ROOT / "data/review_family_knowledge_manifest.json")
    restored = [decode_document(entry) for entry in plan["documents"]]
    assert restored == sorted(catalog.documents, key=lambda d: (d.knowledge_type, d.knowledge_id))
    assert len({d.knowledge_uuid for d in restored}) == 142
    assert len({d.knowledge_id for d in restored}) == 142
    assert sum(d.knowledge_type == "provisional_variant" for d in restored) == 100
    assert sum(d.knowledge_type == "review_family" for d in restored) == 42
    assert "postgresql_ingestion" in plan["source_contracts"]["family"]["excluded_from"]
    assert all("raw_variant" in d["origin"] or "registry_entry" in d["origin"]
               for d in plan["documents"])


def test_plan_reads_only_the_twelve_declared_inputs(monkeypatch: pytest.MonkeyPatch) -> None:
    original = Path.open
    allowed = {ROOT / relative for relative in SOURCE_HASHES}
    seen: set[Path] = set()

    def guarded(path: Path, *args: object, **kwargs: object):  # type: ignore[no-untyped-def]
        assert path in allowed, f"unexpected input/output, including final queries: {path}"
        seen.add(path)
        return original(path, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "open", guarded)
    build_plan(ROOT)
    assert seen == allowed


@pytest.mark.parametrize("relative", list(SOURCE_HASHES))
def test_every_source_pin_rejects_changed_bytes(local_root: Path, relative: str) -> None:
    path = local_root / relative
    path.write_bytes(path.read_bytes() + b"\n")
    output = local_root / "reports/rejected"
    with pytest.raises(ValueError, match="checksum mismatch"):
        publish_bundle(output, local_root)
    assert not output.exists()


def test_missing_input_rejects_before_output(local_root: Path) -> None:
    (local_root / "data/human_labeled_names.json").unlink()
    with pytest.raises(ValueError, match="missing source"):
        publish_bundle(local_root / "reports/missing", local_root)
    assert list((local_root / "reports").iterdir()) == []


@pytest.mark.parametrize("mutation", ["partial", "duplicate", "held", "wrong_type", "uuid",
                                     "payload", "origin", "count", "extra", "order", "boundary"])
def test_rehashed_invalid_plan_rejected(mutation: str) -> None:
    plan = copy.deepcopy(build_plan(ROOT))
    documents = plan["documents"]
    if mutation == "partial":
        documents.pop()
    elif mutation == "duplicate":
        documents[-1] = copy.deepcopy(documents[0])
    elif mutation == "held":
        documents[-1]["knowledge_id"] = "fandom-family-089ff8645b5f2de7"
    elif mutation == "wrong_type":
        documents[0]["knowledge_type"] = "canonical_variant"
    elif mutation == "uuid":
        documents[0]["knowledge_uuid"] = "00000000-0000-0000-0000-000000000000"
    elif mutation == "payload":
        documents[0]["payload"]["casting"] = "tampered casting"
        documents[0]["payload_sha256"] = digest(documents[0]["payload"])
    elif mutation == "origin":
        documents[0]["origin"] = {"file": "unapproved.json"}
    elif mutation == "count":
        plan["counts"]["postgresql_writes"] = False  # False == 0 in Python, but not in JSON
    elif mutation == "extra":
        plan["activated"] = True
    elif mutation == "order":
        documents.reverse()
    else:
        plan["source_contracts"]["family"]["excluded_from"].remove("postgresql_ingestion")
    body = {k: v for k, v in plan.items() if k not in {"content_sha256", "snapshot_id"}}
    plan["content_sha256"] = digest(body)
    plan["snapshot_id"] = "human-knowledge-plan-v1-" + plan["content_sha256"]
    with pytest.raises(ValueError, match="complete pinned"):
        validate_plan(plan, ROOT)


def test_publication_check_and_repeat_preserves_bytes(local_root: Path) -> None:
    output = local_root / "reports/snapshot"
    plan = publish_bundle(output, local_root)
    before = {p.name: p.read_bytes() for p in output.iterdir()}
    assert check_bundle(output, local_root) == plan
    assert render_report(plan).encode() == before["report.md"]
    with pytest.raises(FileExistsError):
        publish_bundle(output, local_root)
    assert before == {p.name: p.read_bytes() for p in output.iterdir()}


@pytest.mark.parametrize("member", ["plan.json", "report.md"])
def test_bundle_tamper_detected(local_root: Path, member: str) -> None:
    output = local_root / "reports/snapshot"
    publish_bundle(output, local_root)
    path = output / member
    path.write_bytes(b"{}" if member == "plan.json" else b"wrong report")
    with pytest.raises(ValueError):
        check_bundle(output, local_root)


def test_incomplete_bundle_is_not_complete_or_overwritable(local_root: Path) -> None:
    output = local_root / "reports/interrupted"
    output.mkdir()
    with pytest.raises(ValueError, match="exactly"):
        check_bundle(output, local_root)
    with pytest.raises(FileExistsError):
        publish_bundle(output, local_root)


def test_failed_publication_cleans_only_new_owned_files(
    local_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*args: object) -> None:
        raise ValueError("simulated verification failure")

    monkeypatch.setattr("product_variant_resolver.human_knowledge_snapshot.check_bundle", fail)
    output = local_root / "reports/failed"
    with pytest.raises(ValueError, match="simulated"):
        publish_bundle(output, local_root)
    assert not output.exists()


def test_failure_never_recursively_removes_unowned_files(
    local_root: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(directory: Path, root: Path) -> None:
        (directory / "unowned.txt").write_text("preserve me")
        raise ValueError("simulated concurrent file")

    monkeypatch.setattr("product_variant_resolver.human_knowledge_snapshot.check_bundle", fail)
    output = local_root / "reports/failed"
    with pytest.raises(ValueError, match="concurrent"):
        publish_bundle(output, local_root)
    assert {p.name for p in output.iterdir()} == {"unowned.txt"}
    assert (output / "unowned.txt").read_text() == "preserve me"


def test_source_and_output_symlinks_rejected(local_root: Path) -> None:
    source = local_root / "data/human_labeled_names.json"
    original = source.read_bytes()
    private = local_root / "private.json"
    private.write_bytes(original)
    source.unlink()
    source.symlink_to(private)
    with pytest.raises(ValueError, match="symlink source"):
        build_plan(local_root)
    source.unlink()
    source.write_bytes(original)
    output = local_root / "reports/link"
    output.symlink_to(local_root / "private-output", target_is_directory=True)
    with pytest.raises(ValueError, match="symlink output"):
        publish_bundle(output, local_root)
    assert not (local_root / "private-output").exists()


def test_output_outside_reports_rejected(local_root: Path) -> None:
    with pytest.raises(ValueError, match="direct child"):
        publish_bundle(local_root / "outside", local_root)
    assert not (local_root / "outside").exists()


def test_duplicate_json_keys_rejected(tmp_path: Path) -> None:
    path = tmp_path / "invalid.json"
    path.write_text('{"documents": [], "documents": []}')
    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_object(path)


def test_cli_check_uses_only_local_pins(local_root: Path) -> None:
    output = local_root / "reports/snapshot"
    publish_bundle(output, local_root)
    result = subprocess.run([sys.executable, str(ROOT / "scripts/plan_human_knowledge_snapshot.py"),
        "--check", "--output", str(output)], capture_output=True, text=True, check=False)
    assert result.returncode == 0, result.stderr
    assert "PASS local PLAN: 100 provisional + 42 family" in result.stdout
    assert "final" not in result.stdout


def test_existing_rehashed_source_manifest_does_not_grant_trust(local_root: Path) -> None:
    source = local_root / "data/human_backed_catalog.json"
    source.write_bytes(source.read_bytes() + b"\n")
    manifest_path = local_root / "data/human_backed_catalog_manifest.json"
    manifest = json.loads(manifest_path.read_bytes())
    manifest["catalog_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="checksum mismatch"):
        build_plan(local_root)
