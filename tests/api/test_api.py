import json
import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from product_variant_resolver.api import create_app
from product_variant_resolver.config import Settings
from product_variant_resolver.retrieval import RetrievalUnavailable

ROOT = Path(__file__).resolve().parents[2]
FAMILY_PROJECTION = ROOT / "data/review_family_knowledge.json"
FAMILY_MANIFEST = ROOT / "data/review_family_knowledge_manifest.json"


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        settings = Settings(
            catalog_path=ROOT / "data/catalog.json",
            benchmark_path=ROOT / "data/benchmark.json",
            ui_path=ROOT / "ui",
        )
        cls.client = TestClient(create_app(settings))

    def test_same_origin_debug_ui_and_static_assets(self):
        page = self.client.get("/")
        self.assertEqual(page.status_code, 200)
        self.assertTrue(page.headers["content-type"].startswith("text/html"))
        self.assertIn('src="./app.js"', page.text)
        self.assertIn('href="./styles.css"', page.text)
        self.assertIn('id="resolve-form"', page.text)

        script = self.client.get("/app.js")
        stylesheet = self.client.get("/styles.css")
        self.assertEqual(script.status_code, 200)
        self.assertIn("javascript", script.headers["content-type"])
        self.assertEqual(stylesheet.status_code, 200)
        self.assertIn("text/css", stylesheet.headers["content-type"])
        self.assertIn('fetchImplementation("/resolve"', script.text)
        self.assertNotIn("innerHTML", script.text)

    def test_static_mount_does_not_shadow_api_or_allow_path_escape(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        self.assertEqual(self.client.get("/openapi.json").status_code, 200)
        response = self.client.post("/resolve", json={"title": "2022 Chevy Nomad Red #101"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get("/../pyproject.toml").status_code, 404)

    def test_health_and_default_debug_omission(self):
        self.assertEqual(self.client.get("/health").status_code, 200)
        response = self.client.post("/resolve", json={"title": "2022 Chevy Nomad Red #101"})
        self.assertEqual(response.status_code, 200)
        self.assertNotIn("debug", response.json())

    def test_request_correlation_and_privacy_safe_logging(self):
        raw_title = "2022 Chevy Nomad Red #101 do-not-log-this"
        with self.assertLogs("product_variant_resolver.resolver", level="INFO") as captured:
            response = self.client.post(
                "/resolve", json={"title": raw_title}, headers={"x-request-id": "trace-123"},
            )
        self.assertEqual(response.headers["x-request-id"], "trace-123")
        logs = "\n".join(captured.output)
        self.assertIn("trace-123", logs)
        self.assertNotIn(raw_title, logs)

        rejected = self.client.get("/health", headers={"x-request-id": "bad id with spaces"})
        self.assertNotEqual(rejected.headers["x-request-id"], "bad id with spaces")

    def test_debug_bounds_and_lowercase_status(self):
        response = self.client.post("/resolve", json={
            "title": "2022 Chevy Nomad Red #101", "debug": True, "debug_candidate_limit": 2,
        })
        body = response.json()
        self.assertIn(body["status"], {"matched", "ambiguous", "no_match"})
        self.assertEqual(body["policy_version"], "fixture-v1-rrf-trained-v2")
        self.assertLessEqual(len(body["debug"]["candidates"]), 2)
        self.assertLessEqual(len(body["debug"]["human_knowledge_candidates"]), 2)
        self.assertEqual(body["debug"]["human_catalog_version"], "human-backed-catalog-v1")
        self.assertEqual(
            body["debug"]["review_family_knowledge_version"],
            "review-family-knowledge-fandom-2025-r790665-v1",
        )
        self.assertTrue(all(
            candidate["knowledge_type"] in {"provisional_variant", "review_family"}
            for candidate in body["debug"]["human_knowledge_candidates"]
        ))
        self.assertEqual(
            body["debug"]["model_versions"]["human_knowledge"],
            "human-knowledge-hybrid-v2",
        )
        self.assertEqual(body["debug"]["model_versions"]["sparse"], "token-index-v1")
        self.assertEqual(body["debug"]["model_versions"]["dense"], "hashing-v1")
        self.assertEqual(body["debug"]["model_versions"]["reranker"], "disabled")
        self.assertEqual(body["debug"]["model_versions"]["reranker_ablation"], "heuristic-v1")
        self.assertTrue(all(candidate["reranker_rank"] is None
                            and candidate["reranker_score"] is None
                            for candidate in body["debug"]["candidates"]))
        health = self.client.get("/health").json()
        self.assertEqual(health["dependencies"]["reranker"]["version"], "disabled")
        self.assertIn("ablation", health["dependencies"]["reranker"]["detail"])
        self.assertEqual(
            health["dependencies"]["human_catalog"]["version"],
            "human-backed-catalog-v1",
        )
        self.assertEqual(
            health["dependencies"]["human_knowledge_index"]["version"],
            "human-knowledge-hybrid-v2",
        )
        self.assertEqual(
            health["dependencies"]["review_family_knowledge"]["version"],
            "review-family-knowledge-fandom-2025-r790665-v1",
        )
        self.assertIn(
            "never canonical identity",
            health["dependencies"]["review_family_knowledge"]["detail"],
        )

    def test_reranker_is_explicit_opt_in(self):
        settings = Settings(
            catalog_path=ROOT / "data/catalog.json",
            benchmark_path=ROOT / "data/benchmark.json",
            ui_path=ROOT / "ui",
            reranker_enabled=True,
            policy_version="fixture-v1-heuristic-opt-in-v1",
        )
        client = TestClient(create_app(settings))
        health = client.get("/health").json()
        self.assertEqual(health["dependencies"]["reranker"]["version"], "heuristic-v1")
        response = client.post("/resolve", json={
            "title": "2022 Chevy Nomad Red #101", "debug": True,
        }).json()
        self.assertEqual(response["debug"]["model_versions"]["reranker"], "heuristic-v1")
        self.assertTrue(all(candidate["reranker_rank"] is not None
                            and candidate["reranker_score"] is not None
                            for candidate in response["debug"]["candidates"]))

    def test_validation_error_contracts(self):
        cases = [
            ({"title": " "}, 422), ({"title": "x" * 501}, 422),
            ({"title": "ok", "unknown": 1}, 422), ({"title": "ok", "debug_candidate_limit": 26}, 422),
        ]
        for body, status in cases:
            response = self.client.post("/resolve", json=body)
            self.assertEqual(response.status_code, status)
            self.assertEqual(set(response.json()), {"error"})
            self.assertNotIn("Traceback", response.text)
        malformed = self.client.post("/resolve", content="{", headers={"content-type": "application/json"})
        self.assertEqual(malformed.status_code, 400)
        unsupported = self.client.post("/resolve", content="hello", headers={"content-type": "text/plain"})
        self.assertEqual(unsupported.status_code, 415)

    def test_not_ready_fails_closed(self):
        settings = Settings(catalog_path=ROOT / "data/missing.json", ui_path=ROOT / "ui")
        client = TestClient(create_app(settings))
        self.assertEqual(client.get("/health").status_code, 503)
        self.assertEqual(client.get("/").status_code, 200)
        response = client.post("/resolve", json={"title": "anything"})
        self.assertEqual(response.status_code, 503)
        self.assertIsNone(response.json().get("canonical_uuid"))

    def test_missing_human_catalog_fails_closed(self):
        settings = Settings(
            catalog_path=ROOT / "data/catalog.json",
            human_catalog_path=ROOT / "data/missing-human-catalog.json",
            ui_path=ROOT / "ui",
        )
        client = TestClient(create_app(settings))
        health = client.get("/health")
        self.assertEqual(health.status_code, 503)
        response = client.post("/resolve", json={"title": "BMW M3 GT2"})
        self.assertEqual(response.status_code, 503)
        self.assertIsNone(response.json().get("canonical_uuid"))

    def test_missing_or_corrupt_review_family_projection_fails_closed(self):
        missing = Settings(
            catalog_path=ROOT / "data/catalog.json",
            human_catalog_path=ROOT / "data/human_backed_catalog.json",
            review_family_knowledge_path=ROOT / "data/missing-family-knowledge.json",
            review_family_knowledge_manifest_path=FAMILY_MANIFEST,
            ui_path=ROOT / "ui",
        )
        missing_client = TestClient(create_app(missing))
        missing_health = missing_client.get("/health")
        self.assertEqual(missing_health.status_code, 503)
        self.assertFalse(
            missing_health.json()["dependencies"]["review_family_knowledge"]["ready"]
        )
        response = missing_client.post("/resolve", json={"title": "Proton Saga"})
        self.assertEqual(response.status_code, 503)
        self.assertIsNone(response.json().get("canonical_uuid"))

        with tempfile.TemporaryDirectory() as directory:
            manifest = json.loads(FAMILY_MANIFEST.read_text(encoding="utf-8"))
            manifest["projection_sha256"] = "0" * 64
            manifest_path = Path(directory) / FAMILY_MANIFEST.name
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            corrupt = Settings(
                catalog_path=ROOT / "data/catalog.json",
                human_catalog_path=ROOT / "data/human_backed_catalog.json",
                review_family_knowledge_path=FAMILY_PROJECTION,
                review_family_knowledge_manifest_path=manifest_path,
                ui_path=ROOT / "ui",
            )
            corrupt_client = TestClient(create_app(corrupt))
            self.assertEqual(corrupt_client.get("/health").status_code, 503)
            response = corrupt_client.post("/resolve", json={"title": "Proton Saga"})
            self.assertEqual(response.status_code, 503)
            self.assertIsNone(response.json().get("canonical_uuid"))

    def test_discriminated_family_debug_candidate_remains_noncanonical(self):
        response = self.client.post(
            "/resolve",
            json={
                "title": "Hot Wheels Proton Saga",
                "debug": True,
                "debug_candidate_limit": 1,
            },
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "no_match")
        self.assertIsNone(body["canonical_uuid"])
        self.assertIsNone(body["canonical_id"])
        self.assertEqual(len(body["debug"]["human_knowledge_candidates"]), 1)
        family = body["debug"]["human_knowledge_candidates"][0]
        self.assertEqual(family["knowledge_type"], "review_family")
        self.assertEqual(family["casting"], "Proton Saga")
        self.assertEqual(
            family["identity_status"], "family_accepted_variants_unreviewed"
        )
        self.assertEqual(family["aliases"], ["Proton Saga"])
        self.assertIn("review_family_uuid", family)
        self.assertIn("review_family_id", family)
        self.assertIn("source_record_ids", family)
        for variant_only_field in (
            "casting_uuid",
            "casting_id",
            "provisional_variant_uuid",
            "provisional_variant_id",
            "series_label",
            "variant_label",
            "human_label_names",
            "example_initial_names",
            "source_case_ids",
        ):
            self.assertNotIn(variant_only_field, family)
        self.assertEqual(
            body["debug"]["review_family_knowledge_version"],
            "review-family-knowledge-fandom-2025-r790665-v1",
        )
        self.assertEqual(
            body["debug"]["model_versions"]["human_knowledge"],
            "human-knowledge-hybrid-v2",
        )

    def test_discriminated_variant_debug_candidate_has_no_family_identity(self):
        response = self.client.post(
            "/resolve",
            json={
                "title": "Hot Wheels BMW M3 GT2 Neon Speeders",
                "debug": True,
                "debug_candidate_limit": 1,
            },
        )
        self.assertEqual(response.status_code, 200)
        candidate = response.json()["debug"]["human_knowledge_candidates"][0]
        self.assertEqual(candidate["knowledge_type"], "provisional_variant")
        self.assertEqual(candidate["casting"], "BMW M3 GT2")
        self.assertIn("provisional_variant_uuid", candidate)
        self.assertIn("human_label_names", candidate)
        for family_only_field in (
            "review_family_uuid",
            "review_family_id",
            "aliases",
            "source_record_ids",
        ):
            self.assertNotIn(family_only_field, candidate)

    def test_openapi_publishes_human_knowledge_type_discriminator(self):
        schemas = self.client.get("/openapi.json").json()["components"]["schemas"]
        items = schemas["DebugPayload"]["properties"]["human_knowledge_candidates"][
            "items"
        ]
        self.assertEqual(items["discriminator"]["propertyName"], "knowledge_type")
        self.assertEqual(
            set(items["discriminator"]["mapping"]),
            {"provisional_variant", "review_family"},
        )
        self.assertEqual(len(items["oneOf"]), 2)

    def test_postgres_backend_without_database_fails_readiness(self):
        settings = Settings(
            catalog_path=ROOT / "data/catalog.json",
            human_catalog_path=ROOT / "data/human_backed_catalog.json",
            ui_path=ROOT / "ui",
            database_url="postgresql+psycopg://pvr:pvr@127.0.0.1:1/pvr",
            backend="postgres",
        )
        client = TestClient(create_app(settings))
        self.assertEqual(client.get("/health").status_code, 503)
        self.assertEqual(
            client.post("/resolve", json={"title": "Nomad"}).status_code,
            503,
        )

    def test_runtime_retrieval_failure_maps_to_dependency_unavailable(self):
        class FailingService:
            def resolve(self, payload, *, request_id=None):
                raise RetrievalUnavailable("database connection lost")

        client = TestClient(create_app(
            Settings(ui_path=ROOT / "ui"),
            service_factory=lambda _settings: FailingService(),  # type: ignore[arg-type]
        ))
        response = client.post("/resolve", json={"title": "Nomad"})
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["error"]["code"], "dependency_unavailable")


if __name__ == "__main__":
    unittest.main()
