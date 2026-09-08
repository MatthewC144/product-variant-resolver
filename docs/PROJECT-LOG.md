# Project Log

## 2026-09-08 — Batch 02 advances the queue and catches a same-name casting conflict

### What was executed and what problem it solves

T36 left a cumulative review queue with fourteen completed family decisions and thirty-nine still
pending. T37 continues the research from that exact checkpoint. It selects the first ten pending
priority-2 families in the T36 queue, examines one casting-specific Hot Wheels Wiki page plus at
least one publisher outside Fandom for each name, and emits a new frozen review packet. This avoids
both re-researching the ten batch-01 families and treating “not found in our small catalog” as
proof that a new casting should be created.

The observable result is a ten-family / eighteen-release batch. Nine names have sufficient
two-source, exact-name evidence for a machine `create_new_casting` recommendation. The tenth,
`Batman and Robin Batmobile`, demonstrates why exact text is not enough: the current mainline name
is also used by a separate 2004 100% Hot Wheels casting tool G5513. That family remains held until
the staged releases can be mapped to a tool-specific lineage. All ten reviewer confirmations are
still pending, every release variant is held, and promotion eligibility remains zero.

### Code changes and why they were made

`priority-2-batch-02-source-notes.json` is the human-readable research input in structured form. It
keeps the queue family ID and exact name beside concise observations and HTTPS evidence. Sources
include Mattel Consumer Services and independent collector/catalog publishers such as Orange Track
Diecast, 164Custom, Hot Wheels Collectors News, Hot Wheels Database, and HW Treasure. The Batman
record additionally stores the related 2004 page and its G5513 distinction, so the hold is based on
an explicit conflicting identity rather than a vague lack of confidence.

`build_fandom_priority_two_research.py` was extended from a batch-01-only command to a shared
batch-aware builder. `--batch 2` binds the input to
`priority-2-batch-01-adjudicated-queue.json` and its manifest, then names the outputs with the
batch-02 prefix and version. Default invocation remains batch 01, so the existing frozen contract
and checksums remain compatible. The validator now accepts `homonymous_castings` as a distinct
source classification and maps it to a mandatory hold; the older `disambiguation` wording remains
unchanged so batch 01 reproduces byte for byte.

The generated JSON stores the ten machine recommendations, complete source rows, evidence hosts,
pending reviewer blocks, and explicit family-versus-variant scope. The Markdown report presents
the same information for owner review. The manifest binds the T36 queue, its manifest, the new
source notes, research JSON, and report with SHA-256 checksums. A dedicated six-test module verifies
later-batch selection, counts, evidence hosts, the Batman homonym, non-promotion boundaries, and
deterministic outputs without weakening the six existing batch-01 tests.

### Technical choices, alternatives, and trade-offs

The later batch reads the latest cumulative queue instead of the original T34 queue. A manual
“skip the first ten” convention would be shorter code, but it would become wrong as soon as a hold
is revisited or batches are applied in a different order. Selecting records whose actual reviewer
status is still `pending` lets the decision artifact, rather than positional memory, define what
work remains. The trade-off is that each research batch is cryptographically coupled to the latest
queue checkpoint and must be rebuilt or deliberately migrated if that upstream artifact changes.

The evidence policy remains two-source rather than manufacturer-only. Manufacturer documentation
is preferred where available, but historical and fantasy castings are often documented more
completely by established collector catalogs. Requiring an exact-name corroboration outside
Fandom reduces single-source dependence without falsely claiming those publishers independently
verified every physical detail. Remote pages can change, which is why the repository freezes URLs,
claims, date, transformed outputs, and checksums rather than pretending it owns an immutable copy
of every source page.

`homonymous_castings` is separate from `disambiguation`. A disambiguation page openly lists several
tools under one title; a homonym can have a dedicated page for the current tool while another page
uses effectively the same display name. Treating both as safe creations would collapse physical
lineages. Treating every related scale or premium release as a conflict would be overly strict, so
the hold is used only where evidence shows a separate casting tool with the same name; Donut
Drifter's separately named Hot Wheels XL product, for example, does not erase the dedicated 1:64
identity.

### Decision changes

Before T37, the builder understood only a dedicated single-casting page or an explicit
disambiguation page, and only batch 01 could be selected from the command line. It now models a
third failure-safe case—distinct tools sharing a display name—and can deterministically build
either research batch from its proper upstream queue. This is a schema-compatible extension:
batch-01 data and output hashes did not change.

Nine new names now have source-backed machine recommendations, but none has moved to completed
review status: `'94 Audi Avant RS2`, `Alpha Pursuit`, `Bogzilla`, `Crescendo`, `Custom '53 Chevy`,
`Custom Cadillac Fleetwood`, `Deora III`, `DMC DeLorean`, and `Donut Drifter`. Batman and Robin
Batmobile is explicitly held. The cumulative adjudication queue itself remains at fourteen
completed / thirty-nine pending because research does not impersonate an owner decision.

### Verification evidence

The combined batch-01 and batch-02 focused suite passed 12/12. It proves that batch 02 equals the
next ten pending items in the T36 queue and excludes a completed batch-01 family; that the output
contains ten families, eighteen rows, nine proposed creations, and one homonymous hold; that the
separate 2004 G5513 tool is retained in evidence; that creation recommendations span Fandom plus a
different host; and that all reviewer, variant, and promotion boundaries remain closed.

Both `python3 scripts/build_fandom_priority_two_research.py --batch 1 --check` and `--batch 2
--check` passed. The batch-02 research checksum is
`e0814c8017361049c2fa3b712198a22968e9818c2db273c49af668c2639050dc`; its readable report checksum
is `86444256ded953b6ed5e329dccfdf531e5f2565df7212370178fb1a45d81a7ca`; and its upstream T36 queue
checksum is `2b82ca5023439857f186aa0ab122f0b4511290bb4d1303ac533df5c96fbc6790`.

The complete host suite passed 117/117 on the available Python 3.14.6 interpreter. Fixture and
Wiki-pilot validation, T31–T37 deterministic regeneration, Python compilation, default and
PostgreSQL-profile Compose configuration, and `git diff --check` all passed. The host suite emitted
the already documented Starlette TestClient deprecation warning because this machine-wide Python
3.14 environment still exposes legacy `httpx`; the project's constrained Python 3.12 environment
uses `httpx2` and was previously verified warning-free. T37 changed no runtime dependency, and this
research run does not upgrade web-page review into live database or resolver evidence.

### Incomplete work, risks, and next step

These are AI-assisted research recommendations, not human labels. Source accuracy and future page
changes remain risks, and the Batman evidence proves only that the name is ambiguous between tools;
it does not yet prove which tool HYW60 and HYX61 represent. No accepted catalog family, stable
entity ID, canonical variant, PostgreSQL row, or searchable Dual-RAG record was created.

The next immediate task is T38: present this exact ten-item batch to the project owner, record the
owner's accept/hold decisions in a separate attributable file, validate complete agreement and
scope, and derive a new cumulative queue. Only then should batch 03 select the next pending ten.

## 2026-09-08 — Owner approval converts batch-01 research into ten attributable family decisions

### What was executed and what problem it solves

T35 answered the research question for ten possible-new families, but deliberately left the
reviewer fields empty. The project owner then asked to execute the stated next step after being
shown the exact proposal: approve nine `create_new_casting` family outcomes and keep `'55 Chevy`
on hold. T36 records that response as a separate decision event and calculates the new cumulative
queue state.

This closes the gap between “a machine found supporting sources” and “the project owner accepted
the family decision.” It also prevents the short approval message from being interpreted too
broadly. The resulting authority covers exactly the ten displayed recommendations and only casting
family identity; it does not approve colors, releases, canonical UUIDs, database rows, or the other
39 families.

### Code changes and why they were made

`priority-2-batch-01-decisions.json` records the stable batch ID, `project_owner` role, UTC time,
conversation provenance, and ten decisions. Each item cites its T35 research packet and external
evidence, states a family-specific reason, uses `casting_family_only`, has no existing-family
target, and keeps `variant_decision=hold`.

`apply_fandom_priority_two_decisions.py` verifies both the T34 queue checksum and T35 research
checksum before accepting the decision file. It requires valid batch attribution, unique complete
coverage of all research packets, an outcome identical to the approved recommendation, a direct
packet reference, family-only scope, and variant hold. For each creation it rechecks that the Wiki
page was classified as one casting, at least one independent source exists, evidence spans two
hosts, and the earlier exact-match indexes contain no catalog family.

The applier deep-copies the T34 queue and preserves its four priority-1 merge decisions. It replaces
the older single batch field with an ordered two-entry decision history, applies the ten new
decisions, recalculates cumulative counts, and writes a new batch-specific queue, Markdown result,
and checksum manifest. The older all-pending and T34 four-decision queues remain unchanged, so each
stage can be reproduced and compared.

### Technical choices, alternatives, and trade-offs

The code treats approval as an append-only decision layer instead of immediately materializing
nine catalog objects. This adds another artifact in the chain, but it keeps three very different
claims separate: a family probably exists, the owner accepts that conclusion, and a canonical
variant is safe for runtime matching. Collapsing those claims would make source review look like
product-level ground truth.

Complete batch coverage is required rather than accepting a partial list. The user's authorization
referred to the previously displayed ten-item proposal as one set, so all ten outcomes must be
present exactly once. A future correction can use another explicit decision event; silently
dropping an item or changing one recommendation during application is rejected.

The new output has an explicit filename rather than overwriting `adjudicated-queue.json`. This is
slightly more verbose for downstream scripts, but it gives Git a clear audit trail and lets T37
select from the true latest queue without destroying the T34 checkpoint.

### Decision changes

Nine families have moved from machine recommendation to accepted project-owner decisions: 1988
Jeep Wagoneer, 2020 Ram 1500 Rebel, `'21 Ford Bronco`, `'22 Ford Maverick Custom`, `'66 Buick
Riviera`, `'69 Corvette Racer`, `'80 El Camino`, `'87 Audi quattro`, and `'90 Honda Civic EF`.
`'55 Chevy` has moved from proposed hold to an accepted hold because the exact casting lineage is
still unresolved.

The cumulative review queue now contains fourteen completed decisions: four merges from T34, nine
new-family decisions, and one hold. Thirty-nine priority-2 families remain pending. This is not yet
a catalog-count increase; the nine accepted families still exist only as decisions attached to
their source rows.

### Verification evidence

Six focused tests verify the 14/39 cumulative counts, nine-create/one-hold batch, attribution,
family/variant boundary, preservation of all four earlier merges and both decision batches,
fail-closed changed outcome, fail-closed incomplete coverage, hashes, and deterministic rebuild.
The first focused run failed because the new test expected the wrong historical Priority 1 batch
ID. Inspection showed that the product data correctly retained
`fandom-2025-priority-1-owner-confirmation-v1`; the test expectation was corrected and all focused
tests then passed 6/6.

The complete host suite passed 111/111. Fixture and Fandom staging validation, T31–T36 deterministic
checks, Python compilation, default and PostgreSQL Compose configuration, and whitespace checks all
passed. The new cumulative queue checksum is
`2b82ca5023439857f186aa0ab122f0b4511290bb4d1303ac533df5c96fbc6790`; its readable report checksum
is `fe00de56e8c425fa5f80c06722deb702f4fb357d1e40495efb4548830bcfaff9`.

### Incomplete work, risks, and next step

The conversation provenance is auditable inside the repository but not a cryptographic signature.
The underlying external sources can also change. More importantly, the accepted creations have not
been assigned separate catalog entity IDs or made searchable; doing so safely needs its own schema
and must not turn unknown release colors into canonical variants.

The next immediate task is T37: use the T36 cumulative queue to research the next ten of the 39
pending priority-2 families. Keeping research and adjudication in repeated small batches will expose
more ambiguous names before any larger catalog materialization or 3,000-row ingestion begins.

## 2026-09-08 — The first ten possible-new families now have bounded source evidence

### What was executed and what problem it solves

T34 left 49 priority-2 names in the honest state “not found in our current catalogs.” That state
does not prove a name represents a new casting: it can also mean the local catalog is incomplete,
the name is an alias, or one display name hides several physical casting tools. T35 researches the
first ten pending families in the adjudicated queue instead of treating absence as proof.

The research found nine names that each resolve to one dedicated Hot Wheels Wiki casting page and
also appear under the exact Hot Wheels casting name at a publisher outside Fandom. It also found a
counterexample that validates the need for this step. `'55 Chevy` is a disambiguation title for
three distinct tools introduced in 1982, 1998, and 2006; creating one family from that name would
erase a real identity distinction. Batch 01 therefore proposes nine `create_new_casting` outcomes
and one `hold`, while leaving all ten reviewer confirmations pending.

### Code changes and why they were made

`priority-2-batch-01-source-notes.json` records the bounded research input: stable queue ID, exact
casting name, dedicated Wiki page classification, non-Fandom publisher, source type, HTTPS URL,
and a concise paraphrase of the observed claim. The file states that the process was AI-assisted
and does not attribute any identity decision to a human. It stores text notes only and downloads no
images.

`build_fandom_priority_two_research.py` first verifies that the derived T34 queue still matches its
manifest. It then selects exactly the first ten priority-2 families whose reviewer status is still
pending. The source notes must cover those same IDs and names in the same order. Each family must
have a Fandom casting-page classification and at least one exact-name source from another host; a
Fandom URL presented as “independent” is rejected.

The recommendation is derived from this narrow rule rather than typed into the notes. One
`single_casting` page plus the independent confirmation yields `create_new_casting`; a
`disambiguation` page yields `hold`. The generated JSON, readable Markdown report, and manifest
preserve the 19 staged release rows, source links, decision reason, pending reviewer block, variant
hold, and zero promotion eligibility. Six tests lock selection, counts, the `'55 Chevy` exception,
source independence, fail-closed behavior, checksums, and deterministic regeneration.

### Technical choices, alternatives, and trade-offs

A two-source rule was chosen because the yearly list and each casting page share the same community
ecosystem. Requiring another publisher does not make the evidence infallible, but it is materially
stronger than copying a name from one table. Manufacturer evidence is preferred when available;
established collector databases and archived Hot Wheels case documents are used for older or less
visible models where a current Mattel product page is not available.

