# Canonical Authority Review — T5-G1 progress evidence

Date: 2026-10-01  
Mode: Lite / Lean Industrial  
Status: **BATCH 2 VERIFIED; T5-G1 PARTIALLY COMPLETE**

## 結論與目前狀態

T5-G1 Batch 2 已在 output-blind owner review contract 下完成記錄。這次只把 Draftnator 的 packet
ordinals `2`、`11`、`18` 從 `staged` 推進到 `reviewed`；其餘 17 筆仍保持 `staged`。`reviewed`
只表示 owner 已完成第一道 evidence review，不是 `approved_exact`：

| State | Count／status |
|---|---:|
| T5-G1 reviewed | 3 |
| Still staged | 17 |
| Exact authority | 0 |
| `approved-authority.json` | absent |
| `authority-manifest.json` | absent |
| RHB artifacts／authorization | absent／false |

本文件不重述或重建 trusted owner response，也不公開 private identity。下一個合法 mutation 仍需 owner
對另一個 frozen batch 提供新的、明確 T5-G1 outcome。

## 一個 batch response，三個逐筆綁定事件

Private state 包含一份 batch authorization 與三份 owner attestations；public state 包含三個
`staged -> reviewed` events。三個 events 都引用同一個 authorization hash，分別綁定自己的 packet
ordinal、candidate／catalog record、evidence 與 prior state。這代表**一份 owner batch response 覆蓋三筆**，
而不是把一段回覆偽造成三次獨立使用者發言。

Recorder 不信任 private ledger 自己宣稱的 response。呼叫端必須另行提供 strict
`ExpectedBatchOwnerAuthorization`；validator 逐欄比對 Gate=`T5-G1`、scope=`staged_to_reviewed`、
declared outcome、covered entries、exact external response hash 與 prior-Gate constraints。若 response、
scope、entry set 或 hash 不一致就 fail closed。T5-G2 仍需要另一份 fresh authorization，不能由本次
response、attestations 或 events 推導。

## Private／public artifacts 與 replay

Private authorization／attestation ledgers 保持 exact Git-ignore 且 mode `0600`；public
`authority-candidates.json` 與 `review-events.json` 為 `0644`，只包含可公開的 state、bindings 與不可逆
hashes，不包含 owner verbatim 或 private identity。第一次記錄回報 `created`，之後兩次 real checks 均
回報 `unchanged`，四個 artifacts 的 before／after hashes 全部穩定：

| Artifact | SHA-256 |
|---|---|
| Private batch authorization ledger | `04fb14d4a3f8e43f31e59900ed7e573f7b46ffd1216c270a67c8457dc0dc272b` |
| Private owner attestations ledger | `49bdf299456179d6087c6276d372d7ed63b1037cef71b02a1034bfa318a55446` |
| Public authority candidates | `1a844f73c875797fce907048a2e8ad9532090f01b356882d990ff07a20d204da` |
| Public review events | `a35c63d4a26a4a4f01be917a15b46ab56477f771e45f3181b6fc88985bbf44ae` |

## Privacy failure、修復與 post-materialization QA

獨立 QA 發現 test fixture 曾把 trusted owner response 硬編碼進 tracked test source。即使 production
outputs 保持 private，測試檔中的 verbatim fragment 仍會造成 repository privacy leak，因此這不是可忽略的
測試資料問題。修復移除所有真實 response，改用明確標示 `TEST-ONLY` 的 synthetic Unicode／backslash
text；production recorder 繼續保持 response-agnostic，不因測試方便而加入任何特定人類字句。

修復後的 repo-wide privacy scan 對 792 個 tracked／unignored files 確認 trusted-response fragments 為零。
QA 也直接驗證 materialized state，而不只測 temporary happy path：3 reviewed／17 staged、1／3／3
authorization-attestation-event counts、private `0600`、public `0644`、parent bindings 與兩次 unchanged
checks 均成立。

## Final QA 與下一步

最終獨立 QA 判定 **PASS**：focused `16 passed`、full repository `1284 passed`；Ruff、Ruff format、strict
MyPy、compileall、fixture isolation、permissions、privacy 與 artifact hashes 全部通過。Exact authority
仍為 0，authority bundle／manifest 與所有 RHB state 仍不存在。沒有 blocker 或 important finding。

下一步不是 T5-G2，而是對另一個尚未 review 的 frozen batch 取得**新的 T5-G1 owner outcome**。只有所有
必要 first-Gate events 都被合法記錄後，才可另外提出 fresh T5-G2 exact-authority request。
