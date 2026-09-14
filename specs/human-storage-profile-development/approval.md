# T49.3 owner confirmation ledger

Recorded: 2026-09-14. Lite mode; main agent, no subagents.

The owner said「確認完成，請繼續執行」immediately after the requirements explanation
and its requirements-confirmation question. This confirms requirements only; it does not
constitute separate design, task/budget, isolated SQL-run, or production-rollout approval.

Approved requirements source: commit `c197d0fbca1a6d16803ba9809933a9c194ca8046`,
`specs/human-storage-profile-development/requirements.md`, SHA-256
`54dfd2dd31fe51a628344832c3eae3463dac811a9cd489347204ecaac47df918`.
The approved file bytes remain unchanged. Its draft heading describes the original publication;
this ledger records the subsequent limited confirmation, without rewriting the approved version.

| Gate | Current state |
|---|---|
| Requirements | CONFIRMED for the exact source above |
| Design | CONFIRMED for the exact source below |
| Tasks and proposed cost protocol/budgets | CONFIRMED for the exact sources below |
| Overall G1 / approved execution freeze | PASS / NOT RUN yet |
| HSP1–4 implementation, new SQL run, profile measurements | NOT RUN |

The owner subsequently said「確認 繼續下一步」after the design explanation and its explicit
design-confirmation question. Approved design source: commit
`7a90be004a017493c61bf52a364a89ef4fb6477e`,
`specs/human-storage-profile-development/design.md`, SHA-256
`26037641051b08799c99d079d4d43b6ffc33b6a6308ba446669d7ff78736a5dd`.
Its bytes remain unchanged; the original draft heading is historical publication status.
This is design confirmation, not task/budget, isolated SQL-run, or rollout approval.

The owner then said「開始執行」after the task/budget explanation and the explicit question
asking approval to start the first input-freeze task. This confirms tasks and the proposed cost
ceilings/sample protocol, and authorizes HSP-1 only in this handoff. Approved sources at commit
`10ee18aca16c85d349ecc56d09abf2615c6a10e8`:

- `specs/human-storage-profile-development/tasks.md`, SHA-256
  `26aa54b33e8ef54c0de0242c17d0960dfc510f49d986e580d7518d9eb5a91fb9`.
- `specs/human-storage-profile-development/protocol-draft.json`, SHA-256
  `e23678bd02f7ad00871a2eca43f05ad1ae2d4139adfe39a1c92e155567d5b235`.

Three sequential confirmations now pass the scoped T49.3 G1. Historical draft flags/headings in
approved source copies are not rewritten; the new frozen approval/protocol records supersede
those publication states. They do not lift legacy exclusions or approve a new SQL run.
HSP-1 must bind a committed freeze producer before publication. Actual adapter/import manifests
and runtime image IDs remain pending before any real experimental output. No new profile output
exists. Full T49.3 and T49.4 remain unchecked; isolated SQL run approval remains separate.
