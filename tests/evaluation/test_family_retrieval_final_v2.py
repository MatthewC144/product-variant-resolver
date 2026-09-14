"""Output-blind query lifecycle. No selected/new-final retrieval is permitted here."""
import runpy
import shutil
from copy import deepcopy
from pathlib import Path

import pytest

from product_variant_resolver import family_retrieval_final_v2 as module
from product_variant_resolver.human_knowledge_identity import HumanKnowledgeIdentityRetriever
from product_variant_resolver.human_knowledge_selection import load_object


def cases():
    return runpy.run_path(str(module.ROOT / module.AUTHOR_SOURCES[1]))["authored_cases"]()


def test_actual_committed_winner_precedes_authoring_without_retrieval(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("final authoring must never call retrieval")
    monkeypatch.setattr(HumanKnowledgeIdentityRetriever, "retrieve_with_work", forbidden)
    original = Path.read_text
    def guarded(path, *args, **kwargs):
        if path.name == "benchmark.json" or "/reports/family-retrieval-v1/" in str(path):
            raise AssertionError("old final labels/results are not authoring inputs")
        return original(path, *args, **kwargs)
    monkeypatch.setattr(Path, "read_text", guarded)
    winner = module.committed_winner()
    assert winner["commit"] == module.WINNER_COMMIT
    assert winner["configuration"] == {"character_score_floor": .5, "character_rrf_weight": 1.0}
    audit = module.validate_cases(cases())
    assert audit["old_question_count"] == 304 and audit["positive_families"] == 42
    assert audit["previous_or_indexed_reuse"] == 0
    assert module.GATES["family_coverage_at_5"] == .90 and "positive_coverage" not in module.GATES


@pytest.mark.parametrize("mutation", ["duplicate", "old_final", "development", "indexed", "compact", "core", "reference", "labels", "counts", "styles"])
def test_invalid_or_reused_queries_reject_before_publication(mutation):
    authored = cases()
    previous = load_object(module.ROOT / "data/evaluation/family-retrieval-v1/query-pack.json")["cases"][0]["query_text"]
    if mutation == "duplicate":
        authored[0]["query_text"] = authored[1]["query_text"]
    elif mutation == "old_final":
        authored[0]["query_text"] = previous
    elif mutation == "development":
        authored[0]["query_text"] = load_object(module.ROOT / "data/evaluation/family-retrieval-development-v1/development-pack.json")["cases"][0]["query_text"]
    elif mutation == "indexed":
        authored[0]["query_text"] = "Max Steel"
    elif mutation == "compact":
        authored[0]["query_text"] = module.normalize_text(previous).replace(" ", "")
    elif mutation == "core":
        authored[0]["query_text"] = previous + " boxed red"
    elif mutation == "reference":
        authored[0]["review_reference"]["review_family_id"] = "unapproved"
    elif mutation == "labels":
        authored[0]["expected"] = {}
    elif mutation == "counts":
        authored.pop()
    else:
        authored[0]["challenge_style"] = "marketplace_noise"
    with pytest.raises(ValueError):
        module.validate_cases(authored)


@pytest.fixture(scope="module")
def temporary_freeze(tmp_path_factory):
    root = tmp_path_factory.mktemp("final-v2-contract")
    for name in module.INPUTS + module.AUTHOR_SOURCES:
        target = root / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(module.ROOT / name, target)
    winner = module.committed_winner()
    authored = cases()
    # Only private fixture lacks Git; actual Git baseline is tested separately above.
    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(module, "committed_winner", lambda *args: winner)
        module.freeze(authored, root)
        assert module.check(authored, root)["status"] == "pending_owner_review"
    return root, authored, winner


def test_freeze_complete_pairs_checksums_and_pending_gate(temporary_freeze, monkeypatch):
    root, authored, winner = temporary_freeze
    monkeypatch.setattr(module, "committed_winner", lambda *args: winner)
    pack = module.check(authored, root)
    assert len(pack["cases"]) == 105 and all("expected" not in case and "candidates" not in case for case in pack["cases"])
    manifest = load_object(root / module.DIRECTORY / "query-pack-manifest.json")
    assert len(manifest["case_sha256"]) == 105
    assert manifest["owner_approval_recorded"] is manifest["expected_labels_created"] is manifest["new_final_retrieval_executed"] is False
    assert sorted(path.name for path in (root / module.DIRECTORY).iterdir()) == ["owner-review.md", "query-pack-manifest.json", "query-pack.json"]
    with pytest.raises(ValueError, match="owner approval"):
        module.require_approval(root)


def test_repeat_freeze_preserves_all_frozen_bytes_and_timestamps(temporary_freeze):
    root, authored, _ = temporary_freeze
    paths = list((root / module.DIRECTORY).iterdir())
    before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]
    with pytest.raises(ValueError, match="exist"):
        module.freeze(authored, root)
    assert before == [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]