The batch size is ten so a non-programmer can inspect the report without reviewing all 49 names in
one sitting. The cost is more batches and manifests. That cost is intentional: small diffs make it
easier to notice exceptions such as the three `'55 Chevy` tools before an incorrect family becomes
part of the catalog.

Remote pages were not copied wholesale. The repository freezes concise observations and URLs,
which avoids unnecessary third-party content duplication and keeps the evidence readable. The
trade-off is that a later audit may find that a remote page has changed or disappeared; the research
date and checksummed notes make that limitation visible instead of implying a permanent snapshot.

### Decision changes

Before T35, all 49 unmatched groups had the same undifferentiated “research required” state. The
first ten now have evidence-backed machine recommendations, but they have not become reviewer
decisions. This distinction matters: the project owner has not yet accepted the nine creations or
the one hold, so the adjudicated queue correctly continues to show 49 pending priority-2 decisions.

The identity boundary is unchanged. A proposed family creation answers only whether a distinct
casting family appears to exist. It does not validate the 2025 color, series, collector number,
toy-number release identity, or any canonical UUID. All 19 release rows therefore remain held.

### Verification evidence

The new batch contains exactly 10 families and 19 Wiki rows in deterministic queue order. Nine
packets propose `create_new_casting`; the single `hold` is `'55 Chevy`. All packets have at least
two distinct source hosts, reviewer status `pending`, variant decision `hold`, and
`promotion_eligible=false`. The focused tests passed 6/6, and the full host suite passed 105/105.

Fixture validation, Wiki staging validation, T31–T35 deterministic checks, Python compilation,
both default and PostgreSQL Compose configurations, and whitespace checks passed. The research JSON
checksum is `a802f64478b73a0c40f43c1d43fa44b182ebdbcde9f67d3d0c97f237c92a241c`; the readable report
checksum is `acdd94dc89abee72f0c2e197bf4392fc2c13671b2282cc68e5765d6dbca9669f`.

Ruff and mypy were not rerun in this host session because they are not installed in the global
Python environment and the sandboxed `uv` attempt could not reach PyPI. This did not prevent the
105-test suite, compilation, data validators, deterministic checks, Compose checks, or whitespace
check from completing.

### Incomplete work, risks, and next step

The strongest remaining risk is confusing source agreement with owner approval. Collector sources
can repeat each other's errors, and the remote pages are not immutable. The nine recommendations
are suitable for an explicit family-level review, not for automatic canonical promotion. The
`'55 Chevy` rows need additional identifier evidence that maps the 2025 release to one of the three
known casting lineages.

The next step is to present these ten outcomes to the project owner for acceptance or correction.
Once the owner provides an explicit decision, a priority-2 decision applier can record the nine
family creations and one hold—still with all release variants held. Batch 02 can then research the
next ten of the 39 priority-2 families not yet examined.

## 2026-09-08 — Four owner-approved family links are recorded without variant promotion

### What was executed and what problem it solves

T33 ended with a precise proposal: connect four exact-name Wiki groups to their existing
human-backed casting families, but keep all nine release variants held. The project owner then asked
to execute the next step. T34 records that follow-up authorization as an auditable decision batch
and applies it through a validator rather than silently editing generated queue data.

The resulting state now distinguishes three facts. Four casting-family relationships are completed
decisions; 49 possible-new-family decisions remain pending; and none of the Wiki releases is a
verified canonical variant. This lets the project honestly say some manual family review has
occurred without overstating the catalog or changing Dual-RAG output.

### Code changes and why they were made

`priority-1-decisions.json` records a batch ID, `project_owner` reviewer role, UTC timestamp,
conversation provenance, and four family-specific decisions. Each includes the stable family-review
ID, exact human target, `casting_family_only` scope, `variant_decision=hold`, a reason explaining
the release differences, and references to the evidence packet, human family, and every relevant
Wiki source row.

`apply_fandom_adjudication_decisions.py` validates both upstream checksums before reading the batch.
It requires a supported schema, named batch/reviewer, valid UTC timestamp, provenance, unique known
family IDs, permitted outcome, written reason, evidence references, family-only scope, and variant
hold. For a merge, the target must already be one of that family's exact pre-review candidates.
The original all-pending queue is deep-copied rather than modified.

The derived `adjudicated-queue.json` marks those four reviewer decisions completed, retains all
other entries as pending, and keeps `promotion_eligible=false` everywhere. A readable result and
manifest capture the 4 completed / 49 pending / 9 variant-held / 0 promotion-eligible counts and
freeze the queue, evidence, decision input, and outputs. Tests also inject a wrong merge target and
prove that application fails closed.

### Technical choices, alternatives, and trade-offs

Decisions are stored as data separate from both the machine-generated queue and the resulting
state. This event-like design adds files, but it preserves the before state, reviewer action, and
after state independently. Editing `adjudication-queue.json` in place would be shorter yet destroy
deterministic regeneration and make it hard to tell whether a field came from code or a reviewer.

The reviewer is recorded as the role `project_owner`, not an invented personal name. The provenance
accurately states that the owner requested execution after receiving the explicit merge/hold
proposal. This is traceable repository evidence, although it is not a cryptographic signature or
external identity proof.

Completing a family merge still does not make the family promotion eligible. That may look
conservative, but the human target is itself provisional and the Wiki rows still lack verified
colors. The accepted outcome is therefore a knowledge relationship inside the review layer, not a
new canonical entity.

### Decision changes

T32's queue contract allowed four outcomes, while T34 deliberately narrows this particular batch to
family scope with variant hold. This prevents a broadly worded follow-up request from accidentally
granting release-level approval. Future priority-2 batches may use create/hold/reject, but they must
pass their own evidence requirements.

The project also moves from “zero human decisions” to “four project-owner family decisions,” while
leaving the accuracy/evaluation boundary unchanged. Documentation now distinguishes family linkage,
variant verification, canonical promotion, and evaluation labels as separate states.

### Verification evidence

Four completed decisions target the exact human candidates for `'67 Chevy C10`, `Purple Passion`,
`Subaru BRZ`, and `Tesla Model S Plaid`. Forty-nine decisions remain pending. Nine Wiki release
variants remain held, and promotion-eligible and newly canonical records both remain zero.

The decision checksum is
`ef17632c486850ab8f39604462e474c8c0e97894a8a8fc0003aef58b5fab03f0`; the adjudicated queue
checksum is `6ab11ddef990e31918e507372c451cc0bfce531d7c9ec41e91ecc680288d0082`;
the readable result checksum is
`bd916df6b82866f87766c5ab038646d6aee90c4dd69e93a57120aef91cbaf023`.

Five focused tests passed, including the invalid-target failure. The complete host suite passed
99/99. T30–T33 deterministic checks, fixture validation, Python compilation, both Compose
configurations, and whitespace checks passed. T34 made no network request, PostgreSQL write,
canonical catalog edit, runtime change, or AI-evaluation mutation.

### Incomplete work, risks, and next step

The four relationships point to a provisional human-backed catalog, not the canonical catalog.
They cannot yet answer which 2025 toy number corresponds to which color or whether a Wiki release
matches the existing human provisional variant. The conversation-based owner provenance is
auditable but not signed.

The remaining work is the 49 priority-2 families. Before any `create_new_casting` decision, the
project needs independent text-source confirmation that the normalized Wiki name is a real distinct
casting rather than an alias, punctuation difference, or incomplete catalog coverage. That research
should be performed in bounded batches before any database scaling.

## 2026-09-08 — Four side-by-side packets make the first decisions reviewable

### What was executed and what problem it solves

T32 created a clean 53-family queue, but the four priority-1 entries still pointed to IDs rather
than showing why a reviewer should accept or reject them. T33 assembles the evidence needed for
those first bounded decisions. For each exact-name family it places every Wiki release row beside
the retained human label, original source name when available, structured series/variant fields,
source case IDs, provisional variant ID, and target human casting ID/UUID.

The evidence reveals an important boundary that a name-only table hides. All four pairs clearly
refer to the same named casting family, but their releases are not automatically the same variant.
The 2015 green `'67 Chevy C10` human record differs from the 2025 HW Hot Trucks rows; the Purple
Passion human label says 2026/pink while the Wiki rows are 2025 HW Designed By; Tesla's human red
label lacks matching Wiki color evidence. Subaru BRZ shares a 2025/Zamac clue, but its human series
is Walmart Exclusive while the Wiki series is HW J-Imports.

### Code changes and why they were made

`build_fandom_priority_one_evidence.py` validates the T32 queue checksum and pending-state boundary,
requires exactly one human casting candidate per priority-1 family, rechecks normalized brand and
casting equality, and joins the family with `human_backed_catalog.json`. It retains both
`human_label_names` and `initial_names`; this matters because the initial text carries year or
listing context that a cleaned human label may omit.

The builder emits `priority-1-evidence.json`, a human-readable Markdown report, and a manifest that
freezes the queue, queue manifest, human catalog, and both outputs. It calculates only explicit
facts: source rows, release years, series sets, exact normalized family equality, and shared tokens
between the Wiki variant notes and human variant labels. It does not infer colors, dates, or release
identity from the prose.

Each packet contains two deliberately separate recommendations. The casting-family recommendation
is `merge_existing_family`, targeting the exact human casting. The variant recommendation is
`hold`, with `variant_identity_verified=false`. Reviewer confirmation fields remain empty, and the
family remains promotion-ineligible. Five tests freeze the four families, nine Wiki rows, exact
targets, retained evidence, Subaru `zamac` fact, family/variant boundary, hashes, and deterministic
regeneration.

### Technical choices, alternatives, and trade-offs

The evidence packet reuses frozen repository inputs rather than fetching four more web pages. The
purpose of this decision is to judge whether the two already-governed sources refer to the same
casting family; the exact names and recorded provenance are sufficient to pose that limited
question. Additional web research would be necessary for release/color promotion, which is
explicitly outside this packet.

The code reports shared variant tokens but does not turn them into a match score. A score would look
precise without a validated relationship to correctness. Showing `zamac` directly for Subaru is
more honest: it helps the reviewer understand why the release may be related, while differing
series labels and null Wiki color keep the variant held.

A single yes/no family question per packet was chosen instead of asking the user to interpret raw
UUIDs or decide every Wiki release at once. This keeps the immediate review small without weakening
the audit boundary. The trade-off is that even an accepted family merge will not increase the
canonical release count yet.

### Decision changes

The previous queue treated all evidence references as future reviewer work. T33 now pre-assembles
the repository evidence for priority 1 so the reviewer does not need to search across files. It
does not populate the reviewer's evidence field, because selecting which evidence justifies a
decision remains part of the reviewer-owned act.

The earlier shorthand “merge these four” is also narrowed to “recommend merging the casting family
only.” Variant identity remains held even for Subaru. This prevents a valid family conclusion from
silently granting invalid year/color/series equivalence.

### Verification evidence

Four packets cover nine unique Wiki source rows and exactly four human casting targets. Each target
passes exact normalized brand/casting equality, has retained human source cases and provisional
variant evidence, recommends a family-only merge, holds the variant, and remains pending and
promotion-ineligible. Only Subaru has a shared explicit variant token: `zamac`; its series sets are
not exact.

The packet checksum is
`4d6ede8ba1bbb3447f2d403885d4d68bb9d71893cbf012994b2be37e77ad8294`; the Markdown checksum is
`077d9b078514b8628b99244936f426652a46679f4e74642858c00c8067db98ab`.
The deterministic `--check` passed, five focused tests passed, and the complete host suite passed
94/94. T30–T32 checks, fixture validation, Python compilation, both Compose configurations, and
whitespace checks passed. No network request or database/runtime mutation occurred.

### Incomplete work, risks, and next step

No human decision has been recorded. The evidence packet uses stored labels and does not prove the
source listings themselves are still available. Exact family naming can support the proposed
family relationship but cannot establish individual release identities or resolve missing colors.

The next step is for the project owner to accept or reject the four family-only recommendations.
Acceptance means only “these Wiki rows and this human draft belong to the same named casting
family”; all nine release rows remain variant-held. Once the answers are given, a validator can
record reviewer/time/reason/evidence and update the queue without creating canonical database rows.

## 2026-09-08 — A 53-family queue makes human adjudication explicit

### What was executed and what problem it solves

T31 reduced 100 Wiki rows to 53 casting-family relationships, but its row-level JSON was still a
machine pre-review rather than a practical human workflow. T32 prepares the actual adjudication
queue. It groups every source row under one stable family-review ID, puts the four exact
human-catalog candidates first, places the remaining 49 research-required groups second, and emits
both a machine-readable queue and a Markdown worksheet that a non-programmer can inspect.

This solves two different risks. First, it prevents a reviewer from issuing the same casting
decision two or three times merely because one model has several release/color rows. Second, it
makes the absence of completed human review visible: all 53 decision objects are pending, their
reviewer fields are empty, and none is eligible for promotion or PostgreSQL ingestion.

### Code changes and why they were made

`build_fandom_adjudication_queue.py` validates the T31 report against its manifest, rejects
duplicate source IDs or rows that have already crossed the review boundary, groups by the frozen
normalized family key, unions exact candidate IDs, preserves every contributing toy/collector/
series/variant row, and assigns stable SHA-derived family-review IDs. Exact-candidate groups receive
priority 1; groups requiring source research receive priority 2.

The generated `adjudication-queue.json` defines a closed decision contract:
`merge_existing_family`, `create_new_casting`, `hold`, or `reject`. A completed decision must state
who decided it, when, why, and which evidence supports it. Creating a new casting additionally
requires independent source confirmation. `adjudication-queue.md` renders the same queue as two
plain tables, making the work accessible without editing or understanding the larger JSON files.

The queue manifest freezes both T31 input files plus the JSON and Markdown outputs. Build mode
writes all three outputs; `--check` rebuilds them in memory and rejects any byte difference. Five
tests verify complete one-time source coverage, stable unique family IDs, priority ordering, the
four exact human candidates, the closed decision contract, all-pending safety, hashes, and
determinism.

### Technical choices, alternatives, and trade-offs

The unit of human work is a casting family, not a Wiki row. This reduces the decision count from 100
to 53 while retaining nested release evidence. It does not merge the releases themselves: a family
decision can confirm that two sources discuss `Subaru BRZ`, but color, series, toy number, edition,
and rarity remain separate variant questions.

