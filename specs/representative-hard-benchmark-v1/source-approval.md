# Representative Hard Benchmark v1 — Source owner approval

Date: 2026-09-26. Mode: Lite / Lean Industrial. Gate: **RHB-T3 PASSED FOR DECLARED SCOPES**.

Owner decision: `project_owner`, confirmed at `2026-09-27T01:44:16Z` (UTC).

## 這一關確認了什麼

RHB-T3 只決定「哪個來源可以做哪件事」，不替資料貼上正確車款答案，也不表示已經能製作 60-case benchmark。Owner 已同意本文件的保守方案：本機來源只在明確欄位與 local-only 邊界內使用；Git 只保存獲准的 schema、checksum、筆數、aggregate 與非敏感摘要；既有 Wiki derivative 僅限已 check-in revision 並保留 attribution；任何 live website collection 仍然禁止。

機器可讀決策位於
`data/evaluation/representative-hard-benchmark-v1/source-decisions.json`。共 11 個來源、6 種用途、66 個格子：23 個 `approved`、43 個 `rejected`、0 個 `held`。依 publication scope 計算，分別是 10 個 `local_only`、3 個 `aggregate_only`、10 個 `public_rows` 與 43 個 `prohibited`。因此 source Gate 只能在這些狹窄範圍內通過。

## 三個狀態的意思

| 狀態 | 初學者說明 |
|---|---|
| `approved` | 只能依該格的 allowed fields、publication scope 與 conditions 使用；不是整個來源的無限制授權。 |
| `rejected` | 此用途目前禁止。未來即使權利證據改變，也要建立新版 source entry/decision，不能默認翻轉。 |
| `held` | 尚待 owner 決定。本版沒有 held cell。 |

## Owner-confirmed 來源 × 用途 × 公開範圍

下表中的 `public(existing only)` 只表示舊有 checked-in artifact 可依現行 license/attribution 繼續存在。只有 Wiki 的既有 100-row revision 另有明確的 typed `query_pack`/`family_context` 許可；其他舊有公開檔案不會因此取得建立新公開 benchmark rows 的權利。

| Source | Query text | Evidence retention | Reviewer identity | Local-only benchmark use | Public Git artifacts | Exact authority |
|---|---|---|---|---|---|---|
| `fixture-v1-benchmark` | rejected | approved — public(existing only) | rejected | approved — regression only | approved — regression only | rejected |
| `fixture-v1-catalog` | rejected | approved — public(existing only) | rejected | approved — regression only | approved — regression only | rejected |
| `human-labeled-real-noisy-v1` | approved — local-only | approved — raw local-only | approved — role only | approved — local-only | approved — aggregate/digest only | rejected |
| `human-labeled-to-fixture-alignment-v1` | rejected | approved — local-only/inherits parent | rejected | approved — family context only | approved — aggregate/digest only | rejected |
| `owner-local-release-snapshot-2023-2026-v1` | rejected | approved — raw local-only | approved — role only | approved — family context only | approved — aggregate/digest only | rejected |
| `fandom-hot-wheels-2025-pilot-r790665-v1` | approved — existing 100 rows with attribution | approved — public(existing only) | approved — role only | approved — family context only | approved — existing derivative only | rejected |
| live eBay | rejected | rejected | rejected | rejected | rejected | rejected |
| live Mercari | rejected | rejected | rejected | rejected | rejected | rejected |
| live Facebook Marketplace | rejected | rejected | rejected | rejected | rejected | rejected |
| live Fandom | rejected | rejected | rejected | rejected | rejected | rejected |
| any other live network source | rejected | rejected | rejected | rejected | rejected | rejected |

## Owner-confirmed 使用規則

### 101 筆 human-labeled names

- Query text 可用於 local-only query pack；owner-reviewed label 只允許 `ambiguous` 或 `no_match`，不得產生 `matched`。
- Human label 與 family label 可用於 local-only benchmark review。
- Raw query evidence 只留本機，不建立新的 row-level public copy。
- Git 只能保存 schema、SHA-256、筆數、非敏感 aggregate/summary 與 reviewer role。
- 現有檔案曾在 repository 出現，不等於獲准建立新的公開 query/label artifact。
- 它不能建立 exact canonical UUID。

### 1,763 筆 owner workbook rows

允許的 row fields 只有：

- `product_name`
- `year`
- `series`
- `color`
- `collector_number`
- `series_position`

