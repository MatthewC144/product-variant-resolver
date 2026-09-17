# SEL-CRAWL1 — Design

Date:2026-09-16. Mode:Lite.

```text
explicit URL + exact host + permission flag
                 │
                 ▼
       fail-closed source guard
                 │
                 ▼
 Selenium Chrome (one page,text tables only)
                 │ DOM table snapshot
                 ▼
 header mapper + year filter + provenance
                 │ review-only records in memory
                 ▼
 portable OpenPyXL XLSX: Summary + Releases
```

The crawler is Python because the project and its tests already use Python. Selenium is an optional
`crawler` dependency so the FastAPI/Dual RAG runtime does not acquire a browser dependency. DOM extraction
uses JavaScript inside Selenium because Fandom-like tables may be rendered after page load;normalization is
a pure Python function so aliases,year filtering and error behavior can be unit-tested without a browser.

The target URL is never hardcoded. Exact-host comparison prevents an allowed hostname from silently
redirecting to an unrelated site. Fandom/Wikia suffixes are denied in code without an override. The command
also requires `--confirm-permission`;this records an operator assertion,not legal proof. CAPTCHA,access-denied
and rate-limit text stop the run. The first version reads one page only,so there is no crawl frontier or
request-rate scheduler to misconfigure.

The runtime workbook exporter uses OpenPyXL because it is publicly installable with the Python crawler extra.
`Summary` contains source/counter information and formulas for exported/error row counts. `Releases` keeps
normalized columns beside source location and raw JSON. A separate Codex-only artifact-tool builder creates
and renders the checked-in sample for visual QA;it is not a runtime dependency because the package is absent
from the public npm registry. This is a collection artifact,not a database input:canonical UUID/review approval
fields are intentionally absent.

Tests use synthetic table snapshots plus an opt-in real Chrome smoke test against a local HTML fixture whose
table appears after JavaScript runs. This proves Selenium behavior without contacting Fandom or the unknown
future target. The main risk is a different header vocabulary;the safe response is a visible “no eligible
table” failure,then a reviewed alias addition—not guessing column meaning from position alone.