The queue is stored as JSON plus Markdown instead of adding a database admin UI. JSON provides a
strict future automation contract; Markdown gives the project owner a readable worksheet and clean
Git diff. A full UI could improve ergonomics later, but building authentication, concurrent edits,
and audit storage before validating the decision model would expand this Lite milestone without
improving identity evidence.

No entries were filled on behalf of the user. Although an AI can suggest that an exact name should
be reviewed for merge, recording that as `human verified` would create false provenance. Empty
reviewer fields are intentionally treated as meaningful safety state, not incomplete formatting.

### Decision changes

The prior next step was described broadly as human adjudication. Implementation clarified that the
project first needed an artifact a human could actually adjudicate. T32 therefore completes queue
preparation while leaving the substantive decisions open. This is a narrower claim, but it creates
a defensible separation between AI-assisted organization and human-owned labels.

The decision contract also changed from an informal request for a reason to a required four-part
audit record: reviewer, timestamp, reason, and evidence references. This makes future promotion
decisions reproducible and allows a validator to reject anonymous or unsupported approvals.

### Verification evidence

The queue contains 53 stable family IDs and nests all 100 unique source rows exactly once. Four
families are priority 1 and 49 are priority 2. Completed decisions and promotion-eligible families
are both zero. The queue checksum is
`638f35d36bbf25ec0767210c038e6ee3c1e097f4f3e67d78a9bbef4a8dd45558`; the worksheet checksum is
`748ce49c0c54afe0b60e2cc7d25275a990462f8116060f105059c4dc000acd36`.

The queue's deterministic `--check` passed, five focused tests passed, and the complete host suite
passed 89/89. Fixture validation, T30 staging validation, T31 review verification, Python
compilation, both Docker Compose configurations, and whitespace checks passed. The milestone made
no network request, database write, catalog mutation, or AI-evaluation change.

### Incomplete work, risks, and next step

Every substantive decision remains pending. The Markdown worksheet is readable but not a multi-user
approval interface, and the current builder deliberately refuses to infer human identity. A later
decision validator still needs to enforce target IDs for merges, evidence for new castings, and the
required audit fields before a promotion artifact can exist.

The next step now genuinely requires reviewer input, beginning with the four priority 1 families.
After those decisions are recorded, the 49 priority 2 names require independent source checking.
Only validated decisions—not the queue or pre-review suggestions—may feed future canonical and
PostgreSQL ingestion.

## 2026-09-07 — Cross-catalog review turns 100 Wiki rows into 53 review groups

### What was executed and what problem it solves

T30 produced a safe 100-row staging dataset, but a reviewer would still have needed to open three
large JSON files and compare every name manually. T31 builds the missing bridge: a deterministic
row-level report that checks each Wiki candidate against both the canonical fixture and the
human-backed draft, while preserving the rule that only a person may approve identity promotion.

The result also exposes why “100 imported rows” is not the same as “100 new car models.” Those rows
collapse to 53 distinct normalized casting families because many models have a base release and a
second-color or other variation. Nine rows, representing four families, already have an exact
human-backed family candidate. Ninety-one rows, representing 49 families, have no exact candidate
in either reviewed catalog. None exactly match the intentionally narrow synthetic canonical
fixture.

### Code changes and why they were made

`review_fandom_catalog_pilot.py` loads the frozen Wiki staging file, `catalog.json`, and
`human_backed_catalog.json`. It builds indexes on normalized brand plus casting and emits a review
record for every source row. Each result includes the input fields needed for review, normalized
family key, match reason, exact canonical/human candidate IDs, recommended review action, and three
remaining checks: confirm casting identity, classify release versus variant, and resolve color
without image inference.

The same command supports `--check`. In build mode it writes `review.json` and a manifest; in check
mode it regenerates both entirely in memory and requires byte-for-byte equality with the committed
files. The manifest hashes all three inputs and the output, so changing the Wiki snapshot or either
catalog makes the old review demonstrably stale instead of silently reusing it.

Five tests freeze row coverage, source order, status/family counts, the four current human-family
names, candidate boundaries, disabled unsafe matching options, all-hold decisions, checksums, and
determinism. README, attribution, MVP requirements, QA review, AI-eval exclusions, evidence, and the
decision log were updated so the report cannot be mistaken for model evaluation or database
ingestion.

### Technical choices, alternatives, and trade-offs

The matcher uses NFKD ASCII normalization, case folding, and alphanumeric tokens, then requires an
exact brand/casting key. This mirrors the project's conservative human-label alignment philosophy
and handles harmless punctuation differences such as curly apostrophes. It deliberately does not
use embedding similarity or fuzzy edit distance. Those methods could surface useful suggestions,
but without a verified threshold they could merge related yet distinct Skyline, Camaro, or model-
year castings and make a review shortcut look like ground truth.

Collector number was also rejected as a stand-alone identity key. In the Wiki data, multiple color
rows share collector numbers, and the canonical fixture uses a different synthetic scope. A number
match without matching source semantics would therefore be a coincidence, not sufficient identity
evidence.

Even exact human-family matches remain non-promoting. The human catalog itself is provisional, and
the Wiki row still lacks verified color. The report consequently chooses
`review_existing_human_family` as a recommended action while keeping canonical UUID/ID null. For
unmatched rows it says `review_possible_new_casting_family`, not “new casting,” because absence of
an exact match may be caused by spelling or coverage gaps.

### Decision changes

The previous next-step wording proposed a promote/merge/reject review of all 100 rows. Implementation
showed that automatic final decisions would overstate the available evidence. T31 therefore splits
review into two stages: deterministic pre-classification now, human adjudication later. This still
reduces the workload to 53 family groups and gives every decision an evidence trail, without
claiming that code can replace source-aware review.

This also changes the practical review order. The four exact human-family groups should be examined
first because they already have related human-labelled evidence. The 49 unmatched groups follow as
possible new families. Release/color classification remains separate within each family so a
second-color row cannot accidentally create a second casting.

### Verification evidence

The frozen report contains 100 rows across 53 families. Row counts are 9
`exact_human_casting_family` and 91 `no_exact_casting_family`; family counts are 4 and 49. The
matched families are `'67 Chevy C10`, `Purple Passion`, `Subaru BRZ`, and `Tesla Model S Plaid`.
All 100 decisions are `hold_for_human_review`, and canonical promotion count is zero.

The report checksum is
`720292870a04656df0a7a61ab7d649457990e09a19172b450f4557ad878f0c4e`. The `--check` regeneration
passed, five focused tests passed, and the complete host suite passed 84/84. Fixture validation,
Wiki staging validation, Python compilation, both Compose configurations, and patch whitespace
checks also passed. T31 made no network request and no PostgreSQL or runtime-catalog write.

### Incomplete work, risks, and next step

The report is machine pre-review, not human verification. Exact spelling does not prove that a
2025 release belongs to the same variant, and no exact spelling does not prove that a family is
new. Color remains unresolved for all 100 source rows. The human-backed catalog is itself a review
draft, so its four matches cannot grant canonical identity.

The next step is human adjudication beginning with those four matched family groups. Each group
needs a recorded merge/hold/reject decision and reasoning, followed by the 49 possible-new-family
groups. Only approved rows should feed a separate promotion artifact and PostgreSQL transaction;
the raw review JSON must never be ingested directly.

## 2026-09-07 — A governed 100-row Wiki pilot starts catalog expansion

### What was executed and what problem it solves

The project previously had two useful but deliberately limited sources: 120 synthetic/curated
canonical variants and 101 human-reviewed noisy names whose identities mostly remain provisional.
Neither source tests how a larger public catalog would enter the system. T30 introduces the first
external catalog intake without prematurely treating community data as canonical truth.

The Hot Wheels Wiki robots endpoint returned HTTP 403, so the work did not begin an HTML crawler or
try to bypass that response. A single identified MediaWiki site-information request was used to
confirm the API and its reported `CC-BY-SA` rights metadata. A second request retrieved the complete
2025 mainline list at frozen revision `790665`. Because the revision response contained the whole
table in roughly 93 KB, the pilot required no individual model-page or image requests.

### Code changes and why they were made

`fandom_ingestion.py` contains the bounded network adapter and pure table parser. The adapter uses a
fixed HTTPS API origin, URL-encoded parameters, an identifying User-Agent, a 30-second timeout, a
3 MB response ceiling, and strict response/license checks. The parser selects the first sortable
table, cleans Wiki and HTML presentation syntax, preserves source markers, and splits descriptions
such as “2nd Color - Zamac” into a separate variant note. It never reads the photo cell into the
normalized record.

`fetch_fandom_catalog_pilot.py` writes three artifacts: the raw revision, 100 normalized staging
records, and a checksum manifest. Its `--raw-input` mode can rebuild normalized output from the
frozen revision without another network call. This was added after the first fetch so parser fixes
or schema reviews do not create unnecessary requests or silently move to a newer Wiki revision.

`validate_fandom_catalog_pilot.py` enforces the accepted boundary: exactly 100 records and unique toy
numbers, sequential source rows, matching raw/normalized checksums, the expected license, null
colors, null canonical UUIDs, review-only status, and no copied `File:` reference in normalized
records. Parser tests cover Wiki links, HTML, templates, series values, color-variation suffixes,
determinism, limit errors, and insufficient table rows.

The source attribution README links the exact revision and contributor history, describes every
normalization change, and states that the source-derived files retain CC-BY-SA terms. The external
directory is excluded from the runtime Docker build: the repo retains review evidence, while the
shipping API cannot accidentally load the staging snapshot.

### Technical choices, alternatives, and trade-offs

The pilot uses one completed yearly list instead of walking thousands of casting pages. A yearly
table is closer to the required product-variant grain because it includes year, toy number,
collector number, series, and series position in one revision. It also sharply reduces load and
makes the exact source reproducible. The trade-off is that the table does not contain a trustworthy
text color field and some suffixes describe release variations without fully defining their color.

Unknown color therefore remains null. Inferring “green” or “red” from a photo filename would turn
presentation metadata into unreviewed product truth, while downloading the image would introduce a
different copyright boundary because Fandom explicitly warns that media need not share the Wiki
text license. This reduces immediate field completeness but prevents a much harder-to-detect data
quality and licensing failure.

The records were not appended to `data/catalog.json` and were not inserted into PostgreSQL. A Wiki
row is a release/variation candidate, not automatically a unique casting or a canonical identity.
The accepted architecture treats collection as reversible staging and promotion as a later human
decision. This preserves the existing resolver benchmark and prevents external knowledge from
leaking into test labels.

### Decision changes

The earlier plan described future catalog expansion at approximately 3,000 rows but had no accepted
source adapter or promotion boundary. That is now narrowed into two separate milestones: first
prove revision-frozen, attributed, review-only intake; only then define promotion and scale. The
project can now reproduce external extraction, but it still cannot claim a 220- or 3,000-row
canonical catalog.

The first generated parser counted the header chunk when assigning `source_row`, making the first
data record appear as row 2. Review caught that ambiguity before acceptance. The parser now numbers
valid data rows from 1, the raw revision remains unchanged, and normalized/checksum artifacts were
regenerated offline. This decision makes source-row references understandable without another API
request.

### Verification evidence

The accepted dataset is `fandom-hot-wheels-2025-pilot-r790665-v1`. It contains 100 records with 100
unique toy numbers, sequential rows 1–100, and 45 explicit variant notes. All 100 colors and
canonical UUIDs are null. The raw checksum is
`67521e8544de2dd15527e6d2234598c7c70a1e6d9e6597fde06c88bf95854510`; the normalized checksum is
`e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6`.

The dedicated frozen validator passed, the complete host suite passed 79/79, Python compilation
passed, and patch whitespace checks passed. No image file was downloaded. The checked-in raw and
normalized files total under 200 KB, and neither is part of the Docker runtime context.

### Incomplete work, risks, and next step

The 100 rows still need human review before promotion. The largest unresolved field is color, and
the identity policy must distinguish a new casting, an ordinary yearly release, a second color, a
store exclusive, Treasure Hunt, and Super Treasure Hunt. Assigning UUIDs before those rules exist
would produce durable but potentially wrong identities.

CC-BY-SA attribution/share-alike obligations apply to the source-derived directory, and this record
is not legal advice. The bounded importer has implementation safeguards but did not receive a formal
security or legal sign-off. It is intentionally a manual one-shot command, not recurring scraping.

The next step is to create a review/promotion artifact for these 100 rows: compare them with the
existing canonical and human-backed catalogs, classify exact casting-family matches versus new
families, and leave unresolved records unpromoted. Only after reviewing that report should the same
revision-frozen method fetch additional completed years toward 3,000 variants.

## 2026-09-07 — Exact pgvector completes the PostgreSQL canonical retrieval pair

### What was executed and what problem it solves

T09 moved canonical text candidate generation into PostgreSQL, but dense candidates still came from
vectors calculated and searched inside each API process. T10 now gives the same deterministic
catalog vectors a durable lifecycle: a command materializes them into PostgreSQL, startup proves
that the complete expected artifact is present, and each PostgreSQL-backed request performs exact
cosine-distance retrieval through pgvector. Canonical sparse and dense sources therefore share the
database boundary while the independent human-knowledge RAG remains non-canonical.

The change solves more than storage. Previously a database could be catalog-ready while containing
zero vector rows, and the API had no way to distinguish that incomplete state. It now refuses
readiness if dense metadata is missing, the catalog/model/text version differs, the artifact
checksum changes, or even one expected UUID/version/checksum row is absent.

### Code changes and why they were made

`embedding_artifacts.py` defines a stable catalog-text contract, composite embedding version,
pgvector literal encoding, per-product checksum, and whole-index checksum. These values are derived
from sorted canonical UUIDs so the artifact does not change merely because catalog file order
changes. The vector is included in each row checksum so a change to input text or deterministic
encoding output changes the recorded artifact.

`postgres_embeddings.py` adds the `pvr-materialize-embeddings` command. It first verifies the T07
canonical catalog, then writes every `vector(192)` row and the `canonical_dense` metadata row inside
one transaction. `ON CONFLICT` makes an identical rerun safe, while identities outside the loaded
catalog are rejected instead of silently deleted. A post-commit verification ensures the command
does not report success for an incomplete artifact.

`PostgresDenseRetriever` encodes the normalized query with the same versioned model and sends the
vector, version, and limit as SQLAlchemy-bound parameters to the existing exact `<=>` query. The
database returns UUIDs and cosine similarity scores; every UUID must map back to the checksum-matched
catalog. `ResolverService` now injects both PostgreSQL sparse and dense retrievers when that backend
is selected. Debug and health output report the actual dense implementation rather than a generic
configuration label.

