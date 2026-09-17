# VAR-PLAN2 source gate — beginner summary

Date:2026-09-16 local /2026-09-17 UTC. Status:BLOCKED;planning artifact only.

## What was decided

The existing100 offline rows remain the baseline. The project may eventually target500,1,500 and
approximately3,000 unique real source-release rows,but no current network request is authorized.

Fandom's general licensing page says wiki text is generally CC BY-SA3.0 with attribution/share-alike.
Its current Terms of Use,last revised2025-12-19,also prohibit automated access/scraping without express
prior written permission. These are different questions:content reuse terms do not grant bot access.
The project has no written permission and could not directly verify the Hot Wheels Wiki-specific license,
endpoint or robots state,so Fandom collection is blocked.

## What exists now

- A machine-readable plan with collection disabled,zero endpoints and zero current request budgets.
- A read-only validator that rejects invented permission,enabling collection or removing stop conditions.
- A conditional three-request canary proposal that cannot run until written permission,source checks and
  a separate owner approval exist.
- Separate counters for requests,raw observations,deduplicated releases,reviewed variants and canonical
  products,so a3,000-row source goal cannot be reported as3,000 verified products.
- A permission-request guide. No request has been sent.

## What happens next

The owner may send the proposed permission request to Fandom. If Fandom grants sufficiently specific written
permission,the response must be stored locally with sensitive contact details redacted and checked against
the proposed purpose,endpoints,fields,volume,retention and attribution. Then the project must recheck current
Hot Wheels Wiki license,terms and robots through an authorized method and ask the owner again before a maximum
three-request canary. A denial,narrower scope or no response means the automated Fandom lane stays blocked.

This document is technical planning,not legal advice.