這些欄位只可在本機提供 `family_context`，不能直接進入 query pack 或 scored labels。Raw rows 保持 local-only/untracked；Git 只放 schema、hash、count、aggregate 與非敏感摘要。Seller、contact、account 及其他身份資料一律排除。Workbook staging rows 沒有 canonical links，因此不能建立 exact authority。

### 既有 100 筆 Wiki derivative

已 check-in、revision-bound 的 100 rows 可用於 public query/context，並可依既有 CC-BY-SA 邊界保存/publication，但必須保留 attribution。每個 public query 的 `source_record_ref` 必須是 checksum-bound 100-row revision 內的真實 ID；任意新 ID 會被拒絕。這個批准只涵蓋目前 revision，不批准重新抓取 Fandom、擴充年份、圖片/OCR 或把 Wiki row 當 scored label/canonical truth。

## 機器強制的 downstream permissions

自由文字 conditions 只是給人閱讀；真正決定下游能不能使用來源的是 typed permissions：

| Source class | Typed permission | Machine-enforced limit |
|---|---|---|
| Synthetic fixtures | `regression_only` | 只能做 regression/tooling，不得計入代表性 pilot。 |
| 101 human names | `query_pack`, `scored_labels` | 只限 local-only query，label 只准 `ambiguous`/`no_match`。 |
| Human-to-fixture alignment | `family_context` | 只能提供 family-level context。 |
| 1,763-row workbook | `family_context` | 不得成為 query pack 或 scored labels。 |
| Checked-in Wiki revision | `query_pack`, `family_context` | 可公開 query/context，但只能引用 checksum-bound 100-row ID 且保留 attribution。 |
| Live external sources | `none` | 所有使用與 collection 均禁止。 |

`validate_canonical_authority`、`validate_query_pack`、`validate_labels` 都強制要求 owner-confirmed decision artifact 與其 checksum-bound inventory；省略決策檔、只修改 inventory flag 或擴張 scope 都會 fail closed。`validate_labels` 還會用相同 overlay 重新驗證序列化後的 query pack 與 canonical authority，因此不能先建立低階 model、再修改內層欄位來繞過 author/reviewer/source/scope 規則。

### Reviewer identity

需要人工 review 的公開 artifact 一律只寫穩定角色 `project_owner`。不得加入真名、email、電話、帳號或其他 contact data。角色名稱可公開；任何額外身份資料都不在本次許可內。

### Evidence、query、labels 與 Git 的界線

- Raw evidence：`local_only`。
- Human-derived query text 與允許的 labels：`local_only`；workbook 不可直接產生 query/labels。
- Git：schema、non-reversible hash、count、aggregate、non-sensitive summary，以及 role-only reviewer identity。
- Wiki：只有既有 checksum-bound 100-row derivative 可支援 public query/context 並保留 attribution。
- Synthetic fixtures：只供 regression/tooling，不計入 non-synthetic pilot。
- `aggregate_only` 絕不能裝入 raw rows。

## Exact authority 仍未通過

RHB-T3 的通過不會把任何來源升格為 canonical truth。目前六個 inventory sources 的 `exact_variant_authority` 仍全數 `rejected`：fixtures 只適合 synthetic regression；human labels 與 alignment 最多是 family-level context；owner workbook 與 Wiki rows 是 staging/review evidence。

下一步 RHB-T4 必須獨立審查是否存在 source-independent exact-variant authority。若找不到足夠 authority，matched pilot 仍要停止，不能用 resolver output、family match、staging row 或 owner 同意來推導 UUID。

## 網路收集仍然禁止

`network_collection_authorized=false`。本次 owner decision 不批准 Selenium、crawler、API harvesting、登入、自動化瀏覽、proxy、CAPTCHA bypass、圖片下載或 OCR。eBay、Mercari、Facebook Marketplace、live Fandom 與其他 live network source 的所有用途均為 `rejected`。

未來若取得 source-specific permission 或 authorized export，必須建立新的 source inventory entry、collection manifest 與 owner decision；不得擴張解讀本次批准。

## Gate 結果與下一步

RHB-T3 在上述 declared scopes 內完成，沒有 held cell。允許的下一個獨立任務是 **RHB-T4 catalog-ground-truth eligibility audit**；本次沒有開始 T4，也沒有開始 query pack、label authoring 或 T5。
