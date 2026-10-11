from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

DIRECTORY_INDEXES = (
    "artifacts/README.md",
    "config/README.md",
    "constraints/README.md",
    "data/README.md",
    "docs/README.md",
    "migrations/README.md",
    "reports/README.md",
    "runtime/README.md",
    "scripts/README.md",
    "specs/README.md",
    "src/product_variant_resolver/README.md",
    "tests/README.md",
    "ui/README.md",
)

FORBIDDEN_TRACKED_EXACT = {".env"}
FORBIDDEN_TRACKED_PREFIXES = (
    ".mypy_cache/",
    ".pytest_cache/",
    ".ruff_cache/",
    ".venv/",
    "HW data/",
    "model-cache/",
    ".local-image-search-collection",
)


def test_every_content_directory_has_a_github_entry_point() -> None:
    for relative in DIRECTORY_INDEXES:
        assert (ROOT / relative).is_file(), relative

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for relative in DIRECTORY_INDEXES:
        directory = relative.removesuffix("/README.md")
        assert directory in readme, directory


def test_legacy_guides_are_explicitly_historical_and_obsolete_draft_is_removed() -> None:
    historical = (
        "docs/REAL-CATALOG-ROADMAP.md",
        "docs/HUMAN-STORAGE-PROFILE-GUIDE.md",
        "docs/T49-2-ISOLATED-TEST-PLAN.md",
    )
    for relative in historical:
        beginning = (ROOT / relative).read_text(encoding="utf-8")[:500]
        assert "Historical" in beginning
        assert "不是目前" in beginning or "不是建立" in beginning

    assert not (ROOT / "docs/FANDOM-SOURCE-PERMISSION-GUIDE.md").exists()


def test_package_metadata_and_github_attributes_state_current_intent() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert pyproject["project"]["description"] == (
        "Confidence-aware product entity resolution and learning-to-rank"
    )

    attributes = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    assert "*.safetensors binary" in attributes
    assert "reports/**/*.json linguist-generated=true" in attributes


def test_local_only_paths_are_not_tracked() -> None:
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=ROOT,
        capture_output=True,
        check=True,
        text=True,
    )
    tracked = result.stdout.splitlines()
    violations = [
        path
        for path in tracked
        if path in FORBIDDEN_TRACKED_EXACT
        or any(path.startswith(prefix) for prefix in FORBIDDEN_TRACKED_PREFIXES)
        or "/__pycache__/" in f"/{path}"
        or path.endswith((".pyc", ".pyo"))
    ]
    assert not violations, violations
