# Decision — one-page Selenium collector with separate XLSX exporter

Date:2026-09-16. Status:accepted for SEL-CRAWL1 Lite.

## Problem

The project needs a reusable collector for a non-Fandom site that uses the same style of JavaScript-rendered
wiki tables. The target URL is not yet known,so code cannot safely bind to one schema or permission policy.
The output must be understandable to a beginner and must not silently enter the existing Dual RAG catalog.

## Decision

Use Python Selenium for one explicit URL,an exact host allowlist and a mandatory operator permission flag.
Permanently deny Fandom/Wikia. Extract text-table snapshots in the browser,then normalize them with a pure
Python header mapper. Use publicly available OpenPyXL to build a two-sheet `.xlsx`;retain a separate
artifact-tool builder only for Codex-side rendering and sample verification.

## Why

Selenium matches the requested technology and handles tables inserted after JavaScript runs. Separating DOM
access from normalization makes most behavior fast and deterministic to test. Header mapping is safer than
fixed column positions when the target reorders fields. A one-page boundary avoids an implicit crawl frontier
before the real site's rules,pagination and volume are known. XLSX keeps raw fields and source positions beside
normalized values,which lets a human review color and other variant attributes before database work.

## Alternatives and costs

The existing MediaWiki API adapter was not reused because the new site may expose only rendered HTML and the
user specifically requested Selenium. A generic recursive crawler was rejected because the real host and
allowed path set are unknown. Artifact-tool alone was rejected as the runtime writer after npm returned404 for
its package:that would produce code that worked only inside Codex. OpenPyXL keeps the GitHub clone runnable;
artifact-tool still supplies the required inspect/render QA for the delivered sample. The first release does
not expand pagination or database ingestion. Those become separate decisions after one real page is reviewed.
