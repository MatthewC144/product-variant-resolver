from __future__ import annotations

import json
import subprocess
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
UI = ROOT / "ui"


def _assert_ui_assets_are_self_contained_and_use_safe_rendering() -> None:
    html = (UI / "index.html").read_text(encoding="utf-8")
    javascript = (UI / "app.js").read_text(encoding="utf-8")

    assert "./styles.css" in html
    assert "./app.js" in html
    assert "https://" not in html
    assert "http://" not in html
    assert "innerHTML" not in javascript
    assert "insertAdjacentHTML" not in javascript
    assert "eval(" not in javascript
    assert 'fetchImplementation("/resolve"' in javascript
    assert "textContent" in javascript


def _assert_ui_controller_smoke_states_and_contract() -> None:
    app_path = json.dumps(str(UI / "app.js"))
    harness = textwrap.dedent(
        f"""
        const assert = require("node:assert/strict");
        const fs = require("node:fs");
        const vm = require("node:vm");

        class ClassList {{
          constructor() {{ this.values = new Set(); }}
          toggle(name, force) {{
            if (force) this.values.add(name); else this.values.delete(name);
          }}
          contains(name) {{ return this.values.has(name); }}
        }}

        class Element {{
          constructor(id = "") {{
            this.id = id;
            this.textContent = "";
            this.value = "";
            this.hidden = false;
            this.disabled = false;
            this.children = [];
            this.dataset = {{}};
            this.style = {{}};
            this.className = "";
            this.classList = new ClassList();
            this.listeners = {{}};
            this.attributes = {{}};
          }}
          append(...children) {{ this.children.push(...children); }}
          replaceChildren(...children) {{ this.children = children; }}
          addEventListener(name, callback) {{ this.listeners[name] = callback; }}
          setAttribute(name, value) {{ this.attributes[name] = value; }}
        }}

        const ids = [
          "resolve-form", "title", "candidate-limit", "submit-button", "empty-state",
          "error-panel", "error-message", "error-request-id", "result", "request-status",
          "query-echo", "decision-status", "decision-reason", "confidence-value",
          "confidence-bar", "identity-details", "canonical-id", "canonical-uuid",
          "product-summary", "policy-version", "abstention-note", "debug-sections",
          "signals-grid", "catalog-version", "candidate-count", "candidates-empty",
          "candidates-table-wrap", "candidates-body", "human-catalog-version",
          "human-candidate-count", "human-candidates-empty", "human-candidates-table-wrap",
          "human-candidates-body", "timings-grid", "model-versions"
        ];

        function makeDocument() {{
          const elements = Object.fromEntries(ids.map((id) => [id, new Element(id)]));
          elements["candidate-limit"].value = "10";
          return {{
            elements,
            getElementById(id) {{ return elements[id]; }},
            createElement() {{ return new Element(); }},
          }};
        }}

        global.setTimeout = (callback) => callback();
        vm.runInThisContext(fs.readFileSync({app_path}, "utf8"), {{ filename: "app.js" }});
        const ui = global.PVRDebugUI;
        assert.deepEqual(ui.buildResolveRequest("  listing  ", 99), {{
          title: "listing", debug: true, debug_candidate_limit: 25,
        }});
        assert.equal(ui.clampCandidateLimit(0), 1);

        const baseDebug = {{
          signals: {{
            normalized_title: "hot wheels", tokens: ["hot", "wheels"], year: 2022,
            collector_number: "101", series_position: null, quantity: null,
            multipack_hint: false, color_hints: ["red"], parse_warnings: [],
          }},
          candidates: [{{
            canonical_uuid: "00000000-0000-0000-0000-000000000001",
            canonical_id: "safe-candidate", sparse_rank: 1, sparse_score: 0.9,
            dense_rank: 1, dense_score: 0.8, structured_rank: 1, structured_score: 2,
            rrf_rank: 1, rrf_score: 0.04, reranker_rank: 1, reranker_score: 0.97,
            structured_matches: ["year"], structured_conflicts: [],
          }}],
          human_knowledge_candidates: [{{
            casting_uuid: "00000000-0000-0000-0000-000000000002",
            casting_id: "human-hot-wheels-bmw-m3-gt2",
            provisional_variant_uuid: "00000000-0000-0000-0000-000000000003",
            provisional_variant_id: "human-hot-wheels-bmw-m3-gt2-neon-speeders",
            identity_status: "needs_canonical_review", brand: "Hot Wheels",
            casting: "BMW M3 GT2", series_label: "Neon Speeders",
            variant_label: "Neon Speeders",
            human_label_names: ['<img src=x onerror="global.pwned=true">'],
            example_initial_names: ["BMW M3 GT2"], source_case_ids: ["case-1"],
            sparse_rank: 1, sparse_score: 9.1, dense_rank: 1, dense_score: 0.9,
            rrf_rank: 1, rrf_score: 0.03, matched_tokens: ["bmw", "m3", "gt2"],
          }}],
          timings_ms: {{ total: 3.2 }}, catalog_version: "fixture-v1",
          human_catalog_version: "human-backed-catalog-v1",
          model_versions: {{ reranker: "heuristic-v1", human_knowledge: "human-knowledge-hybrid-v1" }},
        }};

        async function runSuccess(payload, title = "ordinary title") {{
          const document = makeDocument();
          document.elements.title.value = title;
          let captured = null;
          let release;
          const pending = new Promise((resolve) => {{ release = resolve; }});
          const fetchMock = async (url, options) => {{
            captured = {{ url, options }};
            await pending;
            return {{ ok: true, status: 200, json: async () => payload }};
          }};
          const controller = ui.createController(document, fetchMock);
          const completion = controller.submit({{ preventDefault() {{}} }});
          assert.equal(document.elements["submit-button"].disabled, true, "loading state");
          assert.equal(document.elements["resolve-form"].attributes["aria-busy"], "true");
          release();
          await completion;
          return {{ document, captured }};
        }}

        (async () => {{
          const markup = '<img src=x onerror="global.pwned=true">';
          const match = await runSuccess({{
            status: "matched", canonical_uuid: "00000000-0000-0000-0000-000000000001",
            canonical_id: "hot-wheels-chevy", confidence: 0.94,
            reason: "score_and_margin_above_threshold",
            product: {{ brand: "Hot Wheels", casting: "Chevy", release_year: 2022,
              series: "Mainline", color: "Red" }}, policy_version: "fixture-v1", debug: baseDebug,
          }}, markup);
          const request = JSON.parse(match.captured.options.body);
          assert.equal(match.captured.url, "/resolve");
          assert.equal(request.debug, true);
          assert.equal(request.debug_candidate_limit, 10);
          assert.equal(request.title, markup);
          assert.equal(match.document.elements["query-echo"].textContent, markup, "markup stays text");
          assert.equal(match.document.elements["decision-status"].textContent, "matched");
          assert.equal(match.document.elements["identity-details"].hidden, false);
          assert.equal(match.document.elements["candidates-body"].children.length, 1);
          assert.equal(match.document.elements["human-candidates-body"].children.length, 1);
          assert.equal(
            match.document.elements["human-candidates-body"].children[0].children[0].textContent,
            markup,
            "human-reviewed markup stays text",
          );
          assert.equal(global.pwned, undefined);

          const abstention = await runSuccess({{
            status: "ambiguous", canonical_uuid: null, canonical_id: null, confidence: 0.61,
            reason: "top1_top2_margin_too_small", product: null,
            policy_version: "fixture-v1", debug: {{
              ...baseDebug, candidates: [], human_knowledge_candidates: [],
            }},
          }});
          assert.equal(abstention.document.elements["decision-status"].textContent, "ambiguous");
          assert.equal(abstention.document.elements["identity-details"].hidden, true);
          assert.equal(abstention.document.elements["abstention-note"].hidden, false);
          assert.equal(abstention.document.elements["candidates-empty"].hidden, false);
          assert.equal(abstention.document.elements["human-candidates-empty"].hidden, false);

          const errorDocument = makeDocument();
          errorDocument.elements.title.value = "x";
          const errorController = ui.createController(errorDocument, async () => ({{
            ok: false, status: 422, json: async () => ({{
              error: {{ code: "invalid_request", message: "request validation failed",
                request_id: "request-123", details: [] }},
            }}),
          }}));
          await errorController.submit({{ preventDefault() {{}} }});
          assert.equal(errorDocument.elements["error-panel"].hidden, false);
          assert.equal(errorDocument.elements["error-message"].textContent, "request validation failed");
          assert.equal(errorDocument.elements["error-request-id"].textContent, "Request ID: request-123");

          console.log("ui smoke states passed");
        }})().catch((error) => {{ console.error(error); process.exit(1); }});
        """
    )
    completed = subprocess.run(
        ["node", "-e", harness],
        check=False,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "ui smoke states passed" in completed.stdout


class DebugUiTests(unittest.TestCase):
    def test_ui_assets_are_self_contained_and_use_safe_rendering(self) -> None:
        _assert_ui_assets_are_self_contained_and_use_safe_rendering()

    def test_ui_controller_smoke_states_and_contract(self) -> None:
        _assert_ui_controller_smoke_states_and_contract()


if __name__ == "__main__":
    unittest.main()