@pytest.mark.parametrize("field", ["status", "split", "authorship_policy", "final_gates", "authored_at"])
def test_freeze_metadata_tampering_rejects(temporary_freeze, monkeypatch, field):
    root, authored, winner = temporary_freeze
    monkeypatch.setattr(module, "committed_winner", lambda *args: winner)
    original = module.load_object
    def load(path):
        value = original(path)
        if path.name == "query-pack.json":
            value = deepcopy(value)
            value[field] = "2020-01-01T00:00:00Z" if field == "authored_at" else "changed"
        return value
    monkeypatch.setattr(module, "load_object", load)
    with pytest.raises(ValueError):
        module.check(authored, root)


def test_stale_authoring_source_rejects(temporary_freeze, monkeypatch):
    root, authored, winner = temporary_freeze
    monkeypatch.setattr(module, "committed_winner", lambda *args: winner)
    original = module.sha
    monkeypatch.setattr(module, "sha", lambda path: "0"*64 if str(path).endswith(module.AUTHOR_SOURCES[0]) else original(path))
    with pytest.raises(ValueError):
        module.check(authored, root)


def test_partial_staging_failure_never_publishes_final_directory(temporary_freeze, tmp_path, monkeypatch):
    source, authored, winner = temporary_freeze
    for name in module.INPUTS + module.AUTHOR_SOURCES:
        target = tmp_path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source / name, target)
    monkeypatch.setattr(module, "committed_winner", lambda *args: winner)
    original = module.publish_new
    calls = 0
    def fail_second(*args):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("simulated manifest write failure")
        return original(*args)
    monkeypatch.setattr(module, "publish_new", fail_second)
    with pytest.raises(OSError):
        module.freeze(authored, tmp_path)
    assert not (tmp_path / module.DIRECTORY).exists()
    assert not list((tmp_path / module.DIRECTORY.parent).glob(".family-retrieval-v2-*"))


def test_actual_frozen_pack_has_no_labels_approval_or_new_candidates(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("no final retrieval before owner confirmation")
    monkeypatch.setattr(HumanKnowledgeIdentityRetriever, "retrieve_with_work", forbidden)
    pack = module.check(cases())
    assert pack["status"] == "pending_owner_review" and len(pack["cases"]) == 105
    directory = module.ROOT / module.DIRECTORY
    assert sorted(path.name for path in directory.iterdir()) == ["owner-review.md", "query-pack-manifest.json", "query-pack.json"]
    with pytest.raises(ValueError, match="owner approval"):
        module.require_approval()


def test_superseded_draft_preserves_provenance_without_question_or_output_changes():
    directory = module.ROOT / "data/evaluation/family-retrieval-v2-superseded-draft-01"
    draft = load_object(directory / "query-pack.json")
    authoritative = load_object(module.ROOT / module.DIRECTORY / "query-pack.json")
    assert draft["cases"] == authoritative["cases"]
    assert "positive_coverage" in draft["final_gates"]
    assert "family_coverage_at_5" in authoritative["final_gates"]
    manifest = load_object(directory / "query-pack-manifest.json")
    assert module.sha(directory / "query-pack.json") == manifest["query_pack_sha256"]
    assert all(module.sha(directory / "source-snapshot" / Path(name).name) == manifest["source_sha256"][name]
        for name in module.AUTHOR_SOURCES)
    assert manifest["owner_approval_recorded"] is manifest["expected_labels_created"] is manifest["new_final_retrieval_executed"] is False
