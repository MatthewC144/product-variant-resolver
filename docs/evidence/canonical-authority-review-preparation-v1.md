# Canonical Authority Review Preparation v1 — CAR-T5P evidence

Date: 2026-09-30  
Mode: Lite / Lean Industrial  
Status: **PREPARATION PASS; AWAITING EXPLICIT OWNER GATE T5-G1**

## 結論與授權邊界

CAR-T5P 已把 catalog-v2 中由 CAR-T4A 套用的 20 筆 records 準備成 output-blind authority-review
packet。使用者目前的 generic continuation 只授權**準備下一份審查材料**；它不是逐筆 review outcome，
也不是 exact-authority approval。Preparation 因此正確停在 `awaiting_owner_review_gate`：

| Preparation state | Count／value |
|---|---:|
| Staged `existing_uuid` entries | 20 |
| Family batches | 7：`[3,3,3,3,3,3,2]` |
| Agreeing evidence rows | 120（每筆 6 rows） |
| Null color／edition | 20／20 |
| Review events | 0 |
| Owner attestations | 0 |
| `approved_exact` | 0 |
| Authority-bundle records | 0 |
| Network requests | 0 |
| Resolver／model output consulted | false |
| RHB-T5 authorized | false |

這個 PASS 只表示 20 筆既有 catalog identities 已被確定性地整理成可供人類檢查的材料；它不表示
任何一筆已被 owner review、批准為 exact、由 manufacturer 認證，或可直接進入 RHB。

## Historical-to-current binding 與兩道 Gate

Frozen CAR-T4 candidates 保持原樣，不為了 catalog 已落地而回寫 UUID 或 application state。每筆 review
entry 另建立 immutable resolution binding，將 historical candidate／proposal hashes 綁到 catalog-v2 的
既有 UUID、canonical ID、release key 與 catalog-record hash。這個 bridge 同時保留歷史 provenance 和目前
catalog identity，避免把舊 phase-local artifact 靜默改造成新 truth。

Authority review 採兩道不同契約：

1. **T5-G1** 只允許 `staged -> reviewed`，或明確記錄 held／conflicted／insufficient outcome；
2. **T5-G2** 必須在 G1 後取得新的 exact-authority scope，才允許 `reviewed -> approved_exact`。

未來 batch event 必須對照 ledger 外部提供的 strict `ExpectedBatchOwnerAuthorization`，綁定 Gate、scope、
declaration、outcome、exact external response hash 與 covered entries。G2 還必須引用獨立提交的 G1 response
hash；同一 response hash 明確禁止跨 Gate 重用。這使「準備」「已 review」和「exact approval」不能被一段
模糊 continuation 或一份自我雜湊的 mutable artifact 合併。

## Private／public artifacts 與 deterministic replay

Owner-facing JSON packet 和 Markdown review file 位於 exact Git-ignored workspace；directory mode 為 `0700`，
private files 為 `0600`。它們包含審查所需的 row-level material，但本文件不公開任何 product row、問題或
owner verbatim。Tracked public manifest 只包含安全 counts、parent hashes、ordered entry digests、attribution、
license 與 next Gate。

| Artifact | SHA-256 |
|---|---|
| Private authority-review packet | `1086fa0ea7ddd4fda2b7a4b021797e5630a7b55d9f840c3508c4744d9703fe2b` |
| Private owner-review Markdown | `f1bfa2d7a296de06d132e019513b03745d7cf3062007f23e40bc9655c1260bf2` |
| Public safe manifest | `6b849f016a5c965397aaba7839e5c6c3d81acb44ed796e171355990c5b211053` |

第一次 materialization 回報 `created`；之後兩次 real `--check` 均回報 `unchanged`，且 before／after hashes
一致。Catalog、CAR-T4 packet／proposals／decision ledger、CAR-T4A application 與 authority outputs 都沒有被
這個 preparation step 改寫。

## QA 發現與修復

獨立 QA 先證明有限的 **generic blacklist** 不是 authorization contract：只列出若干「繼續」或非核准
字句，仍可能讓未列入 blacklist 的模糊文字通過；若 Gate fields 與 hashes 都可重算，同一 response 也可能
被重新包裝到另一道 Gate。修復改採 positive、external `ExpectedBatchOwnerAuthorization`，精確比對 Gate／
scope／declaration／outcome／response，並要求 G2 攜帶 G1 response hash 且禁止 current hash 與 prior hash
相同。Cross-Gate rehash 因此 fail closed，而不是靠持續擴充關鍵字名單。

Materialization 後的 fixture 測試又暴露 state coupling：temporary repository 複製到真實 T5P outputs 後，
舊 setup 會移除過多上游 inputs，使測試不再代表正式 workspace。修復後 temp fixture **只移除三個 T5P
outputs**（兩個 private preparation files 與一個 public manifest），完整保留 catalog-v2、CAR-T4 與
CAR-T4A parents，再從真實 parent state 驗證 `created` 與 `unchanged`。

## Final QA 與下一步

最終獨立 QA 判定 **PASS**：CAR-T5P focused `23 passed`、authority suite `199 passed`、full repository
`1268 passed`。Ruff、Ruff format、strict MyPy 與 compileall 全部通過；permissions、privacy、canonical
bytes、ignore behavior、parent immutability、兩次 unchanged replay 與 T5-G1 next Gate 也通過。唯一訊息是
既有、無關的 Starlette deprecation warning。

下一步是 **Owner Gate T5-G1**。Owner 必須對 frozen packet 明確提供 20 筆 outcomes，才能建立 append-only
`staged -> reviewed` events；沒有 outcome 就維持 staged。T5-G2 exact approval、authority bundle、CAR-T6／
RHB re-audit 與 RHB-T5 都不由本輪自動開始。
