from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

import product_variant_resolver.canonical_catalog_application as application_module
import product_variant_resolver.canonical_catalog_decisions as decision_module
from product_variant_resolver.canonical_authority_packet import derive_workspace
from product_variant_resolver.canonical_authority_review import (
    AuthorityContractError,
    content_sha256,
    stable_json_bytes,
)
from product_variant_resolver.canonical_catalog_application import (
    PRIVATE_EVENT_REFERENCE,
    PUBLIC_MANIFEST_REFERENCE,
    TRANSACTION_DIRECTORY_REFERENCE,
    TRANSACTION_JOURNAL_REFERENCE,
    _build_catalog,
    _build_event,
    _build_public_manifest,
    _catalog_row,
    _parent_catalog_payload,
    _read_json,
    _record_bindings,
    _validate_collisions,
    _validate_complete_ledger,
    apply_catalog_application,
    check_catalog_application,
    recover_catalog_application,
)
from product_variant_resolver.canonical_catalog_decisions import (
    PUBLIC_METHOD_REFERENCE,
    PUBLIC_PROGRESS_REFERENCE,
    CatalogDecisionLedger,
    ProgressCommitment,
    PublicCatalogDecisionProgress,
)
from product_variant_resolver.catalog import load_catalog

ROOT = Path(__file__).resolve().parents[2]
OWNER_RESPONSE = "Apply exactly the approved 20-record catalog namespace batch."
AUTHORIZED_AT = datetime(2026, 9, 30, 16, 0, tzinfo=UTC)

COPY_PATHS = (
    ".gitignore",
    "data/catalog.json",
    "data/manifest.json",
    "data/authority-review/canonical-authority-review-v1/candidate-plan.json",
    "data/authority-review/canonical-authority-review-v1/catalog-proposal-manifest.json",
    "data/authority-review/canonical-authority-review-v1/source-decisions.json",
    "data/authority-review/canonical-authority-review-v1/source-decisions-manifest.json",
    "data/external/hot-wheels-wiki/pilot-2025/normalized.json",
    "data/external/hot-wheels-wiki/pilot-2025/manifest.json",
    "specs/canonical-authority-review-v1/design.md",
    "specs/canonical-authority-review-v1/requirements.md",
    "specs/canonical-authority-review-v1/source-approval.md",
    "specs/canonical-authority-review-v1/tasks.md",
    "specs/canonical-authority-review-v1/catalog-proposal-review.md",
    "data/authority-review/canonical-authority-review-v1/catalog-proposal-review-progress.json",
)


@pytest.fixture
def isolated_root(tmp_path: Path) -> Path:
    for reference in COPY_PATHS:
        source = ROOT / reference
        target = tmp_path / reference
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
    local = Path("data/authority-review/canonical-authority-review-v1/local-catalog-review-v1")
    shutil.copytree(ROOT / local, tmp_path / local)
    (tmp_path / ".git").write_text(f"gitdir: {ROOT / '.git'}\n", encoding="utf-8")
    return tmp_path


