from __future__ import annotations

import copy
import importlib.util
from pathlib import Path
from unittest.mock import patch

import pytest

from product_variant_resolver import human_knowledge_selection as selection

ROOT = selection.ROOT


def perfect_metrics() -> dict:
    return {"raw_counts": {"forbidden_family_candidates": 0, "unrelated_nonempty": 0,
                           "merge_hits_at_5": 4, "merge_total": 4,
                           "positive_styles": {style: {"hits_at_5": 42, "total": 42}
                                               for style in selection.STYLES}},
            "recall_at_5": 1.0, "recall_at_1": 1.0, "mrr_at_5": 1.0}


def cheap_cost() -> dict:
    return {"real_142": {"p50_ms": 1, "p95_ms": 2}, "synthetic_3000": {"p95_ms": 3}}


def test_exact_precommitted_grid_and_no_v1_file_reads() -> None:
    original = Path.read_bytes
    text_original = Path.read_text
    opened = []

    def bytes_guard(path: Path) -> bytes:
        opened.append(str(path))
        assert "family-retrieval-v1" not in str(path)
        return original(path)

    def text_guard(path: Path, *args, **kwargs) -> str:
        opened.append(str(path))
        assert "family-retrieval-v1" not in str(path)
        return text_original(path, *args, **kwargs)

    with patch.object(Path, "read_bytes", bytes_guard), patch.object(Path, "read_text", text_guard):
        pack, manifest = selection.load_development()
    assert opened
    assert len(pack["cases"]) == 199
    assert len(selection.grid()) == 21
    assert len({tuple(item.values()) for item in selection.grid()}) == 21
    assert manifest["selection_contract"] == pack["selection_contract"]


@pytest.mark.parametrize("failure", ["forbidden", "unrelated", "merge", "overall", "style", "real_cost", "scale_cost"])
def test_every_safety_quality_cost_gate_rejects(failure: str) -> None:
    metrics, cost = perfect_metrics(), cheap_cost()
    if failure == "forbidden":
        metrics["raw_counts"]["forbidden_family_candidates"] = 1
    elif failure == "unrelated":
        metrics["raw_counts"]["unrelated_nonempty"] = 1
    elif failure == "merge":
        metrics["raw_counts"]["merge_hits_at_5"] = 3
    elif failure == "overall":
        metrics["recall_at_5"] = 0.89
    elif failure == "style":
        metrics["raw_counts"]["positive_styles"]["single_edit"]["hits_at_5"] = 35
    elif failure == "real_cost":
        cost["real_142"]["p95_ms"] = 25.01
    else:
        cost["synthetic_3000"]["p95_ms"] = 150.01
    assert selection.rejection_reasons(metrics, cost)
    assert not selection.rejection_reasons(perfect_metrics(), cheap_cost())


def test_safety_first_and_all_tie_break_levels() -> None:
    entries = [{"configuration": item, "metrics": perfect_metrics(), "rejection_reasons": []}
               for item in selection.grid()]
    assert selection.choose(entries) == {"character_score_floor": 0.55, "character_rrf_weight": 0.5}
    entries[0]["metrics"]["recall_at_1"] = 1.1
    assert selection.choose(entries) == entries[0]["configuration"]
    entries[1]["metrics"]["mrr_at_5"] = 1.1
    assert selection.choose(entries) == entries[1]["configuration"]
    entries[1]["rejection_reasons"] = ["unrelated_nonempty"]
    assert selection.choose(entries) == entries[0]["configuration"]
    for entry in entries:
        entry["rejection_reasons"] = ["unrelated_nonempty"]
    assert selection.choose(entries) is None


def test_nearest_rank_latency_and_synthetic_scope() -> None:
    result = selection.latency(list(range(1, 21)), {})
    assert result["p50_ms"] == 10
    assert result["p95_ms"] == 19
    catalog = selection.synthetic_catalog()
    assert len(catalog.documents) == 3000
    assert len({item.knowledge_uuid for item in catalog.documents}) == 3000
    assert catalog.variant_document_count == 0


def test_committed_raw_report_recomputes_and_tampering_fails() -> None:
    if not selection.REPORT.exists():
        pytest.skip("development grid has not been executed yet")
    report = selection.load_object(selection.REPORT)
    selection.validate_report(report)
    bad = copy.deepcopy(report)
    bad["configurations"][0]["metrics"]["recall_at_5"] = -1
    with pytest.raises(ValueError, match="recompute"):
        selection.validate_report(bad)
    bad = copy.deepcopy(report)
    bad["configurations"][0]["cost"]["real_142"]["p95_ms"] = -1
    with pytest.raises(ValueError, match="cost"):
        selection.validate_report(bad)
    bad = copy.deepcopy(report)
    bad["winner"] = selection.grid()[0]
    bad["verdict"] = "PASS"
    with pytest.raises(ValueError, match="outcome"):
        selection.validate_report(bad)
    bad = copy.deepcopy(report)
    bad["sources"] = {}
    with pytest.raises(ValueError, match="incomplete"):
        selection.validate_report(bad)
    bad = copy.deepcopy(report)
    candidate = next(row["candidates"][0] for row in bad["configurations"][0]["cases"]
                     if row["candidates"])
    candidate["knowledge_id"] = "invented-identity"
    with pytest.raises(ValueError, match="identity"):
        selection.validate_report(bad)


def test_no_winner_never_creates_or_overwrites_artifact(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("freeze_v3", ROOT / "scripts/freeze_human_knowledge_v3.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    path = tmp_path / "active.json"
    with patch.object(module, "load_object", return_value={"verdict": "FAIL", "winner": None}), patch.object(module, "validate_report"):
        assert module.freeze(tmp_path / "selection.json", path) is False
        assert not path.exists()
        path.write_bytes(b"existing active artifact")
        assert module.freeze(tmp_path / "selection.json", path) is False
        assert path.read_bytes() == b"existing active artifact"


def test_winner_freezer_binds_all_metrics_and_refuses_replacement(tmp_path: Path) -> None:
    spec = importlib.util.spec_from_file_location("freeze_v3_winner", ROOT / "scripts/freeze_human_knowledge_v3.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    entries = [{"configuration": item, "metrics": perfect_metrics(), "rejection_reasons": []}
               for item in selection.grid()]
    payload = {"verdict": "PASS", "winner": selection.choose(entries), "configurations": entries}
    output = tmp_path / "winner.json"
    # Isolate construction from genuine quality: no real report is claimed PASS here.
    with patch.object(module, "load_object", return_value=payload), patch.object(module, "validate_report"), patch.object(module, "sha", return_value="0" * 64):
        assert module.freeze(selection.REPORT, output)
        artifact = selection.load_object(output)
        assert len(artifact["selection_evidence"]["configurations"]) == 21
        assert artifact["selection_evidence"]["sha256"] == "0" * 64
        assert artifact["configuration"]["character_score_floor"] == 0.55
        original = output.read_bytes()
        with pytest.raises(ValueError, match="already exists"):
            module.freeze(selection.REPORT, output)
        assert output.read_bytes() == original
