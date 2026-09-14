"""Approval/label lifecycle tests; all final retrieval is forbidden in this phase."""
import shutil
from copy import deepcopy
from datetime import UTC, datetime, timedelta

import pytest

from product_variant_resolver import family_retrieval_final_v2_labels as labels
from product_variant_resolver.human_knowledge_identity import HumanKnowledgeIdentityRetriever
from product_variant_resolver.human_knowledge_selection import load_object


@pytest.fixture(scope="module")
def actual_pack():
    return labels.committed_questions()


@pytest.fixture
def workspace(tmp_path, monkeypatch, actual_pack):
    for name in labels.source_hashes(labels.ROOT):
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(labels.ROOT / name, path)
    monkeypatch.setattr(labels, "committed_questions", lambda root: actual_pack)
    def forbidden(*args, **kwargs):
        raise AssertionError("T4 approval/labeling must never retrieve final candidates")
    monkeypatch.setattr(HumanKnowledgeIdentityRetriever, "retrieve_with_work", forbidden)
    monkeypatch.setattr(HumanKnowledgeIdentityRetriever, "retrieve", forbidden)
    return tmp_path


def test_actual_question_commit_is_verified_without_retrieval(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("no new final retrieval")
    monkeypatch.setattr(HumanKnowledgeIdentityRetriever, "retrieve_with_work", forbidden)
    pack = labels.committed_questions()
    assert len(pack["cases"]) == 105 and pack["winner"]["commit"] == labels.questions.WINNER_COMMIT


def test_complete_freeze_labels_and_types(workspace, actual_pack):
    labels.freeze(deepcopy(labels.CONTEXT), workspace)
    benchmark = labels.validate(workspace)
    directory = workspace / labels.DIRECTORY
    assert sorted(path.name for path in directory.iterdir()) == sorted(labels.FILES)
    assert benchmark["family_coverage_denominator"] == 42
    assert benchmark["final_gates"] == labels.questions.GATES
    assert benchmark["split_counts"] == {"train": 0, "dev": 0, "test": 105}
    groups = set()
    for original, row in zip(actual_pack["cases"], benchmark["cases"], strict=True):
        assert {key: row[key] for key in original} == original
        expected = row["expected"]
        if row["case_type"] == "positive_family":
            assert expected["review_family_id"] == original["review_reference"]["review_family_id"]
            assert expected["knowledge_type"] == "review_family" and expected["review_family_uuid"]
            groups.add(row["casting_group_id"])
        elif row["case_type"] == "merge_control":
            assert expected["casting_uuid"] and expected["casting_id"]
            assert expected["knowledge_type"] == "provisional_variant"
            assert "provisional_variant_uuid" not in expected  # No specific release truth.
        elif row["case_type"] == "hold_control":
            assert expected["expected_materialized"] is False
            assert "expected_candidate_count" not in expected  # Other valid hits need not be empty.
        else:
            assert expected["expected_candidate_count"] == 0
    assert len(groups) == 42
    decisions = load_object(directory / labels.FILES[0])
    assert decisions["message_timestamp"] is None
    assert decisions["conversation_context"] == labels.CONTEXT
    assert len(decisions["decisions"]) == 105
    assert decisions["decision_granularity"] == "whole_pack_confirmed_targets"
    assert all(item["decision"] == "approve" for item in decisions["decisions"])


@pytest.mark.parametrize("mutation", ["generic", "no_target", "scope", "context", "negative"])
def test_incomplete_or_unapproved_context_cannot_publish(workspace, mutation):
    context = deepcopy(labels.CONTEXT)
    if mutation == "generic":
        context = {"proceed_confirmation": "幫我進行下一步"}
    elif mutation == "no_target":
        context["target_confirmation"] = None
    elif mutation == "scope":
        context["scope_explained"] = "All release variants are verified"
    elif mutation == "negative":
        context["proceed_confirmation"] = "不要繼續"
    else:
        context["invented_message_time"] = "2026-09-14T00:00:00Z"
    with pytest.raises(ValueError, match="confirmation"):
        labels.freeze(context, workspace)
    assert not (workspace / labels.DIRECTORY).exists()
    assert not list((workspace / labels.questions.DIRECTORY).glob(".approved-final-v2-*"))


def test_repeated_freeze_preserves_bytes_and_timestamps(workspace):
    labels.freeze(labels.CONTEXT, workspace)
    paths = list((workspace / labels.DIRECTORY).iterdir())
    before = [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]
    with pytest.raises(ValueError, match="already exists"):
        labels.freeze(labels.CONTEXT, workspace)
    assert before == [(path.read_bytes(), path.stat().st_mtime_ns) for path in paths]


@pytest.mark.parametrize("mutation", ["partial", "duplicate", "decision", "case_hash", "expected", "query", "gates", "denominator", "scope", "flag_type", "manifest", "source"])
def test_stale_or_changed_approval_benchmark_rejects(workspace, mutation):
    labels.freeze(labels.CONTEXT, workspace)
    directory = workspace / labels.DIRECTORY
    name = labels.FILES[0] if mutation in {"partial", "duplicate", "decision", "case_hash", "expected"} else labels.FILES[1]
    path = directory / name
    doc = load_object(path)
    if mutation == "partial":
        doc["decisions"].pop()
    elif mutation == "duplicate":
        doc["decisions"][1] = doc["decisions"][0]
    elif mutation == "decision":
        doc["decisions"][0]["decision"] = "reject"
    elif mutation == "case_hash":
        doc["decisions"][0]["case_sha256"] = "0" * 64
    elif mutation == "expected":
        doc["decisions"][0]["expected"]["expected_materialized"] = True
    elif mutation == "query":
        doc["cases"][0]["query_text"] += " rewritten"
    elif mutation == "gates":
        doc["final_gates"]["positive_recall_at_5"] = 0
    elif mutation == "denominator":
        doc["family_coverage_denominator"] = 84
    elif mutation == "scope":
        doc["scope"] = "canonical_variant_truth"
    elif mutation == "flag_type":
        doc["new_final_retrieval_executed"] = 0  # bool/int equality must not hide schema edits.
    elif mutation == "manifest":
        path = directory / labels.FILES[2]
        doc = load_object(path)
        doc["benchmark_sha256"] = "0" * 64
    else:
        path = workspace / labels.SOURCES[1]
        path.write_text(path.read_text() + "\n# stale source\n")
    if mutation != "source":
        path.write_text(labels.questions.json_text(doc))
    with pytest.raises(ValueError, match="changed"):
        labels.validate(workspace)


def test_publication_failure_leaves_no_partial_directory(workspace, monkeypatch):
    publish = labels.publish_new
    def failing(path, value):
        if path.name == labels.FILES[1]:
            raise OSError("simulated publication failure")
        publish(path, value)
    monkeypatch.setattr(labels, "publish_new", failing)
    with pytest.raises(OSError, match="publication failure"):
        labels.freeze(labels.CONTEXT, workspace)
    assert not (workspace / labels.DIRECTORY).exists()
    assert not list((workspace / labels.questions.DIRECTORY).glob(".approved-final-v2-*"))


@pytest.mark.parametrize("timestamp", ["2026-09-14T00:00:00Z", "invalid", "2026-09-14T16:00:00", "future"])
def test_invalid_record_time_rejects(workspace, actual_pack, timestamp):
    if timestamp == "future":
        timestamp = (datetime.now(UTC) + timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with pytest.raises(ValueError):
        labels.documents(actual_pack, labels.CONTEXT, timestamp, workspace)


def test_uncommitted_benchmark_blocks_score_gate(workspace, monkeypatch):
    labels.freeze(labels.CONTEXT, workspace)
    from subprocess import CompletedProcess
    monkeypatch.setattr(labels.questions, "git", lambda *args: CompletedProcess([], 0, "", ""))
    with pytest.raises(ValueError, match="committed before scoring"):
        labels.require_committed_benchmark(workspace)


def test_modified_builder_at_commit_blocks_score_gate(workspace, monkeypatch):
    labels.freeze(labels.CONTEXT, workspace)
    from subprocess import CompletedProcess
    def fake_git(root, *args):
        if args[0] == "log":
            return CompletedProcess([], 0, "abc123\n", "")
        name = args[-1].split(":", 1)[1]
        text = (root / name).read_text()
        if name == labels.SOURCES[0]:
            text += "# changed\n"
        return CompletedProcess([], 0, text, "")
    monkeypatch.setattr(labels.questions, "git", fake_git)
    with pytest.raises(ValueError, match="differs from its freeze commit"):
        labels.require_committed_benchmark(workspace)


def test_committed_benchmark_gate_validates_every_file(workspace, monkeypatch):
    labels.freeze(labels.CONTEXT, workspace)
    from subprocess import CompletedProcess
    checked = []
    def fake_git(root, *args):
        if args[0] == "log":
            return CompletedProcess([], 0, "abc123\n", "")
        name = args[-1].split(":", 1)[1]
        checked.append(name)
        return CompletedProcess([], 0, (root / name).read_text(), "")
    monkeypatch.setattr(labels.questions, "git", fake_git)
    assert labels.require_committed_benchmark(workspace) == "abc123"
    assert checked == [*(str(labels.DIRECTORY / name) for name in labels.FILES), *labels.SOURCES]
