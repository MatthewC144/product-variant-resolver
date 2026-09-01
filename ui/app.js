"use strict";

(function bootstrap(globalObject) {
  const MIN_CANDIDATES = 1;
  const MAX_CANDIDATES = 25;
  const DEFAULT_CANDIDATES = 10;

  function asText(value, fallback = "—") {
    if (value === null || value === undefined || value === "") return fallback;
    if (Array.isArray(value)) return value.length ? value.map(String).join(", ") : fallback;
    return String(value);
  }

  function safeText(element, value, fallback = "—") {
    element.textContent = asText(value, fallback);
  }

  function clampCandidateLimit(value) {
    const parsed = Number.parseInt(String(value), 10);
    if (!Number.isFinite(parsed)) return DEFAULT_CANDIDATES;
    return Math.min(MAX_CANDIDATES, Math.max(MIN_CANDIDATES, parsed));
  }

  function buildResolveRequest(title, candidateLimit) {
    return {
      title: String(title).trim(),
      debug: true,
      debug_candidate_limit: clampCandidateLimit(candidateLimit),
    };
  }

  function formatNumber(value, digits = 4) {
    if (value === null || value === undefined || !Number.isFinite(Number(value))) return "—";
    return Number(value).toFixed(digits).replace(/\.?0+$/, "");
  }

  function rankScoreCell(documentObject, rank, score) {
    const wrapper = documentObject.createElement("span");
    wrapper.className = "rank-score";
    const rankLine = documentObject.createElement("span");
    const scoreLine = documentObject.createElement("span");
    safeText(rankLine, rank === null || rank === undefined ? "rank —" : `rank ${rank}`);
    safeText(scoreLine, score === null || score === undefined ? "score —" : `score ${formatNumber(score)}`);
    wrapper.append(rankLine, scoreLine);
    return wrapper;
  }

  function createDefinition(documentObject, label, value) {
    const wrapper = documentObject.createElement("div");
    const term = documentObject.createElement("dt");
    const detail = documentObject.createElement("dd");
    safeText(term, label);
    safeText(detail, value);
    wrapper.append(term, detail);
    return wrapper;
  }

  function errorMessage(payload, status) {
    if (payload && payload.error && payload.error.message) return asText(payload.error.message);
    return `The resolver returned HTTP ${status}.`;
  }

  function createController(documentObject, fetchImplementation) {
    const elements = {
      form: documentObject.getElementById("resolve-form"),
      title: documentObject.getElementById("title"),
      limit: documentObject.getElementById("candidate-limit"),
      submit: documentObject.getElementById("submit-button"),
      empty: documentObject.getElementById("empty-state"),
      error: documentObject.getElementById("error-panel"),
      errorMessage: documentObject.getElementById("error-message"),
      errorRequestId: documentObject.getElementById("error-request-id"),
      result: documentObject.getElementById("result"),
      requestStatus: documentObject.getElementById("request-status"),
      queryEcho: documentObject.getElementById("query-echo"),
      status: documentObject.getElementById("decision-status"),
      reason: documentObject.getElementById("decision-reason"),
      confidenceValue: documentObject.getElementById("confidence-value"),
      confidenceBar: documentObject.getElementById("confidence-bar"),
      identity: documentObject.getElementById("identity-details"),
      canonicalId: documentObject.getElementById("canonical-id"),
      canonicalUuid: documentObject.getElementById("canonical-uuid"),
      productSummary: documentObject.getElementById("product-summary"),
      policyVersion: documentObject.getElementById("policy-version"),
      abstention: documentObject.getElementById("abstention-note"),
      debugSections: documentObject.getElementById("debug-sections"),
      signals: documentObject.getElementById("signals-grid"),
      catalogVersion: documentObject.getElementById("catalog-version"),
      candidateCount: documentObject.getElementById("candidate-count"),
      candidatesEmpty: documentObject.getElementById("candidates-empty"),
      candidatesTable: documentObject.getElementById("candidates-table-wrap"),
      candidatesBody: documentObject.getElementById("candidates-body"),
      timings: documentObject.getElementById("timings-grid"),
      modelVersions: documentObject.getElementById("model-versions"),
    };

    let activeRequest = null;

    function setLoading(loading) {
      elements.submit.disabled = loading;
      elements.title.disabled = loading;
      elements.limit.disabled = loading;
      elements.submit.classList.toggle("is-loading", loading);
      elements.form.setAttribute("aria-busy", String(loading));
      safeText(elements.requestStatus, loading ? "Resolving title…" : "", "");
    }

    function resetView() {
      if (activeRequest) activeRequest.abort();
      activeRequest = null;
      setLoading(false);
      elements.empty.hidden = false;
      elements.error.hidden = true;
      elements.result.hidden = true;
      elements.debugSections.hidden = true;
      elements.errorMessage.textContent = "";
      elements.errorRequestId.textContent = "";
      elements.queryEcho.textContent = "";
      elements.candidatesBody.replaceChildren();
      elements.signals.replaceChildren();
      elements.timings.replaceChildren();
    }

    function renderDecision(payload, query) {
      const isMatch = payload.status === "matched";
      safeText(elements.queryEcho, query);
      safeText(elements.status, payload.status);
      elements.status.dataset.status = asText(payload.status, "unknown");
      safeText(elements.reason, payload.reason);

      const confidence = Math.min(1, Math.max(0, Number(payload.confidence) || 0));
      safeText(elements.confidenceValue, `${Math.round(confidence * 100)}%`);
      elements.confidenceBar.style.width = `${confidence * 100}%`;

      elements.identity.hidden = !isMatch;
      elements.abstention.hidden = isMatch;
      safeText(elements.policyVersion, payload.policy_version);
      if (isMatch) {
        safeText(elements.canonicalId, payload.canonical_id);
        safeText(elements.canonicalUuid, payload.canonical_uuid);
        const product = payload.product || {};
        const summary = [product.brand, product.casting, product.release_year, product.series, product.color]
          .filter((value) => value !== null && value !== undefined && value !== "")
          .map(String)
          .join(" · ");
        safeText(elements.productSummary, summary);
      }
    }

    function renderSignals(debugPayload) {
      const signals = debugPayload.signals || {};
      const fields = [
        ["Normalized title", signals.normalized_title],
        ["Tokens", signals.tokens],
        ["Year", signals.year],
        ["Collector no.", signals.collector_number],
        ["Series position", signals.series_position],
        ["Quantity", signals.quantity],
        ["Multipack", signals.multipack_hint === true ? "yes" : "no"],
        ["Color hints", signals.color_hints],
        ["Series hints", signals.series_hints],
        ["Parse warnings", signals.parse_warnings],
      ];
      elements.signals.replaceChildren(...fields.map(([label, value]) =>
        createDefinition(documentObject, label, value)));
      safeText(elements.catalogVersion, `catalog ${asText(debugPayload.catalog_version)}`);
    }

    function evidenceCell(candidate) {
      const wrapper = documentObject.createElement("div");
      wrapper.className = "evidence";
      const matches = Array.isArray(candidate.structured_matches) ? candidate.structured_matches : [];
      const conflicts = Array.isArray(candidate.structured_conflicts) ? candidate.structured_conflicts : [];
      if (!matches.length && !conflicts.length) {
        const none = documentObject.createElement("span");
        safeText(none, "—");
        wrapper.append(none);
      }
      for (const match of matches) {
        const line = documentObject.createElement("span");
        line.className = "match";
        safeText(line, `+ ${match}`);
        wrapper.append(line);
      }
      for (const conflict of conflicts) {
        const line = documentObject.createElement("span");
        line.className = "conflict";
        safeText(line, `− ${conflict}`);
        wrapper.append(line);
      }
      return wrapper;
    }

    function renderCandidates(debugPayload) {
      const candidates = Array.isArray(debugPayload.candidates) ? debugPayload.candidates : [];
      elements.candidatesBody.replaceChildren();
      for (const candidate of candidates) {
        const row = documentObject.createElement("tr");
        const identity = documentObject.createElement("td");
        safeText(identity, candidate.canonical_id);
        const columns = [
          [candidate.sparse_rank, candidate.sparse_score],
          [candidate.dense_rank, candidate.dense_score],
          [candidate.structured_rank, candidate.structured_score],
          [candidate.rrf_rank, candidate.rrf_score],
          [candidate.reranker_rank, candidate.reranker_score],
        ];
        row.append(identity);
        for (const [rank, score] of columns) {
          const cell = documentObject.createElement("td");
          cell.append(rankScoreCell(documentObject, rank, score));
          row.append(cell);
        }
        const evidence = documentObject.createElement("td");
        evidence.append(evidenceCell(candidate));
        row.append(evidence);
        elements.candidatesBody.append(row);
      }
      safeText(elements.candidateCount, `${candidates.length} returned`);
      elements.candidatesEmpty.hidden = candidates.length !== 0;
      elements.candidatesTable.hidden = candidates.length === 0;
    }

    function renderTimings(debugPayload) {
      const entries = Object.entries(debugPayload.timings_ms || {});
      const cards = entries.map(([name, value]) => {
        const card = documentObject.createElement("div");
        card.className = "timing";
        const label = documentObject.createElement("span");
        const timing = documentObject.createElement("strong");
        safeText(label, name);
        safeText(timing, `${formatNumber(value)} ms`);
        card.append(label, timing);
        return card;
      });
      elements.timings.replaceChildren(...cards);
      const versions = Object.entries(debugPayload.model_versions || {})
        .map(([name, version]) => `${name} ${version}`)
        .join(" · ");
      safeText(elements.modelVersions, versions);
    }

    function renderSuccess(payload, query) {
      elements.empty.hidden = true;
      elements.error.hidden = true;
      elements.result.hidden = false;
      renderDecision(payload, query);
      elements.debugSections.hidden = !payload.debug;
      if (payload.debug) {
        renderSignals(payload.debug);
        renderCandidates(payload.debug);
        renderTimings(payload.debug);
      }
      safeText(elements.requestStatus, `Resolution complete: ${asText(payload.status)}`);
    }

    function renderError(message, requestId = "") {
      elements.empty.hidden = true;
      elements.result.hidden = true;
      elements.error.hidden = false;
      safeText(elements.errorMessage, message);
      safeText(elements.errorRequestId, requestId ? `Request ID: ${requestId}` : "", "");
      safeText(elements.requestStatus, `Resolution failed: ${message}`);
    }

    async function submit(event) {
      if (event && typeof event.preventDefault === "function") event.preventDefault();
      const requestBody = buildResolveRequest(elements.title.value, elements.limit.value);
      elements.limit.value = String(requestBody.debug_candidate_limit);
      if (!requestBody.title) {
        renderError("Enter a marketplace title before resolving.");
        return;
      }

      if (activeRequest) activeRequest.abort();
      activeRequest = typeof AbortController === "undefined" ? null : new AbortController();
      setLoading(true);
      elements.error.hidden = true;

      try {
        const response = await fetchImplementation("/resolve", {
          method: "POST",
          headers: { "content-type": "application/json" },
          body: JSON.stringify(requestBody),
          signal: activeRequest ? activeRequest.signal : undefined,
        });
        let payload = null;
        try {
          payload = await response.json();
        } catch (_error) {
          payload = null;
        }
        if (!response.ok) {
          const requestId = payload && payload.error ? payload.error.request_id : "";
          renderError(errorMessage(payload, response.status), requestId);
          return;
        }
        renderSuccess(payload, requestBody.title);
      } catch (error) {
        if (!error || error.name !== "AbortError") {
          renderError("The local resolver could not be reached.");
        }
      } finally {
        activeRequest = null;
        setLoading(false);
      }
    }

    elements.form.addEventListener("submit", submit);
    elements.form.addEventListener("reset", () => globalObject.setTimeout(resetView, 0));
    resetView();
    return Object.freeze({ submit, resetView });
  }

  const publicApi = Object.freeze({
    asText,
    buildResolveRequest,
    clampCandidateLimit,
    createController,
    errorMessage,
    safeText,
  });
  globalObject.PVRDebugUI = publicApi;

  if (globalObject.document && globalObject.fetch) {
    const initialize = () => createController(globalObject.document, globalObject.fetch.bind(globalObject));
    if (globalObject.document.readyState === "loading") {
      globalObject.document.addEventListener("DOMContentLoaded", initialize, { once: true });
    } else {
      initialize();
    }
  }
}(globalThis));
