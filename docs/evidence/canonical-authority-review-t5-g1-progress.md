# Canonical Authority Review — T5-G1 progress evidence

Date: 2026-10-01
Mode: Lite / Lean Industrial
Status: **BATCHES 2–4 VERIFIED; T5-G1 PARTIALLY COMPLETE**

## 結論與目前狀態

T5-G1 Batch 4 已在 output-blind owner review contract 下完成 bounded append。Nissan Skyline
2000GT-R LBWK 的 packet ordinals `4`、`13`、`20` 從 `staged` 推進為 `reviewed`；Batches 2–3
既有 objects 保持不變。累積狀態如下：

| State | Count／status |
|---|---:|
| T5-G1 reviewed | 9 |
| Still staged | 11 |
| Private batch authorizations | 3 |
| Private owner attestations | 9 |
| Public review events | 9 |
| Exact authority | 0 |
| Authority bundle／manifest | absent |
| RHB-T5 authorization | false |

`reviewed` 只表示第一道 evidence review 已完成，不是 `approved_exact`。本文件不重述、推導或
硬編碼任何 trusted response 或 private identity。

## Bounded prefix 與 atomic append

Recorder 的允許範圍依序擴充為 Batch 2 → Batch 3 → Batch 4。Batch 4 只有在 Batches 2–3 的完整、
有效 decision prefix 已存在時才能追加；不能跳過 predecessor、替換舊 objects，或把同一授權跨 Gate
重用。每個 batch 各有一份 private authorization；每筆 record 各有自己的 private attestation 和 public
`staged -> reviewed` event，並綁定 ordinal、candidate／catalog record、evidence 與 prior state。

使用 bounded prefix，而不是接受任意 batch 的通用 append，是為了讓每次 mutation 的合法前置狀態可被
精確驗證，也讓歷史 objects 保持不可改寫。四個 decision outputs 仍採整組 atomic write；任何 promotion
失敗都回復原始 bytes，避免 public／private ledgers 停在不同步的半完成狀態。第一次 Batch 4 記錄回報
`created`，之後兩次 real checks 都回報 `unchanged`；Batches 2–3 objects 亦保持不變。

## Privacy 與驗證

Public artifacts、tracked source、tests 與 docs 均不得包含 trusted responses 或 private identity；公開狀態
只保留 bounded state、bindings 與不可逆 hashes。Private authorization／attestation ledgers 與 public
candidate／event artifacts 分開保存，讓可審計的狀態進度不需要公開授權原文。

獨立 pre-materialization QA 判定 **PASS**：focused `53 passed`、full repository `1298 passed`。驗證亦涵蓋
Batch 4 的 `created`、兩次 `unchanged` replay、Batches 2–3 object preservation、累積 9／11 state、
3／9／9 authorization-attestation-event counts，以及 exact／bundle／manifest／RHB 邊界。本次文件策展
沒有重跑測試。

Post-materialization QA 最終為 **PASS WITH RISKS**。首次 focused run 在 specs 與 source manifest
並行更新期間為 7 pass／23 fail，全部 failure 皆是 fixture 複製到瞬間不一致的 tasks hash／
manifest binding。當前 binding 已一致，穩定重跑 `30 passed`；正式 3／9／9 links、權限、
Git-ignore、Batches 2–3 object preservation 與 794 個 tracked／unignored files 的三輪 response privacy
scan 均通過。該風險保留為 shared-workspace update race，不是 decision-state failure。

本輪 final artifact hashes 為：

| Artifact | SHA-256 |
|---|---|
| Private batch authorization ledger | `8364814f455385672f5b72fc20cdd95e02b044b3714629c07069ac1865ffd7a0` |
| Private owner attestations ledger | `c71cbfd8a653600252eeee51c3bcbf9d409a3f672ee7f9cf2febdf54f157415f` |
| Public authority candidates | `153dcc28d71fbb6ef64041efd298588cfc306a214b803400eb9169d9094744b0` |
| Public review events | `b71abc25be4d430a8311966cc50c8673b28ddf820b58f5c4803a96e7bd9a5342` |

## 邊界與下一步

Exact authority 仍為 0，authority bundle／manifest 不存在，RHB-T5 仍為 false。下一個合法 mutation 仍需
對另一個 frozen batch 提供新的、明確 T5-G1 outcome。只有必要 first-Gate events 全部合法記錄後，才可
另外提出 fresh T5-G2 exact-authority request。
