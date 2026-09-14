# T49.1 — 本機人工知識匯入計畫

Snapshot: `human-knowledge-plan-v1-f7830e460650e99ab5107ec0f049c96d2dcf322daa5c140c5847a53f969e144f`

驗證結果：142 筆完整人工知識，100 筆 provisional variant + 42 筆 review family。
這是匯入前的計畫，不是 PostgreSQL 匯入、正式商品確認或檢索上線。
原有 ID／UUID／typed payload 可完整還原；原始內容、來源及限制一併保留。
4 個 merge-source family、7 個 held family 未另建知識文件；79 筆 accepted source rows。
來源仍排除 canonical authority／variant identity／PostgreSQL ingestion；本計畫不解除限制。
SQL 寫入 0；網站請求 0；新增 canonical UUID 0；未重跑已封存的 final 評估。

## 來源檔案指紋（12 個本機輸入；非整個歷史 evidence tree 的重新驗證）

- `data/external/hot-wheels-wiki/pilot-2025/manifest.json`：`960c639765759d3ab7b610718c026fa784e1995844f4acc9587718d94218f111`
- `data/external/hot-wheels-wiki/pilot-2025/normalized.json`：`e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6`
- `data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-05-adjudicated-queue-manifest.json`：`6b532978c86adf39dbc2f41222d41ca9b765b1c615dce5453a0ba04955a9f6ff`
- `data/external/hot-wheels-wiki/pilot-2025/priority-2-batch-05-adjudicated-queue.json`：`989bc914f9493051a071472c9defd352fe1cb8cc217c062e1f479bdcb9c6e4d8`
- `data/human_backed_catalog.json`：`d29b69cde8099cb229136a73b893ca99b6313d9652ead5ff4aea48c20242e74f`
- `data/human_backed_catalog_manifest.json`：`c79a3bc699d2bfcccae992a672fda79cbb905f1f2252dbfda8fa219ed55e43c7`
- `data/human_labeled_names.json`：`68b5dfdb8d0fa4972328d172cc5a56d78ac8bf00bc740083b2bfc07eb2a91188`
- `data/human_labeled_names_manifest.json`：`f56cba710a720959d4c535c3353730f012911ab18e5a6054ebef2e5750ada84c`
- `data/review_family_knowledge.json`：`8615cbb99b453673599e1f9baf54f6900314d7ba64e53a31ea7891c71810b9d7`
- `data/review_family_knowledge_manifest.json`：`0239e272d27276d9a25df2c36edbbe6a7251facce7728ef947b86dcaa417c2ef`
- `data/review_family_registry.json`：`3f289b802cc2e8280ed5c3586d87cfabbee7ce37b10ae79504b5aa6b8837367d`
- `data/review_family_registry_manifest.json`：`ae9eda741aa2ec7cb9354424e17b789ba73c05890859e73d19cd845c5cab3ff2`

## 後續界線

T49.2 必須先指定並確認隔離測試資料庫；未授權操作既有資料庫或收集新網站資料。
這份 plan 不包含 embedding／SQL schema，也不決定 release equivalence。
