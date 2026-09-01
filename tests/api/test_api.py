import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from product_variant_resolver.api import create_app
from product_variant_resolver.config import Settings

ROOT = Path(__file__).resolve().parents[2]


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
        self.assertEqual(body["debug"]["model_versions"]["reranker"], "disabled")
        self.assertEqual(body["debug"]["model_versions"]["reranker_ablation"], "heuristic-v1")
        self.assertTrue(all(candidate["reranker_rank"] is None
                            and candidate["reranker_score"] is None
                            for candidate in body["debug"]["candidates"]))
        health = self.client.get("/health").json()
        self.assertEqual(health["dependencies"]["reranker"]["version"], "disabled")
        self.assertIn("ablation", health["dependencies"]["reranker"]["detail"])

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


if __name__ == "__main__":
    unittest.main()
