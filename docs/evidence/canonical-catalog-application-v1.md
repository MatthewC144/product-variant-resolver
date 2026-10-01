# Canonical Catalog Application v1 — CAR-T4A evidence

Date: 2026-09-30  
Mode: Lite / Lean Industrial  
Status: **CATALOG APPLICATION COMPLETE; FINAL POST-APPLY QA PASS**

## 結論與授權邊界

CAR-T4A 在獨立 owner catalog-application Gate 下，將 CAR-T4 已完成 review 的 20 筆 proposals
一次套用至 canonical catalog namespace。Owner 的 exact application response 只保存在
Git-ignored private event；本文件不重述該文字，也不公開 private candidate／review payload。

這次 application 只建立 catalog identities。它沒有批准 exact authority、manufacturer truth、
benchmark label 或 RHB-T5：

| 狀態 | Application 前 | Application 後 |
|---|---:|---:|
| Catalog version | `fixture-v1` | `catalog-v2` |
| Catalog products | 120 | 140 |
| Synthetic fixture rows | 120 | 120 |
| Community-snapshot catalog rows | 0 | 20 |
| Applied reviewed proposals | 0 | 20 |
| Exact-authority rows | 0 | 0 |
| RHB-T5 authorized | false | false |

20 筆新增 rows 的 `color` 與 `edition` 全部維持 `null`。Catalog inclusion 只表示該 release
identity 已由 owner 批准進入 catalog，不代表 Mattel／manufacturer 認證，也不代表可以用作
exact-variant benchmark truth。

## Materialization 與 identity 選型

原 120 筆 synthetic records 保持在前段、順序與 record-level content 不變；20 筆
`licensed_community_snapshot` derivatives 依 frozen packet order 追加。來源仍是固定 revision 的
community snapshot，且公開 catalog 保留 attribution、CC-BY-SA 與「not exact authority」界線。

部分 reviewed releases 共享 casting、year、series、collector number 與 series position，而來源又沒有
actual color／edition。實作因此採 proposal 已核准的 `release_key` 作 release discriminator，並把 toy
number 保存為 typed identifier；沒有用猜測的顏色、edition、alias 或 rarity 製造唯一性。Loader 同時
檢查 UUID、canonical ID、release key、typed identifier 與 legacy natural key collisions。

## 實作與 runtime compatibility

CAR-T4A 新增 strict catalog-v2 schema、deterministic materializer、catalog-only application CLI、private
authorization event、public safe manifest，以及具 journal／rollback 的 atomic publication。Current runtime、
in-memory ingestion 與 PostgreSQL ingestion 均支援 catalog-v2；Alembic migration `0004` 新增 nullable
`release_key`／`normalized_release_key` pair、unique normalized release-key constraint 與 pair consistency
constraint，讓既有 legacy fixture rows 可保持 null，新 rows 則能以 explicit release identity 儲存。

Fixture generator 不得靜默覆蓋已套用的 catalog-v2。歷史 RHB／CAR artifacts 繼續綁定可重建的原始
120-row parent；current runtime 才讀取 140-row child，因此沒有把舊 evidence 偷換成新 catalog 結論。

## Application 與 hash evidence

Authorized application 的第一次執行回報 `created`；read-only `--check` 回報 `valid`；相同輸入重播回報
`unchanged`。公開 artifact 只揭露安全 counts、lineage 與 hashes：

| Artifact | SHA-256 |
|---|---|
| `data/catalog.json` | `e763c8739a76ab4cc9b66169aecd4aea241ee810d8a27cdfb7d05bcacd98562e` |
| `data/manifest.json` | `38b7d3c0332bbbf757979576d796e08ace6659aa158de3e9466f5ed22dc2fac5` |
| public catalog-application manifest | `cf1c95ec8985f80f9ee48c2d8af8b297f5e7d771eff3bb07990034643e4b37b4` |

Public manifest 明確記錄 20 applied、140 total、120 synthetic、20 non-synthetic、20 null colors、
20 null editions、0 exact authority、0 network requests、resolver output not consulted 與 RHB-T5 false。

## QA 演進：失敗如何改進 transaction contract

Application 前的獨立 QA 沒有只看 happy path，而是依序發現並修正四個 provenance／crash-window
問題：

