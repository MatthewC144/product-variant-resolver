from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
RESULT = (
    ROOT
    / "data/evaluation/serper-dual-source-evaluation-v1/raw-pointwise-final-test.json"
)
PUBLIC_DOCS = (
    README,
    ROOT / "docs/README.md",
    ROOT / "docs/PORTFOLIO-GUIDE.md",
    ROOT / "docs/CODE-TOUR.md",
    ROOT / "docs/RESULTS.md",
    ROOT / "docs/LIMITATIONS.md",
    ROOT / "docs/ARTIFACT-POLICY.md",
    ROOT / "docs/architecture/system-overview.md",
    ROOT / "docs/archive/README.md",
)
MARKDOWN_LINK = re.compile(r"(?<!!)\[[^]]+\]\(([^)]+)\)")


def test_readme_is_a_bounded_portfolio_landing_page() -> None:
    readme = README.read_text(encoding="utf-8")

    assert 150 <= len(readme.splitlines()) <= 250
    assert "Confidence-Aware Product Entity Resolution & Learning-to-Rank" in readme
    assert "dual-rag" not in readme.casefold()
    assert "authority-separated dual-corpus retrieval" in readme
    assert "portfolio-grade AI engineering system" in readme


def test_headline_metrics_match_the_frozen_result() -> None:
    readme = README.read_text(encoding="utf-8")
    normalized_readme = " ".join(readme.replace(">", " ").split())
    payload = json.loads(RESULT.read_text(encoding="utf-8"))
    metrics = payload["combined_metrics"]
    rrf = metrics["rrf"]
    pointwise = metrics["neural_pointwise"]

    expected_claims = (
        f"{rrf['exact_release_top1_accuracy']:.0%}",
        f"{pointwise['exact_release_top1_accuracy']:.0%}",
        f"{rrf['casting_top1_accuracy']:.0%}",
        f"{pointwise['casting_top1_accuracy']:.0%}",
        f"{rrf['exact_release_mrr_at_10']:.3f}",
        f"{pointwise['exact_release_mrr_at_10']:.3f}",
        f"{rrf['exact_release_recall_at_25']:.0%}",
    )
    for claim in expected_claims:
        assert claim in readme

    assert metrics["sample_count"] == 100
    assert "100 source observations from 50 held-out product identities" in normalized_readme
    assert "they are not 100 independent products" in normalized_readme


def test_public_documentation_entry_points_exist_and_avoid_primary_dual_rag_wording() -> None:
    for document in PUBLIC_DOCS:
        assert document.is_file(), document

    portfolio_guide = (ROOT / "docs/PORTFOLIO-GUIDE.md").read_text(encoding="utf-8")
    assert "dual-rag" not in portfolio_guide.casefold()
    assert "authority-separated dual-corpus retrieval" in portfolio_guide


def test_public_documentation_relative_links_resolve() -> None:
    broken: list[str] = []
    for document in PUBLIC_DOCS:
        text = document.read_text(encoding="utf-8")
        for target in MARKDOWN_LINK.findall(text):
            if target.startswith(("#", "http://", "https://", "mailto:")):
                continue
            path_text = target.split("#", 1)[0].split("?", 1)[0].strip("<>")
            if not path_text:
                continue
            resolved = (document.parent / path_text).resolve()
            if not resolved.exists():
                broken.append(f"{document.relative_to(ROOT)} -> {target}")

    assert not broken, "broken public documentation links:\n" + "\n".join(broken)