Compose gained a separate `materialize` job after migration and ingestion. Keeping this step
separate makes data lifecycle failures visible and lets a future model upgrade rebuild vectors
without pretending it is ordinary catalog ingestion. Unit tests cover repeatability, content-driven
checksum changes, bound query parameters, limits, empty input, and unknown UUID failure. A dedicated
T10 verifier covers the real database and API boundary.

### Technical choices, alternatives, and trade-offs

The accepted Lite implementation deliberately materializes `hashing-v1` before introducing a
sentence-transformer. This model is local, deterministic, CPU-only, and already used by the verified
offline path. It lets the project test versioning, transactional materialization, readiness, and
pgvector querying without mixing those concerns with model downloads, licensing, caches, or a new
quality claim. It remains a lexical hashing baseline and is not described as neural semantic search.

Exact cosine search was retained instead of adding HNSW or IVFFlat. With 120 current rows—and the
planned first scale check near 3,000 rows—exact search provides deterministic complete comparison
and avoids index build/tuning/recall trade-offs that have not been justified by measurements. An
approximate index becomes a valid option only after observed latency or scale requires it.

The alternative of trusting only one metadata checksum was rejected. Startup compares the expected
identity, embedding version, and checksum for every row. This costs one deterministic catalog
encoding pass during startup, but catches incomplete or stale materializations instead of letting
the API operate on a silently partial dense index.

### Decision changes

T09 intentionally left PostgreSQL mode hybrid: database sparse retrieval plus in-memory dense
retrieval. That temporary boundary is now removed for the canonical catalog. In PostgreSQL mode,
both candidate sources execute in PostgreSQL; offline mode remains unchanged and requires no
database.

T10 originally requested a pinned local embedding artifact and was marked partial because only the
in-memory hashing implementation existed. Under the accepted Lite scope, the deterministic model
identifier, dimensions, catalog-text contract, vectors, and checksums now form the pinned artifact.
The task is complete for plumbing and exact retrieval, while the materially different claim of a
neural embedding model remains deferred and explicit.

### Verification evidence

The isolated `pvr-t10` environment used host PostgreSQL port `55435`, PostgreSQL 16.14, and the
rebuilt Python 3.12 project image. Migration and ingestion completed before 120/120 embeddings were
materialized with version `hashing-v1-d192-catalog-searchable-text-v1` and index checksum
`557d7153b077624f64cdc7bd2ada824df90a683216f7c67159e22a68f20d2464`. Repeating the command produced
the same logical rows and result.

Exact dense retrieval recovered a catalog alias and all 12 matched frozen-test targets within
Top-25, for Recall@25 `1.0`. Deleting one embedding row made a newly constructed API fail readiness
with 503; rerunning materialization restored the artifact. A real Uvicorn service on
`127.0.0.1:18010` reported both PostgreSQL sparse and exact dense dependencies ready and resolved
`2022 Chevy Nomad Red #101` to `hot-wheels-chevy-nomad-2022-mainline-red-101`. Its correct candidate
ranked first in sparse, dense, structured, and RRF sources. Separate frozen examples preserved all
three policy outcomes: `matched`, `ambiguous`, and `no_match`. The final host suite passed 77/77,
including rejection of an embedding dimension that does not match the `vector(192)` schema.

### Incomplete work, risks, and next step

No PostgreSQL latency benchmark was taken, so the earlier offline/container p95 numbers must not be
applied to this path. Startup recomputes expected deterministic vectors and checksums, which is
acceptable at 120 rows but should be measured near 3,000. Row checksums prove expected provenance
and version metadata; they do not independently hash PostgreSQL's stored float bytes. Runtime health
remains a startup snapshot, although a later database loss fails the next retrieval request with
503.

The next evidence-driven action is to expand the licensed/reviewed catalog toward approximately
3,000 variants and measure exact pgvector latency and retrieval quality. A neural embedding model
or approximate vector index should be selected only if that held-out evidence shows a real gain or
performance need. The remaining T14 external pointwise reranker is likewise not justified by the
current fixture, where the existing heuristic produced zero Top-1 gain over RRF.

## 2026-09-07 — PostgreSQL sparse retrieval enters the canonical RAG path

### What was executed and what problem it solves

T07 made the canonical catalog durable in PostgreSQL, but every API lookup still searched only the
JSON-backed in-memory index. T09 now lets an explicitly selected PostgreSQL backend retrieve
canonical sparse candidates from the installed `product_search` documents. The default offline
mode remains unchanged, while `PVR_BACKEND=postgres` is now a working, readiness-checked option
instead of an intentionally unavailable placeholder.

The observable result was verified over real HTTP. A PostgreSQL-backed API reported database
version `16.14`, sparse retriever `postgres-fts-simple-v1`, and ready health, then resolved
`2022 Chevy Nomad Red #101` to the expected canonical ID. The same database retriever recovered all
12 frozen matched test targets within Top-25 and returned an exact catalog identifier at Top-1.

### Code changes and why they were made

`retrieval.py` now defines `PostgresSparseRetriever` behind the same retriever protocol used by the
in-memory sparse implementation. It converts already normalized title tokens into a bound
`websearch_to_tsquery` value, executes the existing fixed SQL statement, and maps returned UUIDs to
typed `CatalogProduct` objects. Returning an unknown UUID is an error rather than silently accepting
a database/catalog mismatch.

`postgres_retrieval.py` owns SQLAlchemy engine execution and startup verification. It checks the
installed catalog version, full-content checksum, product count, and search-document count before a
service becomes ready. `service.py` selects only the sparse implementation according to
`PVR_BACKEND`; dense and structured retrieval, RRF, calibration, policy, and the independent human
knowledge source retain their existing contracts. Debug metadata identifies the actual sparse
version. `api.py` reports the database/index versions and maps a runtime retrieval dependency loss
to HTTP 503 rather than an internal-error 500.

Compose now passes the backend switch and database URL into the API service. Docker packages the
T09 verifier, while unit tests record the SQL statement and parameters without needing a database.
The README documents migration, ingestion, and the opt-in PostgreSQL API start order.

### Technical choices, alternatives, and trade-offs

The PostgreSQL path was introduced at one retrieval boundary rather than moving sparse, dense, and
structured logic together. This makes failures attributable and leaves T10's vector model/version
questions independent. It creates a temporary hybrid canonical path—PostgreSQL sparse plus
in-memory dense/structured—but avoids pretending that empty `product_embedding` rows are a working
pgvector system.

Normalized tokens are joined with web-search `OR` for candidate generation. An all-`AND` query
would let one irrelevant seller token remove the correct product entirely; candidate retrieval
instead favors recall, while RRF, calibration, and abstention control precision later. PostgreSQL's
built-in `ts_rank_cd` was retained rather than adding a BM25 extension, matching the Lite scope and
avoiding another deployment dependency before 3,000-row evidence exists.

All title content and limits remain SQLAlchemy-bound parameters. Only a fixed repository-owned SQL
constant is executed; raw titles are never interpolated into SQL or identifier names. This matters
even though `websearch_to_tsquery` is designed for user-style input, because SQL parameterization is
the actual boundary preventing a title from becoming executable database syntax.

### Decision changes

The earlier fail-closed decision rejected every `PVR_BACKEND=postgres` configuration because no
query adapter existed. That decision is narrowed: PostgreSQL mode is now accepted only after T07
metadata and row-count verification succeeds, and only canonical sparse retrieval moves to the
database. Missing/stale data still fails readiness. Exact dense pgvector retrieval remains deferred
and the ordinary default remains `offline`.

The project also previously described PostgreSQL as entirely outside the API runtime evidence.
That is no longer accurate for sparse retrieval: both in-process API and real container HTTP paths
passed. Existing latency numbers remain offline-only, so no PostgreSQL latency or concurrency claim
was added.

### Verification evidence

The final host suite passed 71/71, including two additional API fail-closed tests. The isolated
Compose project `pvr-t09` used port `55434`, migrated PostgreSQL 16.14, and ingested all 120 fixture
products. T09 verification reported identifier Top-1, 12/12 Recall@25 (`1.0`), a forced query plan
using `ix_product_search_document`, injection-shaped bound-input safety, API readiness, and checksum
mismatch health 503. A real Uvicorn container on `127.0.0.1:18009` returned the expected matched
canonical ID and PostgreSQL sparse version.

Unit tests additionally prove that query and limit values are parameters, SQL text never contains
the injection-shaped title, invalid limits are rejected, empty token sets avoid database work, and
unknown database UUIDs fail closed. Fixture validation, Python compilation, both default and
PostgreSQL-profile Compose configuration, and `git diff --check` also passed. All isolated T09
containers, network, and volume were removed.

### Incomplete work, risks, and next step

Startup verifies database consistency, but health does not yet actively re-query PostgreSQL on every
request; a database lost after startup is detected on retrieval and returned as 503. OR-based FTS
was measured only on 120 synthetic/curated products, and its ranking quality or latency may change
with 3,000 real variants. The FTS score is not BM25, dense retrieval remains in memory, and no
external Wiki catalog has been imported.

The single highest-value next action is **T10 — materialize versioned deterministic embeddings and
execute exact pgvector retrieval**. After both PostgreSQL candidate sources work, the project can
benchmark the complete database-backed canonical path before scaling the licensed catalog toward
3,000 records.

## 2026-09-06 — Atomic PostgreSQL canonical-catalog ingestion

### What was executed and what problem it solves

The PostgreSQL schema had already passed its migration lifecycle, but the running project still had
no implementation that could put catalog knowledge into those tables. T07 now installs a complete
validated catalog snapshot through the same ingestion contract used by the in-memory tests. This
closes the gap between “the database tables exist” and “the database contains a coherent catalog.”

On the first fixture import PostgreSQL received 120 product variants, 240 aliases, 120 identifiers,
120 provenance records, 120 sparse-search documents, and one catalog metadata record. Repeating the
same import left every stored row unchanged. A deliberately conflicting import modified an early
record before failing later, and the transaction restored the entire pre-import snapshot. A second
negative case omitted one existing product and was rejected rather than silently deleting its
canonical identity.

### Code changes and why they were made

`src/product_variant_resolver/postgres_ingestion.py` implements the existing `CatalogRepository`
contract with SQLAlchemy 2 parameterized statements. One connection and transaction span every
product plus the final metadata update. Parent product identity is checked by UUID, canonical slug,
and natural-key fingerprint; aliases are reconciled by normalized text; identifiers are checked for
ownership before update; provenance is replaced only when its complete ordered content changes;
and `product_search` receives deterministic source text plus PostgreSQL's `simple` `tsvector`.

`catalog.py` now preserves the structured alias and identifier type/source records that the prior
in-memory resolver flattened into strings. The flattened values remain for retrieval compatibility,
while PostgreSQL can retain `alias_type`, `identifier_type`, and source provenance. Its checksum now
covers the complete normalized catalog representation instead of UUID/slug alone, because a casting,
series, alias, or provenance correction must produce observable version evidence.

The installed `pvr-ingest` command and Compose `ingest` service provide one documented operator
path. Docker includes the isolated verification runner, while `.dockerignore` permits only that
specific additional script. The API backend was deliberately not switched to PostgreSQL: writing
catalog rows is T07, whereas querying FTS and pgvector safely belongs to T09/T10.

### Technical choices, alternatives, and trade-offs

Atomic full-snapshot ingestion was chosen over per-product commits and truncate/reload. Per-product
commits could leave the database half-updated after record 2,500 of a future 3,000-row import.
Truncation would temporarily remove all identities and recreate unchanged surrogate rows. The
selected reconciliation keeps unchanged rows and timestamps stable but still makes all changes
commit together.

The importer also refuses to infer deletion from omission. This is intentionally conservative for
future external sources: a disappeared Wiki row could mean a parsing or export problem rather than
a retired Hot Wheels release. The cost is that genuine retirement will require a later explicit
active/retired field and policy. `product_embedding` remains empty because inserting placeholder
vectors would make T10 look complete without a versioned embedding model or checksum.

### Decision changes

T07 was previously marked partial because only `InMemoryCatalogRepository` implemented the
transaction contract. It is now complete for the 120-product Lite fixture and real PostgreSQL 16
runtime. PostgreSQL is still not the API resolver backend: this milestone promotes database
persistence only, not database retrieval, latency, or 3,000-record external-catalog readiness.

The first checksum implementation tracked only UUID and slug. That was sufficient to recognize an
identity list but would miss corrected searchable fields. The checksum was expanded before accepting
T07 so metadata changes whenever relevant catalog content changes. Structured alias/identifier
records were preserved for the same reason: source and type are database facts, not disposable
loading details.

### Verification evidence

The isolated Compose project `pvr-t07` used host port `55433` and a dedicated named volume. Alembic
upgraded an empty PostgreSQL 16/pgvector database to revision `0001`. The production repository then
passed first import, exact repeated-row comparison, mid-import canonical-ID collision rollback, and
incomplete-snapshot refusal. Counts were 120 products, 240 aliases, 120 identifiers, 120 provenance
rows, 120 search documents, one metadata row, and zero embeddings by design.

The first verification attempt exposed a string-versus-`Path` mismatch in the verification
entrypoint before any write occurred. Explicit environment-boundary conversion fixed it; the rebuilt
image passed the complete scenario and the strengthened missing-row scenario. The host suite passed
66/66 before documentation finalization, fixture checksum validation passed, Python compilation and
Compose configuration passed, and the isolated containers, network, and volume were removed.

### Incomplete work, risks, and next step

The importer expects a migrated PostgreSQL database and a complete validated canonical snapshot. It
does not crawl Fandom, create provisional identities, review licensing, materialize embeddings, or
query PostgreSQL during `/resolve`. It also does not yet model retired products, so intentional
deletion is refused. The local Compose password is development-only and must not be reused outside
the loopback development environment.

The single highest-value next action is **T09 — PostgreSQL sparse retrieval**. That task will query
the populated `product_search` GIN index with bound parameters and prove that identifiers and rare
casting terms recover the correct canonical candidates before pgvector is added.

## 2026-09-06 — Human-backed catalog connected as the second RAG source

### What was executed and what problem it solves

