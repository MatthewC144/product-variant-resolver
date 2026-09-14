from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/run_human_knowledge_postgres_test.py"


def runner() -> Any:
    spec = importlib.util.spec_from_file_location("t49_test_runner", SCRIPT)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_cli_without_disposable_flag_refuses_before_docker() -> None:
    result = subprocess.run([sys.executable, str(SCRIPT), "--run"], capture_output=True,
                            text=True, check=False)
    assert result.returncode == 2
    assert "requires --allow-disposable-test" in result.stderr


def test_report_publication_never_overwrites(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = runner()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    (tmp_path / "reports").mkdir()
    path = tmp_path / "reports/test.json"
    module.publish(path, {"verdict": "PASS"})
    before = path.read_bytes()
    with pytest.raises(FileExistsError):
        module.publish(path, {"verdict": "FAIL"})
    assert path.read_bytes() == before
    assert list(path.parent.iterdir()) == [path]


def test_outside_report_publication_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = runner()
    monkeypatch.setattr(module, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="exclusive project"):
        module.publish(tmp_path / "outside.json", {})
    assert not (tmp_path / "outside.json").exists()


def test_existing_report_run_does_not_touch_docker(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    module = runner()
    path = tmp_path / "existing.json"
    path.write_text("preserve me")

    def forbidden(*args: object, **kwargs: object) -> None:
        raise AssertionError("Docker must not be called on repeated evidence")

    monkeypatch.setattr(module, "docker", forbidden)
    with pytest.raises(ValueError, match="already exists"):
        module.run(path)
    assert path.read_text() == "preserve me"


def test_staging_inputs_never_include_user_env_or_final_questions() -> None:
    paths = runner().source_paths()
    assert ROOT / "data/human_backed_catalog.json" in paths
    assert ROOT / "reports/human-knowledge-snapshot-v1/plan.json" in paths
    assert all(path.suffix != ".env" and "data/evaluation" not in str(path)
               and "reports/family-retrieval-v2" not in str(path) for path in paths)
