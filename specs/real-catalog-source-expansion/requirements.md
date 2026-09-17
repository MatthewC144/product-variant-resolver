# VAR-PLAN2 — Real catalog source-access and staged-expansion requirements

Date:2026-09-16. Mode:Lite. Status:DRAFT EXECUTED;collection remains blocked pending source permission
and a separate owner-approved canary. Upstream:VAR-REVIEW1 complete4/4 at commit`e4af68f`.

## Purpose and scope

Turn the owner's approximately3,000-row goal into a source-specific,fail-closed collection contract.
This checkpoint researches public rules and creates a machine-checkable plan only. It does not crawl
Hot Wheels Wiki,call its API,download images,write PostgreSQL,promote reviewed releases,or create UUIDs.

## Observable requirements

### VSP-R1 — Distinguish content license from access permission

WHEN a source is proposed,THE SYSTEM SHALL record content-license evidence and automated-access terms
as separate fields;general CC BY-SA reuse language SHALL NOT be treated as automated collection consent.

### VSP-R2 — Block Fandom collection without written permission

WHILE Fandom's current terms require express written permission for automated access and no project-specific
permission artifact exists,THE SYSTEM SHALL set collection disabled,approve zero endpoints and make zero
source requests;MediaWiki API etiquette SHALL NOT substitute for Fandom permission.

### VSP-R3 — Preserve exact research provenance

WHEN public policy research is recorded,THE SYSTEM SHALL retain publisher,URL,check time,last-revision when
available,observed rule,retrieval limitation and whether the evidence is source-specific or general guidance.

### VSP-R4 — Require a second canary gate after permission

IF written source permission is later obtained,THEN THE SYSTEM SHALL verify its scope/expiry/endpoints,
the Hot Wheels community text license and robots rules,and SHALL require separate owner approval of an exact
canary manifest before any request. Permission alone SHALL NOT start collection.

### VSP-R5 — Bound transport and stop safely

WHEN a canary is approved,THE SYSTEM SHALL use descriptive contact-bearing User-Agent,serial requests,
cache,revisions/checksums and`maxlag`;it SHALL stop on missing/expired permission,terms/robots drift,
401/403/429,rate-limit response,CAPTCHA/challenge,unexpected redirects/schema,or checksum/revision mismatch.

### VSP-R6 — Exclude media and bypasses

WHILE this plan is active,THE SYSTEM SHALL collect text release-table evidence only and SHALL NOT download
images/video,use OCR,authenticate around restrictions,rotate identities/proxies,impersonate a browser,
solve CAPTCHAs,or use search-engine caches as a replacement dataset.

### VSP-R7 — Stage real rows without quota padding

WHEN expansion is authorized,THE SYSTEM SHALL proceed from the existing100 offline rows toward500,1,500
and approximately3,000 unique real source-release rows in separately approved batches;duplicate snapshots,
synthetic rows and repeated editions SHALL NOT satisfy a milestone.

### VSP-R8 — Report distinct counters

WHEN a batch is reported,THE SYSTEM SHALL separately count requests,pages/revisions,raw observations,
deduplicated source releases,castings,held/conflicted/unresolved releases,owner-reviewed variants,canonical
products,errors and cache hits;about3,000 source rows SHALL NOT be reported as3,000 verified products.

### VSP-R9 — Preserve field evidence and review authority

WHEN text is staged,THE SYSTEM SHALL retain source page/revision/row,license/attribution,raw and normalized
field values and evidence state;unknown color/wheel/tampo SHALL remain null,and no row SHALL be promoted
without a later exact owner review event and separate canonical contract.

### VSP-R10 — Keep planning artifacts local and deterministic

WHEN this checkpoint is delivered,THE SYSTEM SHALL publish requirements/design/tasks,a JSON plan,read-only
validator,tests,permission guide,QA/evidence/rubric/decision/log only inside`Product Variant Resolver`.
Validation SHALL perform no network/database/write operation and SHALL reject enabling collection,
nonzero current request budgets,approved endpoints or media while permission evidence is absent.

## Out of scope

Actual remote collection;contacting Fandom;legal advice;Hot Wheels community-specific license clearance;
API/robots probing;images/OCR;credentials;PostgreSQL staging;parser implementation;canonical promotion;
identity-v2;variant evaluation;claiming current Fandom permission or production readiness.