The human-backed catalog previously existed only as a checked-in draft. This iteration connected it
to the running resolver so the project now searches two distinct knowledge corpora for every title.
The original canonical catalog path still owns final identity and abstention. The new human
knowledge path searches reviewed real-world names and exposes provisional suggestions that explain
what the system has seen before, especially when the small fixture catalog cannot return a product.

For the smoke query `Hot Wheels BMW M3 GT2 Neon Speeders`, the human path ranks the reviewed BMW M3
GT2 record first, but the final response remains `no_match` with null UUID because no canonical BMW
exists in the fixture catalog. This is the intended safety boundary: the second RAG source improves
knowledge retrieval without changing a draft label into a production identity.

### Code changes and why they were made

`src/product_variant_resolver/human_knowledge.py` adds a strict loader and an independent hybrid
retriever over the 100 provisional variants. Sparse scoring uses IDF-weighted token overlap so rare
model tokens contribute more than common words. Dense scoring reuses the deterministic `hashing-v1`
embedding already shipped by the Lite runtime, and RRF combines the two ranks without directly
adding incomparable scores. A shared-token gate prevents the non-semantic hashing baseline from
returning candidates for wholly unrelated input.

`ResolverService` loads both catalogs, runs `human_knowledge_retrieval` after shared signal
extraction, records a separate timing/span and candidate count, and includes bounded human results
only in debug payloads. The canonical candidate list alone continues into reranking, calibration,
policy, and final product selection. `schemas.py` therefore gives human candidates explicitly
provisional fields instead of reusing `CandidateDebug`, which would incorrectly imply canonical
identity. `config.py`, `.env.example`, Dockerfile, and `/health` expose the new required catalog and
index versions; a missing human catalog makes readiness fail rather than silently claiming Dual RAG.

The debug UI now renders a separate Reviewed-name candidates table with a visible warning that the
rows are retrieval evidence only. Human names and even markup-like text are assigned through
`textContent`, preserving the existing untrusted-input boundary. Default API responses remain
unchanged and continue to omit all debug data.

### Technical choices, alternatives, and trade-offs

The new source deliberately does not merge its provisional records into the canonical catalog and
does not override `no_match`. Merging would make the existing calibrator and thresholds operate on a
different identity space without training evidence. Allowing a human hit to override policy would
produce apparent coverage immediately, but would erase the distinction between a reviewed name and
a fully specified canonical variant.

Running the second retrieval on every request makes the Dual RAG execution boundary observable and
keeps timing evidence honest. The trade-off is additional CPU work even when debug is false; the
catalog currently has only 100 provisional variants, so Lite mode accepts that cost while deferring
performance optimization until a measured bottleneck exists. The output is shown only in debug to
preserve the minimal consumer contract.

No Top-1 or Recall@K claim is made for the new path. Its indexed aliases come from the same source
cases, so evaluating those aliases against the index would measure memorization. A defensible metric
requires a separate grouped holdout or independently written noisy queries. The next task should
create that evaluation set or define the review-to-canonical promotion workflow before human
evidence influences final decisions.

### Verification evidence

The focused backend, API, observability, and UI selection passed 25/25 tests after adding an explicit
loader test that rejects any provisional variant whose status bypasses canonical review. The full
host suite then passed **64/64**. `scripts/validate_fixture_data.py` reproduced manifest SHA-256
`a4c851228939b3d12db7c879ce9c81e4ae008fd19d1032adb376b833e23c31b8`; Python compilation and
`git diff --check` both passed.

The integration evidence exercises the important product boundary, not only internal functions.
`Hot Wheels BMW M3 GT2 Neon Speeders` retrieves `BMW M3 GT2` / `Neon Speeders` first from the human
source while the API remains `no_match` with a null canonical identity. A known fixture query still
resolves through the canonical source, and default responses omit debug evidence. Health metadata
reports both human catalog and human retrieval-index versions. A missing human catalog prevents app
readiness rather than silently falling back to a single-source system.

These checks use the deterministic 100-document Lite catalog and `hashing-v1`; they do not establish
semantic quality on unseen marketplace titles, production latency under load, or a neural embedding
benchmark. The existing Starlette TestClient deprecation warning remains visible and non-failing in
the host environment. The single highest-value next action is an independently authored, casting-
grouped holdout evaluation so retrieval quality can be measured without testing the index against
its own aliases.

## 2026-09-06 — Human-backed casting catalog and provisional variants

### What was executed and what problem it solves

The conservative alignment proved that the 10-family synthetic fixture catalog cannot represent
the 97 real castings in the reviewed dataset. This iteration therefore built a separate
`human-backed-catalog-v1` instead of weakening alignment rules or overwriting the synthetic fixture.
All 101 confirmed source records are now organized into 97 casting entities and 100 provisional
variant groups that can support retrieval and a future human-review workflow.

The count difference is intentional. Three `83 Chevy Silverado` records remain three variants
because their labels distinguish blue, black, and baby-blue versions. Two `Toyota Supra` records
remain separate because one is Hot Wheels XL/Greddy and the other is Mainline/Fast & Furious. Two
`1970 Chevrolet Chevelle SS` records share the same normalized Premium/Fast and Furious structure,
so they become one provisional variant while retaining both case IDs, names, and pricing keywords.

### Code and data changes, with reasons

`scripts/build_human_backed_catalog.py` creates `data/human_backed_catalog.json` and its checksum
manifest. A casting key uses exact normalized brand and casting. A provisional variant key adds the
reviewed series and variant labels. Both levels receive deterministic UUIDv5 and readable IDs so
regeneration does not change references, while every variant remains explicitly
`needs_canonical_review`.

The catalog keeps all human names, pricing keywords, available initial names, failure categories,
and source case IDs. It does not parse missing year, collector number, scale, color, or edition from
free text. Those values may appear inside a human name, but automatically promoting them into typed
identity fields would mix interpretation with verified evidence and could make later corrections
silently remint an identity.

Focused QA initially exposed inconsistent brand display casing: the reviewed source contains both
`Hot wheels` and `Hot Wheels`, so choosing one complete spelling by frequency produced `Hot wheels`
throughout the draft. The builder now derives a stable display form from the already normalized
brand tokens, producing `Hot Wheels`, `Matchbox`, and `M2` consistently while retaining the original
human strings inside name aliases. This changes presentation only; grouping keys and stable UUIDs
remain based on the same normalized identity.

`scripts/validate_fixture_data.py` now checks the new catalog checksum against the human dataset,
count agreement, unique casting and provisional-variant identifiers, exact one-time coverage of all
101 cases, and mandatory canonical-review status. Seven focused tests cover deterministic output,
the 97/100/101 accounting, exact duplicate preservation, ID uniqueness, evaluation exclusions, and
non-merging of similar-but-distinct names. R19 and T28 record the behavior; README, decision D10,
QA, and AI-eval evidence explain why this catalog is retrieval-ready but not canonical truth.

### Technical choice and next decision

A two-level casting/variant draft was chosen over either extreme of creating 101 unrelated products
or collapsing every record with the same casting into one product. It preserves known structure
and repeated evidence without claiming that incomplete variant labels are production identifiers.
The trade-off is an additional review state and a second catalog artifact, but this boundary makes
future promotion auditable.

The next step is to connect this draft as a second, explicitly non-canonical retrieval source in the
Dual RAG pipeline. Results from that source must be presented as candidate knowledge or review
suggestions until typed attributes are verified and a promotion process mints final canonical IDs.

### Verification evidence

The builder produced 97 castings and 100 provisional variants from all 101 source records, and the
manifest recorded one merged duplicate source record. The central fixture validator passed. Seven
focused catalog tests passed, the complete host suite passed 57/57 with `PYTHONPATH=src`, Python
compilation passed, and `git diff --check` reported no whitespace errors. The already documented
host TestClient deprecation warning remained non-failing and is unrelated to this data-only runtime
boundary.

## 2026-09-06 — Conservative alignment exposes the real catalog-coverage gap

### What was executed and what problem it solves

The newly imported 101-record human-label corpus could not yet participate in canonical resolver
evaluation because the labels had no verified links to this repository's UUIDs. This iteration ran
the requested catalog-alignment step and created a deterministic, reviewable status for every
record. The outcome is 0 canonical mappings, 2 exact casting-family-only matches, and 99 unmapped
records. The two partial matches are `Toyota Supra`; each still has 12 possible synthetic variants,
so neither receives a UUID.

This result identifies the actual constraint rather than hiding it behind a similarity score. The
current fixture catalog contains 10 synthetic casting families, while the human corpus contains 97
real casting names. The next accuracy bottleneck is catalog coverage and variant provenance, not
the mechanics of matching the two JSON files.

### Code and data changes, with reasons

`scripts/align_human_labeled_names.py` builds
`data/human_labeled_catalog_alignment.json` plus a checksum manifest. Each row retains its human
name fields, alignment status, reason, nullable canonical identity, matched family, and possible
canonical IDs. Exact Unicode/punctuation-normalized brand and casting are required for a family
match. A UUID additionally requires exact series and one variant discriminator—color, edition, or
rarity tier—to reduce the family to one unique product.

Fuzzy string matching was intentionally excluded from label creation. It would be useful as a
retrieval signal, but unsafe as ground truth: for example, `Dodge Challenger` versus `Dodge
Charger`, a chassis-specific Skyline versus a generic Skyline family, or a real 2000 Chevy Nomad
versus synthetic 2022/2023 variants can look textually close while representing different product
identities. The conservative policy allows those items to remain visible as unmapped instead of
silently assigning an incorrect UUID.

`scripts/validate_fixture_data.py` now verifies the alignment checksum, source dataset checksum,
catalog checksum, complete case-ID coverage, status values, and UUID/slug integrity. Five focused
tests cover the current 0/2/99 result, the 12-candidate Toyota Supra families, null identities for
unmapped rows, frozen inputs/output, and deterministic regeneration. R18 and completed task T27
were added to the Lite brief; README, QA review, decision D9, and the AI-eval evidence document now
state that this is a catalog-coverage measurement rather than an accuracy result.

### Technical choice and next decision

The method uses standard-library normalization and exact structured fields instead of adding an
embedding model or fuzzy-matching dependency. This keeps the alignment deterministic, auditable,
and appropriate for the Lite workflow. The trade-off is deliberately low automatic coverage: it
prefers a review queue over false canonical labels.

The next data task should not weaken the threshold. It should define how reviewed names become a
separately versioned, human-backed catalog: deduplicate repeated scans, settle whether series and
variant fields describe the product or marketplace listing, add provenance, mint stable IDs, and
then create a casting-family grouped evaluation split. PostgreSQL ingestion T07 remains valuable,
but loading a broader catalog should follow a clear source-of-truth decision.

### Verification evidence

The alignment command processed all 101 records and reproduced the frozen 0 mapped / 2
casting-family-only / 99 unmapped counts. The central fixture validator passed with both input and
output checksums linked. Five focused alignment tests passed, the complete host suite passed 50/50
with `PYTHONPATH=src`, Python compilation passed, and `git diff --check` reported no whitespace
errors. The existing host TestClient deprecation warning remains an environment/dependency warning
already documented by the project; it did not cause a test failure.

## 2026-09-06 — Human-labeled real-noisy names added as an auxiliary dataset

### What was executed and what problem it solves

The project previously relied on a 100-case synthetic/curated benchmark. That fixture is useful for
proving the resolver architecture, but it does not show how recognition output differs from a
person's verified answer on real noisy scans. This iteration imported the user-approved local
labeling queue into `human-labeled-real-noisy-v1`. The new corpus contains 101 confirmed human
labels: 91 records have both the original top recognition name and the human-verified name, and 10
records preserve the fact that recognition returned no candidate while still retaining the human
answer. Four rows explicitly excluded during the earlier human review were not imported.

This solves two immediate problems. First, future work can measure name cleanup and candidate
selection against real reviewed examples instead of relying only on generated titles. Second,
failed recognition attempts are represented as data rather than disappearing from the sample,
which prevents coverage from looking better simply because empty outputs were dropped.

### Code and data changes, with reasons

`scripts/import_human_labeled_names.py` was added as a deterministic CSV-to-JSON boundary. It
requires the source columns used to distinguish `candidate_1` from `human_expected_candidate` and
the normalized human casting/pricing fields. Included rows must have confirmed human labels;
candidate confidence must be numeric and bounded; duplicate case IDs fail the import. The generated
record uses the explicit fields `initial_name` and `human_label_name`, so a beginner reviewing the
data can see the before/after pair without reconstructing meaning from the old labeling workbook.

The importer writes `data/human_labeled_names.json` and a separate frozen manifest. The manifest
records the source checksum and generated dataset checksum rather than a machine-specific absolute
path. Local frame paths and images were not copied because the current Product Variant Resolver is
a text-first Dual RAG project and the requested evidence is the name pair; omitting those paths also
keeps this repository portable when only the `Product Variant Resolver/` folder is pushed.

`scripts/validate_fixture_data.py` now validates the auxiliary corpus alongside the original
catalog and benchmark. `tests/test_human_labeled_names.py` checks the 101 total records, the 91/10
paired-versus-no-candidate split, confirmed human labels, unique IDs, checksum integrity, and the
declared evaluation exclusions. The MVP brief adds R17 and completed task T26, while the QA review,
README, decision record, and AI-eval evidence explain the data boundary and its limitations.

### Technical and method choices

JSON was selected as the checked-in runtime format because the existing project already uses
versioned JSON fixtures and can validate them with Python's standard library. Keeping XLSX as the
runtime source would add spreadsheet parsing dependencies and make automated validation harder;
copying the CSV would retain many source-only workflow columns and local frame paths that this
project does not need. A deterministic importer preserves the option to regenerate the compact
artifact from the original review queue while allowing GitHub users to inspect the resulting data
without the source project.

The real-name corpus was not merged into `benchmark.json`. Those 101 labels describe reviewed
names, but they have not yet been mapped to this repository's immutable canonical UUIDs and slugs.
Using them immediately for canonical accuracy or calibration would turn text similarity into an
unsupported identity claim and risk label leakage. They are therefore limited to candidate-name
evaluation, name-normalization evaluation, and future catalog alignment. Once mappings and a
casting-family grouped split exist, a qualified subset can be promoted into the formal benchmark.

### Verification evidence and remaining limitation

