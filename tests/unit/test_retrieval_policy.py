import math
import tempfile
import unittest
from collections.abc import Sequence
from pathlib import Path
from uuid import UUID

from product_variant_resolver.calibration import (
    FEATURE_SCHEMA,
    CalibrationArtifact,
    LogisticCalibrator,
    train_logistic,
)
from product_variant_resolver.catalog import CatalogProduct
from product_variant_resolver.policy import DecisionPolicy, select_policy
from product_variant_resolver.rerank import NeuralPointwiseReranker
from product_variant_resolver.retrieval import Candidate, reciprocal_rank_fusion
from product_variant_resolver.schemas import ExtractedSignals, ProductView, ResolutionStatus


def product(number: int) -> CatalogProduct:
    return CatalogProduct(
        UUID(int=number), f"variant-{number}",
        ProductView(brand="Hot Wheels", casting=f"Car {number}"), (), (), ({"source": "test"},),
    )


class _RecordingScorer:
    version = "cross-encoder/test-revision"

    def __init__(self, scores: tuple[float, ...]) -> None:
        self.scores = scores
        self.pairs: tuple[tuple[str, str], ...] = ()

    def score_pairs(self, pairs: Sequence[tuple[str, str]]) -> tuple[float, ...]:
        self.pairs = tuple(pairs)
        return self.scores


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

    def test_neural_policy_does_not_treat_negative_logit_as_no_match(self):
        first = Candidate(product(1), reranker_score=-1.0)
        second = Candidate(product(2), reranker_score=-2.0)
        policy = DecisionPolicy(
            match_threshold=.8, no_match_threshold=0.0, margin_threshold=0.0,
            max_conflicts=5, require_positive_top_score=False, runtime_eligible=False,
        )
        self.assertEqual(
            policy.decide([first, second], .9)[0], ResolutionStatus.matched,
        )
        self.assertEqual(
            policy.decide([first, second], .5)[0], ResolutionStatus.ambiguous,
        )

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

    def test_neural_pointwise_adapter_batches_and_uses_frozen_ordering(self):
        first = Candidate(product(1), rrf_score=.02, rrf_rank=1)
        second_product = CatalogProduct(
            UUID(int=2), "variant-2",
            ProductView(brand="Hot Wheels", casting="Car 2", release_year=2025,
                        series="Mainline", collector_number="002"),
            ("Second Car",), ("HYX02",), ({"source": "test"},),
        )
        second = Candidate(second_product, rrf_score=.01, rrf_rank=2)
        scorer = _RecordingScorer((.1, .9))
        reranker = NeuralPointwiseReranker(scorer)
        signals = ExtractedSignals(normalized_title="raw query", tokens=["raw", "query"])

        ranked = reranker.rerank(signals, [first, second], query="Raw Query #002")

        self.assertEqual(reranker.version, "cross-encoder/test-revision")
        self.assertEqual([item.product.canonical_id for item in ranked], ["variant-2", "variant-1"])
        self.assertEqual([item.reranker_rank for item in ranked], [1, 2])
        self.assertEqual([item.reranker_score for item in ranked], [.9, .1])
        self.assertTrue(all(pair[0] == "Raw Query #002" for pair in scorer.pairs))
        self.assertIn("casting=car 2", scorer.pairs[1][1])
        self.assertIn("year=2025", scorer.pairs[1][1])
        self.assertIn("aliases=second car", scorer.pairs[1][1])
        self.assertIn("identifiers=hyx02", scorer.pairs[1][1])

    def test_neural_pointwise_adapter_uses_rrf_tie_break_and_fails_closed(self):
        first = Candidate(product(1), rrf_score=.01, rrf_rank=2)
        second = Candidate(product(2), rrf_score=.02, rrf_rank=1)
        signals = ExtractedSignals(normalized_title="query", tokens=["query"])
        ranked = NeuralPointwiseReranker(_RecordingScorer((.5, .5))).rerank(
            signals, [first, second],
        )
        self.assertEqual([item.product.canonical_id for item in ranked], ["variant-2", "variant-1"])
        with self.assertRaisesRegex(ValueError, "wrong score count"):
            NeuralPointwiseReranker(_RecordingScorer((.5,))).rerank(
                signals, [first, second],
            )
        with self.assertRaisesRegex(ValueError, "RRF rank"):
            NeuralPointwiseReranker(_RecordingScorer((.5,))).rerank(
                signals, [Candidate(product(3))],
            )


if __name__ == "__main__":
    unittest.main()
