import tomllib
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def _constraints(path: Path) -> dict[str, str]:
    constraints: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.partition("#")[0].strip()
        if line:
            name, separator, version = line.partition("==")
            if not separator or not version:
                raise AssertionError(f"constraint must use an exact pin: {line}")
            normalized_name = name.lower()
            if normalized_name in constraints:
                raise AssertionError(f"duplicate constraint: {normalized_name}")
            constraints[normalized_name] = version
    return constraints


class DependencyConstraintTests(unittest.TestCase):
    def setUp(self) -> None:
        self.project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))[
            "project"
        ]
        self.constraints = _constraints(ROOT / "constraints" / "python312.txt")

    def test_runtime_dependencies_are_covered_by_python312_constraints(self) -> None:
        runtime_names = {
            requirement.split("[", 1)[0].split(">", 1)[0].split("<", 1)[0].split("=", 1)[0]
            for requirement in self.project["dependencies"]
        }
        self.assertLessEqual(runtime_names, self.constraints.keys())

        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn("-c constraints/python312.txt", dockerfile)

    def test_testclient_uses_httpx2_without_legacy_httpx_dev_dependency(self) -> None:
        dev_requirements = self.project["optional-dependencies"]["dev"]
        self.assertFalse(any(requirement.startswith("httpx") for requirement in dev_requirements))
        self.assertIn("httpx2", self.constraints)
        self.assertIn("httpcore2", self.constraints)
        self.assertIn("anyio", self.constraints)


if __name__ == "__main__":
    unittest.main()
