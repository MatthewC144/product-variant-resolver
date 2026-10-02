# Canonical Authority Review — T5-G1 completion evidence

Date: 2026-10-01
Mode: Lite / Lean Industrial
Status: **T5-G1 COMPLETE — 20 REVIEWED／0 STAGED; T5-G2 NOT STARTED**

## 結論與目前狀態

Final Batch 1 已在 output-blind owner review contract 下完成 bounded append。Mazda Autozam 的
packet ordinals `1`、`10`、`16` 從 `staged` 推進為 `reviewed`，Batches 2–7 的 17 個既有
candidate／event objects 保持完全不變。T5-G1 的 20 筆第一道 evidence review 因此全部完成：

| State | Count／status |
|---|---:|
| T5-G1 reviewed | 20 |
| Still staged | 0 |
| Private batch authorizations | 7 |
| Private owner attestations | 20 |
| Public review events | 20 |
| Exact authority | 0 |
| Authority bundle／manifest | absent |
| RHB-T5 authorization | false |

`reviewed` 只表示第一道 evidence review 完成，不是 `approved_exact`，也不建立 manufacturer-certified
truth。本文件不重述、推導或硬編碼 trusted response 或 private identity。

## Final-batch append 與資料完整性

Batch 1 是刻意延後的最後一批，因此 recorder 不採任意順序，而是要求完整 Batches 2–7 predecessor
state。只有 17 個既有 events、attestations、authorizations 與 candidates 全部通過 hash／link／state
驗證後，才可追加三筆 Batch 1 objects。Authorization ledger 最終依 batch ordinal 排列為 `1`–`7`；
先前六份 authorizations 與 17 個逐筆 objects 不被重寫。

四個 private／public outputs 仍採整組 atomic promotion 與 rollback，避免 candidate state、events、
authorization 與 attestations 停在不同步的半完成狀態。真實 materialization 首次回報 `created`，
隨後兩次 real `--check` 均回報 `unchanged`，證明重播不會改變 bytes。

## Privacy 與驗證

授權原文只存在 Git-ignored private ledger；tracked public artifacts 僅包含 bounded state、bindings 與
不可逆 hashes。Private 目錄為 `0700`、private files 為 `0600`、public files 為 `0644`，兩個 private
ledgers 皆由 `.gitignore` 明確排除。

Pre-materialization QA：focused recorder suite `71 passed`、full repository `1339 passed`，Ruff、format、
strict MyPy、compileall 與 diff check 全部通過；唯一訊息是既有 Starlette／AnyIO dependency warning。

Post-materialization QA：20 條 candidate→event→attestation→authorization links 全部有效；先前 17 個
events 與 reviewed candidate objects 完全保留；兩次 replay bytes-stable；794 個 tracked／unignored
files 的真實授權 privacy scan 為 0 hits。`approved_exact`、authority bundle／manifest 與 RHB-T5
仍不存在或為 false。本輪 post-materialization 檢查沒有重跑完整測試套件。

Final artifact hashes：

| Artifact | SHA-256 |
|---|---|
| Private batch authorization ledger | `6ae5e419dc45e7f0df87f79c63c0da146907ebe95fec9e65b84c47ad475b9db8` |
| Private owner attestations ledger | `b776b3f9818fe7b20dabab247bddd7cb1e36766d8815da1ed30df10022b91868` |
| Public authority candidates | `1faa0d14a3c75052d44a0b974ae4447331cdc504a3d3605a994bd171c5500d96` |
| Public review events | `02cde956261f541669adc3be54a7b347dfe996fd4ccd458092ea9987ec3a6dae` |

## 邊界與下一步

T5-G1 已完成，但 CAR-T5 尚未完成。下一個合法 Gate 是 T5-G2：針對 20 筆 reviewed scope 取得新的、
獨立且明確的 exact-authority outcomes。任何 T5-G1 或 catalog-application response 都不得重用。
T5-G2 完成後才能執行 CAR-T5F freeze；CAR-T6 RHB-T4 re-audit 與 RHB-T5 仍需更後面的獨立 Gate。
