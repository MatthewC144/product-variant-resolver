# Canonical Authority Review — T5-G1 progress evidence

Date: 2026-10-01
Mode: Lite / Lean Industrial
Status: **BATCHES 2–3 VERIFIED; T5-G1 PARTIALLY COMPLETE**

## 結論與目前狀態

T5-G1 Batch 3 已在 output-blind owner review contract 下完成 bounded append。Subaru BRZ 的 packet
ordinals `3`、`8`、`14` 從 `staged` 推進為 `reviewed`；Batch 2 的 ordinals `2`、`11`、`18` 及其
既有 authorization、attestations、events 保持不變。累積狀態如下：

| State | Count／status |
|---|---:|
| T5-G1 reviewed | 6 |
| Still staged | 14 |
| Private batch authorizations | 2 |
| Private owner attestations | 6 |
| Public review events | 6 |
| Exact authority | 0 |
| Authority bundle／manifest | absent |
| RHB-T5 authorization | false |

`reviewed` 只表示 owner 已完成第一道 evidence review，不是 `approved_exact`。本文件不重述、推導或
硬編碼任何 trusted owner response 或 private identity。

## 從單批 recorder 擴充為 bounded append

Recorder 的允許範圍由只處理 Batch 2，擴充為依序處理 Batch 2 → Batch 3。Batch 3 只有在完整、有效的
Batch 2 decision state 已存在時才能追加；它不能跳過 predecessor、替換舊 objects，或把同一授權跨 Gate
重用。每個 batch 各有一份 private authorization；每筆 record 各有自己的 private attestation 和 public
`staged -> reviewed` event，並綁定 ordinal、candidate／catalog record、evidence 與 prior state。

為相容 Batch 2 已落地的 private ledger shape，讀取時加入嚴格、單向的 legacy migration。Migration 只把
舊 shape 正規化到目前 append contract，不能擴張 scope、產生新 review outcome，或變更既有語意。四個
decision outputs 仍採整組 atomic write；任何 promotion 失敗都回復原始 bytes，避免 public／private ledgers
停在不同步的半完成狀態。

第一次 Batch 3 記錄回報 `created`，之後兩次 real checks 都回報 `unchanged`。這證明已存在的完整狀態可
重播而不追加重複事件；同時不代表 T5-G2、exact authority 或 RHB-T5 已獲授權。

## Privacy 與驗證

隱私檢查同時涵蓋歷史與本輪新增 response，而非只掃描最新輸入。理由是 Batch 3 append 若只保護新增
response，仍可能在 migration、fixture 或 renderer 中重新洩漏 Batch 2 內容。Public artifacts、tracked
source、tests 與 docs 均不得包含 trusted responses 或 private identity；公開狀態只保留 bounded state、
bindings 與不可逆 hashes。

QA 在 changed-test strict MyPy 檢查中先發現 7 個型別錯誤，修正後該 scoped check 為 0 errors。這是本輪
變更範圍的修復證據，不宣稱整個 repository 的既有 type debt 已經消失。Recorder 的 created／兩次
unchanged replay、歷史 objects 保留、6／14 counts、2／6／6 authorization-attestation-event counts、atomic
rollback 與歷史＋新增 response public-leak scan 均已驗證；本次文件策展沒有重跑測試。

獨立 QA 最終判定 **PASS**：focused `22 passed`、pre-materialization full repository `1290 passed`；
post-materialization 再確認 Batch 2 的三個 public event objects 未改變、private directory／files 權限為
`0700`／`0600`、public files 為 `0644`，且 794 個 tracked／unignored files 沒有真實 response
辨識片段。本輪 final artifact hashes 為：

| Artifact | SHA-256 |
|---|---|
| Private batch authorization ledger | `15832acae0b87887d28fb75fb76bece1e534e5a5e2fef3eb1364668bac5645ac` |
| Private owner attestations ledger | `af8caa230cbda8c9d31703dcbdb84eee144ba2e352dcc981e664db04e73ae569` |
| Public authority candidates | `42a8a722c3f1ce808ccfe169b0d03219ef7c604596a945e5ece4021d6b55afdd` |
| Public review events | `216ac30491531bc95b8c42d4ba5eba186952392f217f011f4844502a5f72f9da` |

## 邊界與下一步

Exact authority 仍為 0，authority bundle／manifest 不存在，RHB-T5 仍為 false。下一個合法 mutation 仍需
owner 對另一個 frozen batch 提供新的、明確 T5-G1 outcome。只有必要 first-Gate events 全部合法記錄後，
才可另外提出 fresh T5-G2 exact-authority request。