def _load(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _write(path: Path, payload: dict[str, Any]) -> None:
    path.write_bytes(stable_json_bytes(payload))


def _apply(root: Path) -> tuple[str, Any]:
    return apply_catalog_application(
        root,
        owner_response_verbatim=OWNER_RESPONSE,
        authorized_exact_owner_response=OWNER_RESPONSE,
        authorized_at=AUTHORIZED_AT,
    )


def test_applies_catalog_v2_in_packet_order_and_replay_is_unchanged(
    isolated_root: Path,
) -> None:
    catalog_path = isolated_root / "data/catalog.json"
    parent = _load(catalog_path)
    parent_rows = copy.deepcopy(parent["products"])
    parent_hashes = [content_sha256(row) for row in parent_rows]
    protected = {
        path: path.read_bytes()
        for path in (
            isolated_root
            / "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1/catalog-proposals.json",
            isolated_root
            / "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1/catalog-proposal-review-packet.json",
            isolated_root
            / "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1/catalog-decision-ledger.json",
        )
    }

    status, manifest = _apply(isolated_root)

    assert status == "created"
    assert manifest.catalog_record_applied_count == 20
    assert manifest.catalog_product_count == 140
    assert manifest.synthetic_product_count == 120
    assert manifest.nonsynthetic_product_count == 20
    assert manifest.exact_authority_count == 0
    assert manifest.rhb_t5_authorized is False
    assert manifest.child_catalog_version == "catalog-v2"
    catalog = _load(catalog_path)
    assert catalog["catalog_version"] == "catalog-v2"
    assert catalog["dataset_version"] == "fixture-v1"
    assert len(catalog["products"]) == 140
    assert [content_sha256(row) for row in catalog["products"][:120]] == parent_hashes
    packet = _load(
        isolated_root
        / "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1/catalog-proposal-review-packet.json"
    )
    appended = catalog["products"][120:]
    assert [row["canonical_uuid"] for row in appended] == [
        entry["proposal"]["proposed_canonical_uuid"] for entry in packet["entries"]
    ]
    assert all(row["color"] is None and row["edition"] is None for row in appended)
    assert all(row["aliases"] == [] and row["rarity_tier"] is None for row in appended)
    assert all(row["release_key"].startswith("release-2025-") for row in appended)
    assert all(row["identifiers"][0]["identifier_type"] == "toy_number" for row in appended)
    assert all("CC-BY-SA" in row["provenance"][0]["license_note"] for row in appended)
    assert all("not exact authority" in row["provenance"][0]["confidence_note"] for row in appended)
    runtime = load_catalog(catalog_path)
    assert len(runtime.products) == 140
    assert len(runtime.by_release_key) == 20
    assert runtime.by_release_key["release-2025-hyx45"].identifiers == ("HYX45",)
    data_manifest = _load(isolated_root / "data/manifest.json")
    assert data_manifest["product_count"] == 140
    assert data_manifest["catalog_version"] == "catalog-v2"
    assert data_manifest["parent_product_count"] == 120
    assert data_manifest["parent_catalog_version"] == "fixture-v1"
    assert data_manifest["catalog_sha256"] == manifest.output_catalog_sha256
    public_text = (isolated_root / PUBLIC_MANIFEST_REFERENCE).read_text(encoding="utf-8")
    assert OWNER_RESPONSE not in public_text
    assert "car-t3-" not in public_text
    assert "Mazda Autozam" not in public_text
    assert "CC-BY-SA" in public_text
    assert all(path.read_bytes() == raw for path, raw in protected.items())

    before_check = {
        path: path.read_bytes()
        for path in (
            catalog_path,
            isolated_root / "data/manifest.json",
            isolated_root / PRIVATE_EVENT_REFERENCE,
            isolated_root / PUBLIC_MANIFEST_REFERENCE,
        )
    }
    assert (
        check_catalog_application(isolated_root, expected_owner_response=OWNER_RESPONSE) == manifest
    )
    assert derive_workspace(isolated_root).review_packet == derive_workspace(ROOT).review_packet
    assert all(path.read_bytes() == raw for path, raw in before_check.items())
    replay_status, replay_manifest = _apply(isolated_root)
    assert replay_status == "unchanged"
    assert replay_manifest == manifest
    assert all(path.read_bytes() == raw for path, raw in before_check.items())


def test_requires_exact_external_authorization_and_leaves_parent_unchanged(
    isolated_root: Path,
) -> None:
    before = {
        path: path.read_bytes()
        for path in (isolated_root / "data/catalog.json", isolated_root / "data/manifest.json")
    }
    with pytest.raises(AuthorityContractError, match="exact external"):
        apply_catalog_application(
            isolated_root,
            owner_response_verbatim=OWNER_RESPONSE,
            authorized_exact_owner_response="Paraphrased authorization.",
            authorized_at=AUTHORIZED_AT,
        )
    assert all(path.read_bytes() == raw for path, raw in before.items())
    assert not (isolated_root / PRIVATE_EVENT_REFERENCE).exists()
    assert not (isolated_root / PUBLIC_MANIFEST_REFERENCE).exists()


@pytest.mark.parametrize(
    "mutation",
    [
        lambda ledger: ledger["events"].pop(),
        lambda ledger: ledger["events"][-1].update({"decision": "hold"}),
        lambda ledger: ledger["events"][-1].update({"decision": "reject"}),
        lambda ledger: ledger["events"].reverse(),
    ],
)
def test_rejects_partial_nonapproval_or_reordered_decision_ledger(
    isolated_root: Path, mutation: Any
) -> None:
    ledger_path = isolated_root / PRIVATE_EVENT_REFERENCE.parent / "catalog-decision-ledger.json"
    ledger = _load(ledger_path)
    mutation(ledger)
    _write(ledger_path, ledger)
    with pytest.raises((AuthorityContractError, ValueError)):
        _apply(isolated_root)
    assert _load(isolated_root / "data/manifest.json")["product_count"] == 120


@pytest.mark.parametrize(
    "mutation",
    [
        lambda packet: packet["entries"].reverse(),
        lambda packet: packet["entries"].pop(),
        lambda packet: packet["entries"][0]["proposal"]["proposed_product_record"].update(
            {"color": "Blue"}
        ),
        lambda packet: packet["entries"][0]["proposal"]["proposed_product_record"].update(
            {"edition": "Zamac"}
        ),
    ],
)
def test_rejects_reordered_missing_or_inferred_proposal_fields(
    isolated_root: Path, mutation: Any
) -> None:
    packet_path = (
        isolated_root
        / "data/authority-review/canonical-authority-review-v1/local-catalog-review-v1/catalog-proposal-review-packet.json"
    )
    packet = _load(packet_path)
    mutation(packet)
    _write(packet_path, packet)
    with pytest.raises((AuthorityContractError, ValueError)):
        _apply(isolated_root)
    assert len(_load(isolated_root / "data/catalog.json")["products"]) == 120


def test_collision_checks_cover_uuid_id_release_identifier_and_parent_natural_key(
    isolated_root: Path,
) -> None:
    artifacts, _, ledger = _validate_complete_ledger(isolated_root)
    parent_payload, _ = _read_json(isolated_root / "data/catalog.json")
    parent = _parent_catalog_payload(parent_payload)
    output, _ = _build_catalog(parent, artifacts)
    parent_rows = output["products"][:120]
    appended = output["products"][120:]
    mutations: list[list[dict[str, Any]]] = []
    for field in ("canonical_uuid", "canonical_id"):
        rows = copy.deepcopy(appended)
        rows[1][field] = rows[0][field]
        mutations.append(rows)
    release = copy.deepcopy(appended)
    release[1]["release_key"] = release[0]["release_key"]
    mutations.append(release)
    identifier = copy.deepcopy(appended)
    identifier[1]["identifiers"][0]["identifier_value"] = identifier[0]["identifiers"][0][
        "identifier_value"
    ]
    mutations.append(identifier)
    parent_natural = copy.deepcopy(appended)
    for field in (
        "brand",
        "casting",
        "release_year",
        "series",
        "color",
        "collector_number",
        "edition",
    ):
        parent_natural[0][field] = parent_rows[0][field]
    mutations.append(parent_natural)
    for rows in mutations:
        with pytest.raises(AuthorityContractError, match="colli"):
            _validate_collisions(parent_rows, rows)

    entry = artifacts.review_packet.entries[0]
    wrong_candidate = entry.candidate.model_copy(update={"proposed_release_key": "release-other"})
    with pytest.raises(AuthorityContractError, match="family or release"):
        _catalog_row(entry.model_copy(update={"candidate": wrong_candidate}))
    assert len(ledger.events) == 20


def test_synchronized_private_quote_rewrite_still_fails_external_check(
    isolated_root: Path,
) -> None:
    _apply(isolated_root)
    artifacts, packet_sha, ledger = _validate_complete_ledger(isolated_root)
    event_payload = _load(isolated_root / PRIVATE_EVENT_REFERENCE)
    event = application_module.CatalogApplicationAuthorizationEvent.model_validate(event_payload)
    catalog = _load(isolated_root / "data/catalog.json")
    bindings = _record_bindings(artifacts, ledger, catalog)
    paraphrase = "Apply the catalog batch, please."
    rewritten = _build_event(
        owner_response=paraphrase,
        authorized_exact_owner_response=paraphrase,
        authorized_at=event.authorized_at,
        packet_sha256=packet_sha,
        proposal_bundle_sha256=event.proposal_bundle_sha256,
        ledger_sha256=ledger.ledger_sha256,
        cumulative_decision_events_sha256=ledger.cumulative_events_sha256,
        decision_event_head_sha256=ledger.events[-1].event_sha256,
        ordered_record_bindings=bindings,
        output_catalog_sha256=event.planned_child_catalog_sha256,
        output_data_manifest_sha256=event.output_data_manifest_sha256,
    )
    public = _build_public_manifest(
        rewritten,
        parent_ordered_product_sha256=_load(isolated_root / "data/catalog.json")["catalog_lineage"][
            "parent_ordered_product_sha256"
        ],
    )
    (isolated_root / PRIVATE_EVENT_REFERENCE).write_bytes(
        stable_json_bytes(rewritten.model_dump(mode="json"))
    )
    (isolated_root / PUBLIC_MANIFEST_REFERENCE).write_bytes(
        stable_json_bytes(public.model_dump(mode="json"))
    )
    with pytest.raises(AuthorityContractError, match="external exact authorization"):
        check_catalog_application(isolated_root, expected_owner_response=OWNER_RESPONSE)


def test_rehashed_event_twenty_rewrite_is_rejected_by_git_anchor(
    isolated_root: Path,
) -> None:
    artifacts, packet_sha = decision_module._validate_car_t4_inputs(isolated_root)
    ledger_path = isolated_root / PRIVATE_EVENT_REFERENCE.parent / "catalog-decision-ledger.json"
    ledger = CatalogDecisionLedger.model_validate(_load(ledger_path))
    previous = ledger.events[-2]
    original = ledger.events[-1]
    paraphrase = "全部批准，維持 color 與 edition 為 null。"
    rewritten_event = decision_module._build_event(
        artifacts.review_packet.entries[-1],
        ordinal=20,
        packet_sha256=packet_sha,
        decision=original.decision,
        owner_response_verbatim=paraphrase,
        authorized_exact_owner_response=paraphrase,
        reviewed_at=original.reviewed_at,
        review_reason=original.review_reason,
        previous_event_sha256=previous.event_sha256,
    )
    rewritten_ledger = decision_module._build_ledger(
        artifacts, packet_sha, [*ledger.events[:-1], rewritten_event]
    )
    progress_path = isolated_root / PUBLIC_PROGRESS_REFERENCE
    progress = PublicCatalogDecisionProgress.model_validate(_load(progress_path))
    commitment = ProgressCommitment(
        anchor_commit_sha=progress.anchor_commit_sha,
        previous_progress_sha256=progress.previous_committed_progress_sha256,
        previous_private_ledger_sha256=progress.previous_committed_ledger_sha256,
        previous_committed_event_count=progress.previous_committed_event_count,
    )
    rewritten_progress = decision_module._build_public_progress(rewritten_ledger, commitment)
    _write(ledger_path, rewritten_ledger.model_dump(mode="json"))
    _write(progress_path, rewritten_progress.model_dump(mode="json"))
    (isolated_root / PUBLIC_METHOD_REFERENCE).write_text(
        decision_module._render_public_method(rewritten_progress), encoding="utf-8"
    )

    with pytest.raises(AuthorityContractError, match="Git-committed HEAD anchor"):
        _apply(isolated_root)
    assert _load(isolated_root / "data/manifest.json")["product_count"] == 120


def test_transaction_failure_rolls_back_every_output(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    originals = {
        path: path.read_bytes()
        for path in (isolated_root / "data/catalog.json", isolated_root / "data/manifest.json")
    }
    real_replace = os.replace
    calls = 0

    def fail_third(source: str | bytes | Path, target: str | bytes | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise OSError("simulated transaction failure")
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", fail_third)
    with pytest.raises(OSError, match="simulated transaction failure"):
        _apply(isolated_root)
    assert all(path.read_bytes() == raw for path, raw in originals.items())
    assert not (isolated_root / PRIVATE_EVENT_REFERENCE).exists()
    assert not (isolated_root / PUBLIC_MANIFEST_REFERENCE).exists()
    assert not (isolated_root / TRANSACTION_JOURNAL_REFERENCE).exists()
    assert not (isolated_root / TRANSACTION_DIRECTORY_REFERENCE).exists()


def test_staging_write_failure_cleans_preparation_and_retry_succeeds(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    originals = {
        path: path.read_bytes()
        for path in (isolated_root / "data/catalog.json", isolated_root / "data/manifest.json")
    }
    real_write = application_module._write_file
    staged_writes = 0

    def fail_second_staged(path: Path, payload: bytes) -> None:
        nonlocal staged_writes
        if path.name.startswith("staged-"):
            staged_writes += 1
            if staged_writes == 2:
                raise OSError("simulated staging write failure")
        real_write(path, payload)

    monkeypatch.setattr(application_module, "_write_file", fail_second_staged)
    with pytest.raises(OSError, match="simulated staging write failure"):
        _apply(isolated_root)
    assert all(path.read_bytes() == raw for path, raw in originals.items())
    assert not (isolated_root / TRANSACTION_JOURNAL_REFERENCE).exists()
    assert not (isolated_root / TRANSACTION_DIRECTORY_REFERENCE).exists()

    monkeypatch.setattr(application_module, "_write_file", real_write)
    status, _ = _apply(isolated_root)
    assert status == "created"


def test_interrupted_transaction_is_recovered_to_exact_parent(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    originals = {
        path: path.read_bytes()
        for path in (isolated_root / "data/catalog.json", isolated_root / "data/manifest.json")
    }
    real_replace = os.replace
    calls = 0

    def interrupt_third(source: str | bytes | Path, target: str | bytes | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 3:
            raise KeyboardInterrupt
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", interrupt_third)
    with pytest.raises(KeyboardInterrupt):
        _apply(isolated_root)
    assert (isolated_root / TRANSACTION_JOURNAL_REFERENCE).is_file()
    monkeypatch.setattr(os, "replace", real_replace)
    assert recover_catalog_application(isolated_root) == "rolled_back"
    assert all(path.read_bytes() == raw for path, raw in originals.items())
    assert not (isolated_root / PRIVATE_EVENT_REFERENCE).exists()
    assert not (isolated_root / PUBLIC_MANIFEST_REFERENCE).exists()


def test_completed_outputs_recover_when_journal_unlink_is_interrupted(
    isolated_root: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    journal_path = isolated_root / TRANSACTION_JOURNAL_REFERENCE
    real_unlink = Path.unlink
    interrupted = False

    def interrupt_journal_unlink(path: Path, missing_ok: bool = False) -> None:
        nonlocal interrupted
        if path == journal_path and not interrupted:
            interrupted = True
            raise OSError("simulated journal unlink interruption")
        real_unlink(path, missing_ok=missing_ok)

    monkeypatch.setattr(Path, "unlink", interrupt_journal_unlink)
    with pytest.raises(OSError, match="simulated journal unlink interruption"):
        _apply(isolated_root)
    assert len(_load(isolated_root / "data/catalog.json")["products"]) == 140
    assert journal_path.is_file()
    assert not (isolated_root / TRANSACTION_DIRECTORY_REFERENCE).exists()

    monkeypatch.setattr(Path, "unlink", real_unlink)
    assert recover_catalog_application(isolated_root) == "completed"
    assert not journal_path.exists()
    manifest = check_catalog_application(isolated_root, expected_owner_response=OWNER_RESPONSE)
    assert manifest.catalog_product_count == 140
    status, replay = _apply(isolated_root)
    assert status == "unchanged"
    assert replay == manifest


def test_symlink_and_partial_application_state_fail_closed(
    isolated_root: Path, tmp_path: Path
) -> None:
    public = isolated_root / PUBLIC_MANIFEST_REFERENCE
    public.symlink_to(tmp_path / "outside.json")
    with pytest.raises(AuthorityContractError, match="symlink"):
        _apply(isolated_root)
    public.unlink()
    (isolated_root / PRIVATE_EVENT_REFERENCE).write_text("{}\n", encoding="utf-8")
    with pytest.raises(AuthorityContractError, match="partial"):
        _apply(isolated_root)


@pytest.mark.parametrize(
    "mutation",
    [
        lambda journal: journal["entries"][0].update({"target": ".gitignore"}),
        lambda journal: journal["entries"][1].update({"target": journal["entries"][0]["target"]}),
        lambda journal: journal["entries"].pop(),
        lambda journal: journal["entries"].__setitem__(
            slice(0, 2), list(reversed(journal["entries"][:2]))
        ),
        lambda journal: journal["entries"][0].update({"staged": journal["entries"][1]["staged"]}),
    ],
)
def test_recovery_rejects_adversarial_journal_before_any_mutation(
    isolated_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: Any,
) -> None:
    protected = {
        path: path.read_bytes()
        for path in (
            isolated_root / ".gitignore",
            isolated_root / "data/catalog.json",
            isolated_root / "data/manifest.json",
        )
    }
    real_replace = os.replace
    calls = 0

    def interrupt_first_target(source: str | bytes | Path, target: str | bytes | Path) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise KeyboardInterrupt
        real_replace(source, target)

    monkeypatch.setattr(os, "replace", interrupt_first_target)
    with pytest.raises(KeyboardInterrupt):
        _apply(isolated_root)
    monkeypatch.setattr(os, "replace", real_replace)
    journal_path = isolated_root / TRANSACTION_JOURNAL_REFERENCE
    journal = _load(journal_path)
    mutation(journal)
    _write(journal_path, journal)

    with pytest.raises((AuthorityContractError, ValueError)):
        recover_catalog_application(isolated_root)
    assert all(path.read_bytes() == raw for path, raw in protected.items())


def test_cli_applies_and_checks_from_repository_root(isolated_root: Path) -> None:
    environment = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
    command = [
        str(ROOT / ".venv/bin/python"),
        str(ROOT / "scripts/apply_canonical_catalog_proposals.py"),
        "--root",
        str(isolated_root),
    ]
    created = subprocess.run(
        [
            *command,
            "--owner-response",
            OWNER_RESPONSE,
            "--authorized-exact-owner-response",
            OWNER_RESPONSE,
            "--authorized-at",
            "2026-09-30T16:00:00Z",
        ],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert '"status": "created"' in created.stdout
    checked = subprocess.run(
        [*command, "--check", "--expected-owner-response", OWNER_RESPONSE],
        check=True,
        capture_output=True,
        text=True,
        env=environment,
    )
    assert '"status": "valid"' in checked.stdout
