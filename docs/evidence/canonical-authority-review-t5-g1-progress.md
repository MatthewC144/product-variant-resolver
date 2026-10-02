# Canonical Authority Review — T5-G1 progress evidence

Date: 2026-10-01
Mode: Lite / Lean Industrial
Status: **BATCHES 2–7 RECORDED; T5-G1 PARTIALLY COMPLETE**

## 結論與目前狀態

T5-G1 Batch 7 已在 output-blind owner review contract 下完成 bounded append。Mazda MX-5 Miata
的 packet ordinals `9`、`15` 從 `staged` 推進為 `reviewed`；Batches 2–6 的 15 個既有 objects
保持不變。因本批只有兩筆，累積計數依實際 batch cardinality 增加兩筆，而不是假設每批固定三筆：

| State | Count／status |
|---|---:|
| T5-G1 reviewed | 17 |
| Still staged | 3 |
| Private batch authorizations | 6 |
| Private owner attestations | 17 |
| Public review events | 17 |
| Exact authority | 0 |
| Authority bundle／manifest | absent |
| RHB-T5 authorization | false |

`reviewed` 只表示第一道 evidence review 已完成，不是 `approved_exact`。本文件不重述、推導或
硬編碼任何 trusted response 或 private identity。

## Batch 1 pre-materialization readiness

Final Batch 1 recorder 已完成但尚未 materialize。它綁定 Mazda Autozam 的 ordinals `1`、`10`、`16`
與三個 frozen toy identifiers，並只在 Batches 2–7 的完整 17-event predecessor state 通過驗證後接受
append。成功的合成測試結果為 20 reviewed／0 staged、7 authorizations、20 attestations、20 events，
同時維持 exact authority 0、authority bundle／manifest absent 與 RHB-T5 false。

專項 `71 passed`、完整 repository `1339 passed`，Ruff、format、strict MyPy、compileall 與 diff check
亦通過；唯一訊息仍是既有 Starlette／AnyIO dependency warning。測試只使用 `TEST-ONLY` 合成授權，
沒有把一般 continuation 指示升格成真實 owner decision，因此目前公開與私密真實狀態仍維持
17 reviewed／3 staged。

## Bounded prefix、動態筆數與 atomic append

Recorder 的允許範圍依序擴充為 Batch 2 → Batch 3 → Batch 4 → Batch 5 → Batch 6 → Batch 7。
Batch 7 只有在 Batches 2–6 的完整、有效 decision prefix 已存在時才能追加；不能跳過 predecessor、
替換舊 objects，或把同一授權跨 Gate 重用。每個 batch 各有一份 private authorization；本批依實際兩筆
record 建立兩份 private attestations 與兩個 public `staged -> reviewed` events，並逐筆綁定 ordinal、
candidate／catalog record、evidence 與 prior state。

採用由 frozen batch 決定筆數的 append，而不是硬編碼「每批三筆」，使兩筆批次的授權、attestation、
event 與 state 計數保持一致。bounded prefix 則讓每次 mutation 的合法前置狀態可被精確驗證，也保護
歷史 objects 不被改寫。四個 decision outputs 仍採整組 atomic write；任何 promotion 失敗都回復原始
bytes，避免 public／private ledgers 停在不同步的半完成狀態。第一次 Batch 7 記錄回報 `created`，之後
兩次 real checks 都回報 `unchanged`；Batches 2–6 的 15 個既有 objects 亦保持不變。

## Privacy 與驗證

Public artifacts、tracked source、tests 與 docs 均不得包含 trusted responses 或 private identity；公開狀態
只保留 bounded state、bindings 與不可逆 hashes。Private authorization／attestation ledgers 與 public
candidate／event artifacts 分開保存，讓可審計的狀態進度不需要公開授權原文。

獨立 pre-materialization QA 判定 **PASS**：focused `60 passed`、full repository `1328 passed`；唯一訊息為
既有 dependency warning。後續 materialization 證據包含 Batch 7 的 `created`、兩次 `unchanged`
replay、Batches 2–6 object preservation、累積 17／3 state、6／17／17 authorization-attestation-event
counts，以及 exact／bundle／manifest／RHB 邊界。本次文件策展沒有重跑測試。

獨立 post-materialization QA 亦判定 **PASS**：17 條 candidate→event→attestation→authorization links
皆有效，既有 15 個 events、candidate objects 與 attestation hashes 全數保持不變。Private 目錄／檔案與
public artifacts 權限、Git-ignore 邊界、bytes-stable replay，以及涵蓋六份真實授權輸入的 794-file
privacy scan 均通過；Blocker 與 Important 為 0。

Batch 4 的 post-materialization QA 曾因 specs 與 source manifest 並行更新，遇到瞬間 tasks hash／
manifest binding 不一致；穩定重跑後通過。這項 shared-workspace update race 保留為已知風險。
現有證據只支持 first-Gate review 進度，不擴張成 exact authority、authority bundle／manifest 或 RHB-T5
結論。

本輪 final artifact hashes 為：

| Artifact | SHA-256 |
|---|---|
| Private batch authorization ledger | `f3aeae64ba10af3f7d6c8a03192ebb8bc67f2113c6f154c763cf374c29acede0` |
| Private owner attestations ledger | `cc7855f641ce1e8f1a06e74c116c5cd931e9c023448838da7900a5715a5dc83f` |
| Public authority candidates | `768a3025fac5ebd5e66a44112f16240b636be9eb61f4d4393bc99edb9921836d` |
| Public review events | `b910d6bd8e9727a68bbf6f1c961788a29e78b9ca3047baa68793d7538e1a8df5` |

## 邊界與下一步

Exact authority 仍為 0，authority bundle／manifest 不存在，RHB-T5 仍為 false。目前還有 3 筆 staged，
全部屬於 Batch 1 Mazda Autozam 的 ordinals `1`、`10`、`16`；因此 **T5-G1 尚未完成**。下一個合法
mutation 仍需對 Batch 1 提供新的、明確 T5-G1 outcome。只有必要 first-Gate events 全部合法記錄後，
才可另外提出 fresh T5-G2 exact-authority request。