The central fixture validator passed with the new corpus included. Four focused human-label tests
passed, and the complete host test suite passed 45/45 with `PYTHONPATH=src`. Python compilation and
`git diff --check` also passed. A first complete-suite command omitted `PYTHONPATH=src` and therefore
could not import the package; rerunning with the repository's documented module path passed, so
that attempt is recorded as an invocation error rather than a product failure.

Targeted Ruff and mypy were not rerun in this host interpreter because those optional development
modules are not installed. An offline `uv` attempt could not access its external cache under the
workspace sandbox. The added code is covered by compilation and behavioral tests, but static-tool
verification should be repeated in the pinned development or Docker QA environment before a later
release claim expands beyond this Lite data milestone.

## 2026-09-01 — Lite/MVP fixture implementation and handoff

### Context, problem, and observable outcome

This iteration ran in **Lite / MVP Mode**. The starting specification described a production-shaped
resolver—catalog-backed identity, hybrid retrieval, reranking, calibrated abstention, an API, and a
reproducible benchmark—but the useful first delivery had to be demonstrable without claiming that
PostgreSQL, pgvector, external models, or a real marketplace catalog already worked. The engineering
problem was therefore twofold: build a complete resolution loop that could run offline, and make
every resulting claim traceable to a frozen fixture and an explicit runtime boundary.

The delivered offline path now accepts a noisy title, extracts generic syntax and catalog-derived
hints, retrieves candidates through sparse, dense, and structured signals, fuses them with RRF,
calibrates the leading candidate, and returns `matched`, `ambiguous`, or `no_match`. FastAPI exposes
that path through `/resolve` and `/health`; the default response omits internal evidence, while
`debug=true` returns bounded signals, ranks, conflicts, model versions, and stage timings. The
observable result is a versioned `fixture-v1` report over 21 synthetic test cases rather than an
unsupported production claim: Recall@25 and Top-1 are `1.0`, hard-negative accuracy is `1.0` (4/4),
precision is `1.0`, false-match rate is `0.0`, and coverage is `0.8333`.

Focused re-verification exposed three places where the implementation and its claims needed to be
tightened. First, series text needed to be treated as catalog knowledge, not an application-coded
rule, and a wrong series needed to remain a visible soft conflict rather than filter out the correct
candidate. Second, the heuristic reranker had been available in the pipeline without evidence that
it improved the fused ranking. Third, latency needed an HTTP-level measurement and an explicit
statement of what that measurement excluded. After correction, catalog-provided series values
produce `series_hints`; a target with a conflicting series remains in the top 25 and records
`structured_conflicts=["series"]`; RRF and the heuristic reranker both score Top-1 `1.0` on the same
12 matched frozen-test cases; and the report retains warmed in-process ASGI samples while stating
that Docker, TCP, reverse proxy, database, and concurrency were not measured.

### Implementation trace

The implementation was organized by pipeline responsibility so that each claim has a narrow code
and test surface:

- `data/`, `scripts/generate_fixture_data.py`, and `scripts/validate_fixture_data.py` establish the
  frozen catalog, benchmark, grouped split metadata, checksums, provenance, and fixture validators.
  This was necessary to make evaluation reproducible and to prevent synthetic data from being
  presented as scraped marketplace truth.
- `src/product_variant_resolver/{identity,catalog,ingestion}.py` defines immutable UUID/slug
  behavior, normalized catalog records, and idempotent in-memory ingestion.
  `src/product_variant_resolver/{signals,schemas}.py` keeps syntax
  extraction typed and generic. The series correction was implemented through the catalog-derived
  vocabulary assembled in `src/product_variant_resolver/service.py`, passed into
  `extract_signals`, and represented as
  `series_hints`; no Hot Wheels series branch was added to application code.
- `src/product_variant_resolver/retrieval.py` contains the token sparse baseline, deterministic
  `hashing-v1` dense baseline,
  structured match/conflict features, RRF, and fail-closed retrieval orchestration. Series joins
  year, color, collector number, and series position as a soft structured feature so conflicting
  evidence remains inspectable instead of destructively pruning a candidate.
- `src/product_variant_resolver/{rerank,service,config}.py` provides the pointwise interface, optional
  `heuristic-v1` implementation, pipeline assembly, and runtime selection. `reranker_enabled`
  defaults to false; when disabled, debug and health metadata report `disabled` instead of implying
  that a reranker ran.
- `src/product_variant_resolver/{calibration,policy,training}.py` implements logistic calibration,
  train-only model
  fitting, dev-only threshold selection, artifact/version checks, and the three-state decision
  policy. Training and evaluation both use the same catalog-derived color and series vocabulary,
  avoiding a mismatch between runtime and offline scoring.
- `src/product_variant_resolver/{api,observability}.py` and `ui/` supply structured request
  validation, error mapping,
  readiness, request correlation, privacy-safe logging, stage timings, and the minimal debug UI.
  API-provided strings are rendered as text, and raw titles are not placed in resolution logs.
- `src/product_variant_resolver/{evaluation,reporting}.py`,
  `scripts/generate_evaluation_report.py`, and `reports/fixture-v1/` preserve raw ranks, decision
  counts, latency samples, derivations, configuration, disclaimers, and SVG summaries. Reporting
  now records `selected_default="rrf"`, the exact reranker gain,
  whether an external cross-encoder was evaluated, and whether container latency was measured.
- `tests/unit/`, `tests/integration/`, `tests/api/`, `tests/evaluation/`, and `tests/ui/` cover identity,
  parsing, soft conflicts, fusion, calibration/policy guards, three-state resolution, fail-closed
  behavior, report disclosures, and UI rendering. `migrations/`, `Dockerfile`, and
  `docker-compose.yml` preserve future persistence/deployment boundaries, but their presence is not
  counted as runtime verification.

### Technical choices, alternatives, and trade-offs

The default retrieval path uses deterministic token overlap plus `hashing-v1` vectors because both
run offline and make the fixture loop reproducible. The specification's PostgreSQL FTS and exact
pgvector path remains the intended scalable alternative, while a pinned sentence-transformer is the
intended semantic alternative. The trade-off is deliberate: the current baselines have low setup
cost and fail no external dependency, but `hashing-v1` is not a neural embedding and the measured
fixture accuracy cannot establish semantic recall on real marketplace titles.

RRF was chosen over direct addition of sparse and dense scores because the component scores live on
different scales, while RRF needs only ranks and remains deterministic. Weighted score fusion could
eventually learn more domain-specific signal weighting, but it would add tuning risk to a 100-case
synthetic benchmark. Structured attributes therefore contribute explicit matches and conflicts
without becoming hard filters, preserving recall when seller titles contain an incorrect year,
color, or series.

Calibration and abstention were retained instead of an always-pick-Top-1 policy because an entity
resolver must refuse weak or near-tied evidence. The calibration model is fit on grouped train data,
thresholds are selected on grouped dev data, and test labels are held for final evaluation. This
adds artifact and policy-version management, but it makes `ambiguous` and `no_match` first-class
outcomes and exposes the precision/coverage trade-off.

The pointwise reranker underwent an explicit **selection reversal**. Before the frozen comparison,
the architecture allowed the local heuristic after RRF as a normal pipeline stage. Catalog-derived
series handling then strengthened the generic retrieval and structured evidence, and the same 12
matched test queries produced Top-1 `1.0` for both RRF and `heuristic-v1`. The measured absolute gain
was therefore `0.0`, below the R11 `0.05` value gate. After that evidence, the runtime default was
changed to RRF, the heuristic became an opt-in/offline ablation via
`PVR_RERANKER_ENABLED=true`, and calibration/policy versions were aligned with the RRF path. This
avoids paying for and explaining an unproven stage while preserving a replaceable pointwise
interface. No external cross-encoder was evaluated, so this decision does not predict whether a
pinned neural reranker would help on real hard negatives.

### Verification evidence

Final QA recorded **PASS WITH RISKS** for the dependency-light fixture path. The available unit,
integration, API, UI harness, fixture, training, evaluation, and reporting suite passed 38/38;
Python compilation and fixture validation passed; calibration and dev-selected policy artifacts
were regenerated with `test_labels_accessed=false`; and both default and PostgreSQL-profile Compose
configurations passed static validation. Manual API checks observed all three decision states,
default debug omission, bounded debug candidates, structured validation failures, and fail-closed
responses for a missing catalog, PostgreSQL backend selection, unavailable external providers, and
a simulated retriever failure.

The frozen data evidence is `fixture-v1`: 120 products and 100 benchmark cases (`60 matched`,
`20 ambiguous`, `20 no_match`) across 14 casting families and 30 near-duplicate groups. Families
occur in exactly one query split, and the catalog and benchmark SHA-256 values match
`data/manifest.json`. The checked-in report evaluates exactly 21 synthetic test cases, including 12
matched cases, and retains the raw counts used by every headline metric.

Latency evidence is intentionally bounded. The latest checked-in report records internal-pipeline
p95 `1.5525 ms` and warmed in-process HTTP/ASGI p95 `7.9523 ms`, each over 21 sequential samples
after five excluded warm-up requests at candidate K=25. A separate fresh QA regeneration recorded
HTTP/ASGI p95 `2.45 ms`; both remain below the 1500 ms fixture smoke budget. These numbers include
FastAPI middleware, validation, dispatch, serialization, and response headers only for the
in-process boundary. They do not include Docker/container startup or execution, TCP/network,
PostgreSQL, a reverse proxy, concurrency, or load, and must not be reported as production latency.

Traceable sources are the [MVP brief](../specs/product-variant-resolver/mvp-brief.md),
[final QA review](../specs/product-variant-resolver/review.md),
[versioned report](../reports/fixture-v1/evaluation-fixture-v1-test.md), and
[MVP evidence](evidence/product-variant-resolver-mvp.md).

### Incomplete work, risks, and next step

The offline fixture path is demonstrable, but the original technology scope is not complete.
`PostgresRetrieverAdapter.execute_ranked` remains unimplemented; Alembic migration cycles,
PostgreSQL ingestion, FTS, exact pgvector retrieval, and live database failure behavior were not
run. The verified dense provider is `hashing-v1`, and the verified optional reranker is
`heuristic-v1`; no pinned external embedding model or cross-encoder, license/checksum, or local
model-cache flow was exercised. Selecting those unavailable providers correctly fails readiness,
but that is not equivalent to implementing them.

Docker received static configuration checks only because the daemon was unavailable. Image build,
container health, read-only filesystem behavior, Alembic execution, and the project-pinned Python
3.12 runtime remain unverified; host QA used macOS arm64 with Python 3.14.6. The UI was exercised
through a Node DOM harness rather than a live browser, post-start readiness transition is not yet
covered, the Starlette TestClient deprecation warning remains, and no formal architect, security,
or performance-agent review was performed.

The next highest-value step is to run the existing default stack in Docker on Python 3.12 and
capture container/TCP health and latency evidence without weakening the current disclaimer. If the
repository will claim PostgreSQL/pgvector or neural models as executable features, implement and
integration-test those adapters next; otherwise keep them explicitly deferred. Real catalog data
and marketplace-derived hard negatives are required before revisiting semantic retrieval,
reranking, calibration, or production-accuracy claims.

## 2026-09-01 — Docker/Python 3.12 runtime milestone

### Context, problem, and observable outcome

The preceding handoff had only static Docker Compose validation. The daemon was unavailable during
that QA pass, so the documentation correctly treated image construction, Python 3.12 execution,
container readiness, filesystem restrictions, real port forwarding, and the installed reporting
CLI as unverified. That was the largest remaining gap in the default offline MVP: source-level and
in-process evidence existed, but a user still could not point to a successful build-and-run record
for the shipped container.

This milestone closes that gap for the **default offline runtime**. A no-cache image build ran on
Docker Desktop 29.5.3/aarch64, installed the project on Python 3.12.14, started healthy as non-root
user `pvr` (UID 100) with a read-only root filesystem and writable `/tmp` tmpfs, and exposed only
the loopback-bound API port. From the host, health, UI assets, `matched`, `ambiguous`, and
`no_match` flows were observable; default responses omitted debug data and carried request IDs. A
separate missing-catalog container returned health and resolve 503 without asserting an identity.
The installed `pvr-report` command also generated and validated its JSON, Markdown, and four SVG
artifacts inside the rebuilt read-only image.

### Implementation trace

The runtime work added `scripts/measure_http_latency.py` to give host→container timing a dedicated,
repeatable measurement path instead of reusing the in-process TestClient numbers. Its output,
`reports/runtime-validation/docker-python312-http-latency.json`, freezes the boundary, environment,
warm-up/sample counts, percentile method, summary, raw samples, request payload, and explicit
inclusions/exclusions. Keeping this result separate from `reports/fixture-v1/` prevents the fixture
evaluation report's in-process ASGI latency from being mistaken for a container measurement.

`pyproject.toml` added `httpx2>=2,<3` to runtime dependencies. The reason is operational rather than
test-only: the installed `pvr-report` entry point directly uses FastAPI TestClient when it generates
HTTP samples. The runtime image therefore needs the compatible client library even when development
extras are not installed. The Dockerfile and default Compose configuration did not need a new
product architecture; the milestone exercised their existing non-root, read-only, tmpfs,
loopback-port, and healthcheck settings and captured evidence that those settings work together.

### Technical choices, alternatives, and trade-offs

Host→container latency is measured with a small standard-library HTTP script rather than folding a
live socket test into the fixture evaluator. This keeps the artifact dependency-light and makes the
boundary explicit: host `urllib`, Docker Desktop port forwarding, Uvicorn/FastAPI, resolver work,
and JSON serialization/parsing are included. An in-container TestClient benchmark would be faster
and more deterministic but would skip port forwarding; a full load tool behind TLS and a proxy
would be closer to production but would add infrastructure and concurrency questions outside this
Lite milestone. The selected sequential, concurrency-1 loopback smoke is therefore useful for
runtime verification, not capacity planning.

For reporting dependencies, alternatives included putting `pvr-report` behind a separate extra or
image, rewriting its HTTP measurement to avoid TestClient, or leaving the HTTP client in the dev
extra. Keeping `httpx2` in runtime dependencies makes the already-shipped CLI usable in the default
image with the smallest code change. The trade-off is a larger runtime dependency surface and
weaker rebuild reproducibility because versions are bounded but not locked.

### Decision changes

