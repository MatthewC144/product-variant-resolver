import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from product_variant_resolver.calibration import CalibrationArtifact
from product_variant_resolver.config import Settings
from product_variant_resolver.training import train_and_select
from product_variant_resolver.service import ResolverService

ROOT = Path(__file__).resolve().parents[2]


class TrainingIntegrationTests(unittest.TestCase):
    def test_grouped_train_dev_pipeline_writes_versioned_artifacts(self):
        settings = Settings(catalog_path=ROOT / "data/catalog.json", benchmark_path=ROOT / "data/benchmark.json")
        with tempfile.TemporaryDirectory() as directory:
            calibration, policy = train_and_select(settings, Path(directory))
            artifact = CalibrationArtifact.load(calibration)
            policy_data = json.loads(policy.read_text())
            self.assertEqual(artifact.dataset_version, "fixture-v1")
            self.assertEqual(policy_data["calibration_split"], "train")
            self.assertEqual(policy_data["selection_split"], "dev")
            self.assertFalse(policy_data["test_labels_accessed"])
            trained_service = ResolverService.from_settings(replace(
                settings, calibration_artifact=calibration, policy_artifact=policy,
            ))
            self.assertEqual(artifact.artifact_version, "fixture-v1-rrf-logistic-v2")
            self.assertEqual(trained_service.policy.version, "fixture-v1-rrf-trained-v2")
            self.assertFalse(trained_service.settings.reranker_enabled)


if __name__ == "__main__":
    unittest.main()