1. **Git anchor**：只讓 private/public hashes 自洽，仍可能接受被重寫的 decision history；修正後以
   Git first-parent anchor 驗證完整 20-event review prefix。
2. **Pre-journal orphan**：若 staging 在 durable journal 建立前失敗，可能留下未受管理的 temporary
   artifact；修正後失敗必須清乾淨，retry 才能從明確 parent state 開始。
3. **Strict journal allowlist**：journal 不能自行指定任意 targets。Recovery 現在只接受四個 canonical
   targets 與精確 owned references，並在 mutation 前拒絕 unrelated、duplicate、omitted、reordered 或
   swapped target／staged entries。
4. **Completed-child cleanup interruption**：四個 child outputs 已完整 promotion、transaction directory
   已刪除，但 journal unlink 中斷時，舊 recovery 可能無法判斷成功狀態。修正後可由完整 child hashes
   識別 completed publication、安全清理 journal，並保持後續 check／replay idempotent。

最終 **pre-apply** QA 通過：`47 passed` focused、`1243 passed` full suite，另有一個既有
Starlette／AnyIO deprecation warning；Ruff、format、strict MyPy、compileall、Source Gate、兩個 builders、
ledger、fixture validation、JSON、privacy／secret／symlink 與 diff checks 也通過。該 QA 是在真實 catalog
mutation 前完成的 safety Gate。

Application 後的第一輪驗證另外發現 **test-state coupling**：部分 fixture／history checks 把目前 140-row
catalog-v2 child 當成原始 120-row fixture parent，因而無法可靠證明 parent lineage。修正後，測試透過既有
generator 重建 immutable 120-row parent，逐筆比對 current catalog 前 120 rows，並以 CAR canonical JSON
encoding 重算 parent checksum；historical checks 與 current runtime 因此各自使用正確的資料狀態，而不是為了
讓測試通過去改寫歷史 evidence。

同一輪 scoped quality check 找到 9 個 Ruff 問題：兩個帶 shebang 的 scripts 缺 executable bit，另有七個
invalid-type paths 使用了不正確的例外類型。修復只補 executable metadata 並將這些 paths 改為
`TypeError`，沒有改變 catalog application scope 或資料內容；修復後受影響 tests 為 `21 passed`。

## Final post-apply QA 與下一個 Gate

最終獨立 read-only QA 判定 **PASS**。真實 application `--check` 為 `valid`；在 temporary copy 上重播為
`unchanged`，四個 outputs hashes 完全不變，transaction journal／directory 均不存在。Catalog-v2 精確為
140 rows：可重建 frozen hash 的 120-row immutable synthetic parent，加上 packet-order 的 20-row community
snapshot suffix；20 筆全部維持 `color=null`、`edition=null`。本文件前述三個 final hashes 均逐一吻合，
exact authority 仍為 `0`，RHB-T5 仍為 `false`。

Runtime loader、`ResolverService` 與 in-memory ingestion 全部通過，loader 可見 140 products 與 20 release
keys；PostgreSQL repository／migration／runtime standalone subset 為 `26 passed`。Live destructive PostgreSQL
runners 沒有執行，資料庫相容性結論限於 repository harness 與 migration contract tests。Historical CAR
builders、Source Gate、decision ledger、fixture validator、Fandom review、RHB source／audit、release-casting
checks 均為 `valid` 或 `unchanged`；human-alignment 在 temporary directory 重建後與 frozen outputs byte-for-byte
一致。

最終測試證據為 focused `201 passed`、full suite `1245 passed, 1 warning`，唯一 warning 仍是既有
Starlette／AnyIO deprecation。Ruff 與 Ruff format（17 files）、strict MyPy（8 個 implementation／script
files）、compileall、JSON／hash、privacy／secret、license、symlink 與 diff checks 全部通過。這完成
CAR-T4A 的 Lean G3 catalog-application sign-off，但只限本文件定義的 application claims。

下一個產品 Gate 是**獨立 CAR-T5 exact-authority review**。Catalog application 不會自動產生
`approved_exact` rows、authority bundle、fresh RHB-T4 pass 或 RHB-T5 authorization。
