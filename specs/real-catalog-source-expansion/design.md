# VAR-PLAN2 — Source gate and staged-expansion design

Date:2026-09-16. Lite. Status:planning artifact complete;remote collection BLOCKED.

## Overview

The first collection candidate is Hot Wheels Wiki on Fandom because the existing100-row pilot came from
that catalog and the owner named it for expansion. Public research found two separate facts:general Fandom
wiki text is usually reusable under CC BY-SA3.0 with attribution/share-alike,but Fandom's Terms of Use,
last revised2025-12-19,prohibit automated access/scraping without express prior written permission. The
project has no such permission. Direct official terms/licensing opens also returnedHTTP402 through the
research browser,so this checkpoint does not probe the community/API/robots or infer permission.

```text
public policy metadata ─► source gate JSON ─► read-only validator ─► BLOCKED
                                                  │
written permission + local license/robots check ──┤ (future separate evidence)
                                                  ▼
owner-approved 3-request canary ─► frozen revisions/cache ─► reviewed staged batch
```

## Interfaces and data model

`reports/real-catalog-source-expansion-v1/plan.json`is the current authority. Its top-level authority
must remain planning-only,collection disabled,remote requests0,media/OCR false and canonical changes0.
Each research evidence item stores publisher,URL,check time,observed rule,scope and retrieval limitation.
The Fandom source record separates general text license from automated-access permission and keeps
permission evidence null/approved endpoints empty.

The conditional canary is a proposal,not a budget authorization:threeGET requests maximum,concurrency1,
five-second minimum spacing,descriptive contact-bearing User-Agent,JSON,GZip,cache and`maxlag=1`. Exact
endpoint,page titles,revisions,permission artifact SHA and robots/terms snapshots must be frozen later.
If written permission is narrower,the narrower rule wins. A human-supplied local export can be considered
only with its acquisition method,license,attribution and checksum;it does not retroactively authorize bots.

## Milestones and accounting

The existing100 rows are an offline baseline,not a fresh network batch. Targets500/1,500/about3,000 are
unique real source-release observations after source-level dedup,not canonical products. Each milestone
requires its own page/revision manifest,exact request budget,parser fixture and owner handoff. Advancing
requires the prior batch to publish raw/request/cache/error counters plus held/conflict/review counts.
No synthetic padding,repeated revision or duplicate release may increase the unique-real-row counter.

## Error handling and security

Missing/expired permission,unverified community license or absent endpoint manifest fails before network.
At runtime,terms/robots change,401/403/429,CAPTCHA/challenge,unexpected redirect/schema,permission-scope
violation,revision drift or checksum mismatch stops the batch and preserves partial raw evidence as failed;
there is no retry through another identity/proxy. Credentials and personal data are not needed. Images,
video and OCR remain prohibited because Fandom notes that non-text files do not inherit the text license.

General MediaWiki guidance—serial reads,informative User-Agent,caching,JSON,GZip and`maxlag`—becomes a
transport floor only after Fandom grants access. It is not source permission. PostgreSQL is downstream
storage and cannot turn prohibited or weak evidence into an approved source.

## Testing strategy

The validator rejects duplicate JSON keys,unexpected schema/status,collection enabled,nonzero executed
request counts,permission present without a later version,approved endpoints,current budgets,media/OCR,
missing policy evidence,non-serial canary,missing stop conditions,wrong milestones/counters and any canonical
change. Tests mutate each authority boundary and scan the validator for network/database/write clients.
Full repository tests ensure the plan does not affect Dual RAG,FastAPI,storage or prior evidence.

## Alternatives and trade-offs

Direct Fandom scraping would reach the row target sooner but conflicts with current terms and is rejected.
Treating CC BY-SA as access consent confuses copyright reuse with platform access. Manual entry of thousands
of rows avoids a bot but is slow,error-prone and still needs license/attribution. An alternative source with
an explicit bulk/API license may eventually replace Fandom,but none is approved in this checkpoint. The
honest current outcome is a blocked,actionable plan plus a permission request—not an invented dataset.
