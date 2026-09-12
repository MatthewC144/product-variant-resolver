from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from product_variant_resolver.config import Settings


class SettingsTests(unittest.TestCase):
    def test_review_family_paths_can_be_configured_from_environment(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "PVR_REVIEW_FAMILY_KNOWLEDGE_PATH": "/tmp/custom-family.json",
                "PVR_REVIEW_FAMILY_KNOWLEDGE_MANIFEST_PATH": "/tmp/custom-family-manifest.json",
            },
            clear=False,
        ):
            settings = Settings.from_env()

        self.assertEqual(
            settings.review_family_knowledge_path,
            Path("/tmp/custom-family.json"),
        )
        self.assertEqual(
            settings.review_family_knowledge_manifest_path,
            Path("/tmp/custom-family-manifest.json"),
        )

    def test_v3_uses_artifact_paths_instead_of_environment_floats(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "PVR_HUMAN_KNOWLEDGE_RETRIEVAL_ARTIFACT": "/tmp/v3-artifact.json",
                "PVR_HUMAN_KNOWLEDGE_DEVELOPMENT_PATH": "/tmp/development.json",
                "PVR_HUMAN_KNOWLEDGE_DEVELOPMENT_MANIFEST_PATH": "/tmp/development-manifest.json",
            },
            clear=False,
        ):
            settings = Settings.from_env()

        self.assertEqual(
            settings.human_knowledge_retrieval_artifact_path,
            Path("/tmp/v3-artifact.json"),
        )
        self.assertEqual(
            settings.human_knowledge_development_path, Path("/tmp/development.json")
        )
        self.assertEqual(
            settings.human_knowledge_development_manifest_path,
            Path("/tmp/development-manifest.json"),
        )


if __name__ == "__main__":
    unittest.main()
