# VAR-REVIEW1 decision01 — Lamborghini owner event

Date:2026-09-15. Lite. Verdict:VALID owner-scoped event;batch01 progress1/4.

The preceding owner question asked whether to accept one explicit conservative Lamborghini result.
The owner's response`繼續下一步`is stored verbatim and interpreted only within that conversational
scope. Event`decision-01-lamborghini.json`,SHA`b05c52842626b2c9dfadc66901dd6544ce237a7f7a010ce25611facc3475e5ef`,
binds packet SHA`2e2adee366d968b0308d64dbde6b513e53055316b5ec5d58c6e0f4b7ae2700b2`.

The accepted scope confirms exactly three HYW93 fields:Lamborghini Huracán Sterrato,toy number HYW93,
and release year2025. It records15 unknown physical-field decisions across HYW93,HYY45 andJBB86:
color,wheel type,tampo,edition and packaging stay null. In particular,Red Edition remains a source
series and`2nd/3rd Color`remain ordinal notes;none becomes a physical color.

All three within-family row pairs are recorded`different_release`,grounded in separate toy-number rows
and base/2nd/3rd release markers. This distinguishes observations without inventing their physical
attributes or minting variant/canonical IDs. Event canonical changes=0. Subaru,Nissan,Audi and remote
source access are explicitly excluded.

The generic read-only validator checks packet/manifest SHA,owner context,required fields,grounded
confirmed values,unsupported-physical unknowns,all pair decisions,reasons/evidence and recalculated
summary. Ten focused tests cover the passing event and tampered packet SHA,canonical authorization,
ungrounded value,missing field and missing pair failures. Full suite589/589,Ruff F/I,strict MyPy and
compileall PASS;one existing Starlette/AnyIO warning remains.

This event does not complete batch01. Next authority required is the Subaru BRZ conservative review.
