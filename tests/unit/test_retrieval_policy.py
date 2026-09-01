import math
import tempfile
import unittest
from pathlib import Path
from uuid import UUID

from product_variant_resolver.calibration import (
    CalibrationArtifact, FEATURE_SCHEMA, LogisticCalibrator, train_logistic,
)
from product_variant_resolver.catalog import CatalogProduct
from product_variant_resolver.policy import DecisionPolicy, select_policy
from product_variant_resolver.retrieval import Candidate, reciprocal_rank_fusion
from product_variant_resolver.schemas import ProductView, ResolutionStatus


def product(number: int) -> CatalogProduct:
    return CatalogProduct(
        UUID(int=number), f"variant-{number}",
        ProductView(brand="Hot Wheels", casting=f"Car {number}"), (), (), ({"source": "test"},),
    )


class RetrievalPolicyTests(unittest.TestCase):
    def test_rrf_deduplicates_and_tie_breaks(self):
        first, second = product(1), product(2)
        fused = reciprocal_rank_fusion(
            {"dense": [(second, .8), (first, .7)], "sparse": [(first, 2.0), (second, 1.0)]}, 2,
        )
        self.assertEqual(len(fused), 2)
        self.assertEqual(fused[0].product.canonical_uuid, first.canonical_uuid)
        self.assertAlmostEqual(fused[0].rrf_score, 1/61 + 1/62)
        with self.assertRaises(ValueError):
            reciprocal_rank_fusion({}, 26)

    def test_policy_three_states_and_nonfinite(self):
        clear = Candidate(product(1), reranker_score=.9)
        weak = Candidate(product(2), reranker_score=.1)
        policy = DecisionPolicy()
        self.assertEqual(policy.decide([clear, weak], .9)[0], ResolutionStatus.matched)
        close = Candidate(product(2), reranker_score=.86)
        self.assertEqual(policy.decide([clear, close], .9)[0], ResolutionStatus.ambiguous)
        self.assertEqual(policy.decide([], .1)[0], ResolutionStatus.no_match)
        with self.assertRaises(ValueError):
            policy.decide([clear], math.nan)

    def test_calibration_round_trip_and_split_guards(self):
        artifact = train_logistic([((1, .3, 1, 2, 0), 1), ((0, 0, 0, 0, 2), 0)], "v1", split="train")
        self.assertEqual(artifact.feature_schema, FEATURE_SCHEMA)
        LogisticCalibrator(artifact)
        with self.assertRaises(ValueError):
            train_logistic([((1, .3, 1, 2, 0), 1)], "v1", split="test")
        with self.assertRaises(ValueError):
            select_policy([], split="test")
        broken = CalibrationArtifact("v", "m", "a", ("wrong",), (1,), 0)
        with self.assertRaises(ValueError):
            LogisticCalibrator(broken)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "artifact.json"
            artifact.save(path)
            self.assertEqual(CalibrationArtifact.load(path), artifact)


if __name__ == "__main__":
    unittest.main()
