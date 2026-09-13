# HRR-T3 — Fixed Development Execution Protocol

Mode: Lite / Lean Industrial. This protocol interprets the already frozen HRR-T1 selection
contract; it does not change queries, labels, configuration grid or thresholds.

## Inputs and retrieval

The evaluator accepts only development-pack SHA-256
`23589b23567220dbba0de959ec5223cf60365b1222320f3a372f1b156244dbe9` and manifest SHA-256
`3b62969a33e92c6d0d869d8271649417fa177c77b99f1568d1018ca31397f920`.
It verifies every non-v1 source reference from the manifest, constructs the existing 100 provisional
and 42 family documents, then executes seven floors by three character weights. It never opens
v1 files, including authoring-time query-pack references. Default signal extraction is shared
with runtime. Expected identities are not passed to retrieval; ordered Top-5 outputs are serialized
before computing development metrics.

Raw reports retain all 4,179 case/configuration pairs, typed identities and sparse/dense/character/
RRF ranks and scores. Metric checks bind rows to the unchanged pack, verify corpus identities,
finite scores, rank/source consistency and RRF arithmetic, then recompute raw positive/style hits,
MRR, merge hits, forbidden family hits and unrelated nonempty counts. Safety and minimum-quality
gates precede the MRR/Recall@1/higher-floor/lower-weight tie-break. Cost is an additional rejection
gate, not a reason to waive safety.

## Local cost method

Every configuration builds its own index, performs three warm-up queries, then measures the 199
case-ID-ordered development queries with `perf_counter_ns`, K=5, one process. Raw samples and
nearest-rank p50/p95 are recorded. The synthetic scale corpus has exactly 3,000 unique family
UUIDs with `Scale vehicle model NNNN` identities and `Synthetic casting NNNN` aliases. It intentionally
has common-word postings. After three warm-ups it measures the first 20 case-ID-ordered development
queries, records their IDs, and reports index/posting counts and nearest-rank p95. Host OS,
architecture, Python, processor and CPU count are disclosed by the report; the desktop is not an
isolated benchmark host.

These are warmed in-process retrieval measurements excluding startup/index construction,
serialization, HTTP, PostgreSQL, network, concurrent clients and production traffic. The synthetic
documents are not added to the real catalog and do not demonstrate real-catalog quality or growth.

## Preservation and freeze

Report checks recompute arithmetic from saved samples rather than pretend that new wall-clock
measurements must be byte-identical. Sources must still match the recorded hashes. Rendering uses
the validated JSON as its only source. FAIL writes evidence but leaves runtime artifacts untouched.
A qualifying winner uses a new, non-overwriting path and binds all 21 metric summaries plus the full
raw report checksum. T2 ephemeral experimental fixtures remain compatible; T3-generated artifacts
always include the additional validated selection-evidence binding. No qualifying winner means
no runtime activation, no v2 final-query authoring, and no T49 persistence.
