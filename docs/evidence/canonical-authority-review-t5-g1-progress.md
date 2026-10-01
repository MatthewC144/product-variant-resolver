# Canonical Authority Review — T5-G1 progress evidence

Date: 2026-10-01
Mode: Lite / Lean Industrial
Status: **BATCHES 2–5 RECORDED; T5-G1 PARTIALLY COMPLETE**

## 結論與目前狀態

T5-G1 Batch 5 已在 output-blind owner review contract 下完成 bounded append。'21 Ford Bronco
的 packet ordinals `5`、`7`、`17` 從 `staged` 推進為 `reviewed`；Batches 2–4 既有 objects
保持不變。累積狀態如下：

| State | Count／status |
|---|---:|
| T5-G1 reviewed | 12 |
| Still staged | 8 |
| Private batch authorizations | 4 |
| Private owner attestations | 12 |
| Public review events | 12 |
| Exact authority | 0 |
| Authority bundle／manifest | absent |
| RHB-T5 authorization | false |

`reviewed` 只表示第一道 evidence review 已完成，不是 `approved_exact`。本文件不重述、推導或
硬編碼任何 trusted response 或 private identity。

## Bounded prefix 與 atomic append

Recorder 的允許範圍依序擴充為 Batch 2 → Batch 3 → Batch 4 → Batch 5。Batch 5 只有在
Batches 2–4 的完整、有效 decision prefix 已存在時才能追加；不能跳過 predecessor、替換舊
objects，或把同一授權跨 Gate 重用。每個 batch 各有一份 private authorization；每筆 record 各有
自己的 private attestation 和 public `staged -> reviewed` event，並綁定 ordinal、candidate／catalog
record、evidence 與 prior state。

使用 bounded prefix，而不是接受任意 batch 的通用 append，是為了讓每次 mutation 的合法前置狀態可被
精確驗證，也讓歷史 objects 保持不可改寫。四個 decision outputs 仍採整組 atomic write；任何 promotion
失敗都回復原始 bytes，避免 public／private ledgers 停在不同步的半完成狀態。第一次 Batch 5 記錄回報
`created`，之後兩次 real checks 都回報 `unchanged`；Batches 2–4 objects 亦保持不變。

## Privacy 與驗證

Public artifacts、tracked source、tests 與 docs 均不得包含 trusted responses 或 private identity；公開狀態
只保留 bounded state、bindings 與不可逆 hashes。Private authorization／attestation ledgers 與 public
candidate／event artifacts 分開保存，讓可審計的狀態進度不需要公開授權原文。

獨立 pre-materialization QA 判定 **PASS**：focused `62 passed`、full repository `1307 passed`。後續
materialization 證據包含 Batch 5 的 `created`、兩次 `unchanged` replay、Batches 2–4 object
preservation、累積 12／8 state、4／12／12 authorization-attestation-event counts，以及 exact／bundle／
manifest／RHB 邊界。本次文件策展沒有重跑測試。

Batch 4 的 post-materialization QA 曾因 specs 與 source manifest 並行更新，遇到瞬間 tasks hash／
manifest binding 不一致；穩定重跑後通過。這項 shared-workspace update race 保留為已知風險。
Batch 5 本輪未重現該競態；post-materialization QA 最終判定 **PASS**。正式狀態的 4 份
authorizations、12 份 attestations、12 個 events 與 12 組 links 全部有效；Batches 2–4 的
9 個既有 objects 逐筆保留，permissions、Git-ignore、replay 與 794 個 tracked／unignored files
的四輪 response privacy scan 全部通過。Blocker／Important／Later 皆為 0。

本輪 final artifact hashes 為：

| Artifact | SHA-256 |
|---|---|
| Private batch authorization ledger | `ca0a01fd5e46431eb69e15119fa41b213401ec6dbee978c0607db4869c3efe67` |
| Private owner attestations ledger | `baa850e198cf18c1a68e65466be4e4b78129e0cf07a468c8e46966a1f425e18c` |
| Public authority candidates | `08a31fba48a773a58a3d46d434c8631fbae127531b9421f6b2824211d81565ec` |
| Public review events | `7b8dfaaf1c86e0ec59cb68594dee77e962a35fe88d077ff7bdea4f87198eb66e` |

## 邊界與下一步

Exact authority 仍為 0，authority bundle／manifest 不存在，RHB-T5 仍為 false。目前還有 8 筆 staged；
下一個合法 mutation 仍需
對另一個 frozen batch 提供新的、明確 T5-G1 outcome。只有必要 first-Gate events 全部合法記錄後，才可
另外提出 fresh T5-G2 exact-authority request。