Before this milestone, Docker/Python 3.12 was documented as unverified and T23 remained partial;
only Compose syntax had passed. After the successful build, health/UI/three-state flow,
missing-catalog failure, filesystem/user checks, and host→container measurement, the default
offline Docker runtime is now an evidenced deliverable and T23 is complete for that Lite boundary.
This does not promote the optional PostgreSQL profile into a working resolver path.

QA also found that the reporter's HTTP client could not be treated as merely a development concern:
`pvr-report` is installed in the runtime image and invokes TestClient directly. The prior dependency
boundary therefore did not guarantee a usable shipped CLI. After moving the compatible client to
runtime requirements, a no-cache rebuild resolved FastAPI 0.141.1, Starlette 1.6.0, httpx2 2.12.0,
and httpcore2 2.12.0; `pvr-report` then produced all six expected artifacts under the read-only,
non-root constraints. The repository still has no lockfile or constraints file, and the dev extra
still lists legacy `httpx`, so this is a runtime-boundary correction rather than complete dependency
reproducibility.

### Verification evidence

The verified image was `product-variant-resolver:lite` with image ID
`sha256:f5df8cba0c0abaae77b1e01be9269cdbef2dd874be5b168da47aed5d365cc739`.
Docker reported version 29.5.3/aarch64; the container reported Python 3.12.14, UID/GID
`100(pvr)/101(pvr)`, `ReadonlyRootfs=true`, and a healthy loopback publication at
`127.0.0.1:8000`. `/app` was not writable and `/tmp` was writable. Container compile passed with
bytecode directed to `/tmp`; mounted API tests passed 8/8 and reporting tests passed 2/2. Earlier
runtime runs also passed 10 unit, 7 integration, 4 evaluation-metric, and 5 fixture tests, while
direct container evaluation retained Recall@25 `1.0`, Top-1 `1.0`, hard-negative accuracy `1.0`,
precision `1.0`, coverage `0.8333`, and false-match rate `0.0`.

The checked-in [Docker latency artifact](../reports/runtime-validation/docker-python312-http-latency.json)
contains 50 finite sequential samples after 10 warm-ups. Sorting those samples and applying the
recorded nearest-rank rule, `ceil(0.95 * 50) - 1`, reproduces p95 **`4.721208 ms`**; median is
`2.7867085 ms` and mean is `3.14272922 ms`. The test used one local macOS arm64 machine,
concurrency 1, loopback, and the offline-memory backend. Container startup, warm-ups, TLS, reverse
proxy, remote network, concurrent load, and PostgreSQL are excluded. This is a runtime smoke result,
not production latency.

The no-cache reporter verification generated exactly one JSON, one Markdown, and four SVG files.
The JSON passed `validate_report_payload`, retained 21 in-process HTTP samples and the exact
21-case synthetic disclaimer, and correctly kept `container.measured=false` because that report's
latency is not the host→Docker artifact. The final [QA review](../specs/product-variant-resolver/review.md)
records R13 as PASS for this limited boundary, R15 as PASS WITH RISK, and R16 as PASS; the full host
suite remains 38/38 green.

### Incomplete work, risks, and next step

The verified boundary is intentionally narrow. PostgreSQL ingestion, FTS, exact pgvector search,
migration-cycle E2E, external embeddings/cross-encoders, TLS, reverse proxy, remote network,
concurrency/load, and post-start dependency failure transitions remain unverified. The runtime
artifact comes from one Docker Desktop arm64 machine and cannot support a production latency or
capacity claim. The UI still lacks a live-browser smoke beyond the Node harness, and no formal
architect, security, or performance-agent review was performed.

Dependency resolution is the next hardening priority. The successful image used compatible bounded
ranges, but no committed lockfile or constraints file ensures the same versions on a future build;
the dev extra's legacy `httpx` also continues to produce a host warning. The next highest-value step
is to freeze or constrain the verified runtime set and reconcile the TestClient dependency across
runtime and development. PostgreSQL/pgvector and external-model adapters should remain explicitly
deferred unless they are implemented and integration-tested before being claimed.

## 2026-09-02 — GitHub publication milestone

### Context, problem, and observable outcome

The publication requirement was narrower than “push the workspace.” The user explicitly wanted
only `Product Variant Resolver/` to become the GitHub repository so that the parent workspace's
`AGENTS.md`, `.codex/` agent configuration, and original `Product Variant Resolver.md` requirement
document would not enter public history. Treating the parent directory as the Git root and relying
on an ignore list would have made that boundary easier to misconfigure and harder to prove after
the fact.

Publication therefore used the existing independent Git repository rooted inside
`Product Variant Resolver/`. That repository already contained two project commits:
`5fef769` (`feat: establish offline product resolver MVP`) followed by `ad9b74a`
(`test: validate Docker Python 3.12 runtime`). GitHub publication completed successfully to the
public repository `MatthewC144/product-variant-resolver` on `main`. The local branch now tracks
`origin/main`, and both pointed to `ad9b74a` when this milestone was verified. The project is
publicly reviewable without placing the parent workspace's agent instructions or source brief in
the published history.

### Implementation trace

No product code was changed to make publication work. The important implementation boundary is the
nested repository itself: `/Users/yuchen/Desktop/resume project2/Product Variant Resolver/.git`
owns only the project subtree, while the outer workspace remains outside that repository. The
tracked-file inventory begins with project-owned files such as `.dockerignore`, `.env.example`,
`.gitignore`, `Dockerfile`, `README.md`, configuration, fixture data, evidence, migrations, source,
tests, and UI assets. A history-wide name check returned no tracked `AGENTS.md`, `.codex/` path, or
parent-level `Product Variant Resolver.md` requirement document.

The repository remote is the credential-free HTTPS URL
`https://github.com/MatthewC144/product-variant-resolver.git` for both fetch and push. The local
`main` branch was published and configured to track `origin/main`. This project-log entry records
the publication workflow and its safety boundary; it does not copy any outer workspace content into
the repository.

### Technical choices, alternatives, and trade-offs

An independent subdirectory repository was selected over initializing Git at the parent workspace
and maintaining a large exclusion list. A parent repository plus `.gitignore` could also publish a
single project, but one missed pattern or later `git add -f` could expose orchestration files. A
subdirectory Git root makes the intended scope structural: normal Git commands cannot stage parent
files because they are outside the work tree. The trade-off is operational discipline—contributors
must run Git commands from this repository or explicitly pass its path, and parent-workspace tooling
must not be assumed to manage this history.

HTTPS was retained for the remote rather than placing a personal token in the URL or repository
configuration. The GitHub plugin was useful for verifying the authenticated account
`MatthewC144` and the public target repository, but it did not expose a create-repository
capability. The local `gh` token was also no longer valid. Alternatives were to renew CLI
authentication, switch to SSH after configuring a key, or wait for a plugin capability change.
For this one-time bootstrap, the smallest authorized path was for the user to create an empty
public repository in GitHub and then let standard Git publish the already-prepared local history.
This added one manual step but avoided inventing unsupported plugin behavior or placing credentials
in project files.

### Decision changes

The initial automation preference was to create and publish the repository through an available
GitHub integration or the local `gh` CLI. Capability and authentication checks changed that plan:
the plugin could validate the GitHub identity and repository state but could not create a
repository, while the local CLI credential could not authorize creation. Continuing with either
path would have required new authentication authority or an unsupported operation.

After that evidence, repository creation was split from code publication. The user created the
empty public `MatthewC144/product-variant-resolver` repository; the local independent repository
then added the clean HTTPS remote and performed the first push to `main`. This preserved the
subfolder-only history and avoided expanding the agent's credential or repository-creation
authority. Now that `origin` exists and `main` tracks `origin/main`, future releases do not need the
create-repository capability; they use the normal reviewed commit-and-push workflow.

### Verification evidence

The GitHub plugin verified the signed-in account as `MatthewC144` and the destination as the public
repository `MatthewC144/product-variant-resolver`. Local Git independently showed:

- `origin` fetch and push URLs are both
  `https://github.com/MatthewC144/product-variant-resolver.git`;
- the active branch is `main`, configured as `[origin/main]`;
- `HEAD`, `main`, and `origin/main` resolved to `ad9b74a` after the successful first push;
- the two published commits were `5fef769` and `ad9b74a`, in that order; and
- `git ls-files` plus a history-wide path-name search found no `AGENTS.md`, `.codex/`, or parent
  `Product Variant Resolver.md` content in tracked history.

The first push completed successfully, and the local working tree was clean before this
post-publication documentation entry was added. The remote URL contains no embedded token. This
milestone did not rerun application tests because publication did not change product behavior; the
quality and Docker evidence remain attached to the two published commits and the preceding log
entries.

### Incomplete work, risks, and next step

The GitHub plugin still cannot create repositories, and the local `gh` credential remains
unusable until the user deliberately reauthenticates it. Neither limitation blocks routine work on
the existing `origin`, but a future repository bootstrap must again use an explicitly authorized
creation path. The project is public, so future commits must continue to avoid credentials,
machine-local files, external private data, and parent-workspace instructions. Publication does not
change the previously documented product limitations around synthetic fixtures,
PostgreSQL/pgvector, external models, or production readiness.

For future remote updates, begin inside `Product Variant Resolver/`, confirm
`git rev-parse --show-toplevel` resolves to that directory, inspect `git status` and the staged
diff, and repeat the tracked-path check for `AGENTS.md`, `.codex/`, and the parent requirement file
before committing. Push ordinary reviewed commits to `origin main`, then confirm local `main` and
`origin/main` agree. Do not initialize or publish the parent workspace, embed tokens in remote URLs,
or use force-push as a routine update mechanism. Documentation changes made after the initial
two-commit publication, including this milestone record, should follow that same review, commit,
push, and remote-verification sequence.

## 2026-09-06 — Quantity `x` token-boundary correction

### Context, problem, and observable outcome

While reviewing the signal-extraction stage, a concrete false positive was reproduced from the
title `box12 Nomad`: the quantity expression treated the trailing `x12` inside the word `box12` as
an independent quantity marker. `extract_signals()` therefore returned `quantity=12` and
`multipack_hint=true`, even though the title did not contain a quantity token. This could distort
the structured evidence passed into retrieval and make an ordinary single-product title look like
a multipack.

The correction narrows only the `x` quantity syntax. After the change, an `x` must begin outside a
word, so `box12` is no longer interpreted as a quantity while the intentionally supported forms
`x12` and `x 12` continue to produce quantity 12. The observable behavior is therefore more
precise without removing the compact marketplace notation that the resolver already accepted.

### Implementation trace

The regression was captured first in `tests/unit/test_identity_signals.py`. The new coverage
asserts both sides of the contract: the embedded substring in `box12 Nomad` must not produce a
quantity or multipack hint, while standalone `x12` and `x 12` remain valid. Writing the failing
test before the fix preserved the original defect as evidence and prevented a narrow correction
from silently breaking supported input.

The product change is confined to the quantity pattern in
`src/product_variant_resolver/signals.py`. Only the `x` branch of `QUANTITY_RE` changed, gaining the
negative lookbehind `(?<!\w)`. No retrieval, ranking, calibration, policy, API, or catalog behavior
was modified. This limited scope matches the root cause: the extractor lacked a left token
boundary for one syntax branch rather than having a broader quantity-parsing design failure.

### Technical choices, alternatives, and trade-offs

The selected boundary, `(?<!\w)x`, rejects an `x` immediately preceded by a Unicode word
character while still accepting `x12`, `x 12`, and an `x` preceded by punctuation or whitespace.
It was chosen as the smallest rule that describes the intended semantic distinction: `x` is a
quantity marker only when it starts a token-like expression, not when it is part of an existing
word.

A simple whitespace requirement was considered conceptually but would be unnecessarily strict:
marketplace titles can place compact quantity markers after punctuation or at the beginning of a
title. A broader parser or post-match tokenization layer could offer more control over multilingual
and unusual listing formats, but it would enlarge the change surface without evidence that those
formats are currently required. The accepted trade-off is that this remains a regex-based,
English-oriented heuristic rather than a general quantity grammar.

### Decision changes

The earlier quantity rule implicitly allowed the `x` marker at any character position. Review
evidence from `box12 Nomad` showed that this permissive behavior was not merely theoretical: it
produced a false structured signal and a false multipack hint. The decision was therefore narrowed
from “any `x` followed by digits may indicate quantity” to “only an `x` without a word character on
its left may indicate quantity.”

The supported configuration and public signal schema did not change. Existing `lot of`, `qty`,
`quantity`, and pack-style branches were deliberately left untouched because the reproduced fault
and regression coverage concern only the standalone `x` notation.

### Verification evidence

The responsible implementation run reported that the new unit test failed before the regex change
and passed afterward. Following the correction, the signal-focused unit set passed **6/6**, the
complete `unittest` suite passed **39/39**, and `git diff --check` reported **PASS**. These results
verify the local Python test boundary and patch formatting; they do not add Docker, browser,
PostgreSQL, external-model, or production accuracy evidence.

The test run continued to emit the repository's existing Starlette/httpx deprecation warning. No
new warning was attributed to this change, but the warning remains part of the active dependency
maintenance risk and should not be represented as resolved by the passing suite.

### Incomplete work, risks, and next step

Quantity extraction still recognizes a deliberately small set of English-oriented patterns. This
milestone did not expand coverage for other languages, locale-specific notation, Unicode
multiplication symbols, or additional marketplace-specific quantity formats, and it did not
replace regex extraction with a parser. Those cases remain deferred until real catalog or listing
evidence justifies their complexity.

The highest-value next action is to continue the planned Lite-mode product work while keeping new
quantity formats evidence-driven: when a real false positive or false negative is found, add the
smallest paired regression test before changing the grammar. Separately, the existing
Starlette/httpx deprecation warning should be resolved through the already documented dependency
reconciliation work rather than mixed into signal-extraction changes.

## 2026-09-06 — Python 3.12 dependency contract hardening

### Context, problem, and observable outcome

The Lite runtime had already been exercised with Python 3.12 and Docker, but dependency resolution
was still allowed to drift inside broad version ranges. The immediate symptom was a deprecation
warning during TestClient use. Investigation traced the first cause to the development extra
explicitly installing legacy `httpx`: with Starlette 1.3+/1.6 this allowed TestClient to take its
legacy fallback path even though the project already depended on the current `httpx2` transport.
Removing that duplicate transport exposed a second, independent compatibility warning in a fresh
Python 3.12 environment: AnyIO 4.15.1 deprecated an alias still imported by Starlette 1.6.

