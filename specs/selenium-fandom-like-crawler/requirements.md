# SEL-CRAWL1 — Configurable Fandom-like Selenium collector requirements

Date:2026-09-16. Mode:Lite. Status:implemented for one explicitly permitted page.

## Purpose

Provide a beginner-usable Selenium command that reads a different website whose catalog table resembles
Fandom,then exports reviewable `.xlsx`. It must not target Fandom itself or feed unreviewed rows into the
canonical catalog,PostgreSQL,Dual RAG evaluation or runtime.

## Observable requirements

### SC-R1 — Explicit source permission and exact host

WHEN remote collection is requested,THE COMMAND SHALL require an explicit permission confirmation,an
absolute HTTP(S) URL and an exact allowlisted host;embedded credentials and cross-host redirects SHALL fail.

### SC-R2 — Permanently refuse Fandom/Wikia

WHEN the requested or final host is `fandom.com`,`wikia.org` or a subdomain,THE COMMAND SHALL stop before
export and SHALL provide no override flag.

### SC-R3 — Read one dynamic catalog page with Selenium

WHEN the permitted page loads,THE COMMAND SHALL use Chrome Selenium,wait for a Fandom-like table,and read
text cells only;it SHALL disable image loading and SHALL NOT follow links,download files or solve challenges.

### SC-R4 — Normalize by headers and requested year

WHEN a table includes a model/casting header plus a toy/collector identifier header,THE COLLECTOR SHALL map
supported header aliases,filter explicit nonmatching years,separate trailing color-variant notes,and retain
color only when the table explicitly supplies it.

### SC-R5 — Preserve provenance and errors

WHEN a row is exported,THE COLLECTOR SHALL retain source URL/title/table/row,time,raw field JSON and parse
status;missing identifiers SHALL remain visible as errors rather than silently becoming verified products.

### SC-R6 — Produce a usable XLSX

WHEN at least one row is available,THE EXPORTER SHALL create `Summary` and `Releases` worksheets with
filters,frozen headers,source metadata,typed numeric fields and visible parse errors.

### SC-R7 — Bound and stop safely

WHEN no eligible table/year rows exist,the row limit is invalid,a challenge is detected,or navigation leaves
the allowed host,THE COMMAND SHALL fail without substituting another source. One run SHALL read one page and
at most5,000 rows.

### SC-R8 — Test without remote collection

WHEN the feature is verified,UNIT TESTS SHALL use synthetic snapshots and the browser smoke test SHALL use
only a local JavaScript-rendered fixture;tests SHALL make no request to Fandom or the future target website.

## Out of scope

Fandom access,multi-page crawling,login,CAPTCHA/proxy bypass,robots/terms discovery,image/OCR,canonical
promotion,PostgreSQL ingestion,Dual RAG retraining and claiming the local fixture as real catalog data.
