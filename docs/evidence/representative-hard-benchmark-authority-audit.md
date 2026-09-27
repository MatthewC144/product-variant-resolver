# Representative Hard Benchmark v1 — Canonical Authority Audit

Date: 2026-09-27
Mode: Lite / Lean Industrial
Milestone: RHB-T4

## 結論：Engineering PASS / Data Gate BLOCKED

RHB-T4 的工程交付通過 QA：authority audit 可以離線、確定性地重建，會檢查完整父產物、來源決策、資料數量與
checksum，且遇到過期、缺漏、偽造或不一致內容會 fail closed。資料 Gate 則正確停在
`blocked_insufficient_exact_authority`，因為目前 repository 中沒有任何可用於非合成 matched benchmark 的獨立
exact-variant truth。

這兩個結果不能混為一談。Engineering PASS 表示「檢查與阻擋機制正確」；Data Gate BLOCKED 表示「上游真實資料仍
不足」，不是 resolver accuracy 結論，也不授權開始 RHB-T5。

## Audit 方法與 frozen parent 契約

Builder `scripts/build_representative_hard_benchmark_canonical_authority.py` 不連網、不呼叫 resolver，也不查看 benchmark
labels。它先重新驗證 RHB-T1 source inventory／manifest 與 RHB-T3 owner source decisions，再逐一稽核兩個 catalog
surface 與全部 11 個來源的 exact-authority eligibility。稽核順序如下：

1. 確認 `fixture-v1` 的 120 個 products 都只有 `synthetic_fixture` provenance 與
   `synthetic://fixture-v1/` reference，因此全部排除於真實 release truth。
2. 確認 Human-backed catalog 只有 casting-level 與 provisional variant 資訊：97 個 castings、100 個 provisional
   variants、0 個 exact variants，且每筆仍需 canonical review。
3. 對照 RHB-T3 決策，確認 11/11 個來源的 `exact_variant_authority` 都是 rejected，且沒有來源取得 typed
   `canonical_authority` downstream permission。
4. 只把同時通過來源授權、獨立證據、catalog／UUID／record checksum、所有已填 variant fields、reviewer 與 aware
   timestamp 契約的紀錄放入 authority artifact。現況沒有合格紀錄，所以結果明確為 `records=[]`，而不是以最近候選、
   family match 或 staged row 猜測 UUID。
5. 以預先設定的最低門檻重新計算 Gate：至少 20 個 pilot-usable exact variants，並涵蓋至少 4 個同 casting、不同
   release 的 eligible families；任一不足就必須停止。

「Frozen parent」表示 audit manifest 不只記錄檔名，而是保存所有必要上游 artifact 的排序後路徑與 SHA-256；authority
artifact 本身也由 SHA-256、version 與 record order 綁定。任何 parent、catalog、source decision、builder 或 authority
內容改變，都必須產生新的 checksum 並重新稽核，不能把舊結論套到新資料。這個設計讓 clean checkout 可重現同一結果，
也避免 partial write、漏掉來源或靜默資料漂移。

## 稽核結果

| 稽核面 | Frozen observation | 判定 |
|---|---:|---|
| `fixture-v1` catalog | 120 products；120/120 全為 synthetic regression-only | 不可作真實 exact authority |
| Human-backed catalog | 97 castings；100 provisional variants；0 exact | 只可作 provisional／family context |
| Owner-confirmed sources | 11 個來源；11/11 exact-authority decisions rejected | 無來源可建立 canonical UUID |
| Canonical authority | `records=[]` | 不推測或補造 UUID |
| Eligible exact variants | 0 | 未達最低 20；shortfall 20 |
| Pilot-usable exact variants | 0 | matched pilot 不可開始 |
| Eligible same-casting multi-release families | 0 | 未達最低 4；shortfall 4 |
| Network / resolver / labels consulted | 0 / false / false | audit 保持離線且 output-blind |

機器產物是
[`canonical-authority.json`](../../data/evaluation/representative-hard-benchmark-v1/canonical-authority.json) 與
[`canonical-authority-manifest.json`](../../data/evaluation/representative-hard-benchmark-v1/canonical-authority-manifest.json)。
前者用空陣列表達「已完整稽核但沒有合格紀錄」；後者保存來源逐項排除理由、frozen parents、門檻、shortfall、禁止的
下游步驟與唯一允許的下一步。家族名稱、Human labels、Wiki derivative、owner workbook staging、synthetic UUID、candidate
或 resolver output 都不能替代 exact release authority。

## Fail-closed 驗證證據

QA 不只驗證 happy path，也確認下列 14 類 mutation 都被拒絕：

1. stale authority SHA；
2. stale parent SHA；
3. partial status；
4. unknown field；
5. source count mismatch；
6. source order mismatch；
7. 把 rejected exact-authority decision 升格；
8. 為 fixture 偽造非空 authority record；
9. stale catalog-record checksum；
10. 缺少 catalog 已填寫的 variant-field evidence coverage；
11. 錯誤 reviewer role；
12. timezone-naive review time；
13. 空白 independent evidence；
14. `resolver_output_consulted=true`。

QA 記錄的 focused T1–T4 tests 為 `76 passed`，完整 repository 為 `1051 passed`（另有既有 Starlette deprecation
warning）。Ruff check、Ruff format、strict MyPy、compileall、JSON parsing、secret scan 與 `git diff --check` 均通過；
T1 inventory check 為 `unchanged`，T4 builder 連續兩次 check 也都是 `unchanged`。完整命令與 requirement mapping 保存在
[`review.md`](../../specs/representative-hard-benchmark-v1/review.md)。這些是已完成 QA 的紀錄，本文件沒有重新執行測試。

## Blocker 與允許的下一步

RHB-T5、network collection、query-pack authoring、label authoring、matched-pilot construction 與 canonical UUID promotion
都未獲授權。`records=[]` 也不能以 family-only、Wiki、workbook、synthetic catalog 或模型候選補齊。

要解除 blocker，必須先取得新的、合法可用且與現有來源獨立的 release-level exact-variant authority，明確通過新的
T3-style source/use/publication 決策，並提供可綁定 catalog version、canonical UUID、product-record checksum、所有已填
variant-defining fields、獨立 evidence references、reviewer 與 aware timestamp 的逐筆證據。之後仍須重跑本 audit，且至少
達到 20 個 pilot-usable exact variants 與 4 個 eligible same-casting/multi-release families。這裡只定義證據契約，不指定或
杜撰尚不存在的資料來源。