The dependency contract is now explicit for the compatibility-sensitive Python 3.12 web stack.
Fresh constrained installation selects one TestClient transport and keeps its import warning-free;
ordinary Docker builds consume the same constraints instead of silently choosing new FastAPI,
Starlette, transport, AnyIO, Pydantic, or Uvicorn versions. This is dependency hardening for the
existing Lite application, not a product-feature or retrieval-behavior change.

### Implementation trace

`pyproject.toml` removed legacy `httpx` from the `dev` extra. Runtime `httpx2` remains because the
installed `pvr-report` command uses FastAPI TestClient, so this was not merely a test-only concern.
The direct dependency declarations continue to express supported ranges; they were not replaced
with exact pins in project metadata.

`constraints/python312.txt` was added as the selective exact-version layer for the validated web
stack: FastAPI 0.141.1, Starlette 1.6.0, `httpx2` 2.12.0, `httpcore2` 2.12.0, AnyIO 4.14.0,
Pydantic 2.13.5, and Uvicorn 0.52.4. `constraints/README.md` explains the scope, local install
command, coupled update procedure, and evidence required before promoting future versions.
`Dockerfile` now uses `python:3.12.14-slim`, copies the constraints directory, and applies
`constraints/python312.txt` through pip's `-c` option while installing the existing PostgreSQL
extra.

`tests/unit/test_dependency_constraints.py` adds executable contract checks rather than relying on
documentation alone. It verifies that every direct runtime dependency is represented in the
Python 3.12 constraints, that Docker applies the constraint file, and that development no longer
installs legacy `httpx` while the selected TestClient transport and AnyIO compatibility pin remain
present.

### Technical choices, alternatives, and trade-offs

A selective constraints file was chosen instead of converting `pyproject.toml` to exact versions.
This preserves normal Python package semantics—direct dependencies still publish bounded supported
ranges—while Docker and reproducible local verification can constrain the small stack whose
versions demonstrably interact. The alternative of leaving only broad ranges was simpler, but a
future install could reproduce either warning or introduce an unreviewed compatibility change.
A complete transitive lock would provide stronger reproducibility, but it would also expand this
Lite milestone into packaging, platform-marker, PostgreSQL, and build-tool resolution work that has
not yet been runtime-validated.

AnyIO 4.14.0 was pinned instead of suppressing the warning or accepting AnyIO 4.15.1. Warning
suppression would hide compatibility drift without removing it, while changing Starlette or the
TestClient transport again would disturb the already validated FastAPI stack. Keeping the known
Starlette 1.6/`httpx2` 2.12 combination and constraining the smallest newly identified edge made
the dependency decision evidence-driven. The fixed Docker patch tag similarly reduces unexpected
Python drift, while deliberately avoiding an architecture-specific digest so the same Dockerfile
continues to support ARM64 and AMD64.

### Decision changes

The first decision was to resolve the TestClient warning solely by removing legacy `httpx` from
development dependencies and relying on the project's existing `httpx2` runtime dependency. A
fresh Python 3.12 install showed that this was necessary but insufficient: once the legacy fallback
was gone, AnyIO 4.15.1 produced a separate alias-deprecation warning through Starlette 1.6. The
decision therefore changed from transport cleanup alone to a coupled, selectively constrained web
stack with AnyIO fixed at 4.14.0.

The runtime-image policy also narrowed from the moving `python:3.12-slim` family to the verified
`python:3.12.14-slim` patch tag, and from unconstrained pip resolution to `pip -c`. These changes do
not claim that every transitive package is locked: PostgreSQL extras and packaging dependencies
remain range-resolved. Future updates must treat Starlette, AnyIO, `httpx2`, and `httpcore2` as a
compatibility set and regenerate evidence rather than changing one pin in isolation.

### Verification evidence

The responsible implementation run created a fresh environment under `/private/tmp` with Python
3.12.13 and installed the project successfully using the new constraints. Importing and using
FastAPI TestClient was warning-free. The full suite passed **41/41** with warnings promoted to
errors via `pytest -W error`; `pip check`, targeted Ruff, targeted strict mypy, Docker Compose
configuration validation, and `git diff --check` all reported **PASS**. Docker Hub manifest
inspection confirmed that the selected `python:3.12.14-slim` base is published for both ARM64 and
AMD64.

This initially proved constrained host installation and the static dependency/Docker contract. At
that point the Docker daemon was not running, so the first record correctly stopped short of
container validation. A subsequent closure run on Docker Desktop 29.5.3 completed
`docker compose build --no-cache api` and produced image
`sha256:e67d64e95abab329c901bdb5946f86962a09dc7217e2048a3b1c0568ec8b9d75`.
The image reported Python 3.12.14, UID/GID `100(pvr)/101(pvr)`, FastAPI 0.141.1, Starlette 1.6.0,
`httpx2`/`httpcore2` 2.12.0, AnyIO 4.14.0, Pydantic 2.13.5, and Uvicorn 0.52.4. A
`python -W error` TestClient import completed without warnings, and legacy `httpx` was absent.

With the repository mounted into a read-only container and writable paths supplied through tmpfs,
the 39 backend/API/evaluation/reporting/integration/unit/fixture tests that do not require Node all
passed. The attempted full 41-test container selection was not a 41/41 pass: the UI controller
test errored because this runtime image intentionally has no Node executable. That is a validation-
environment boundary, not evidence of a UI regression; the fresh constrained host Python 3.12
environment remains the evidence for the complete 41/41 suite. In the same read-only container,
`pvr-report` generated one JSON, one Markdown, and four SVG artifacts successfully. Compose reached
healthy state; inspection confirmed `User=pvr` and `ReadonlyRootfs=true`; live HTTP checks returned
ready health plus the expected `matched`, `ambiguous`, and `no_match` outcomes, with no identity in
the latter two states.

The container closure promotes the exact selected pins from host-only to container-verified for
this Lite offline boundary. It does not change the earlier scope caveats: full-repository Ruff still
reports 36 pre-existing findings, and whole-repository mypy debt also remains outside this focused
dependency check.

### Incomplete work, risks, and next step

`constraints/python312.txt` is intentionally not a complete transitive lock. PostgreSQL extras,
setuptools/build tooling, platform markers, and indirect packages outside the compatibility-
sensitive web stack may still resolve differently, so this milestone does not establish fully
reproducible builds. It also does not resolve the 36 existing whole-repository Ruff findings or
change the previously deferred PostgreSQL runtime adapter.

The no-cache container closure is now complete for the Lite offline path. The next dependency
decision is deferred until the PostgreSQL runtime path is implemented: at that stage, evaluate a
complete transitive lock that includes its extras and repeat the same constrained build/runtime
evidence. Until then, the selective constraints must not be described as a complete lock, the
runtime image must not be expected to execute Node-based UI tests, and the existing whole-repository
Ruff/mypy findings remain explicit maintenance debt.

## 2026-09-06 — T04 PostgreSQL/pgvector migration-cycle verification

### Context, problem, and observable outcome

T04 already had an Alembic `0001` migration describing the PostgreSQL/pgvector catalog schema,
but the repository did not yet contain runtime evidence that a new database could apply it,
reverse it, and apply it again without schema drift. The task therefore closed the verification
gap rather than redesigning the database: the existing migration schema required no changes.

An isolated PostgreSQL 16/pgvector database now completed the full
empty → upgrade `0001` → downgrade `base` → upgrade `0001` cycle. Both upgraded states were
inspected and found equivalent. The observable result is a reproducible T04 check that verifies
the seven application tables, their identity and integrity constraints, the required indexes and
specialized PostgreSQL types, the `vector` extension, and final Alembic revision `0001`.

### Implementation trace

`scripts/verify_postgres_migration.py` was added as the executable verification boundary. Before
making any migration change it requires an empty application schema, then drives Alembic through
the complete cycle and inspects PostgreSQL metadata after each upgrade. The runner asserts all
seven application tables; their primary keys; the required product, alias, and identifier unique
constraints; the complete normalized release-year expression; and each cascade foreign key from
its source column to `product_variant.canonical_uuid`. Index checks bind table, index name, access
method, ordered columns, and column order rather than accepting a name/method match alone. The
runner also verifies `product_search.search_document` as `tsvector`,
`product_embedding.embedding` as `vector(192)`, removal of the application tables after
downgrade, and final database revision `0001`. Alembic's `script_location` is resolved to an
absolute repository path so execution does not depend on the caller's working directory.

`Dockerfile` now includes this runner so the verification can execute from the same constrained
project image used by the repository. `.dockerignore` was narrowed only enough to allow
`scripts/verify_postgres_migration.py` into that build context; other scripts remain excluded.
The existing `migrations/versions/0001_initial_catalog.py` schema was left unchanged because the
runtime assertions matched its intended contract. No API, resolver, fixture, retrieval, or
calibration code changed as part of T04.

### Technical choices, alternatives, and trade-offs

A committed, fail-fast runner was selected instead of documenting only a sequence of manual
Alembic and `psql` commands. Manual commands could demonstrate one successful attempt, but they
would leave important checks dependent on operator memory and make the downgrade/second-upgrade
comparison difficult to repeat consistently. The runner turns the intended migration contract
into executable assertions and produces a structured result that a future developer or CI job can
re-run against a disposable database.

The accepted trade-off is deliberate strictness: this runner is for isolated, empty databases and
refuses to operate when application tables already exist. It is not a general database diagnostic
or an upgrade tool for developer or production data. The empty-schema guard deliberately inspects
application tables, not every possible schema object, so it must still be paired with a disposable
database rather than treated as a universal safety detector. Schema assertions use PostgreSQL
catalog and SQLAlchemy inspection rather than adding a second migration framework. No
approximate-nearest-neighbor index was added because T04 only establishes the schema and the
planned T10 path requires exact pgvector retrieval at MVP scale; an ANN structure would add
maintenance and tuning without a current acceptance requirement.

### Decision changes

The prior project record treated PostgreSQL migration cycling as deferred because only migration
files and static Compose configuration had been reviewed. Runtime evidence from the isolated
cycle now promotes T04 itself to complete: the database can be created, downgraded, and recreated,
and the resulting constraints, indexes, types, extension, and revision are explicitly checked.
This does not promote the broader PostgreSQL resolver path, because ingestion and retrieval remain
separate tasks.

The downgrade policy intentionally removes the application schema while leaving the `vector`
extension installed. Extensions can be shared by other schemas or applications in the same
database, so automatically dropping it would create a wider destructive boundary than T04 needs.
Consequently, the runner checks that application tables are gone after downgrade but does not
misrepresent retention of the shared extension as a failed rollback.

QA follow-up initially identified three ways a schema check could pass too loosely: indexes could
match without proving their ordered columns, foreign keys could match without proving their target,
and the release-year check could be accepted from partial numeric fragments. The runner was
narrowed to compare complete index tuples, complete source/target/delete-action foreign-key tuples,
and the normalized full check expression. The absolute Alembic script path additionally removes a
working-directory assumption. Re-execution closed these verification risks without changing the
`0001` migration itself.

### Verification evidence

The responsible implementation run used the isolated Compose project name `pvr-t04` and host port
`55432`, keeping the verification separate from ordinary project services and local PostgreSQL
ports. It reported a successful empty → upgrade `0001` → downgrade `base` → upgrade `0001` cycle
and passed every schema assertion: seven tables, primary and unique constraints, the release-year
check, fully targeted cascade foreign keys, btree/GIN index definitions including ordered columns,
`tsvector`, `vector(192)`, the `vector` extension, and final revision `0001`. A separate sentinel
safety check created an application table before invocation and confirmed that the runner refused
to migrate or downgrade the non-empty schema. After verification, the temporary container,
network, and volume were removed.

The same implementation run reported **41/41 host tests PASS**, Python compilation of the added
runner and migration sources **PASS**, and `git diff --check` **PASS**. These results support the
migration runner, existing host behavior, and patch integrity. They do not constitute PostgreSQL
fixture-ingestion, sparse-FTS, exact-vector-retrieval, resolver-E2E, production-data, or
concurrent-load evidence.

### Incomplete work, risks, and next step

Creating the `vector` extension depends on database permissions; environments where the migration
role cannot install extensions still need administrator provisioning or a documented preinstall
step. The runner must remain restricted to disposable empty databases because its deliberate
downgrade would remove all application tables. The guard detects existing application tables but
does not inventory views, functions, types, or every other possible object in `public`, and CI does
not yet provision PostgreSQL and run this cycle automatically. Its decision to preserve the shared
`vector` extension also means the cycle does not prove complete database-level teardown. ANN
indexing remains unnecessary for the exact-search MVP and has not been implemented or evaluated.

T07, T09, and T10 remain incomplete: PostgreSQL fixture ingestion, PostgreSQL full-text search,
and exact pgvector retrieval have not been exercised by this milestone. The single highest-value
next action is **T07 — implement idempotent PostgreSQL fixture ingestion**, preserving immutable
canonical IDs and catalog/index version metadata while proving that repeated loads are identical
and invalid or colliding fixtures fail transactionally. Completing T07 will turn the verified
empty schema into a populated, repeatable database foundation for the later retrieval tasks.

## Required format for future entries

Every future project-log entry must preserve the following traceability structure:

1. **Context, problem, and observable outcome:** explain what triggered the work, what was wrong or
   missing, what was executed, and what a caller or evaluator can observe afterward.
2. **Implementation trace:** name the changed modules or file groups and explain why each group
   changed; do not provide only a list of completed tasks.
3. **Technical choices, alternatives, and trade-offs:** record the selected method, viable
   alternatives considered, and the cost or limitation accepted.
4. **Decision changes:** when a choice is reversed or narrowed, record the before/after decision,
   the exact evidence that triggered it, and any version/configuration impact.
5. **Verification evidence:** cite commands/results already produced by the responsible agent,
   frozen data/report versions, raw-count-derived metrics, runtime/hardware, and measurement scope.
   Never upgrade a static check into runtime evidence or a synthetic result into a production claim.
6. **Incomplete work, risks, and next step:** state deferred adapters, unrun environments/reviews,
   known warnings, and the single highest-value next action.

Entries may use a small table or compact list for navigation, but the main record must remain an
explanatory engineering narrative linked to existing specifications, code, QA evidence, or reports.
