from __future__ import annotations

import json
from pathlib import Path

from product_variant_resolver.config import Settings
from product_variant_resolver.domain_ranker_v2_selection import (
    AUTHORIZATION_PATH,
    RESULT_PATH,
    check,
)

ROOT = Path(__file__).resolve().parents[2]


def test_t7_closure_preserves_null_winner_and_runtime_default() -> None:
    result = check(ROOT)
    settings = Settings()
    assert result["status"] == "ranker_gate_failed"
    assert result["winner"] is None
    assert result["selected_checkpoint_sha256"] is None
    assert settings.reranker_enabled is False
    assert settings.reranker_provider == "heuristic-v1"
    assert settings.backend == "offline"


def test_t7_runtime_sources_do_not_import_or_select_v2_checkpoint() -> None:
    runtime_text = "\n".join(
        (ROOT / path).read_text(encoding="utf-8")
        for path in (
            "src/product_variant_resolver/api.py",
            "src/product_variant_resolver/config.py",
            "src/product_variant_resolver/service.py",
        )
    )
    assert "domain_ranker_v2" not in runtime_text
    assert "5a4f2ea21b93a864f1e1ddb54523f68a0ae2766db555535c0f35721588b6e297" not in runtime_text
    assert "83db9ab75c1c431ce2c6f3e4c717bae821c187a060f0864e45204ee8a4056e99" not in runtime_text


def test_t7_public_selection_artifacts_are_aggregate_only() -> None:
    payloads = [
        json.loads((ROOT / path).read_text(encoding="utf-8"))
        for path in (AUTHORIZATION_PATH, RESULT_PATH)
    ]
    serialized = json.dumps(payloads, ensure_ascii=False).casefold()
    for forbidden in (
        '"query"',
        '"target_uuid"',
        '"case_id"',
        '"candidates"',
        '"prediction"',
        "drv2-q",
    ):
        assert forbidden not in serialized
    assert payloads[1]["guardrails"]["public_row_level_records"] == 0
    assert payloads[1]["guardrails"]["runtime_activations"] == 0


def test_t7_readme_states_negative_selection_result_without_runtime_claim() -> None:
    readme = " ".join((ROOT / "README.md").read_text(encoding="utf-8").split())
    assert "V2 selection result is also `winner: null`" in readme
    assert "Seed 17 improved exact Top-1 from `23/30` to `24/30`" in readme
    assert "No v2 checkpoint is selected for calibration, final evaluation, or runtime" in readme
