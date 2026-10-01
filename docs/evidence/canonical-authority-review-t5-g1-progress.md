# Canonical Authority Review — T5-G1 progress evidence

Date: 2026-10-01
Mode: Lite / Lean Industrial
Status: **BATCHES 2–6 RECORDED; T5-G1 PARTIALLY COMPLETE**

## 結論與目前狀態

T5-G1 Batch 6 已在 output-blind owner review contract 下完成 bounded append。Morgan Super 3
的 packet ordinals `6`、`12`、`19` 從 `staged` 推進為 `reviewed`；Batches 2–5 既有 objects
保持不變。累積狀態如下：

| State | Count／status |
|---|---:|
| T5-G1 reviewed | 15 |
| Still staged | 5 |
| Private batch authorizations | 5 |
| Private owner attestations | 15 |
| Public review events | 15 |
| Exact authority | 0 |
| Authority bundle／manifest | absent |
| RHB-T5 authorization | false |

`reviewed` 只表示第一道 evidence review 已完成，不是 `approved_exact`。本文件不重述、推導或
硬編碼任何 trusted response 或 private identity。

## Bounded prefix 與 atomic append

Recorder 的允許範圍依序擴充為 Batch 2 → Batch 3 → Batch 4 → Batch 5 → Batch 6。Batch 6 只有在
Batches 2–5 的完整、有效 decision prefix 已存在時才能追加；不能跳過 predecessor、替換舊
objects，或把同一授權跨 Gate 重用。每個 batch 各有一份 private authorization；每筆 record 各有
自己的 private attestation 和 public `staged -> reviewed` event，並綁定 ordinal、candidate／catalog
record、evidence 與 prior state。

使用 bounded prefix，而不是接受任意 batch 的通用 append，是為了讓每次 mutation 的合法前置狀態可被
精確驗證，也讓歷史 objects 保持不可改寫。四個 decision outputs 仍採整組 atomic write；任何 promotion
失敗都回復原始 bytes，避免 public／private ledgers 停在不同步的半完成狀態。第一次 Batch 6 記錄回報
`created`，之後兩次 real checks 都回報 `unchanged`；Batches 2–5 objects 亦保持不變。

## Privacy 與驗證

Public artifacts、tracked source、tests 與 docs 均不得包含 trusted responses 或 private identity；公開狀態
只保留 bounded state、bindings 與不可逆 hashes。Private authorization／attestation ledgers 與 public
candidate／event artifacts 分開保存，讓可審計的狀態進度不需要公開授權原文。

獨立 pre-materialization QA 判定 **PASS**：focused `72 passed`、full repository `1317 passed`；唯一訊息為
既有 dependency warning。後續 materialization 證據包含 Batch 6 的 `created`、兩次 `unchanged`
replay、Batches 2–5 object preservation、累積 15／5 state、5／15／15 authorization-attestation-event
counts，以及 exact／bundle／manifest／RHB 邊界。本次文件策展沒有重跑測試。

Batch 4 的 post-materialization QA 曾因 specs 與 source manifest 並行更新，遇到瞬間 tasks hash／
manifest binding 不一致；穩定重跑後通過。這項 shared-workspace update race 保留為已知風險。
正式狀態保留 5 份 authorizations、15 份 attestations 與 15 個 events；
Batches 2–5 的 12 個既有 objects 逐筆保留。現有證據只支持 first-Gate review 進度，不擴張成
exact authority、authority bundle／manifest 或 RHB-T5 結論。

Post-materialization QA 最終判定 **PASS**：focused `72 passed`，15 條 links、35 個 item hashes
與 4 個頂層 hashes 均有效；private `0700`／`0600` 權限、Git-ignore、forbidden-output absence 與
794 個 tracked／unignored files 中五輪 response 的 0 hits 均通過。Blocker／Important／Later
皆為 0。

本輪 final artifact hashes 為：

| Artifact | SHA-256 |
|---|---|
| Private batch authorization ledger | `2ce0714ab4084ced00855965a76ebbf9922288ad403b131a776b8244472967a0` |
| Private owner attestations ledger | `067476a2d8c2e3a96c1e61b0f29e41777fbb430a132bac50a38624a3153a6267` |
| Public authority candidates | `359457f3758498e9f7b98fc37f5dc11e477c4a9b288173eb077ded021c17eb77` |
| Public review events | `f98d5281fbd1e0d0ddd8210777c8adf6b07a1116f796e26a203adb55a116f213` |

## 邊界與下一步

Exact authority 仍為 0，authority bundle／manifest 不存在，RHB-T5 仍為 false。目前還有 5 筆 staged；
下一個合法 mutation 仍需
對另一個 frozen batch 提供新的、明確 T5-G1 outcome。只有必要 first-Gate events 全部合法記錄後，才可
另外提出 fresh T5-G2 exact-authority request。
