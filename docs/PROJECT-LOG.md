# Project Log

## 2026-10-05 — Pointwise 三分類 development calibration：通過雙門檻但保持 runtime 關閉

### 新執行了什麼，解決什麼問題

依 PNMR-G1 overlay，本輪把原有 100 筆 catalog-present development cases 與 52 筆真實、人工確認且相對
frozen catalog 不存在的 cases 組成新的三分類 development calibration。Fit 嚴格使用 70 positive + 32
no-match；threshold selection 使用互斥的 30 positive + 20 no-match。這解決前一版只能安全選擇
matched/ambiguous、完全沒有 no-match evidence 的核心缺口。

兩個預先固定的 gate 都通過。Match threshold `0.9424986749501544` 接受 7/50，7 筆 exact release 全對，
precision 100%。No-match threshold `0.15503728534608827` 判定 10/50，其中 9 筆正確，precision 90%、
no-match recall 45%；30 筆 catalog-present 中有 1 筆被錯拒，false-no-match rate 3.33%，低於 10% 上限。
剩餘 33 筆保持 ambiguous，代表 policy 用 coverage 換取可靠性，而不是強迫每筆都回答。

### 代碼修改了哪一部分、原因與決策

`image_search_pointwise_calibration.py` 抽出可重用的 pinned scoring context，使 positive 與 negative rows
共用同一 catalog、retrieval、candidate limit 與 CrossEncoder instance，避免兩組資料在不同 runtime 條件
下評分。新增 `pointwise_three_class_calibration.py`，負責驗證 PNMR-G1、組合 frozen partitions、重新 fit
五特徵 logistic calibrator，以及分別選擇 match/no-match thresholds。

No-match selector 的條件是至少 5 筆、precision 至少 90%、catalog-present false rejection 不超過 10%；
在合格 thresholds 中先最大化 no-match recall，再依 false count、precision 與較低 threshold 保守決勝。
若任一 gate 不成立，程式會輸出 aggregate shortfall 且不產生 policy。新增 API 測試也確認，即使有人把
v2 artifacts 接進 neural provider，`runtime_eligible=false` 仍使 `/health` 與 `/resolve` fail closed。

### 技術棧／方法選型、驗證與下一步

沿用純 Python logistic calibration 與 pinned local CrossEncoder，沒有新增模型、外部 API 或網路請求。
Artifacts 只保存 weights、thresholds、parent hashes 與 aggregate metrics；query、case ID、row label、
prediction 與 split membership 都未公開。Calibration SHA 為 `22990e…406d`，policy SHA 為
`68969b…b418`，第二次完整 in-memory run 可 byte-for-byte 重現。

67 個 relevant tests、Ruff、strict MyPy、v1/v2 CLI checks 與 diff check 通過；final test 完全未讀取或
執行，runtime default 未改。這個結果可作為履歷中的「可治理三分類 abstention policy」development
證據，但不是 production claim：20 筆 negative selection 已用於選 threshold，不能再當 untouched test。
若未來要啟用 runtime，下一個必要證據是獨立治理的全新 no-match holdout，加上固定的 catalog-present
policy test；不得再更動目前模型、feature 或 thresholds。

## 2026-10-05 — PNMR-G1：封存 owner 授權並建立窄範圍 development overlay

### 新執行了什麼，解決什麼問題

本輪將 project owner 對 PNMR-G1 的完整批准文字封存為 checksum-bound authorization，並產生
`pointwise-no-match-governance-overlay-v1`。Overlay 同時綁定 human dataset、52-row candidate set、
1,763-row catalog、32/20 split assignment 與前一階段 readiness hashes。這解決了原資料明確禁止
calibration/threshold selection、但 owner 已同意特定例外時，如何不改寫歷史檔案仍能留下可機器驗證
permission 的問題。

### 代碼修改了哪一部分、原因與決策

新增 `pointwise_no_match_governance.py`，驗證批准文字不是概括授權、所有四組 parent hashes 與數量完全
相符，再以 exclusive-create 方式寫入 owner authorization 與 overlay。允許動作只有 materialize overlay、
Pointwise development calibration-fit 及 threshold-selection；final retuning、runtime activation、row-level
publication 與 global truth claim 都是明文禁止。原始 `human_labeled_names.json` 的 `excluded_from` 沒有被
修改，因為 overlay 是對指定 candidate set 的窄例外，不是 source-wide promotion。

### 技術棧／方法選型、驗證與下一步

採用 append-only versioned overlay，而不是直接刪除原始 exclusions，是為了同時保存「原始資料治理決策」
與「後來由 owner 授權的例外」，讓 reviewer 能追出 permission 何時、對哪些 bytes 發生改變。六個 focused
tests、Ruff、strict MyPy 與 overlay CLI check 通過。下一步可依同一授權執行 development-only 三分類
calibration；若安全門檻無法成立，必須發布 shortfall，不能啟用 runtime。

## 2026-10-05 — 真實 no-match readiness：找到 52 筆證據，但不越過原始資料權限

### 新執行了什麼，解決什麼問題

本輪沒有為了補齊三分類而合成負例，也沒有重新爬取網站。Readiness audit 將既有 101 筆
`human-labeled-real-noisy-v1` 與 frozen 1,763 筆第三方 catalog 做 brand/casting family 的精確正規化比對。
91 筆具有非空的真實原始查詢且人工 confidence 為 confirmed；其中 39 筆 family 已存在 catalog，因此不能
當 no-match，另外 52 筆 family 不存在，可作為 catalog-relative no-match 候選。52 筆中 46 筆仍是 Hot
Wheels，6 筆來自其他品牌，能同時涵蓋同品牌未知 casting 與跨品牌 out-of-scope 情境。

這一步解決的是「是否必須再收集一批 negative data」的問題：目前證據數量已足以保留 32 筆 fit、20 筆
threshold-selection，因此不需要再啟動網路資料搜集。不過原資料合約明確把 calibration training 與
threshold selection 列在 `excluded_from`；readiness 只證明候選存在，沒有擅自把它升格為可用校準資料。

### 代碼修改了哪一部分、原因與決策

新增 `pointwise_no_match_readiness.py`，以固定輸入 SHA-256、嚴格 JSON、唯一 case/query/identity、精確
normalized brand/casting absence 等條件重建候選集合。公開 artifact 只保存總數、candidate-set digest 與
prospective split digest，不保存 query、case ID、逐筆 label 或 partition membership。32/20 split 在模型
評分前由 versioned salt 決定，避免未來看到結果後再挑容易的 negative rows。

模組同時強制保留兩個 permission blockers，並記錄 resolver/model 未載入、development/final case 均未
評分、final test 未讀取、calibration/policy 未寫入及 runtime default 未變。這些不是說明文字而已；CLI
checker 會對 guardrail、counts、hash 與 row-level key 做 fail-closed 驗證。

### 技術棧／方法選型、驗證與下一步

採用 exact normalized family absence，而非 fuzzy similarity 或 resolver output，因為本階段只做 source
alignment readiness；若先看模型輸出再挑 negative，會造成 selection bias。Exact absence 仍只代表相對
frozen 2023–2026 third-party snapshot 不存在，不代表 Mattel/global truth，這個限制已寫入 artifact。

60 個 relevant tests、Ruff、strict MyPy 與 CLI integrity check 通過。下一步只有一個必要 Owner Gate：是否
允許 candidate-set SHA `08d08e…5c53` 在指定 catalog SHA `b4e074…09d4` 下，僅用於 Pointwise
development calibration-fit 與 threshold-selection。批准後才能 materialize versioned overlay；仍不會授權
final-test retuning、runtime activation 或 global no-match truth。

## 2026-10-05 — Pointwise decision calibration：只用 development 選擇保守門檻

### 新執行了什麼，解決什麼問題

本輪完成 neural Pointwise 的 development-only decision calibration。Frozen 100 筆 development 被新的
versioned salt 穩定切成 70 筆 calibration-fit 與 30 筆 threshold-selection；53 筆 final test 沒有讀入
校準、沒有重新執行，`test_cases_scored` 固定為零。這解決了 CrossEncoder raw logit 只能排序、不能直接
解讀為「答案正確機率」的問題，同時避免用 final test 選 threshold 造成資料洩漏。

在 30 筆 selection 中，Pointwise exact-release Top-1 答對 21 筆。預先規定的門檻搜尋要求至少接受 5 筆，
且 empirical precision 至少 90%；最終 threshold `0.641259466766539` 接受 11 筆，其中 10 筆正確，得到
90.91% precision 與 36.67% coverage，其餘 19 筆回傳 ambiguous。這組 development 全是 catalog-present
positive cases，沒有可用的真實 no-match 樣本，因此結果刻意不宣稱已完成三分類 policy。

### 代碼修改了哪一部分、原因與決策

新增 `image_search_pointwise_calibration.py`，負責 frozen inner split、記憶體內 feature/target 蒐集、純
Python logistic calibration、保守 threshold selection、aggregate-only artifact 產生與 strict integrity
check。輸出只包含 weights、threshold、hash 與總計，不保存 query、case ID、prediction 或逐筆 label。

`policy.py` 新增 `require_positive_top_score`，使 neural negative logits 可以交由 calibrator 解讀，而不是
被舊有 heuristic 規則直接拒絕；同時新增 `runtime_eligible`。`service.py` 在 neural provider 載入時檢查
後者：本輪產生的 positive-only policy 明確為 `false`，即使使用者把檔案路徑接入設定，readiness 仍會
fail closed。這個選擇讓研究結果可驗證，但不會把不完整的 no-match 能力誤部署到 API。

### 技術棧／方法選型、驗證與下一步

採用五個既有、可解釋的 ranking features 配合小型 logistic calibrator，而沒有新增外部服務或再次訓練
CrossEncoder。70/30 nested split 的原因是同一批資料不能同時 fit probability mapping 又挑 threshold；
在只有 100 筆的限制下，它保留足夠 fit 資料，也留下獨立 development selection 證據。相較加入複雜
calibration library，純 Python 實作可固定演算法與輸出 bytes，較適合此履歷型專案的可重現要求。

57 個相關 unit／API／integration／evaluation tests、Ruff、strict MyPy、artifact integrity check 與 diff
check 全數通過；校準與 policy bytes 可重現。153-row dataset、1,763-row source 及 final aggregate 的
SHA-256 均未改變。下一個必要缺口是建立不接觸 final test 的 catalog-absent/no-match development evidence，
再版本化產生 runtime-eligible 的三分類 policy；在此之前 RRF 仍是預設，neural runtime 保持關閉。

## 2026-10-05 — Pointwise runtime integration：完成受控接線但不提前啟用決策路徑

### 新執行了什麼，解決什麼問題

本輪把已通過 development selection 與一次 final test 的 `neural_pointwise`，從實驗 runner 接到正式
`ResolverService` 的可選 provider 邊界。新的 `neural-pointwise-v1` 只能由明確設定啟用；未設定時仍是
`PVR_RERANKER_ENABLED=false`，既有 RRF 排名、calibration 與 policy 完全不變。這解決了「模型已證明有
ranking value，但正式 API 尚無安全載入與觀測路徑」的問題。

同時沒有把 67.92% exact Top-1 誤解成可以立即部署。CrossEncoder 輸出是相對 ranking logit，不是
match probability；若直接沿用 heuristic 或 RRF 的 calibrator，API 可能以錯誤 confidence 回傳
`matched`。因此 neural provider 在缺少明確 calibration 或 policy artifact、artifact version 未綁定
`neural-pointwise-v1`、model bytes 缺失或 hash 不符時一律 fail closed，API readiness 會回報不可用。

### 代碼修改了哪一部分、原因與決策

`config.py` 新增 allowlisted provider、pinned config path 與 Git-ignored local model path；`.env.example`
只展示設定方式，沒有把 neural 設成預設。`rerank.py` 新增 batch `NeuralPointwiseReranker`：使用與 frozen
comparison 相同的 brand、casting、year、series、color、collector number、series position、edition、
aliases、identifiers 渲染順序，一次送入最多 25 個 query/candidate pairs，按 neural logit 排序，分數相同
時依 RRF rank 與 canonical UUID 穩定決勝。

`service.py` 只在顯式 opt-in 時 lazy-load 本機 CrossEncoder，並沿用 manifest 對 model ID、revision、
license、allowlist、檔案大小與 SHA-256 的驗證。Debug 顯示實際載入的
`cross-encoder/ms-marco-MiniLM-L6-v2@233902d…0a`；`/health` 同樣回報實際版本，而不是只有抽象 provider
名稱。缺模型或不相容 artifacts 的測試確認 `/health` 與 `/resolve` 都 fail closed。

### 技術棧／方法選型、驗證與下一步

這次重用既有 `sentence-transformers` CrossEncoder adapter 與 safetensors-only local snapshot，沒有再新增
模型、網路 API 或下載流程。選擇 batch adapter 而不是把 neural 包裝成逐候選 heuristic `score()`，是因為
逐筆呼叫會增加延遲，且既有 heuristic 還會混入 source-support／match bonus，導致 runtime 排序偏離已驗證
的 Pointwise arm。模型仍位於 Git-ignored `model-cache/`，Git 只保存 config、程式與驗證證據。

54 個相關 unit／API／integration／evaluation tests、Ruff、strict MyPy 與 diff check 通過；另以本機
snapshot 實際載入固定 revision 成功。測試只讀取既有 final aggregate artifact 以確認 rerun guard，沒有再次
執行 53-case final test，也沒有修改 153-row dataset。下一個必要工作是只用 frozen 100-case development
建立 neural 專用 calibration 與 `matched / ambiguous / no_match` policy，完成前 neural runtime 保持不可
啟用的 fail-closed 狀態。

## 2026-10-05 — Final release-ranking gate：Pointwise 在未見 test 上維持勝出

### 新執行了什麼，解決什麼問題

本輪依照已封存的 development selection，明確且只執行一次 53-case final test。執行前沒有更換模型、
feature、候選數、selection rule 或 threshold；四個 arms 仍共用 frozen 1,763-row corpus 與每筆 25 個
candidates。結果顯示 `neural_pointwise` 不只在 development 勝出，也在未用於選型的 test 維持第一：
casting Top-1 `52/53 = 98.11%`、exact release Top-1 `36/53 = 67.92%`、MRR@10 `83.21%`、
Recall@10/25 均為 `100%`。

相較原始 RRF 的 exact Top-1 `29/53 = 54.72%`，Pointwise 多答對 7 筆，提升 13.21 percentage points；
RRF casting Top-1 為 `46/53 = 86.79%`。Release heuristic 的 exact Top-1 為 `33/53 = 62.26%`，
Listwise 為 `32/53 = 60.38%`，因此沒有理由在看到 test 後改選較複雜的 Listwise。這一步解決了
「development 改善是否能泛化」的核心問題，同時避免用 final test 反覆調參而把測試集變成訓練集。

### 代碼修改了哪一部分、原因與決策

`image_search_ranking_development.py` 把共用 comparison runner 明確分成 development 與 test 路徑，並新增
需要雙重明示參數的 final-test CLI、strict final artifact validator，以及 final artifact 已存在時拒絕再次
執行的 fail-closed guard。驗證器會重新計算 raw counts 與 rates、winner、dataset／split／model hash
binding，也會遞迴拒絕實際 key 為 `cases` 或 `predictions` 的 row-level output；它不再以全文字串搜尋，
避免把合法的 `test_cases_scored` 誤判為 row data。

新增 `data/evaluation/image-search-release-ranking-v1/final-comparison.json`，只保存四組 aggregate metrics、
generalization gates 與 negative guardrails。沒有保存 query、case ID、prediction 或 failure row；正式
`dataset.json` 與 canonical catalog 均未修改。最終決策是保留 `neural_pointwise` 為 release-ranking winner，
但此結論只授權下一階段評估如何整合，不等於已改變 resolver runtime default，也不代表 neural score
已成為 calibrated match probability。

### 技術棧／方法選型、驗證與下一步

Pointwise 沿用 frozen `cross-encoder/ms-marco-MiniLM-L6-v2@233902d…0a`，沒有使用 100 筆 development 或
53 筆 test 重新 fit。其 test p95 rerank latency 為 `130.49 ms`，低於既有 `1,500 ms` budget；Listwise
含 Pointwise 的 p95 為 `130.91 ms`，沒有帶來 accuracy 優勢。13 個 focused tests、Ruff、strict MyPy、
final CLI integrity check 與 diff check 通過；final artifact 將 `test_rerun_allowed`、`post_test_retuning_allowed`
與 `post_test_model_switch_allowed` 全部固定為 `false`。

ISRR-T4 至此完成。下一個必要工作不是再次查看 test，而是把已選 Pointwise 接入正式 resolver 的受控
設定路徑，並只使用 development 資料設計或校準 match／ambiguous／no_match policy；完成後若需要報告
policy 表現，必須沿用目前 frozen 結果與治理邊界，不能用 53-case final answers 重新選模型或門檻。
所有 accuracy 都是 frozen 第三方 release source-relative 結果，不代表 Mattel／manufacturer-certified
或 global canonical truth。

## 2026-10-05 — Pointwise development selection freeze：封存選型但保持 test 與 runtime 關閉

### 新執行了什麼，解決什麼問題

本輪把上一輪的 development comparison 封存為 aggregate-only selection manifest。Manifest 綁定正式
dataset SHA、100/53 split assignment SHA、1,763 candidate corpus、25-candidate limit、四個 arms 的 raw
development metric counts，以及 Pointwise／Listwise 模型 bytes。Selection rule 固定為 exact release
Top-1、MRR@10、p95 latency 的優先順序；依此重新計算 winner 仍是 `neural_pointwise`。

這一步解決「口頭說 Pointwise 勝出，但後續不知道用的是哪份資料、哪個 split 或哪組模型」的問題。
封存後若 dataset、split、模型 revision、local model manifest、實際 Pointwise model files 或 Listwise
checkpoint 任一漂移，selection check 會 fail closed，不能靜默使用另一組實驗條件。

### 代碼修改了哪一部分、原因與決策

新增 `data/evaluation/image-search-release-ranking-v1/development-selection.json`。它只保存 aggregate raw
counts、selection rule、checksums 與 negative guardrails；不含 query、case ID、candidate、prediction、
failure row 或 test metrics。`image_search_ranking_development.py` 新增 strict Pydantic contract 與
`--check-selection`，驗證 exact arm set、winner 重算、dataset/split binding、authority note、模型 hash 與
`test_cases_scored=0`。

Manifest 明確記錄 `runtime_default_changed=false`、`calibration_or_policy_changed=false`、
`models_refit_on_image_search_development=false`。選擇 Pointwise 只代表它取得 final-test candidate 資格，
不是已部署、已校準或已證明 production winner。

### 技術棧／方法選型、驗證與下一步

Pointwise 綁定 `cross-encoder/ms-marco-MiniLM-L6-v2` revision `233902d…0a`，local manifest SHA 為
`32f889…feb8`；Listwise safetensors SHA 為 `9386c059…8aead`。11 個 focused tests、Ruff、strict MyPy 與
selection CLI integrity check 通過。資料集目錄仍只含最終 `dataset.json`；selection 位於獨立 evaluation
governance 目錄，不是第二份 query dataset。

下一步才是 ISRR-T4 final gate：在不再改模型、feature、selection rule 或 threshold 的前提下，明確執行
一次 53-case test，比較 frozen RRF／heuristic／Pointwise／Listwise。Final 結果出來前，runtime default
與 resolver policy 維持不變。

## 2026-10-05 — Development ranker comparison：Pointwise 提升 exact release Top-1 至 69%

### 新執行了什麼，解決什麼問題

本輪只在 frozen 100-case development split 比較四個相同候選池的 ranking arms：原始 RRF、既有
release-aware heuristic、固定 CrossEncoder Pointwise，以及以同一 Pointwise logit 加 20 個 retrieval／
structured features 的 frozen Listwise head。所有 arm 都先讀取相同的 25 candidates；53-case test 沒有
執行，也沒有保存任何 row-level prediction。

結果顯示 Pointwise 是明確的 development winner：casting Top-1 `96/100`、exact release Top-1
`69/100`、exact MRR@10 `80.87%`、Recall@10/25 都是 `100%`。相較原始 RRF 的 casting `84%`、
exact Top-1 `55%`，Pointwise 分別提升 12 與 14 percentage points，證明 query/candidate pair 的語意
比單靠來源 rank fusion 更能區分同 casting 的 release identity。

### 代碼修改了哪一部分、原因與決策

新增 `image_search_ranking_development.py` 與 CLI `pvr-compare-image-search-rankers`。Runner 只取得 frozen
development IDs，重用相同 in-memory 1,763-row catalog 與 25-candidate retrieval，再對四個 arms 計算
casting Top-1、exact Top-1、MRR@10、Recall@10/25 與 rerank p50/p95。輸出只有 aggregate report，並
明示 `test_cases_scored=0`、`row_level_output_persisted=false`。

Pointwise 使用既有固定 revision `cross-encoder/ms-marco-MiniLM-L6-v2@233902d…0a`；Listwise 使用既有
safetensors checkpoint `9386c059…8aead`。兩者是在先前 fixture benchmark 訓練／選型，本輪對新的
image-search development 做 zero-shot comparison，沒有以這 100 筆 label 重新 fit，因此結果不是
training-set accuracy。

### 技術棧／方法選型、驗證與下一步

RRF exact Top-1/MRR@10 為 `55%/72.88%`；release heuristic 為 `55%/68.97%`；neural Pointwise 為
`69%/80.87%`；neural Listwise 為 `54%/70.46%`。Listwise 雖將 casting Top-1 提升到 `90%`，但 exact
release 低於 RRF 與 Pointwise，表示舊 fixture 上學到的 candidate-set feature weighting無法轉移到目前
的真實 release distribution，因此不應因架構較複雜而選它。

Pointwise rerank p95 約 `127.45 ms`，Listwise（含 Pointwise）約 `127.87 ms`，release heuristic 約
`0.20 ms`；Pointwise 仍低於既有 1,500 ms resolver budget。9 個 focused tests、Ruff 與 strict MyPy
通過；模型完全本機載入，沒有網路請求。下一步是在不重訓、不調參的前提下封存 Pointwise
development selection，然後經明確 final gate 只跑一次 53-case test；在 final 結果前不修改 runtime
default 或 calibration policy。

## 2026-10-05 — Release-ranking split freeze：凍結 100 development／53 test

### 新執行了什麼，解決什麼問題

在改善 exact-release ranking 前，本輪先把 153 筆 image-search benchmark 凍結為 100 筆 development
與 53 筆 test。此前只看過全資料集 aggregate baseline，沒有保存或檢查 row-level predictions、case-level
failures 或 split-specific test metrics；現在先固定 test，避免後續 Pointwise／Listwise 與 policy tuning
反覆看同一批最終答案而形成資料洩漏。

分割不修改 `dataset.json`，也沒有建立第二份 row-level split file。它使用固定 salt、case ID 與 normalized
expected casting 產生 SHA-256 sorting key，前 100 筆為 development、後 53 筆為 test。完整 assignment
checksum 為 `10ed70cc347f1b548c156e033645d6b0e90f48ee66c95af631832e8d55aebdac`；兩組零重疊，
union 恰好為 153 筆。

### 代碼修改了哪一部分、原因與決策

`image_search_evaluation.py` 新增 frozen dataset SHA、split version/salt、deterministic partition 與 fail-closed
checksum validation。CLI 現在預設只跑 `development`；若要碰最終 test，必須明確傳入 `--split test`。
這比把 `split` 欄位寫回 dataset 更符合最小資料要求，也避免為同一批 query 維護兩個可能漂移的來源。

Dataset SHA 固定為 `b0feeff8f1158ab67cfac2ae493eefc04a6aba1b90d4fce448724341315e095c`。
任何內容或 row count 改變都會在分割前失敗，不能靜默產生另一個 test set。測試新增 deterministic、
disjoint、exhaustive、salt sensitivity 與 frozen checksum 驗證。

### 技術棧／方法選型、驗證與下一步

100 筆 development-only baseline 為 casting Top-1 `84/100 = 84%`、exact release Top-1 `55/100 = 55%`、
exact Recall@10 `99%`、Recall@25 `100%`。Policy matched `15/100`、exact correct `13/100`，coverage
`15%`、precision `86.67%`、abstention `85%`。7 個 focused tests、Ruff 與 strict MyPy 通過；53 筆
test 沒有在本輪重新計分。

下一步只使用 development 建立 release-aware ranking baselines，重點比較 year、series、collector number、
series position 與 toy identifier 訊號。只有 development 選型完成後，才允許一次明確的 final test。

## 2026-10-05 — Image-search evaluation：以 1,763 筆 local corpus 驗證 153 筆真實搜尋文字

### 新執行了什麼，解決什麼問題

本輪把 `image-search-resolver-v1` 從靜態 JSON 接上真正的 resolver pipeline。執行前先做 catalog
coverage gate，發現正式 `data/catalog.json` 只有 140 筆產品，新 benchmark 只有 2 個 casting 出現在
其中；若直接計分，151 筆必然因 catalog 缺資料而失敗，不能代表 resolver 能力。因此新增 local-only
evaluation projection：在記憶體中把 frozen 1,763-row release snapshot 轉成候選 catalog，執行完即消失，
不修改 production catalog、PostgreSQL canonical tables 或 human-knowledge corpus。

153 筆 expected identities 全部依 toy number 唯一綁定至來源 row，完整 release fields 全數一致。實際
aggregate 結果為 casting Top-1 `130/153 = 84.97%`、exact release Top-1 `84/153 = 54.90%`、exact
Recall@10 `151/153 = 98.69%`、Recall@25 `153/153 = 100%`。這表示 retrieval 幾乎都能找到正確 release，
但同 casting 的跨年份／系列／編號版本仍需要更好的 release-level ranking。

### 代碼修改了哪一部分、原因與決策

新增 `image_search_evaluation.py` 與 CLI `pvr-evaluate-image-search`。Loader 使用 Pydantic strict schema
拒絕多餘欄位、非連續 ID、重複 query／casting 與答案不一致；source binding 要求 toy number 唯一，
並逐欄核對 brand、casting、year、series、collector number、series position、color 與 variant note。
Candidate identity 使用 source record ID 衍生的 deterministic UUIDv5，但明確標為 evaluation surrogate，
不是 canonical UUID。

選擇 in-memory projection 而不是把 1,763 rows 寫入 `catalog.json`，是因為這批來源仍是第三方 frozen
snapshot，沒有 manufacturer/global canonical authority。這個方法能測真正的 sparse／dense／structured
retrieval、reranker switch、calibration 與 policy，同時不越過既有 canonical governance boundary。

### 技術棧／方法選型、驗證與下一步

沿用既有 Python 3.12、Pydantic、`CatalogProduct`、hashing embedding、RRF retrieval 與 ResolverService。
CLI 必須顯式帶入 `--acknowledge-source-relative-evaluation`；stdout 只輸出 aggregate metrics，沒有保存
row-level prediction。5 個 focused tests、Ruff、strict MyPy 與 compileall 通過；153 筆對 1,763 candidates
的完整 run 約 4.9 秒完成，p50 15.72 ms、p95 17.95 ms。

現有 policy 僅 `24/153` 回傳 matched，其中 `20` 筆 exact correct；policy coverage `15.69%`、precision
`83.33%`、abstention `84.31%`（69 ambiguous、60 no_match）。所以下一個必要工作應先改善 release-level
ranking，再用 development split 重新校準 decision policy；不能只降低門檻，否則會放大四筆已觀察到的
wrong-release matches。這份結果是第三方 source-relative evaluation，不代表 manufacturer-certified
或 production/global accuracy。

## 2026-10-05 — Repository hygiene：清除可重建產物，保留仍有依賴的早期資料

### 新執行了什麼，解決什麼問題

本輪在準備後續 GitHub push 前盤點整個專案，刪除 `.mypy_cache`、`.pytest_cache`、`.ruff_cache`、
Python `__pycache__`、`build/`、egg-info 與 `.DS_Store`。這些內容只由本機工具產生，可在需要時重新建立，
既不是產品程式碼，也不是評估證據；移除後能讓工作目錄保持清楚，不影響 resolver 行為。

同時確認本次 image-search 收集使用的 crawler、圖片與 raw/intermediate responses 已不存在。`.gitignore`
新增 `/.local-image-search-collection*/`，讓未來任何同類暫存資料夾預設無法被 Git 收錄；正式可提交內容
仍只有 `data/evaluation/image-search-resolver-v1/dataset.json`，不會因這條規則被忽略。

### 代碼／資料修改了哪一部分、原因與決策

沒有刪除最早的 `data/benchmark.json`：它目前仍由 API 設定、Docker runtime、metrics、neural reranker、
fixture validator 與測試直接使用。`data/human_labeled_names.json` 也仍是 human-backed catalog、source
inventory 與 frozen human-knowledge snapshot 的上游；family-retrieval v1 則仍被 v2 builder 與 regression
tests 引用。直接刪除任一檔案都不是整理，而是破壞現有 dependency contract。

本機 `HW data/`、1,763-row local export、owner review workspaces、`.venv` 與 pointwise model cache 亦保留。
前四類支援資料重建與治理審計；`.venv` 保持開發與測試可執行；model cache 支援重新執行 pointwise
comparison。它們全部已被 Git ignore，不會隨後續 push 上傳。

### 技術棧／方法選型與驗證

整理採用「Git tracking 狀態 + 全 repo reference scan + 可重建性」三個條件，而不是看到舊版本名稱便
刪除。驗證確認 image-search 正式目錄只含最終 `dataset.json`，暫存收集目錄與下載圖片不存在，Git
沒有未追蹤的非 ignored 檔案。因為本輪沒有改產品碼或資料內容，不重跑完整測試；只執行資料結構、
ignore boundary 與 diff integrity 檢查。

## 2026-10-05 — Image Search Resolver Dataset v1：建立 153 筆 source-grounded 查詢與完整 release 答案

### 新執行了什麼，解決什麼問題

本輪從 owner 提供、Git-ignored 的 1,763 筆 release dataset 中，以固定 seed `20261005` 隨機抽取
180 個不重複 casting，為每個 casting 取得一張 Google Images 搜尋結果圖片，再依 Resume Project
既有 Serper Lens adapter 的候選整理方式產生一筆文字 query。最後將文字 query 與原始 release row
的 casting-level 答案及完整 release identity 配對，形成 `image-search-resolver-v1`。這解決了原本
benchmark query 與目前 catalog coverage 不一定相交、因而大量只能 held 的問題：新資料的每一筆
答案都直接來自抽樣時使用的 1,763 筆來源，而不是事後猜測。

第一次收集雖然得到 180 筆，但必要品質檢查只發現 132 筆 query 與預期 casting 有嚴格文字重疊；
例如搜尋頁第一張可下載圖片可能是相似車款或頁面推薦圖。這批結果沒有直接採用，而是加入 seed image
title 驗證：圖片結果必須包含 toy number、完整 normalized casting，或至少 80% casting token overlap。
保留 139 筆自洽資料並重收／替換 41 筆後，180 張 seed images 均通過來源標題檢查；第二道 query
檢查再排除 27 筆 Lens 文字不足以支持正確答案的結果。這 27 筆包含合法別名，也混有明顯錯車，因此
沒有逐筆主觀挑選，而是整批依同一門檻剔除。最終保留 153 個 unique castings 與 153 個 unique
queries，仍落在預定的 150–200 筆範圍，且每筆都回連同一筆 source-defined identity。

### 代碼修改了哪一部分、原因與決策

永久新增的資料只有 `data/evaluation/image-search-resolver-v1/dataset.json`。每筆只保留 `id`、
`query`、`expected_casting` 與 `expected_full_identity`；完整 identity 使用來源現有的 brand、casting、
release_year、series、collector_number、series_position、toy_number，以及來源實際存在時才保留的
variant_note／color。這樣同時支援 casting-level 與 release-level 評估，又不把 image URL、圖片 hash、
搜尋時間、raw response、候選清單或 adapter metadata 混入最終 benchmark。

所有收集腳本、圖片、raw/progress 檔與 API 中間結果都只存在獨立、Git-ignored 的暫存資料夾；正式
dataset 通過結構與隱私檢查後，該資料夾整體刪除。沒有把 Resume Project 的 `.env` 或 Serper key
複製到本專案。這個選擇符合資料最小化要求，也避免把一次性的收集器誤當成 Product Variant Resolver
的產品程式碼。

### 技術棧／方法選型、驗證與限制

抽樣採 Python fixed-seed shuffle，使 180 筆候選可由相同私有來源重現；圖片搜尋使用 Google Images，
反向圖片文字結果沿用 Resume Project 的 Serper Lens response parsing、文字清理、候選聚類與品質排序，
因此 `query` 是既有 adapter 選出的 Top-1 `display_name`，不是未處理的第一個搜尋片段。永久 JSON 已
驗證為 153 個連續 ID、153 個 unique queries、153 個 unique castings、完整 identity linkage、精確
schema，且不含 URL、hash、timestamp、API key、historical human label、failure category 或 split。

這份答案代表 1,763 筆第三方 release source 所定義的正確身份，不代表 Mattel/manufacturer-certified
global truth，也不是 canonical UUID。由於 seed 圖片是用答案 casting 主動搜尋取得，此資料適合驗證
「圖片搜尋文字 → resolver」流程與 release-level discrimination；它不是衡量自然使用者查詢分布的
無偏樣本，後續報告必須保留這項限制。

## 2026-10-05 — RHB-T6 Review Batch 2：保留十筆證據不足資料，加入安全的 append update

### 新執行了什麼，解決什麼問題

Owner 確認第二批十個 staged cases 全部維持 `held`，且不驗證 provisional challenge tags、不批准
matched，也不開放任何後續評分階段。逐筆決定與完整 owner 原文寫入第二個 Git-ignored、`0600` 的
private event；公開 progress 只從「10 筆已審」更新為「20 筆已審」，累計一筆 approved
catalog-relative `no_match`、十九筆 held、四十筆待審。

這批資料維持 held 的原因不是已證明它們不存在，而是 frozen catalog 沒有足夠候選證據。把 catalog
coverage gap 直接標成 `no_match` 會製造錯誤 ground truth；保留 held 可讓它們在 catalog 或獨立證據
增加後重新審查，同時目前不會進入 labels 或 scoring。

### 代碼修改了哪一部分、原因與決策

Progress builder 新增 Batch 2 的 exact private-file SHA 與 owner-response SHA allowlist，並把下一個合法
動作更新為 Batch 3。另加入安全的 append-update 路徑：既有 public progress 必須能由目前 private
events 的歷史 prefix 完整重算，且新 batch 數只能增加，才允許 atomic replace。若既有檔被修改、batch
倒退或不是有效 prefix，builder 會 fail closed。

這項修改是必要的，因為 Batch 1 之後 public progress 已存在；只支援 create/unchanged 的 builder
無法安全表達後續審閱。選擇驗證舊 snapshot 後 append，而不是直接覆寫 JSON，可保留 event-sourced
審計鏈，並阻止舊 owner decision 被靜默改寫。

### 技術棧／方法選型、驗證與下一步

沿用 Pydantic strict schemas、canonical JSON、SHA-256、private `0600` events 與 public `0644`
aggregate。新增 append-prefix 測試後，完整 representative benchmark suite 共 147 個 tests 通過；
Ruff、strict MyPy、compile、builder replay、private mode、Git-ignore、public privacy 與 diff check 均通過。
沒有建立 labels、held-labels、split、scoring 或 resolver output。

下一步僅為 RHB-T6 Review Batch 3。RHB-T7、Pointwise/Listwise 與 resolver evaluation 仍需另外、明確
的 Owner Gate。

## 2026-10-05 — RHB-T6 Review Batch 1：記錄首批 owner decision，但不提前建立 labels

### 新執行了什麼，解決什麼問題

本輪依 owner 的明確決定處理第一批十個 staged cases：一筆被確認為 frozen-catalog-relative
`no_match`，其餘九筆維持 `held`；所有 provisional challenge tags 仍為未驗證。精確的逐筆決定與
owner 原文只寫入 Git-ignored、`0600` 的 private event，Git 端新增的 progress artifact 只公開總數與
完整性 hash。因此專案現在可以證明「哪些 staged proposals 已被人審過」，又不會公開 row-level query
或 label 資料。

這一步解決 staging suggestion 與 owner decision 容易混淆的問題。原本的 60 筆 proposal 保持不可變，
owner 決定以 append-only event 另外記錄；目前累計十筆已審、一筆 approved decision、九筆 held、五十筆
待審，matched 與 verified challenge tags 都是零。部分審閱不會建立 `labels.json`，也不會讓任何資料
進入 split、scoring 或 resolver evaluation。

### 代碼修改了哪一部分、原因與決策

新增 `representative_benchmark_label_review_progress.py` 與對應 CLI，負責重播 staging parents、驗證
private batch 的 exact file SHA、owner-response SHA、decision content hash、case 不重疊與檔案權限，再
產出 aggregate-only progress。選擇 event sourcing 而不是直接修改 staged proposals，是因為 proposal
是 AI 產生的待審建議，owner decision 是不同信任層級；分開保存才能保留審計軌跡，也能避免未完成的
批次被誤認為最終 labels。

公開 progress 不保存 case ID、query、逐筆狀態、理由、owner 原文或 canonical UUID。它只記錄 batch
數量、已審／待審總數、批准狀態總數、negative authorization flags 與 private file hashes。這種設計
比把逐筆內容提交 Git 更適合目前的資料治理要求，也讓後續 batch 能以 hash chain 驗證前序決定沒有
被改寫。

### 技術棧／方法選型、驗證與下一步

沿用 Python 3.12、Pydantic strict schemas、canonical JSON、SHA-256 與 fail-closed validation。Batch 1
private file SHA 為 `278fe2…cfa1`，public progress hash 為 `284617…b74e`。新增七個 progress tests，
涵蓋 aggregate、replay、private event binding、privacy、tamper、downstream absence 與 dependency
guard；完整 representative benchmark suite 共 146 個 tests 通過。Ruff、strict MyPy、compile、兩個
builder replay、private mode、Git-ignore、public privacy 與 diff check 亦通過。

下一步只允許提出 RHB-T6 Review Batch 2 給 owner 審閱。這次決定沒有批准 matched，也沒有授權
RHB-T7、Development/Test split、Pointwise/Listwise、scoring 或 resolver evaluation。

## 2026-10-05 — RHB-T6 Label Review v1：建立 60 筆私有 staging，揭露 query/authority overlap 缺口

### 新執行了什麼，解決什麼問題

本輪收到獨立的 RHB-T6 Label Review v1 批准後，先把完整批准寫入 Git-ignored、`0600` 的 owner
ledger，再建立 `0700` local review workspace。Workspace 內有 60 筆 evidence packets 與 60 筆
staged label proposals；public Git 只新增 aggregate manifest，沒有 row-level query、source ref、UUID
proposal 或 owner 原文。所有 proposal 都還是 `owner_decision_recorded=false`、`score_eligible=false`，
所以這一步沒有把 AI 建議誤稱為 human label。

這個步驟解決的是「治理 overlay 已允許最多 20 個 matched，但實際 60 個 query 是否真的有足夠 exact
evidence」的問題。結果是沒有：staging 為 `0 matched / 5 ambiguous / 4 no_match / 51 held`。唯一命中
admitted family 的 private query 同時對應三個 release，而且沒有其中任何 toy identifier，因此不能
挑一個 UUID。Overlay 提供的是 permission capacity，不會自動創造資料 overlap。

### 代碼修改了哪一部分、原因與決策

新增 `representative_benchmark_label_review.py` 與 CLI。Builder 只讀取 frozen query pack、完整
catalog-v2、governance overlay 與 20-record CAR authority。Evidence discovery 僅使用 normalized exact
casting/alias surface 或含英文字母的 toy identifier；純數字 collector/lot number 不作 candidate
discovery，避免把賣家數量或編號誤認成產品 ID。候選依 canonical UUID 排序並明示
`not_ranked`，因此不會冒充 resolver 或 ranking output。

提議 matched 的門檻刻意很高：必須只有一個 allowlisted authority，同時有 exact toy identifier 與
casting/alias surface。只有 catalog surface 但沒有唯一 admitted authority 時提議 ambiguous；明確的
外部品牌且 catalog candidate 為零時才暫提 catalog-relative no_match；其餘 51 筆全部 held。這個方法
比使用文字相似度自動補齊配額更保守，原因是 RHB-R5 把 false exact identity 視為最嚴重錯誤，而且
owner 已明確禁止 query-only challenge 推定與 quota forcing。

同時修正 governance overlay 的生命週期檢查：舊邏輯在後續 label authorization 出現後會讓歷史
overlay `--check` 失敗。現在「不得已有 downstream authorization/labels」只在首次建立 overlay 時檢查；
既有 overlay 的 hash-bound replay 可跨越後續 Gate 持續驗證。這保留建立順序限制，也避免合法生命週期
讓歷史證據失效。

### 技術棧／方法選型、驗證與後續限制

沿用 Python 3.12、Pydantic strict schemas、canonical JSON、SHA-256、atomic replace 與 `0700/0600`
private storage。Private authorization/content hashes 分別為 `37e2a4…d250`、evidence `a2e8f2…85f6`、
proposals `6c4956…85d`；public manifest hash 為 `457f3c…bb10`。Public manifest 只有 parent hashes、
count 與 negative authorization flags。

十個 focused label-review tests 與更新後 readiness/overlay tests 通過；全部 139 個
representative-benchmark tests 通過。Ruff、format、strict MyPy、compile、replay、private file modes、
Git-ignore、public privacy、partial-output rollback 與 diff check 都通過。歷史 human labels、
`data/human_labeled_names.json`、failure categories、resolver output、split、Pointwise/Listwise、scoring
與 network 都未讀取或執行。

下一步不是 RHB-T7，而是把 staged proposals 分批交給 owner。Owner 可以確認 ambiguous/no_match、
要求更多 evidence 或維持 held；任何一筆都不能在沒有明確 row/batch decision 時升格為 label。即使全部
60 筆都完成 review，若 matched 仍不足 20，RHB-R11 仍必須誠實保持未通過，後續需要另行治理的
query/source revision，而不能在目前 pack 補造資料。

## 2026-10-05 — RHB-T6 Governance Repair v1：實作精確綁定的 overlay，重新開放獨立 Label Owner Gate

### 新執行了什麼，解決什麼問題

本輪收到的批准只允許 materialize versioned governance overlay，因此沒有開始 RHB-T6 label
authoring。系統把批准寫入 Git-ignored、`0600` 的 private ledger，再產出可追蹤的 public overlay。
這個 overlay 僅對 query pack SHA `97f7…858a` 開放最多 20 筆 `matched`，且每筆日後都必須由
`project_owner` 審閱，綁定 CAR authority SHA `72c1…3117` 內明列的 authority ID 與 canonical UUID。

它解決的是前一輪 readiness 發現的兩個 contract 衝突：Human query source 在 frozen T3 中只能產生
`ambiguous/no_match`，CAR 後來審核通過的 20 筆 authority 也仍使用被舊 T1/T3 視為 staging-only 的
Wiki evidence。修復後，有效 matched capacity 從 0 變成 20，完整 20-record bundle 可被 label
validator 使用；但是原始 source-wide 規則沒有改寫，因此這不是把 Human labels 或 Wiki 全部升格。

### 代碼修改了哪一部分、原因與決策

`representative_benchmark_governance_overlay.py` 負責讀取私有批准、重播 proposal/query/authority
parents、建立 canonical JSON 並以 atomic replace 寫入 public overlay。`representative_benchmark.py`
新增 strict overlay schema，也讓 authority/label validators 只有在 overlay、query pack、完整 authority
bundle 與 source decisions 全部吻合時才接受例外；缺少 overlay 時，既有 T1/T3 prohibition 仍會
fail closed。這個選擇比直接修改 `source-decisions.json` 更能保留歷史，也比 source-wide promotion
精確，因為 owner 實際審過的是 20 筆而不是整個 Wiki。

核心 authority validator 同時修正兩個整合問題。第一，CAR authority 指向完整 `catalog-v2`，所以
只有歷史 authority 才還原到 parent fixture catalog，新 authority 保留在 v2 驗證。第二，public PII
scanner 不再把 machine authority ID 與 `sha256:` evidence ref 的長數字誤判為電話；reviewer 與
review reason 仍維持掃描。這些修改沒有降低 identity 或 provenance Gate。

`representative_benchmark_label_readiness.py` 升級為 v2：它同時呈現 frozen baseline matched capacity
0 與 overlay capacity 20，明確標示 `canonical_authority_t1_t3_compatible=false`、
`canonical_authority_admitted_by_overlay=true`，並將狀態改成
`ready_for_separate_owner_authorization`。這只是允許提出下一個 Owner Gate；`rhb_t6_authorized` 仍是
false，16 個 provisional challenge shortfalls 也沒有被治理修復自動消除。

### 技術棧／方法選型、驗證與未授權範圍

沿用 Python 3.12、Pydantic `extra=forbid`、canonical JSON、SHA-256、typed Literals 與原子寫入。私有
批准檔維持 `0700/0600` 且被 Git ignore；public overlay 只含 hashes、20 個 public authority IDs、
safe aggregates 與 negative authorization flags，不含 raw query、label、source-row reference 或 owner
原文。Overlay content SHA 為 `7f3a87…7cbe`，file SHA 為 `9b8a79…9311`；post-overlay readiness SHA
為 `0de130…767b`。

九個 overlay tests 與六個 readiness tests 通過；全部 128 個 representative-benchmark regression
tests 也通過。Ruff、format、strict MyPy、compile、proposal/overlay deterministic replay、private file
mode、Git-ignore 與 public privacy 檢查都通過。RHB-T6 label authoring、RHB-T7、resolver evaluation、
manufacturer/global truth、color/edition 新驗證都沒有被授權或執行。

## 2026-10-05 — RHB-T6 governance repair proposal：用 bundle-specific overlay 避免過度升格來源

### 新執行了什麼，解決什麼問題

前一步 readiness 已證明 matched-label permission 為 0/20，且 CAR authority 與 frozen T1/T3 的
authority-source policy 不相容。本輪沒有直接修改 permission 或建立 labels，而是產出 deterministic、
non-authorizing proposal，把需要 owner 決定的修復範圍完整凍結。Proposal 綁定 60-row query pack、
20-record CAR authority、source inventory/decisions、CAR manifest 與 readiness hash，狀態為
`awaiting_owner_decision`。

這解決了「如何讓 later CAR evidence 能支援 matched label，又不把 Human labels 或整個 Wiki 都升格成
canonical truth」的問題。Query side 只對目前 query-pack SHA 提議新增最多 20 筆 matched；每筆仍必須
由 owner 審閱並綁定 admitted authority ID/UUID。Authority side 只接納目前 20-record bundle 與 revision
790665，不是 source-wide promotion，也不是 Mattel/manufacturer truth。

### 代碼修改了哪一部分、原因與決策

新增 `representative_benchmark_governance_repair.py`、builder CLI、strict proposal schema 與專用測試。
Builder 會重驗 private query pack、T1/T3 與 CAR authority parents，並綁定當時 0/20 matched、authority
incompatible、shortfall 16 的 historical readiness SHA；任一 parent hash、authority ID ordering 或
permission baseline 改變都會 fail closed。JSON 採 canonical bytes 與 self SHA-256，首次建立後 replay
必須是 `unchanged`。Overlay 上線後 readiness 已合法演進，因此 proposal replay 不依賴「目前 readiness
仍 blocked」這個會隨生命週期改變的條件。

方法選型上沒有修改 frozen `source-decisions.json`，也沒有把 Wiki entry 改成全域
`authorized_export`。改用 bundle-specific overlay proposal，是因為原始 source-wide decision 描述當時
證據狀態，而 CAR 後來只審了有限 20 筆。覆寫歷史會失去 audit trail；整體升格又超出 owner 實際審核
範圍。Overlay 讓新證據可以被使用，同時將權限限制在 exact query/authority hashes。

### 技術棧／驗證與未授權範圍

沿用 Python 3.12、Pydantic `extra=forbid`、canonical JSON、SHA-256 與 atomic replace。Public proposal
只有 hashes、public authority IDs、aggregates 與 negative authorization flags，不含 raw query、source
row、owner response、expected label/UUID 或 label record。Proposal content hash 為
`e5d1d74233626dc715f253608d3ea05da8965b043e324255306523b3dffdf8de`，file SHA-256 為
`0df96c2a37c133584b0c15e11b0f84c304b21c233739bc92031ffff56ef3d28a`。

全部 126 個 representative-benchmark tests 通過；proposal 專用八個測試涵蓋 deterministic scope、
canonical materialization、real-file replay、authorization/widening rejection、public privacy、parent
drift、tamper 與 dependency guard。Ruff、format、strict MyPy、compile、兩次 `unchanged` replay 與
diff check 通過。

本輪只準備 Owner Gate。`governance_overlay_materialized=false`、`rhb_t6_authorized=false`；challenge
shortfall 16 會帶到未來 owner review，不能因 proposal 自動消失。下一步需要 owner 明確批准 proposal，
之後才能實作 versioned overlay；即使 overlay 完成，RHB-T6 labeling 還需要另一個獨立批准。

## 2026-10-05 — RHB-T6 readiness：發現 matched permission 與 authority admission 雙重 blocker

### 新執行了什麼，解決什麼問題

本輪沒有直接開始 60 筆 owner labeling，而是新增 deterministic、read-only 的 RHB-T6 readiness。
Validator 會重播 private RHB-T5 query pack、重新驗證 T1/T3、確認 CAR-T6 20-record authority checksum
與 Gate、檢查 labels/held/authorization 都尚未出現，並輸出 hash-bound report。這回答了「已有 60 筆
query 與 20 筆 authority，是否可以直接進 owner labeling」：目前不可以，而且原因不是程式跑不起來，
而是兩個來源治理 contract 尚未對齊。

第一個 blocker 是 60 筆 query 全屬 `human-labeled-real-noisy-v1`，而 frozen T3 只允許這個來源產生
`ambiguous` 與 `no_match`；所需 matched 為 20，但 source-permitted matched capacity 是 0。第二個
blocker 是 CAR-T6 的 20 筆 authority 使用 Wiki pilot evidence；CAR workflow 後來透過 owner review
接受它，但舊 RHB T1/T3 仍把同一來源標成 exact authority 的 `prohibited/staging_only`。此外五種
provisional challenge shortfalls 合計仍為 16。因此 readiness 是
`blocked_before_owner_gate`，不是 RHB-T6 authorization。

### 代碼修改了哪一部分、原因與決策

新增 `representative_benchmark_label_readiness.py`、CLI 與六個直接測試。Readiness 沒有讀取 resolver
output、既有 human labels 或 split，也不建立任何 label；它只使用 query pack contract、source
permission metadata、CAR authority metadata 與 artifact existence。選擇先做可執行 readiness，而不是
直接建立 proposal/labels，是因為 source permission 與 authority admission 都是 owner governance，不能
由程式碼延伸先前授權。

整合時也發現一個 cross-contract bug：RHB-T5 pack 正確寫成由
`fresh_output_blind_independent_agent` 撰寫，但既有核心 `validate_query_pack()` 只接受
`project_owner`；RHB-T5 builder 又直接使用 Pydantic model，繞過了 cross-artifact validator。如果不
修，RHB-T6 的 `validate_labels()` 會在任何 label 之前拒絕整包 query。

修正方式不是放寬成任意作者，而是只在「local-only + Human query source」同時成立時接受固定 agent
role；public、其他來源與任意作者仍 fail closed。RHB-T5 builder 也改成必須呼叫核心
`validate_query_pack()`。這個選擇保留 truthful provenance，同時關閉 schema-valid 但 governance-invalid
的繞過路徑。

### 技術棧／方法選型與目前決策

延續 Python 3.12、Pydantic strict contracts、canonical JSON SHA-256 與 pytest。Readiness 不寫 JSON
artifact，而由 CLI 重現，避免把尚未核准的 Gate 狀態誤當 frozen dataset。真實 readiness hash 為
`b4bf8f9a45b315a2ad64ba9f5626daef63a246c66bbbfc884856b7945e1b9f45`；query pack 仍是 60 筆且
`representative_pilot=false`，label artifact count 為 0，`rhb_t6_authorized=false`。

下一步只能準備 versioned source-decision／authority-admission repair proposal，交由 owner 審核是否讓
Human query 在「必須綁定獨立 CAR authority」的條件下產生 matched label，以及是否把 CAR Wiki
revision 以明確限制接納為該 bundle 的 authority evidence。不能直接修改既有 T1/T3、不能先建立
labels，也不能進 RHB-T7 或 resolver evaluation。

驗證方面，全部 118 個 representative-benchmark tests 通過；Ruff、format、四個相關 source/CLI 的
strict MyPy、compile、query-pack `unchanged` replay 與 diff check 都通過。完整 repository regression
另外執行約 2.5 分鐘，在顯示 5% checkpoint 與其後進度都沒有 failure；因 Lite mode 且無關的
model/evaluation 測試耗時很長而手動停止，所以本輪不宣稱新的 full-suite PASS。

## 2026-10-04 — RHB-T5：完成 60 筆 output-blind authoring artifact，但如實保留 coverage blocker

### 新執行了什麼，解決什麼問題

本輪依 owner 的精確批准，在一個新的獨立 agent 中執行 RHB-T5。該 agent 只能讀取 Git-ignored 的
query-only projection，不能讀 mixed raw source、resolver output、human labels、failure categories 或
split。它建立 60 筆 non-synthetic query pack：query、opaque source reference 與 evidence event 都是
60/60 unique，並形成 53 個 provisional family groups。Raw pack、owner authorization 與 authoring
input 都留在 local-only；Git 只保存 aggregate manifest。

這解決了「如何使用真實 noisy query，又不讓既有 pipeline output 或 human answer 汙染測試題目」的
核心問題。不過它也發現資料本身尚不足以完成所有 hard-case coverage：year、color、series、identifier
與 unknown-to-catalog 分別仍短缺 3、3、4、2、4 筆。因此本輪交付是有效的 provenance/authoring
artifact，不是已完成的 representative benchmark；RHB-T6、RHB-T7 與 resolver evaluation 都沒有開始。

### 代碼修改了哪一部分、原因與決策

新增 `representative_benchmark_query_authoring.py` 與 CLI，把 owner authorization、T1/T3 permission、
projection hash、authoring timestamp、60 筆唯一性、evidence grouping、private permissions、public
aggregate schema 和 atomic write 都變成 executable contract。選擇 Pydantic `extra=forbid` 與
checksum binding，是因為僅靠文件提醒無法阻止未知欄位、舊授權或來源 drift；選擇 temp file + fsync +
atomic replace，是為了避免 private pack 已更新、public manifest 卻仍是舊版的半完成狀態。

QA 首輪另外抓到兩個重要問題：query text 無法證明 `unknown_to_catalog`，而
`same_casting_different_release` 不能只靠單一 family row 宣稱；tracked code 也不應保存 verbatim owner
response。最終重新選擇「provisional surface tags + explicit shortfalls」方法：禁止 T5 推論
unknown-to-catalog、same-casting tag 必須至少有兩筆同 family、public side 只留 owner authorization
hash。這比為了湊四筆而猜標籤更符合 benchmark 的可信度目的。

同時調整 pre-authoring readiness lifecycle：一旦偵測 private Owner Gate，readiness 會在載入 mixed
source 前立即關閉，避免已完成授權後仍把舊 readiness 當作可重複啟動 authoring 的通行證。歷史
pre-authorization 測試則在隔離 fixture 中重建，保留 fail-closed regression coverage。

### 技術棧／方法選型與驗證結果

沿用 Python 3.12、Pydantic strict models、canonical JSON SHA-256 與 pytest，因為這與既有 RHB/CAR
artifact contract 相容，也能讓本機 private workflow 完全 offline、可重播。Private directory/file
權限為 `0700/0600`，public manifest 為 `0644`；private pack SHA-256 為
`97f7f0dd61cf619bb16b198778356d8ef53c7a504086f11542922f90706a858a`，public manifest file SHA-256
為 `8f2927a8f4f318d073793d161c310e319b6ac656c63e2cb20ef60565c1b31949`。

全部 112 個 representative-benchmark tests 通過；Ruff、format、strict MyPy、compile 與 diff check
通過，builder 連續兩次回傳 `unchanged`。Git-ignore 正向命中三個 private RHB-T5 檔案，且 Git 明確
拒絕把 private query pack 視為 tracked file。這些結果只證明 authoring pipeline 的工程與隱私品質；
因 challenge data Gate 尚未通過，沒有宣稱 real-marketplace accuracy 或代表性 benchmark 完成。

## 2026-10-04 — RHB-T5 pre-authoring repair：安全投影完成，readiness 升級為可送 Owner Gate

### 新執行了什麼，解決什麼問題

前一步 readiness 證明有 91 筆可用 query，卻同時發現原始列混放 pipeline output、human labels 與
failure categories，且 local-only 資料的預定輸出路徑會進 Git；此外 `BenchmarkQuery` 在 RHB-T5
就要求填入應由 RHB-T7 決定的 split。本輪完成三項修復，但沒有開始 60-case authoring。

新增 deterministic query projection：由程式只讀 `case_id` 與非空 `initial_name`，輸出 91 筆
`source_record_ref + query`，10 筆空 query 排除，重複數為 0。真實 materialization 回傳 `created`，
接著 check replay 回傳 `unchanged`。Private directory/file 權限為 `0700/0600` 且確實被 Git ignore；
public manifest 只含 schema、SHA-256、筆數、安全 aggregate 與 summary，沒有 row-level query。

### 代碼修改哪一部分、原因與選型

新增 `representative_benchmark_query_projection.py` 與 CLI，把「清除欄位」從人工操作改成 strict
Pydantic contract。Row model 採 `extra=forbid`，所以即使未來有人誤塞 `pipeline_outputs` 或
`human_label_*` 也無法通過。兩個輸出先寫 temp、fsync，再 atomic replace；第二次 replace 故障會
移除第一個已安裝檔，避免 private/public 只有一半完成。

同時從 `BenchmarkQuery` 移除 `split`，並修改 `validate_split`：T5 query 只保存 family/evidence group，
RHB-T7 的 `SplitArtifact` 才保存 Development/Test。這個選擇比把 split 設為 optional 更嚴格，因為
authoring artifact 若提前帶 split 會直接因 unknown field 被拒絕，而不是默默接受可能的人為 Test
selection。Requirements、design、tasks 與資料契約 README 一併回寫 local/private 路徑。

### 驗證結果與仍保留的邊界

Projection SHA-256 為 `d5712684cf73c29dd9ea7f385f78c03eb1c8300ce35afd477c0d09ad0d9032dd`。
Readiness v2 重新驗證投影、manifest、權限、ignore rule、CAR-T6 20/7/0、91/60 容量與 artifact
absence，結果為 `ready_for_separate_owner_authorization`，hash 是
`5b2582049420406f0acf5577bcca17f22f0834e598e87838c294625cdf300d30`。

Projection/readiness/RHB/CAR 全套 representative regression 共 99 tests 全數通過；四個 benchmark
核心模組的 Strict MyPy 為 0 issues，Ruff、format、compile 與 diff check 通過。Projection 連續兩次 check 都是
`unchanged`，readiness v2 連續兩次輸出 byte-identical；private projection 不在 `git ls-files`，且
由 dedicated ignore rule 命中。Public manifest 只保留核准的五個 aggregate 頂層欄位；模擬 fresh
clone 只有 tracked manifest、沒有 private projection 時，builder 只重建私有檔且不改 public bytes。

這個狀態不是 RHB-T5 authorization。仍有兩個 blocker：必須取得 fresh explicit Owner Gate，以及
必須在新的 output-blind context 中 author。現在這個檢查／建置 context 已接觸過來源 schema，不得
用來挑選 60 筆或寫 challenge tags；query pack、labels、resolver/RAG/embedding、Pointwise/Listwise
評估都仍未執行。

## 2026-10-04 — RHB-T5 readiness：60 筆容量足夠，但 output-blind 邊界尚未通過

### 新執行了什麼，解決什麼問題

本輪在不建立 query pack、不建立 labels、也不執行 resolver 的前提下，完成 RHB-T5 authoring
readiness 驗證。新的 read-only validator 重新驗證 T1 inventory／manifest、T3 source decisions、
Wiki revision binding、CAR-T6 versioned authority PASS 與歷史 RHB-T4 blocked checkpoint，並確認
目前沒有任何提前產生的 T5/T6 artifact。這解決了「CAR-T6 已通過後，是否可以直接開始寫 60 筆
query」這個問題：答案是資料數量可以，但流程安全邊界還不可以。

實測 101 筆人工資料中有 91 筆 nonblank 且 case-insensitive unique 的真實 query，對 60 筆目標的
shortfall 為 0；CAR-T6 仍是 20 exact variants、7 qualifying families、0 shortfalls。因此阻礙不是
資料不足，而是 output blindness、publication scope、phase sequencing 與獨立 Owner Gate。

### 代碼修改了哪一部分，以及為何這樣決定

新增 `representative_benchmark_query_readiness.py` 與獨立 CLI，把 readiness 做成可重跑、hash-bound
且完全 read-only 的檢查，而不是用文件人工宣稱「看起來可行」。Validator 會對 human source raw
SHA-256、source permission、CAR-T6 authority hash、historical checkpoint hash、20/4 composition、
query/label absence 與 `BenchmarkQuery.split` 是否仍為 required 逐項 fail closed。這種做法讓未來
任何 source drift、authority tamper 或提前寫入 query/label 都會直接讓 readiness 失敗。

沒有在本輪直接修改 query schema 或生成乾淨資料，是因為驗證先找到了三個相互關聯的 contract
問題，需要作為下一個明確 implementation slice 一起修：原始人工列把 query 與 pipeline output、
human label、failure category 放在同一物件；T3 只允許 raw query local-only，但既有 task 卻規劃
tracked `query-pack.json`；而 query model 在 T5 就要求 `split`，與 RHB-T7 才做 family-safe split 的
規格衝突。先留下可重現 blocker，比填入假 split 或把 local-only rows 推上 Git 更正確。

### 技術棧／方法選型與驗證結果

延續專案既有 Python 3.12 + Pydantic strict-contract 方法，readiness report 拒絕 unknown fields、固定
blocker ordering 並以 canonical JSON SHA-256 綁定。來源解析額外拒絕 duplicate JSON keys；程式只依賴
既有 benchmark contracts 和 filesystem read，不依賴 FastAPI、resolver、network/browser 或模型。
Focused tests 共 6 個全數通過，覆蓋 deterministic/read-only replay、human source hash tamper、CAR-T6
authority tamper、premature query artifact、CLI hash reproduction 與 runtime/network dependency guard。
連同 76 個相關 RHB/CAR contract regression 為 `82 passed`。Strict MyPy 對三個 benchmark 核心模組
為 0 issues，Ruff/format/diff check 通過；完整 repo 回歸執行至 10% 未出現 failure，但因無關的既有
長時間 evaluation tests 而手動停止，因此本輪不宣稱新的 full-suite PASS。真實 readiness hash 是
`9a2f5491a6c22c097eaf8bd913c53a46dab71068b1484906f91c48f7b030c840`。

### 下一步與未授權範圍

下一步只做 pre-authoring safety repair：建立只含 opaque reference + raw query 的 Git-ignored
projection contract、把 raw local-only query pack 與 public aggregate manifest 分離，並把 split 從
T5 query contract 延後到 RHB-T7 `SplitArtifact`。完成並重跑 readiness 後，才向 owner 提出獨立
RHB-T5 Gate。本輪沒有批准 RHB-T5；challenge coverage、duplicate evidence grouping、60-case selection、
labels、resolver output、RAG/embedding/listwise/pointwise 評估全部仍未開始。

## 2026-10-04 — CAR-T7 收尾：CAR-R1–R11 全數驗收，分開呈現工程與資料結果

### 新執行了什麼，解決什麼問題

CAR-T6 已讓 versioned RHB-T4 通過，但專案還缺最後一層「面試官可以直接核對」的總驗收。本輪
完成 CAR-T7：把 CAR-R1～CAR-R11 逐條連到 source decision、catalog review、private packet、
append-only events、CAR-T5F bundle、CAR-T6 re-audit、tests 與 evidence，並把 `review.md` 最上方從
容易誤讀的早期 CAR-T1 FAIL 改成 current milestone verdict。早期 FAIL 與 repair PASS 沒有刪除，
而是保留為後續修正確實發生過的 audit history。

最終結論刻意分成三層：Engineering PASS 代表 contracts、權限、privacy、atomicity、determinism
與文件通過；Data Gate PASS 代表 20 exact variants／7 qualifying families／0 shortfalls；Downstream
CLOSED 則代表 RHB-T5/query/labels 仍未授權。這避免把「已有可靠 authority input」誇大成「已有
real-marketplace accuracy 或 benchmark readiness」。

### 代碼／文件修改與選型原因

本輪沒有修改 resolver、RAG、embedding、API 或 authority product code。主要修改是 final QA
matrix、technical evidence、AI-eval failure rubric、README/Portfolio Guide 的 scoped claims，以及
requirements/design/tasks 的完成狀態。選擇在 `review.md` 新增 current section、而不是重寫舊內容，
是因為 CAR-T1 初次 QA 曾真的找到 permissive schema 與 attribution bypass；保留 FAIL→repair→final
PASS 比只留下漂亮結果更能展示規格驅動閉環。

Portfolio claim 新增的是 20／7／0 與雙 Owner Gate、output-blind、versioned historical audit；沒有
新增 accuracy 百分比，也沒有把 community-reference exact 說成 manufacturer truth。AI eval 明確
把 invented evidence、model-derived truth、privacy leak、hidden conflict、false second reviewer 與
exaggerated benchmark readiness 列為失敗條件。

### 驗證結果、發現與決策

Focused authority/CAR-T6/historical-RHB suite 為 317 tests 全數通過。前一步 final code/data tree 的
完整 repository suite 為 1,379 tests 全數通過，只有既有 Starlette/AnyIO deprecation warning。
Source Gate=`valid`，CAR-T6 與 historical RHB checks 都回傳 `unchanged`；Ruff、format、production
strict MyPy、compileall、critical JSON parsing、privacy 與 diff checks 通過。

QA 主動把 strict MyPy 範圍擴大到所有舊 authority tests 時，找到三個 test modules 共 22 個既有
diagnostics，主要是測試存取 module internals 與用字串索引 enum-keyed dict。因 317 runtime tests
全綠、九個 production/CLI modules 加 CAR-T6 test 的正式 strict scope 為 10 files／0 issues，這些
被記為非阻斷 test-type debt，而沒有被誤報成 repository-wide strict PASS。這是未來若要把 tests
納入全域 type Gate 時應先清理的項目。

### 下一步

CAR v1 在 Lite／Lean Industrial 範圍內完成。下一個產品資料里程碑是 RHB-T5 output-blind query
pack，但它仍需要新的明確 owner authorization；在此之前不建立 queries/labels，也不執行或宣稱
代表性 benchmark、resolver quality 或 production accuracy。

## 2026-10-04 — CAR-T6 完成：versioned RHB-T4 通過，RHB-T5 仍關閉

### 新執行了什麼，解決什麼問題

在 owner 明確只批准 CAR-T6、並排除 RHB-T5/query pack/labels 後，本輪把 CAR-T5F frozen
authority bundle 正式交給新的 versioned RHB-T4 re-audit。首次 materialization 回傳 `created`，
之後兩次真實 check replay 都回傳 `unchanged`。新 authority 共有 20 筆 unique
`approved_exact` UUID、7 個 qualifying multi-release families、0 exact/family shortfalls，因此 Gate
結果為 `passed_exact_authority_gate`。

這解決了 CAR-T5F 之後仍只有「可以重新稽核」、尚未有獨立 RHB 判定的問題。同時沒有改寫原本
0-record、`blocked_insufficient_exact_authority` 的 RHB-T4 checkpoint；舊結果描述當時沒有 exact
authority 的事實，新結果描述 CAR-T5F 之後的證據狀態，兩者都保留才有完整 audit trail。

### 代碼與資料修改、決策原因

本次沒有改 resolver、embedding、RAG、API 或 ranking code，而是由已驗證的 CAR-T6 builder 原子寫入
三個狀態：ignored private owner authorization、public versioned authority、public versioned manifest。
私密檔保存 exact response 並使用 `0600`；公開檔使用 `0644`，只保存不可逆 authorization hash、
authority rows、輸入 hashes、composition 與 Gate boundary。這個設計讓 GitHub 可以展示可重現證據，
又不把 owner verbatim 當成公開資料。

新 public authority/manifest 的 raw SHA-256 分別為 `72c11aeb…3117` 與 `dfb71d8f…6862`。
manifest 同時固定舊 authority/manifest 的 raw SHA-256 `f0a9fe00…1af` / `10c38740…f7d`，並記錄
`preserved_without_overwrite=true`。選擇 versioned append 而不是覆寫的原因，是 audit 結果必須與
產生它的證據時間點一起保存；直接修改舊 JSON 會讓履歷 reviewer 無法重現當時為何正確 blocked。

### 技術驗證、邊界與下一步

CAR-T6 建立後兩次 replay 均為 `unchanged`；舊 RHB-T4 builder 再跑兩次也都是 `unchanged`。
CAR-T6、歷史 audit 與 CAR-T5F 的 post-materialization focused regression 為 21 tests 全數通過，
其中包含不依賴 private owner text、直接驗證 checked-in public authority/manifest 的測試。
完整 repository regression 為 1,379 tests 全數通過，只有既有的 Starlette/AnyIO deprecation
warning。Privacy scan 另外發現測試 fixture 曾使用與本次真實批准相同的句子；已改成明確的
`TEST-ONLY` 英文 response，之後在 final tree 重跑 CAR-T6 與 source-binding suites，48 tests
全數通過。真實 owner verbatim 在 private directory 以外為 0 hits。
權限確認為 private `0600`、public `0644`，exact response 不存在於兩個 public artifacts，private
path 由專用 `.gitignore` 規則命中。整個 audit 的 resolver output、benchmark labels、network
requests 都是零，color/edition 仍為 null。

下一個可能的 benchmark 階段是 RHB-T5 output-blind query-pack authoring，但本次授權明確不包含它。
因此目前只記錄 `next_allowed_step=owner_gate_rhb_t5_separate_authorization_required`；在新的 owner
decision 前，不建立 query pack、labels，也不宣稱 resolver、RAG、embedding 或 ranking quality。

## 2026-10-04 — CAR-T6 readiness：保留舊 blocked audit，準備新的 versioned RHB-T4 re-audit

### 新執行了什麼，解決什麼問題

CAR-T5F 已經封存 20 筆 exact authority，但這不等於舊的 RHB-T4 可以直接改寫成 PASS。本輪新增
CAR-T6 readiness：把 CAR-T5F bundle 當成新證據重新稽核，同時將 2026-09-27 的 RHB-T4
`0 exact / 0 family / blocked` 結果視為不可覆寫的歷史 checkpoint。這解決了兩個衝突：專案需要讓
新的 authority 進入 benchmark Gate，又不能抹掉「當時確實沒有 authority」的可追溯證據。

readiness 在真實 repo 重新驗證 CAR-T5F private authorization、public bundle/manifest、140-row
catalog-v2、40-event review chain、每筆六個 supported fields、null color/edition 與 20/4 composition。
結果為 20 個 unique exact UUID、7 個 qualifying families、0 shortfalls；因此只在記憶體中提出新的
`passed_exact_authority_gate`。本輪沒有寫入 CAR-T6 authorization、新 authority 或 manifest，也沒有
建立 query pack、labels 或開始 RHB-T5。

### 修改了哪一部分，為何這樣決定

新增 `representative_benchmark_reaudit.py` 與對應 CLI，把 readiness、fresh owner authorization、
versioned manifest、atomic three-file install、check replay 和 rollback 放在獨立模組，而不是改動舊
RHB-T4 builder。輸出名稱刻意使用 `canonical-authority-reaudit-v1`：舊檔代表一個已完成且誠實的
歷史判斷，新檔才代表 CAR-T5F 之後的新判斷。這比 in-place migration 更適合履歷專案，因為 reviewer
可以同時看到資料不足時的 fail-closed 行為與後續取得證據後的可重現演進。

授權設計延續兩份 exact-response binding：只有明確同時提到 CAR-T6、versioned RHB-T4 re-audit，
並排除 RHB-T5、query pack 與 labels 的新 response 才能寫檔；「繼續下一步」會失敗。Owner verbatim
只允許存在 ignored private artifact，public manifest 只保留不可逆 hash。三檔先寫 temp，再逐一
replace；中途失敗會還原或刪除已安裝檔案，避免 authorization、authority、manifest 只出現其中一部分。

### 技術驗證與選型結果

測試先發現 manifest 在 hash 前保留 Python `datetime`，無法用穩定 JSON 序列化；已改為 whole-second
UTC ISO-8601 字串後再計算 hash。Focused suite 6 tests 通過；連同歷史 RHB-T4、CAR-T5F freeze 與
source binding 的 61-test regression 也通過；完整 repository regression 為 1,378 tests 全數通過，
只有既有的 Starlette/AnyIO deprecation warning。舊 RHB-T4 builder 連續兩次 `--check` 都回傳
`unchanged`。負向案例涵蓋 generic continuation、response mismatch、stale catalog、unsafe partial
state 與第二次 replace 故障；隔離環境的 authorized path 則得到 `created / unchanged / unchanged`，
並驗證舊 audit bytes 不變、私密文字未進 public artifacts。

### 下一步

下一步仍是獨立 Owner Gate：若 owner 明確批准 CAR-T6，才在真實 repo 建立 versioned RHB-T4
authority 與 manifest。該批准不包含 RHB-T5；即使 re-audit 成功，query pack 與 labels 仍需下一個
獨立決策。

## 2026-10-04 — CAR-T5F 完成：封存 20 筆 exact authority，停在 RHB-T4 re-audit 前

### 新執行了什麼，以及解決了什麼問題

在取得只限 CAR-T5F 的 fresh owner authorization 後，本輪將已驗證的 T5-G1/T5-G2 event chain
封存成 public `approved-authority.json` 與 `authority-manifest.json`。初次執行回報 `created`，接著
兩次使用 private ledger 內的原始授權做真實 check replay，均回報 `unchanged`。

最終 bundle 有 20 筆 `approved_exact`、20 個 distinct canonical UUID、七個 qualifying families
與零 shortfall，manifest 結果為 `eligible_for_rhb_t4_reaudit`。這解決了「資料已逐筆批准，卻還
沒有可交給下游獨立稽核的固定 authority artifact」問題；它沒有把 CAR-T5F 擴張成 RHB-T4 PASS。

### 代碼／資料修改了哪一部分，以及原因

本輪主要變更是資料狀態：exact owner response 寫入 Git-ignored private authorization，public Git
只新增 20-record authority bundle 與 safe manifest。Manifest 綁定 11 個 parent artifacts，包含
packet、candidate/event state、T5-G1/T5-G2 private ledgers、catalog、source decisions 與 CAR-T5F
authorization hash；公開檔沒有 owner verbatim 或 private identity。

另外調整四個 authority test fixtures。原因是這些測試原本直接複製真實 `data/` 來模擬
CAR-T5P、T5-G1、T5-G2 或 pre-freeze 狀態；bundle 正式 checked in 後，如果不明確移除三個
freeze outputs，早期階段測試會被後期真實狀態污染。Fixture 現在只在 temporary repository
移除 outputs，真實 bundle 完全不變。這個設計保留歷史階段的隔離測試，而不是讓測試依賴當前
專案走到哪個 Gate。

### 技術與安全決定

採用 private authorization + public irreversible hash，而不是把批准原文放進 manifest，是為了
同時保留 owner accountability 與 Git privacy。三個輸出使用 atomic transaction，因此 private
authorization、bundle、manifest 不會只成功其中一部分。Bundle 不複製完整產品文字，只保存
candidate/UUID/family/release identity、latest event、catalog-record hash、source decision 與 evidence
hashes，足以稽核又減少公開資料面。

### 驗證結果

真實 bundle 驗證確認 20 distinct UUID、七個 qualifying families、11 個 parent hashes、零 shortfall，
CAR-T6/RHB-T5 都是 false。權限為 private directory `0700`、private authorization `0600`、public
outputs `0644`，且 private path 通過 `git check-ignore`。Public bundle/manifest 未找到批准原文。

Materialization 後受影響的 suites 共 168 tests 全數通過：CAR-T5F 7、preparation 23、T5-G1 71、
T5-G2 26、source binding 41。最終 post-materialization 全 repo regression 為 `1372 passed,
1 warning`，唯一 warning 仍是既有 Starlette／AnyIO deprecation。Ruff/format、source/tasks hash
binding 與 diff check 通過；830 個 tracked/unignored files 對包含本次授權在內的 25 種 private-
response variants 做掃描，結果為 0 hits。

### 下一步與未授權範圍

下一步是另行批准 CAR-T6，執行新的、versioned RHB-T4 re-audit。該 audit 必須獨立重驗 permissions、
hashes、field evidence、owner metadata、blindness、privacy 與 20/4 composition，CAR-T5F 不能強迫它
PASS。CAR-T6、CAR-T7 與 RHB-T5 本輪均未執行；也沒有建立 benchmark query/label 或宣稱 resolver、
RAG、embedding、listwise/pointwise 品質。

## 2026-10-04 — CAR-T5F readiness：完成 freeze 路徑，但不代替 Owner Gate

### 新執行了什麼，以及解決了什麼問題

T5-G2 完成後，資料已是 20 exact／0 reviewed／0 staged，但專案只有 authority bundle 的資料
契約與單元驗證器，沒有一條能把真實 T5-G1/T5-G2 event state 安全封存的執行路徑。本輪新增
CAR-T5F readiness 與 freeze builder：先重建 frozen preparation packet，再驗證七個 T5-G1、七個
T5-G2 authorizations、40 個 events、40 個 private attestations、20 個 latest-event links 與所有
catalog/evidence hashes，最後重新計算 20/4 composition。

真實 readiness 結果是 20 個 distinct exact variants、七個 qualifying families、零 variant/family
shortfall，proposed Gate result 為 `eligible_for_rhb_t4_reaudit`。但本輪沒有建立 freeze
authorization、`approved-authority.json` 或 `authority-manifest.json`；原因是一般的「繼續下一步」
不是規格要求的獨立 CAR-T5F owner decision。

### 代碼修改了哪一部分，原因與方法選擇

新增 `canonical_authority_freeze.py`，將 readiness 與 materialization 分成兩條明確路徑。Readiness
只在記憶體建立預期的 20 筆 bundle records，逐筆核對 UUID、catalog record hash、family/release、
latest event 與六個 distinct evidence hashes，不留下任何授權或 bundle 檔案。Freeze 路徑則要求
fresh exact response 明確包含 CAR-T5F、authority bundle，以及 CAR-T6/RHB-T5 不授權邊界；並拒絕
重用 T5-G1/T5-G2 response、模糊 continuation 或前後不一致的 response。

另外新增獨立 CLI，讓 `--readiness` 無法與任何 freeze 參數併用。未來取得授權後，owner verbatim
只寫入 Git-ignored private workspace；tracked bundle/manifest 只保留不可逆 authorization hash、
record identity、evidence hashes、counts 與 family composition。三個輸出採 temp validation、fsync、
atomic replace 與 rollback，避免只寫入其中一部分就留下錯誤 Gate 狀態。

### 為何採用這個設計

把 readiness 與 freeze 拆開，是為了同時滿足兩件看似衝突的需求：工程可以先驗證所有 parent
與 composition，不必每次等人工才發現程式問題；但工程準備完成又不能被誤解為人已批准資料
Gate。Fresh response、private/public split 與 fail-closed atomic install 讓授權、資料正確性和檔案
落地成為三個可獨立查證的層次，也讓後續履歷展示能清楚說明 human-in-the-loop governance。

### 驗證與修正

新 focused suite 為 `7 passed`，完整 authority regression 為 `303 passed`，涵蓋 read-only
readiness、模糊授權拒絕、response mismatch、真實 20/7 freeze/replay、stale state、atomic
rollback 與 CLI。全 repo regression 為 `1372 passed, 1 warning`，唯一 warning 仍是既有
Starlette／AnyIO deprecation；Ruff、format、strict MyPy、compileall 與 diff check 通過。針對
17 種 private-response variants 掃描 826 個 tracked/unignored files，結果為 0 hits。第一次真實
readiness 因本機 `data/catalog.json` 採較嚴格的 `0600` 而被誤判；修正後公開輸入接受安全的
`0600` 或 `0644`，但新 tracked outputs 仍固定寫成 `0644`。這是權限策略相容性修正，不是放寬
private artifacts；private directory/inputs 仍強制 `0700/0600`。

完整 regression 後又補上「bundle 已 materialize 時 readiness 必須拒絕並導向 check mode」及
既有輸出權限驗證；這個 bounded hardening 完成後，七個 focused tests 已再次全數通過。

### 下一步與仍受限的範圍

下一步仍是獨立的 CAR-T5F Owner Gate。只有 owner 明確授權 freeze validated event chain 與
authority bundle（若 composition 不足則發布 exact shortfalls），並明確排除 CAR-T6/RHB-T5，才會
在真實 repo 寫入 bundle。本輪不代表 RHB-T4 re-audit 已通過，也沒有執行 CAR-T6、CAR-T7 或
RHB-T5。

## 2026-10-03 — T5-G2 Batch 7：Mazda MX-5 Miata 兩筆追加，T5-G2 達到 20 exact／0 reviewed

### 新執行了什麼，以及解決了什麼問題

本輪在完整 Batches 1–6 prefix 已記錄並重播驗證後，取得新的、只限 T5-G2 Batch 7 的
owner decision，將 Mazda MX-5 Miata 的 packet ordinals `9`、`15` 由 `reviewed` 推進為
`approved_exact`。兩個 toy identifiers 是 `HYW18`、`HYX57`，六個 supported fields 都只依據
frozen community snapshot，`color` 與 `edition` 維持 null。

這一步完成 T5-G2 最後兩筆狀態轉移：候選清單現在是 20 exact／0 reviewed／0 staged，
七個 family batches 各有獨立、fresh 且不重用的 T5-G2 response hash。解決的核心問題是讓
「20 筆都已有 exact outcome」成為可重播的資料狀態，而不是用一個批次總數或單一通用授權代替。

### 代碼修改了哪一部分，原因與方法選擇

這次不需要再修改 recorder 程式，而是使用上一階段已經過完整 regression 的 Batch 7 path。
私有 ledger 追加第七個 T5-G2 authorization 與最後兩個 owner attestations，並維持 `0700`／
`0600` 權限與 Git ignore。公開 Git 只更新 `authority-candidates.json` 與 `review-events.json`
中的 hash-bound links，沒有放入授權原文或 private identity。

公開狀態新增兩個 `reviewed -> approved_exact` events，全部 38 個先前 events 與 18 個非目標
candidate objects 都以穩定 identity 比對保留。現在共有 14 個 authorization links、40 個
attestation links、40 個 public events 與 20 個 candidate latest-event links。這些完成的是 T5-G2
event state，不是 CAR-T5F authority bundle。

### 驗證方式與結果

首次 materialization 回報 `created`，後續兩次真實重播都回報 `unchanged`。寫入後
T5-G2 focused suite 為 `26 passed`。寫入前 readiness 的完整 repository 為 `1365 passed,
1 warning`，且本次範圍的 Ruff、format、strict MyPy、compileall 與 diff check 全數通過；
唯一 warning 仍是既有 Starlette／AnyIO deprecation。

最終 821 個 tracked／unignored 文字檔對 17 個 private-response variants 做 privacy scan，結果是
0 hits。Private/public permissions、ignore rules、14 個 fresh response hashes、Mazda 六欄 values、
forbidden-bundle absence 與 RHB-T5=false 全部通過。寫入後沒有重跑完整 suite，因為這次是通過已驗證
recorder 的 state append；專用套件與真實重播均已重新執行。

### 留下的邊界與下一步

T5-G2 的七批、20 筆 exact outcomes 已全部完成，但這不會自動建立 authority bundle。
下一個合法步驟是另行取得 CAR-T5F 授權，再重新驗證全部 parent hashes、event chains、
permissions、privacy 與 20/4 composition，然後封存 safe tracked authority bundle 或公開 exact shortfalls。
CAR-T6 與 RHB-T5 仍是之後的獨立 Gates，本輪沒有授權。

## 2026-10-03 — T5-G2 Batch 6：Morgan Super 3 三筆追加，累積 18 exact／2 reviewed

### 新執行了什麼，以及解決了什麼問題

本輪取得新的、只限 T5-G2 Batch 6 的 owner decision 後，將 Morgan Super 3 的
packet ordinals `6`、`12`、`19` 由 `reviewed` 推進為 `approved_exact`。三個 toy
identifiers 是 `HYX48`、`HYW13`、`HYY33`，六個 supported fields 都只依據 frozen
community snapshot，`color` 與 `edition` 維持 null。公開狀態從 15 exact／5 reviewed
變為 18 exact／2 reviewed／0 staged，而 Mazda MX-5 Miata 兩筆仍保持 `reviewed`。

這一步解決的問題是在 Batch 6 準備與 Batch 7 準備已同時完成的情況下，系統仍必須只消費
Batch 6 自己的授權。Recorder 先驗證完整 Batches 1–5 prefix，再把授權綁定到 Morgan 三筆；
Batch 7 沒有獨立 response，所以不會因「路徑已就緒」被預先寫入。

### 代碼修改了哪一部分，原因與方法選擇

這次不需要修改 recorder 邏輯，而是使用已經通過 1365 項 regression 的 Batch 6 path。
私有 ledger 追加一個 Batch 6 authorization 與三個 owner attestations，保持 `0700`／
`0600` 權限並被 Git ignore；公開只更新 `authority-candidates.json` 與 `review-events.json`
中不含授權原文的 hash-bound 狀態。使用這個 private/public split，可以在不公開人類回覆的前提下，
讓 GitHub 上的每個 state transition 仍能被重播與對帳。

公開事件新增三個 `reviewed -> approved_exact`，全部 35 個先前 events 與 17 個非目標
candidate objects 均以穩定 identity 比對保留。現在共有 13 個 authorization links、38 個
attestation links、38 個 public events 與 20 個 candidate latest-event links。

### 驗證方式與結果

首次 materialization 回報 `created`，後續兩次真實重播都回報 `unchanged`。寫入後
T5-G2 focused suite 為 `26 passed`。寫入前 readiness 的完整 repository 為 `1365 passed,
1 warning`，且本次範圍的 Ruff、format、strict MyPy、compileall 與 diff check 全數通過；
唯一 warning 仍是既有 Starlette／AnyIO deprecation。

最終 819 個 tracked／unignored 文字檔對 15 個 private-response variants 做 privacy scan，結果是
0 hits。Private/public 權限、ignore rules、fresh response hashes、Morgan 六欄 values、forbidden-bundle
absence 與 RHB-T5=false 也全部通過。寫入後沒有重跑完整 suite，因為這次只是通過已完整
驗證 recorder 的 state append；專用套件與真實重播已重新執行。

### 留下的邊界與下一步

T5-G2 剩下最後兩筆 `reviewed` 資料：Mazda MX-5 Miata 的 `HYW18`、`HYX57`。Batch 7
readiness 已完成，下一步只需取得一份新的、只限 Batch 7 的 owner decision；Batch 6 回覆不能重用。
這次授權沒有完成 T5-G2，也不授權 CAR-T5F、CAR-T6 或 RHB-T5。

## 2026-10-03 — T5-G2 Batches 6–7 recorder ready，分別停在兩個 Owner Gates

### 新執行了什麼，以及解決了什麼問題

本輪一次將 T5-G2 bounded recorder 從 `[1,2,3,4,5]` 擴充為完整
`[1,2,3,4,5,6,7]` prefix。Batch 6 是 Morgan Super 3，packet ordinals `6`、`12`、`19`，
toy identifiers 為 `HYX48`、`HYW13`、`HYY33`；Batch 7 是 Mazda MX-5 Miata，ordinals
`9`、`15`，identifiers 為 `HYW18`、`HYX57`。五筆的六個 supported fields 均與 frozen
community snapshot 一致，`color` 與 `edition` 都是 null。

這一步要解決的不只是「讓 recorder 認得最後兩個 family」，而是同時保留決定的
先後關係：Batch 6 必須見到完整 Batches 1–5，Batch 7 又必須見到已合法記錄的 Batch 6。
因此可以在同一輪完成兩條 readiness，卻不會讓 Batch 7 跳過 Batch 6，也不會把一份模糊授權
複用給兩批。本輪沒有 materialize 任何真實 decision，狀態仍是 15 exact／5 reviewed／0 staged。

### 代碼修改了哪一部分，原因與方法選擇

`canonical_authority_exact_decisions.py` 的 frozen map 新增 Morgan Super 3 與 Mazda MX-5
Miata 的 family keys、ordinals 與 identifiers，supported prefix 擴充到 Batch 7，但 Batch 8 仍
fail closed。這次一次實作最後兩批，是因為兩批的 frozen packet、null-field boundary 與
欄位 contract 都已完整，可共用同一輪 regression；但決定邏輯仍保持兩個獨立 response hashes。

測試新增 Batch 6 與 Batch 7 的完整 append/replay、缺 predecessor 拒絕、六欄 values、
identifiers、舊物件保留與 CLI flows。Batch 6 的合成結果是 18 exact／2 reviewed，Batch 7 之後是
20 exact／0 reviewed；這些只是 `TEST-ONLY` evidence，不是真實決定或預先寣告 T5-G2 完成。

### 驗證方式與結果

T5-G2 focused suite 為 `26 passed`，完整 repository 為 `1365 passed, 1 warning`。本次範圍的
Ruff、format、strict MyPy、compileall 與 diff check 全數通過；唯一 warning 仍是既有
Starlette／AnyIO deprecation。真實 Batch 5 在擴充後的 recorder 下重播為 `unchanged`，
證明一次準備兩條後續路徑並未修改任何已有 decision state。

最終 817 個 tracked／unignored 文字檔對 12 份私有 Gate responses 及 Markdown 外框變體的
privacy scan 為 0 hits。私有 exact ledger 仍只有 Batches 1–5，authority bundle 不存在，
RHB-T5 仍是 false。

### 留下的邊界與下一步

下一步是兩個依序但獨立的 Owner Gates。先用新的 Batch 6 response 明確綁定 Morgan
Super 3 三個 identifiers、六欄 scope 與 null color／edition；記錄並驗證 Batch 6 後，再用另一份
不同的 Batch 7 response 綁定 Mazda MX-5 Miata 兩個 identifiers。兩段授權可在同一則使用者訊息中
分開呈現，但不能用同一段文字同時授權兩批。CAR-T5F、CAR-T6 與 RHB-T5 仍不在此 readiness 範圍。

## 2026-10-03 — T5-G2 Batch 5：'21 Ford Bronco 三筆追加，累積 15 exact／5 reviewed

### 新執行了什麼，以及解決了什麼問題

本輪在取得新的、只限 T5-G2 Batch 5 的 owner decision 後，將 `'21 Ford Bronco`
的 packet ordinals `5`、`7`、`17` 由 `reviewed` 推進為 `approved_exact`。首次
materialization 回報 `created`，公開狀態由 12 exact／8 reviewed 變為 15 exact／5 reviewed／
0 staged。三筆只核准 frozen community snapshot 支持的 casting、release year、series、
collector number、series position 與 toy identifier；`color` 與 `edition` 仍為 null。

解決的核心問題是將這份 owner decision 精確綁定到 Bronco 三個 identifiers、frozen
packet、catalog records 和六欄 evidence，而不是用一句模糊的「批准 Batch 5」改動狀態。
這使未來重播可以區分「同一決定」與「不同 Gate 或不同批次的文字」，後者會 fail closed。

### 代碼修改了哪一部分，原因與方法選擇

這次不需要再擴張 recorder 程式，而是使用前一階段已驗證的 Batch 5 bounded path。
私有 ledger 新增一個 batch authorization 與三個 owner attestations，並維持 `0700`／
`0600` 權限與 Git ignore；公開只改動 `authority-candidates.json` 與 `review-events.json`
內不含授權原文的 hash-bound 狀態。選擇繼續分離 private verbatim 與 public audit trail，是為了讓
GitHub 可展示完整可驗證鏈，又不公開人類授權原文。

公開狀態新增三個 `reviewed -> approved_exact` events，並保留全部 32 個先前 events
與 17 個非目標 candidate objects。現在共有 12 個 authorization links、35 個 attestation
links、35 個 public events 與 20 個 candidate latest-event links；不存在 authority bundle，
RHB-T5 仍未授權。

### 驗證方式與結果

首次寫入回報 `created`，後續兩次真實 `--check` 都回報 `unchanged`。寫入後 T5-G2
focused suite 為 `22 passed`。寫入前 readiness 的完整 repository 結果為 `1361 passed,
1 warning`，且本次範圍的 Ruff、format、strict MyPy、compileall 與 diff check 全數通過；
唯一 warning 仍是既有 Starlette／AnyIO deprecation。

一開始的歷史比對假設 public events 只會追加在 array 尾端，因此前 32 個位置比對回報
false；這不是資料被改動，而是 event file 會用 canonical order 重排。後續改用穩定 `event_id`
map 比對，證明 32 個舊 event objects 全部完全一致。這個修正選擇以 identity 比對，而不是固守
array position，因為前者才是 event contract 的穩定主鍵。

最終 815 個 tracked／unignored 文字檔對 12 份私有 Gate responses 以及新回覆去掉 Markdown
外框後的變體做 privacy scan，結果是 0 hits。寫入後沒有重跑完整 suite，因為這次只是通過
已驗證 recorder 的 state append；專用測試、真實重播、hash links、permissions 與 privacy 都已重驗。

### 留下的邊界與下一步

T5-G2 仍未完成，剩餘 5 筆 `reviewed` 資料：Batch 6 的 Morgan Super 3 三筆與 Batch 7
的 Mazda MX-5 Miata 兩筆。下一個合法步驟是先實作並驗證 Batch 6 bounded path，再由
owner 提供新的、只限 Batch 6 的 exact decision。這次授權不建立 manufacturer-certified
truth，也不授權 CAR-T5F、CAR-T6 或 RHB-T5。

## 2026-10-02 — T5-G2 Batch 5 recorder ready，停在 '21 Ford Bronco Owner Gate

### 新執行了什麼，以及解決了什麼問題

本輪將 T5-G2 bounded recorder 從 `[1,2,3,4]` 擴充為 `[1,2,3,4,5]` prefix。下一批是
`'21 Ford Bronco` 的 packet ordinals `5`、`7`、`17`，toy identifiers 為 `HYY32`、
`HYW73`、`HYX50`。三筆在 casting、release year、series、collector number、series
position 與 toy identifier 都和 frozen community snapshot 一致；`color` 與 `edition` 仍為 null。

這一步解決的問題是：即使 Batch 5 的資料表面上完整，也不能直接把三筆記成
`approved_exact`。系統必須先證明 Batches 1–4 是完整、連續且未被篡改的 prefix，再將
Batch 5 的 family、ordinals、identifiers 與 entry hashes 精確綁定。目前只完成這條安全路徑，
並沒有 materialize 任何 Batch 5 owner decision，真實狀態仍是 12 exact／8 reviewed／0 staged。

### 代碼修改了哪一部分，原因與方法選擇

`canonical_authority_exact_decisions.py` 的 frozen batch map 新增 `'21 Ford Bronco` 的 family
key、ordinals 與 identifiers，supported prefix 上限只擴為 Batch 5。繼續使用明確 frozen
map，而不是一次開放 Batches 5–7，是為了讓每批的 context、null-field boundary 與 owner
authorization 分開驗證；因此 Batch 6 仍會 fail closed。

測試新增完整 `[1,2,3,4,5]` append/replay，要求四批舊 authorizations、12 個舊
attestations/exact events 與 17 個非目標 candidate objects 全部保留；也覆蓋缺 Batch 4
時拒絕、Bronco 六欄 evidence values、三個 identifiers、CLI append 與五批 replay。
測試授權文字全是 `TEST-ONLY` 合成內容，沒有複製真實 owner response。

### 驗證方式與結果

T5-G2 focused suite 為 `22 passed`，完整 repository 為 `1361 passed, 1 warning`。本次修改
檔案的 Ruff、format、strict MyPy、compileall 與 diff check 全數通過；唯一 test warning
仍是既有 Starlette／AnyIO deprecation。合成 Batch 5 最終為 15 exact／5 reviewed、5 份
T5-G2 authorizations、15 份 T5-G2 attestations 與 35 個總 events。

真實 Batch 4 在新 recorder 下重播仍為 `unchanged`；813 個 tracked／unignored 文字檔對
四份真實 owner responses 的 privacy scan 為 0 hits。額外的 repo-wide Ruff 探索檢查揭露
245 個既有 lint 技術債，主要在舊 scripts、migrations 與 tests；因為不屬於 Batch 5 且大量
自動修改會擴大風險，本輪只記錄待辦，沒有順便重寫無關檔案。

### 留下的邊界與下一步

下一步是 Batch 5 Owner Gate：需要一份新的、明確綁定三個 Bronco identifiers、
snapshot-relative 六欄 scope、null color／edition 與 `approved_exact` outcome 的 response。
它不能重用 T5-G1 或前四批 response，也不授權 CAR-T5F、CAR-T6 或 RHB-T5。Batch 5
如果通過，還有 Batch 6 的 3 筆與 Batch 7 的 2 筆需要分別完成 readiness 和 owner decision。

## 2026-10-02 — T5-G2 Batch 4：Nissan Skyline LBWK 三筆追加，累積 12 exact／8 reviewed

### 新執行了什麼，以及解決了什麼問題

本輪在取得新的、只限 T5-G2 Batch 4 的 owner decision 後，將 Nissan Skyline
2000GT-R LBWK 的 packet ordinals `4`、`13`、`20` 由 `reviewed` 推進為
`approved_exact`。首次 materialization 回報 `created`，公開狀態由 9 exact／11 reviewed
變為 12 exact／8 reviewed／0 staged；三筆依然只核准 frozen community snapshot 支持的
casting、release year、series、collector number、series position 與 toy identifier。

這一步解決的不是「把名稱標記為正確」而已，而是把每一筆狀態轉移與 frozen
packet、catalog record、六欄 evidence、owner attestation 和 batch authorization 全部用 hash
連結。因此後續若有人改動任一批次或任一欄，重播與封存檢查會 fail closed，不會悄悄接受。

### 代碼修改了哪一部分，原因與方法選擇

這次沒有擴張 recorder 的產品邏輯，而是使用已經過 readiness 驗證的 bounded append
路徑。私有 ledger 只保存精確的 owner response 與 12 份 T5-G2 attestations，並維持
`0700`／`0600` 權限；Git 只追蹤 `authority-candidates.json` 與 `review-events.json`
中不含原文的 hash-bound 狀態。選擇 private/public split，是為了同時滿足「可重播稽核」和
「不將人類授權原文推上 GitHub」兩個需求。

新增的三個 public events 只做 `reviewed -> approved_exact`，並保留先前 29 個 events
與 17 個非目標 candidate objects。全部共有 11 個 batch authorization links、32 個
attestation links、32 個 public events 與 20 個 candidate latest-event links。`color` 和
`edition` 仍為 null；顏色次序文字只是 context，不被提升為 exact field。

### 驗證方式與結果

首次寫入回報 `created`，後續兩次使用同一份 Batch 4 私有授權做真實重播，都回報
`unchanged`。一次操作者檢查曾誤把不同 Gate 的 response 配對，validator 在寫入前即拒絕；
改用本批同一份授權後通過。這個失敗沒有修改公開或私有狀態，也實際證明 cross-Gate
重用會 fail closed。

寫入後 T5-G2 focused suite 收集並通過 20 項測試。寫入前的完整 repository 結果為
`1359 passed, 1 warning`，且 Ruff、format、strict MyPy、compileall 與 diff check 全數通過；
唯一 warning 仍是既有 Starlette／AnyIO deprecation。最終 811 個 tracked／unignored
文字檔對四份真實 owner responses 的 privacy scan 為 0 hits，私有檔仍被 dedicated ignore rule 排除。

### 留下的邊界與下一步

T5-G2 仍未完成，還有 8 筆 `reviewed` 候選資料。下一個合法步驟是先為下一個 frozen
family batch 實作並驗證 bounded path，再取得新的、只限該批的 T5-G2 owner decision。
這次授權不建立 manufacturer-certified truth，也不授權 CAR-T5F、CAR-T6 或 RHB-T5。

## 2026-10-02 — T5-G2 Batch 4 recorder ready，停在 Nissan Skyline LBWK Owner Gate

### 新執行了什麼，以及解決了什麼問題

本輪把 T5-G2 bounded recorder 從 `[1,2,3]` 擴充為 `[1,2,3,4]` prefix。下一批是 Nissan
Skyline 2000GT-R LBWK 的 packet ordinals `4`、`13`、`20`，toy identifiers 為 `HYX54`、
`HYW79`、`HYY30`。三筆的 casting、release year、series、collector number、series position
與 toy identifier 都與 frozen community snapshot 一致；`color` 與 `edition` 均為 null。

來源中的「3rd Color」與「2nd Color」仍只是 context，無法支持一個實際顏色值。因此新批次
仍只能綁定六個 supported fields，不能使用 free-text context 擴張 exact scope。本輪解決
的工程問題是：Batch 4 只能在 Batches 1–3 的 authorization、attestation、event 與 candidate
state 全部通過對帳後追加，而且不能跳批或清除後續歷史。

本輪只完成 readiness，沒有 materialize Batch 4 owner decision；真實狀態仍為 9 exact／
11 reviewed／0 staged。

### 代碼修改了哪一部分，原因與方法選擇

`canonical_authority_exact_decisions.py` 的 frozen batch map 新增 Nissan Skyline family key、ordinals 與
identifiers，supported prefix 上限擴為 Batch 4。繼續使用明確 frozen map，而不是一次開放
所有剩餘 batches，是為了在每一批進入 Gate 前分別驗證 family name、toy identifiers、context
與 null field boundary。Batch 5 仍然 fail closed。

測試新增完整 `[1,2,3,4]` append/replay，要求前三批 authorizations、9 個 attestations、9 個
exact events 與 17 個非目標 candidate objects 完全保留。也覆蓋缺 Batch 3 時拒絕、六欄
evidence values、Nissan identifiers、CLI append 與四批 replay。所有授權文字均為 TEST-ONLY
合成內容。

### 驗證方式與結果

T5-G2 focused suite 為 `20 passed`，完整 repository 為 `1359 passed, 1 warning`；Ruff、
format、strict MyPy、compileall 與 diff check 全數通過。唯一 warning 仍是既有 Starlette／
AnyIO deprecation。合成 Batch 4 最終為 12 exact／8 reviewed、4 份 T5-G2 authorizations、
12 份 T5-G2 attestations 與 32 個總 events。

真實 Batch 3 在新 recorder 下重播仍為 `unchanged`；806 個 tracked／unignored 文字檔對三份
真實 owner responses 的 privacy scan 為 0 hits。真實 private ledger 仍只含 Batches 1–3，所以
合成 Batch 4 counts 只是驗證證據，不是真實批准狀態。

### 留下的邊界與下一步

下一步是 Batch 4 Owner Gate：需要一份新的、明確綁定 Nissan Skyline 三個 identifiers、
snapshot-relative 六欄 scope、null color／edition 與 `approved_exact` outcome 的 response。它不能
重用 T5-G1 或前三批 response，也不授權 CAR-T5F、CAR-T6 或 RHB-T5。

## 2026-10-02 — T5-G2 Batch 3：Subaru BRZ 三筆追加，累積 9 exact／11 reviewed

### 新執行了什麼，以及解決了什麼問題

本輪在取得新的、只限 T5-G2 Batch 3 的 owner decision 後，將 Subaru BRZ 的 packet
ordinals `3`、`8`、`14` 由 `reviewed` 推進為 `approved_exact`。首次 materialization
回報 `created`，公開狀態由 6 exact／14 reviewed 變為 9 exact／11 reviewed／0 staged，
事件鏈由 26 增為 29。這解決第三個 family 如何在完整 Batches 1–2 prefix 上安全
append，同時不改寫前兩批的授權、attestation、event 與 candidate state。

這三筆只承認 frozen community snapshot 的六個 supported fields。`3rd Color` 與 `2nd
Color - Zamac` 繼續只是 context：沒有據此推導實際顏色，也沒有把 Zamac 記為 edition。
`color` 與 `edition` 維持 null，exactness 仍只相對於 frozen community revision，不是
manufacturer-certified truth。

### 代碼與資料修改了哪一部分，以及為何這樣決定

本輪沒有再改 recorder 程式碼，而是使用已通過 18 個 focused tests 與 1,357 個
full-suite tests 的 bounded Batch 3 path。Private exact ledger 追加一份 batch authorization 與三份
attestations；tracked public state 追加三個 events，並只更新對應三個 candidates 的 latest-state。

選擇繼續分離 private verbatim 與 public hash-bound state，是為了使 Git 能稽核變更，但不暴露
owner response。記錄前會重新驗證完整 `[1,2]` prefix、packet/catalog、對應 T5-G1
response hash、六個 evidence values 與 Subaru BRZ identifiers；任一綁定不符都會在寫入前拒絕。

### 驗證方式與結果

真實 append 後兩次 `--check` 均回報 `unchanged`。Post-materialization QA 確認原有 26
個 events 與 17 個非目標 candidate objects 完全保留；10 個 authorization links、29 個
attestation links、29 個 events 與 20 個 latest-state links 全部成立。Batch 3 的三個 events
各含六個正確 evidence fields，toy identifiers 與 expected values 完全符合。

私密／公開權限仍為 `0700`／`0600`／`0644`，private ledgers 繼續被專用 ignore rule
排除。804 個 tracked／unignored 文字檔對三份真實 owner responses 的 privacy scan 為 0 hits。
落地後 focused suite 為 `18 passed`；寫入前完整 repository 為 `1357 passed, 1 warning`，唯一
warning 是既有 Starlette／AnyIO deprecation。狀態寫入後未重跑完整 suite。

### 留下的邊界與下一步

T5-G2 尚未完成，還有 11 筆 `reviewed` 候選資料。下一步是為下一個 frozen family
batch 建立 bounded recorder、執行完整測試後再停在對應 Owner Gate。Authority bundle／
manifest 仍不存在，CAR-T5F、CAR-T6 與 RHB-T5 均未授權。

## 2026-10-02 — T5-G2 Batch 3 recorder ready，停在 Subaru BRZ Owner Gate

### 新執行了什麼，以及解決了什麼問題

本輪將 T5-G2 bounded recorder 從 `[1,2]` prefix 擴充為 `[1,2,3]`，下一批為 Subaru BRZ
的 packet ordinals `3`、`8`、`14`，toy identifiers 為 `JBB55`、`HYY12`、`HYW99`。三筆的
casting、release year、series、collector number、series position 與 toy identifier 均與 frozen
community snapshot 一致，`color` 與 `edition` 仍為 null。

其中來源 context 含有「3rd Color」與「2nd Color - Zamac」，但這些文字不足以證明
具體顏色，也不能把 Zamac 當成 edition。因此 recorder 只能記錄六個 supported fields，
不能擴大 exact scope。本輪解決的工程問題是：第三批必須在 Batches 1–2 完整存在
時才能 append，而且重播舊批次時不能把後續歷史清掉。

本輪只交付 readiness，沒有 materialize Batch 3 owner decision。真實狀態仍是 6
`approved_exact`／14 `reviewed`／0 `staged`。

### 代碼修改了哪一部分，原因與方法選擇

`canonical_authority_exact_decisions.py` 的 frozen batch map 新增 Subaru BRZ family key、ordinals 與三個
identifiers，並把 supported prefix 上限改為 Batch 3。選擇繼續明確列出 frozen map，而不是
讓 recorder 自動接受所有 packet batches，是為了在每批前先審核家族、identifiers、context
與 evidence boundary。因此 Batch 4 依然 fail closed，不會因 Batch 3 readiness 而被間接開放。

測試新增完整 `[1,2,3]` append/replay，要求前兩批 authorizations、六個 attestations、
六個 exact events 與 17 個非目標 candidate objects 完全保留；也覆蓋缺 Batch 2 時拒絕、
六欄 evidence values、toy identifiers、CLI append 與三批 replay。所有 owner text 都是 TEST-ONLY
合成內容。

### 驗證方式與結果

T5-G2 focused suite 為 `18 passed`，完整 repository 為 `1357 passed, 1 warning`；Ruff、
format、strict MyPy、compileall 與 diff check 全部通過。唯一 warning 仍是既有
Starlette／AnyIO deprecation。合成 Batch 3 最終為 9 exact／11 reviewed、3 份 T5-G2
authorizations、9 份 T5-G2 attestations、29 個總 events。

真實 Batch 2 在擴充後的 recorder 下重播仍為 `unchanged`；802 個 tracked／unignored 文字檔
對兩份真實 owner responses 的 privacy scan 為 0 hits。真實 private ledger 仍只含 Batches
1–2，所以合成 Batch 3 counts 只是驗證證據，不是真實批准狀態。

### 留下的邊界與下一步

下一步是 Batch 3 Owner Gate。需要一份全新、明確綁定 Subaru BRZ 三個 identifiers、
snapshot-relative 六欄 scope、null color／edition 與 `approved_exact` outcome 的 response。它不能
重用 T5-G1 或前兩批的 response，也不能擴大為 CAR-T5F、CAR-T6 或 RHB-T5 授權。

## 2026-10-02 — T5-G2 Batch 2：Draftnator 三筆追加，累積 6 exact／14 reviewed

### 新執行了什麼，以及解決了什麼問題

本輪在取得新的、只限 T5-G2 Batch 2 的 owner decision 後，將 Draftnator 的 packet
ordinals `2`、`11`、`18` 由 `reviewed` 推進為 `approved_exact`。首次 materialization
回報 `created`，公開狀態由 3 exact／17 reviewed 變為 6 exact／14 reviewed／0 staged，
事件鏈由 23 增為 26。這解決了第二個 family 如何在不改寫 Batch 1 與 T5-G1
歷史的情況下，用獨立 cross-Gate 授權追加 exact decisions。

這三筆只承認 frozen community snapshot 中的 casting、release year、series、collector
number、series position 與 toy identifier。`color` 與 `edition` 繼續為 null；「2nd/3rd
Color」文字沒有被推導成實際顏色。這不是 manufacturer-certified truth，也沒有產生
authority bundle／manifest 或授權 CAR-T5F、CAR-T6、RHB-T5。

### 代碼與資料修改了哪一部分，以及為何這樣決定

本輪沒有再改 recorder 程式碼，而是使用上一步已通過 16 個 focused tests 與 1,355
個 full-suite tests 的 bounded Batch 2 path。資料寫入方面，private ledger 追加一份 batch
authorization 與三份 attestations；tracked public state 只追加三個 events，並將對應三個
candidate latest-state 更新為 exact。

這種 private／public 分離是為了同時達成兩個目標：Git 可以稽核 status、field evidence 與
不可逆 hashes，但不會公開 owner response。寫入前會重新驗證 Batch 1 prefix、frozen
packet/catalog、六個 supported fields 與對應 T5-G1 response hash；因此不能用「繼續」、
舊授權或不完整批次觸發狀態變更。

### 驗證方式與結果

真實 append 後兩次 `--check` 都回報 `unchanged`。Post-materialization QA 確認原有 23
個 events 與 17 個非目標 candidate objects 完全保留；9 個 authorization links、26 個
attestation links、26 個 events 與 20 個 latest-state links 全部成立。Batch 2 三個 events
各含六個正確 evidence fields 與預期值，沒有 color／edition 推導。

權限仍為 private directory `0700`、private files `0600`、public files `0644`，專用 ignore
rule 命中新 private ledgers。800 個 tracked／unignored 文字檔對兩份真實批准的 privacy scan
為 0 hits。落地後 focused suite 為 `16 passed`；寫入前完整 repository 為 `1355 passed,
1 warning`，唯一 warning 是既有 Starlette／AnyIO deprecation。狀態寫入後未重跑完整
suite。

### 留下的邊界與下一步

T5-G2 仍在進行中，還有 14 筆 `reviewed` 候選資料需要後續獨立 decisions。下一步是
為下一個 frozen family batch 建立同樣的 bounded recorder，完成測試後再停在 Owner Gate。
在所有餘下 outcomes 完整記錄並對帳前，不執行 CAR-T5F、CAR-T6 或 RHB-T5。

## 2026-10-02 — T5-G2 Batch 2 recorder ready，停在 Draftnator Owner Gate

### 新執行了什麼，以及解決了什麼問題

本輪把 T5-G2 recorder 從只能處理 Batch 1，擴充為只能處理已明確審核的 Batch
1→2 prefix。下一批是 Draftnator 的 packet ordinals `2`、`11`、`18`，toy identifiers
為 `HYW70`、`HYX67`、`HYY31`。這三筆的 casting、release year、series、collector
number、series position 與 toy identifier 均與 frozen community snapshot 一致；`color` 與
`edition` 仍為 null。來源中的「2nd/3rd Color」文字只是 context，不被推導為實際顏色。

這次解決的主要問題，是如何讓第二批可以安全 append，同時不得跳過 Batch 1、
不得重用 T5-G1 回覆，也不得因重播舊批次而丟失新批次。本輪只交付 recorder
readiness，沒有 materialize Batch 2 的 owner decision；真實狀態仍是 3 `approved_exact`／
17 `reviewed`／0 `staged`。

### 代碼修改了哪一部分，原因與方法選擇

`canonical_authority_exact_decisions.py` 將 frozen family、ordinals 與 identifiers 定義為明確的
bounded batch map，並要求現有 T5-G2 authorizations 必須是連續 prefix。選擇固定 map，而不是
讓 CLI 接受任意 family，是為了把授權邊界放在可測試的程式中：Batch 2 只能跟在完整
Batch 1 之後，Batch 3 目前仍會 fail closed。

新的 prefix validator 會逐批重建 frozen expectations，並檢查 authorization→attestation→event→
candidate latest-state 的連續關係。不只驗證數量，也綁定 packet/catalog hashes、candidate
IDs、entry hashes、UUID、catalog-record hash、六個 evidence rows、timestamp、reason 與對應的
T5-G1 response hash。如果重播 Batch 1，recorder 會保留已存在的 Batch 2+、而不是用舊輸出
覆寫後續歷史。

測試方面新增 Batch 2 正常 append、不可跳批、fresh cross-Gate response、舊 Batch 1 完整
保留、舊批次重播、六欄 evidence boundary、CLI 與中斷時 atomic rollback。測試全部使用
TEST-ONLY 合成回覆，不會把真實 owner response 放進 source 或 tracked artifacts。

### 驗證方式與結果

T5-G2 focused suite 為 `16 passed`，完整 repository 為 `1355 passed, 1 warning`；Ruff、
format、strict MyPy、compileall 與 diff check 全數通過。唯一 warning 是既有 Starlette／
AnyIO deprecation。合成 Batch 2 可得到 6 approved exact／14 reviewed、2／6 份第二道
Gate authorization／attestation、26 個總 events，並且 Batch 1 的 authorization、3 attestations、3
events 與所有非目標 candidates 保持不變。

真實 Batch 1 在新 recorder 下重播仍為 `unchanged`；798 個 tracked／unignored 文字檔的
真實 owner response privacy scan 為 0 hits。真實 private ledger 仍只有 Batch 1，因此上述 Batch 2
counts 是合成驗證結果，不是已完成的 owner decision。

### 留下的邊界與下一步

下一步是 Owner Gate：只有在取得新的、明確綁定 Draftnator 三個 toy identifiers 與
`approved_exact` 的 T5-G2 response 後，才能 materialize Batch 2。這份回覆不能重用 Batch 1、
T5-G1 或 catalog-application 授權，也不能擴大為 CAR-T5F、CAR-T6 或 RHB-T5 授權。

## 2026-10-01 — T5-G2 Batch 1：3 筆 fresh exact decisions，其餘 17 筆保持 reviewed

### 新執行了什麼，以及解決了什麼問題

本輪在取得新的、明確且只限 T5-G2 Batch 1 的 owner decision 後，將 Mazda Autozam
的 packet ordinals `1`、`10`、`16` 由 `reviewed` 推進為 `approved_exact`。首次
materialization 回報 `created`，公開狀態成為 3 approved exact／17 reviewed／0 staged，
事件鏈由 20 個第一道 Gate events 增為 23 個歷史 events。這解決了「已完成
evidence review 的候選資料，如何在不重用 T5-G1 授權、不覆寫舊事件的前提下，
進入第二道 exact-authority Gate」的問題。

這三筆的 `approved_exact` 僅表示六個有來源支持的欄位與 frozen community snapshot
完全一致，不是 Mattel／manufacturer-certified truth。`color` 與 `edition` 仍為 null；公開
authority bundle／manifest 尚未建立，CAR-T5F、CAR-T6 與 RHB-T5 也沒有被授權。

### 代碼與資料修改了哪一部分，以及為何這樣決定

新增的 `canonical_authority_exact_decisions.py` 與專用 CLI 只允許 T5-G2 Batch 1，並在
寫入前驗證完整的七批 T5-G1 狀態、frozen packet／catalog，以及 20 條舊事件與
private attestations 的鏈結。選擇「另一個 bounded recorder + 另一組 private ledgers」，
而不是直接改 JSON 或延用 T5-G1 recorder，是為了讓兩道 Gate 在授權文字、時間、
transition 與追蹤 hash 上都能獨立稽核。程式明確要求 fresh response hash，並拒絕
任何與對應 T5-G1 response 相同的輸入。

共用的 event contract 則由「每個 candidate 只能有一個 event」改為驗證完整的狀態鏈，
因為同一 candidate 現在合法地擁有 `staged -> reviewed -> approved_exact` 兩個先後事件。
驗證器仍要求穩定排序、唯一 event ID、連續 from/to state 與 terminal counts，所以不會
因支援多事件而放鬆 append-only 安全性。四個 private／public outputs 繼續採 atomic
write／rollback，避免中途失敗後產生授權與公開狀態不同步。

### 驗證方式與結果

新增的 T5-G2 focused suite 為 `12 passed`，T5-G1 regression 為 `71 passed`，完整 repository
為 `1351 passed, 1 warning`；Ruff、format、strict MyPy、compileall 與 diff check 均通過，唯一
warning 是既有 Starlette／AnyIO deprecation。測試使用 TEST-ONLY 合成授權，沒有將真實
owner response 寫入測試。

真實 append 後兩次 `--check` 皆回報 `unchanged`。Post-materialization QA 確認先前 20
個 T5-G1 events 與其餘 17 個 candidate objects 保持完全不變；8 份 batch authorizations、23
份 attestations、23 個 events 與 20 個 latest-event links 全數有效。Private 目錄／檔案權限
為 `0700`／`0600`，public files 為 `0644`；796 個 tracked／unignored 文字檔的真實授權
privacy scan 為 0 hits。狀態寫入後沒有重跑完整 suite。

### 留下的邊界與下一步

T5-G2 仍未完成：另外 17 筆候選資料仍是 `reviewed`，而不是 `approved_exact`。
下一個合法步驟是以新的、明確的 T5-G2 family-bounded owner decision 處理下一批；在
其餘 outcomes 都記錄並重新對帳前，不會執行 CAR-T5F、CAR-T6 或 RHB-T5。

## 2026-10-01 — T5-G1 完成：Final Batch 1 累積 20 reviewed／0 staged

### 新執行了什麼，以及解決了什麼問題

本輪在取得新的、明確且只限 T5-G1 的 owner outcome 後，正式記錄 Mazda Autozam 最後三筆
ordinals `1`、`10`、`16`。首次 materialization 回報 `created`，累積狀態由 17 reviewed／3 staged
推進為 20 reviewed／0 staged；private batch authorizations 由 6 增至 7，private attestations 與 public
events 則各由 17 增至 20。這完成了所有七個 family batches 的第一道 evidence review。

本輪沒有將 review 解讀為 exact truth：`approved_exact` 仍為 0，authority bundle／manifest 未建立，
RHB-T5 authorization 仍為 false。授權原文只存在 Git-ignored private ledger，不會在本日誌重述。

### 代碼與資料修改了哪一部分，以及為何這樣決定

本輪沒有再修改 recorder 程式碼，而是使用上一個已通過 71 個 focused tests 與 1339 個 full-suite
tests 的 final-batch path。公開資料只更新 `authority-candidates.json` 與 `review-events.json`；私密
authorization／attestation ledgers 留在 ignored workspace。選擇分離 public state 與 private verbatim，
是為了讓 Git 能審計 20 筆狀態與 hash links，同時不公開 owner response 或 private identity。

Batch 1 只有在完整 Batches 2–7 predecessor state 驗證成功後才能追加。這個反向依賴不是放寬順序，
而是針對先前延後的最後一批所做的 bounded rule；它保證舊 17 個 events、candidate objects 與其
hash links 不會因補入 Batch 1 而被重寫。

### 驗證方式與結果

真實 append 後兩次 `--check` 都回報 `unchanged`。Post-materialization QA 驗證 20 條
candidate→event→attestation→authorization links、7／20／20 counts、20／0 state 與完整 packet/catalog
bindings；先前 17 個 events 與 reviewed candidate objects 保持完全相同。Private 目錄／檔案權限、
public file 權限與 `.gitignore` 邊界均正確，794 個 tracked／unignored files 的真實授權 privacy scan
為 0 hits。Pre-materialization 的 focused `71 passed`、full `1339 passed`、Ruff、format、strict MyPy、
compileall 與 diff check 結果持續適用；狀態寫入後沒有重跑完整 suite。

### 留下的邊界與下一步

T5-G1 現已完成，但 CAR-T5 尚未完成。下一個合法步驟是 T5-G2：取得另一份 fresh、獨立且明確的
exact-authority outcome，不能重用任何 T5-G1 或 catalog-application response。T5-G2 完成後才能執行
CAR-T5F freeze；CAR-T6 RHB-T4 re-audit 與 RHB-T5 仍是後續不同 Gate。Lite／Lean 模式下的
architect、security 與 performance review 維持 deferred。

## 2026-10-01 — Final Batch 1 recorder ready，等待明確 T5-G1 outcome

### 新執行了什麼，以及解決了什麼問題

本輪完成 Mazda Autozam 最後三筆的 recorder 能力，但沒有 materialize 真實 owner decision。這三筆是
先前刻意保留的 Batch 1 ordinals `1`、`10`、`16`；由於 Batches 2–7 已先完成，原本只接受順序 prefix
的 recorder 無法安全地回頭追加 Batch 1。本次新增「final-batch」路徑，讓它只能建立在完整 17-event
predecessor state 上，避免將缺批、跳批或一般 continuation 指示誤認為可審計授權。

目前真實狀態仍為 17 reviewed／3 staged，exact authority 為 0，authority bundle／manifest 不存在，
RHB-T5 authorization 為 false。這個停點是 Gate contract 的一部分，不是功能失敗。

### 代碼修改了哪一部分，原因與方法選擇

`canonical_authority_decisions.py` 加入 frozen Batch 1 family、ordinals 與 toy identifiers，並把 Batch 1
的必要前置狀態明確定義為 Batches 2–7。選擇「指定完整 predecessor set」而不是放寬成任意 batch
順序，是為了保留既有 append-only 保證：只有當 17 筆既有 candidate／event／attestation／authorization
objects 全部合法時，最後三筆才有資格追加。完成後 authorization ledger 會依 ordinal 排成 1–7，
但測試要求舊有六份 authorizations 與 17 個逐筆 objects 保持完全相同。

測試新增 final append、六種不完整 prefix、exact-response mismatch、direct exact、partial state、tampered
state 與 atomic rollback 情境。所有 owner text 都是 `TEST-ONLY` 合成內容；真實授權原文不進入 source、
test、docs 或 tracked public artifacts。

### 驗證方式與結果

Focused recorder suite 為 `71 passed`，完整 repository 為 `1339 passed`；Ruff、format、strict MyPy、
compileall 與 diff check 均通過。唯一 warning 是既有 Starlette／AnyIO deprecation。合成 materialization
可得到 20 reviewed／0 staged、7／20／20 authorization-attestation-event counts，兩次 replay 保持
`unchanged`，且 direct `approved_exact`、RHB-T5 與 authority bundle／manifest 仍被拒絕。

### 留下的邊界與下一步

一般的繼續指示不等同於逐筆 T5-G1 outcome，所以本輪只交付並驗證 recorder，沒有改動真實 state。
下一步需要一份新的、明確綁定 Batch 1 三個 identifiers、`reviewed`、null `color`／`edition`，並排除
`approved_exact` 與 RHB-T5 的 owner response。記錄成功並完成 post-materialization QA 後，T5-G1
才會成為 20／20 complete；T5-G2 仍需另一份 fresh authorization。

## 2026-10-01 — T5-G1 Batch 7：兩筆 bounded append，累積 17 reviewed／3 staged

### 新執行了什麼，以及解決了什麼問題

本輪記錄 T5-G1 Batch 7，把 Mazda MX-5 Miata 的 packet ordinals `9`、`15` 從 `staged` 推進為
`reviewed`，同時完整保留 Batches 2–6 的 15 個既有 objects。Batch 7 只有兩筆，因此累積狀態從
15 reviewed／5 staged 動態變為 17 reviewed／3 staged；private batch authorizations 由 5 增為 6，
private attestations 與 public events 則各由 15 增為 17。這解決了 recorder 如何承接非三筆批次，並
讓授權、逐筆證據與公開狀態依實際 batch 大小一致增加的問題。

本輪仍只記錄 evidence review：`approved_exact` 為 0，authority bundle／manifest 不存在，RHB-T5
authorization 為 false。日誌不重述、推導或硬編碼 trusted response 或 private identity。

### 修改了哪一部分，以及為何這樣決定

Decision recorder／CLI／tests 的允許 prefix 擴充為 Batch 2 → Batch 3 → Batch 4 → Batch 5 →
Batch 6 → Batch 7。Batch 7 只有在完整且有效的 Batches 2–6 predecessor prefix 已存在時，才能建立
一份 private batch authorization、兩份逐筆 attestations 與兩個 public `staged -> reviewed` events。
計數改由 frozen batch 的實際兩筆 records 驅動，而不是硬編碼每批三筆；這個決定避免少建或多建
attestation／event，也讓 state transition 與授權覆蓋範圍一一對應。

bounded prefix 繼續阻止跳序、漏失或改寫既有 objects，以及跨 batch／Gate 重用授權。四個
private／public outputs 仍採 atomic promotion 與 rollback，確保 candidate state、events、authorization
與 attestations 一起前進，任一失敗都回復原始 bytes。Privacy 方法維持 public／private 分離：tracked
artifacts 只保留 bounded state、bindings 與不可逆 hashes，授權原文與 private identity 不進入 Git
公開內容。

### 驗證方式與結果

Batch 7 首次 materialization 回報 `created`，接著兩次 real checks 均回報 `unchanged`。現有證據確認
Batches 2–6 的 15 個既有 objects 保持不變，累積 17／3 state 與 6／17／17
authorization-attestation-event counts 正確，並持續拒絕 `approved_exact`、authority bundle／manifest
及 RHB-T5 權限擴張。

獨立 pre-materialization QA 判定 **PASS**：focused `60 passed`、full repository `1328 passed`；唯一
訊息為既有 dependency warning。本次 Project Log 只整理已交付的 QA 與 materialization 證據，沒有
重跑測試，也不將 first-Gate evidence 解讀成 resolver accuracy、retrieval quality 或 manufacturer truth。

獨立 post-materialization QA 同樣判定 **PASS**：17 條 decision links 全部有效，先前 15 個 events、
candidate objects 與 attestation hashes 均保持不變；private/public 權限、Git-ignore 邊界、bytes-stable
replay，以及涵蓋六份真實授權輸入的 794-file privacy scan 皆通過。Blocker 與 Important 均為 0。

### 留下的邊界與下一步

目前剩餘 3 筆 staged，全部是 Batch 1 Mazda Autozam 的 ordinals `1`、`10`、`16`，所以 T5-G1
尚未完成。下一步必須對 Batch 1 取得新的、明確 T5-G1 outcome，不能沿用本輪 authorization 或一般
continuation 指示；全部 first-Gate events 合法記錄後，才可另行提出 fresh T5-G2 exact-authority
request。Architect、security 與 performance review 在 Lite／Lean 模式下仍為 deferred。

## 2026-10-01 — T5-G1 Batch 6：bounded prefix 累積 15 reviewed／5 staged

### 新執行了什麼，以及解決了什麼問題

本輪記錄 T5-G1 Batch 6，把 Morgan Super 3 的 packet ordinals `6`、`12`、`19` 從 `staged`
推進為 `reviewed`，同時完整保留 Batches 2–5 的既有 objects。累積狀態成為 15 reviewed／5 staged、
5 份 private batch authorizations、15 份 private attestations 與 15 個 public events。這解決了第五個
review batch 如何在不覆寫前四批歷史、也不越過 first-Gate 授權邊界的前提下安全追加。

本輪仍只記錄 evidence review：`approved_exact` 為 0，authority bundle／manifest 不存在，RHB-T5
authorization 為 false。日誌不重述、推導或硬編碼 trusted response 或 private identity。

### 修改了哪一部分，以及為何這樣決定

Decision recorder／CLI／tests 的允許 prefix 擴充為 Batch 2 → Batch 3 → Batch 4 → Batch 5 →
Batch 6。Batch 6 只有在完整且有效的 Batches 2–5 predecessor prefix 已存在時才能建立一份 private
batch authorization、三份逐筆 attestations 與三個 public `staged -> reviewed` events。選擇 bounded
prefix，而不是讓通用入口接受任意 batch，是為了防止跳序、漏失或改寫歷史 objects，以及跨 batch／
Gate 重用授權。

四個 private／public outputs 仍採 atomic promotion 與 rollback。這項方法確保 candidate state、events、
authorization 與 attestations 一起前進；任一寫入失敗都必須回復原始 bytes，避免公開狀態與私密授權
證據不同步。Privacy 方法也維持 public／private 分離：tracked artifacts 只保留 bounded state、bindings
與不可逆 hashes，授權原文與 private identity 不進入 Git 公開內容。

### 驗證方式與結果

Batch 6 首次 materialization 回報 `created`，接著兩次 real checks 均回報 `unchanged`。現有證據確認
Batches 2–5 的 12 個既有 objects 保持不變，累積 15／5 state 與 5／15／15
authorization-attestation-event counts 正確，並持續拒絕 `approved_exact`、authority bundle／manifest
及 RHB-T5 權限擴張。

獨立 pre-materialization QA 判定 **PASS**：focused `72 passed`、full repository `1317 passed`；唯一
訊息為既有 dependency warning。本次 Project Log 只整理已交付的 QA 與 materialization 證據，沒有
重跑測試，也不將 first-Gate evidence 解讀成 resolver accuracy、retrieval quality 或 manufacturer truth。

Post-materialization QA 同樣判定 **PASS**：focused `72 passed`，15 條
candidate→event→attestation→authorization links、35 個 item hashes 與 4 個頂層 hashes 全部
重算一致；794 個 tracked／unignored files 的五輪 response privacy scan 為 0 hits。
Blocker／Important／Later 皆為 0。

### 留下的邊界與下一步

目前還有 5 筆 staged。下一步需對另一個 frozen batch 取得新的、明確 T5-G1 outcome，不能沿用本輪
authorization 或一般 continuation 指示；所有必要 first-Gate events 合法記錄後，才可另行提出 fresh
T5-G2 exact-authority request。Architect、security 與 performance review 在 Lite／Lean 模式下仍為
deferred。

## 2026-10-01 — T5-G1 Batch 5：bounded prefix 累積 12 reviewed／8 staged

### 新執行了什麼，以及解決了什麼問題

本輪記錄 T5-G1 Batch 5，把 '21 Ford Bronco 的 packet ordinals `5`、`7`、`17` 從
`staged` 推進為 `reviewed`，並完整保留 Batches 2–4 的既有 objects。累積狀態成為 12
reviewed／8 staged、4 份 private batch authorizations、12 份 private attestations 與 12 個 public events。
這解決了第四個 review batch 如何在不改寫前三批歷史、也不擴張授權範圍的前提下安全追加。

本輪仍只完成 first-Gate evidence review：`approved_exact` 為 0，authority bundle／manifest 不存在，
RHB-T5 authorization 為 false。日誌不重述、推導或硬編碼 trusted response 或 private identity。

### 修改了哪一部分，以及為何這樣決定

Decision recorder／CLI／tests 的允許 prefix 由 Batch 2 → Batch 3 → Batch 4 擴充為 Batch 2 →
Batch 3 → Batch 4 → Batch 5。Batch 5 必須先驗證完整 predecessor prefix，才能建立一份 private
batch authorization、三份逐筆 attestations 與三個 public `staged -> reviewed` events。使用 bounded
prefix，而不是讓通用入口接受任意 batch，是為了防止跳序、漏掉歷史 objects、覆寫前一批，或把
同一授權重用到其他 batch／Gate。

四個 private／public outputs 繼續採 atomic promotion 與 rollback，因為 candidate state、events、authorization
與 attestations 必須一起前進；任何一個單獨成功都會造成公開進度和私密授權證據不一致。
Privacy 選型則維持 public／private 分離：Git 內的公開 artifacts 只保留 bounded state、bindings 與不可逆
hashes，trusted response 與 private identity 繼續排除於 tracked content 之外。

### 驗證方式與結果

Batch 5 首次 materialization 回報 `created`，接著兩次 real checks 均回報 `unchanged`。可用證據確認
Batches 2–4 objects 保持不變，累積 12／8 state 與 4／12／12 authorization-attestation-event counts 正確，
並持續拒絕 `approved_exact`、authority bundle／manifest 與 RHB-T5 權限擴張。

獨立 pre-materialization QA 判定 **PASS**：focused `62 passed`、full repository `1307 passed`。本次
Project Log 只整理已交付的 QA 與 materialization 證據，沒有重跑測試，也不把這些結果解讀成
resolver accuracy、retrieval quality 或 manufacturer truth。

Batch 4 曾在 specs 與 source manifest 並行更新時發生 shared-workspace binding 競態，穩定重跑後通過。
這個 orchestration risk 仍保留為已知風險；本輪 Batch 5 沒有重現該問題。Post-materialization QA
最終判定 **PASS**：4／12／12 links、前 9 個 objects 保留、permissions、Git-ignore、replay 與
794 個 tracked／unignored files 的四輪 response privacy scan 全部通過，Blocker／Important／Later
皆為 0。

### 留下的邊界與下一步

目前還有 8 筆 staged。下一步需對另一個 frozen batch 取得新的、明確 T5-G1 outcome，不能沿用
本輪 authorization 或一般 continuation 指示；完成必要的 first-Gate events 後，才可另行提出 T5-G2
exact-authority request。Architect、security 與 performance review 在 Lite／Lean 模式下仍為 deferred。

## 2026-10-01 — T5-G1 Batch 4：bounded prefix 累積 9 reviewed／11 staged

### 新執行了什麼，以及解決了什麼問題

本輪記錄 T5-G1 Batch 4，把 Nissan Skyline 2000GT-R LBWK 的 packet ordinals `4`、`13`、`20`
從 `staged` 推進為 `reviewed`，並保留 Batches 2–3 的全部既有 objects。累積狀態成為 9 reviewed／
11 staged、3 份 private batch authorizations、9 份 private attestations 與 9 個 public events。這解決了
第三個 review batch 如何在不改寫前兩批歷史、也不擴張授權 Gate 的前提下安全追加的問題。

本輪仍只完成第一道 evidence review：`approved_exact` 為 0，authority bundle／manifest 不存在，
RHB-T5 authorization 為 false。日誌不重述、推導或硬編碼 trusted response 或 private identity。

### 修改了哪一部分，以及為何這樣決定

Decision recorder／CLI／tests 的允許 prefix 從 Batch 2 → Batch 3 擴充到 Batch 2 → Batch 3 → Batch 4。
Batch 4 必須先驗證完整 predecessor prefix，才能建立一份 private batch authorization、三份逐筆
attestations 與三個 public `staged -> reviewed` events。這種 bounded prefix 設計刻意沒有改成可接受
任意 batch 的通用入口：固定前置狀態能阻止跳序、遺漏歷史、重寫既有 objects，或把一批授權重用到
另一批與另一道 Gate。

四個 private／public outputs 繼續採 atomic promotion 與 rollback。原因是 candidate state、events、
authorization 和 attestations 必須共同前進；若只寫成其中一部分，公開進度和私密授權證據會互相矛盾。
Privacy 設計則維持 public／private 分離：公開檔案只保留 bounded state、bindings 與不可逆 hashes，授權
材料留在 private ledgers，使 Git 中的可稽核進度不需要攜帶 trusted response 或 private identity。

### 驗證方式與結果

Batch 4 首次 materialization 回報 `created`，接著兩次 real checks 都回報 `unchanged`。驗證確認 Batches
2–3 objects 保持不變，累積 9／11 state 與 3／9／9 authorization-attestation-event counts 正確，並持續
拒絕 `approved_exact`、authority bundle／manifest 與 RHB-T5 權限擴張。

獨立 pre-materialization QA 判定 **PASS**：focused `53 passed`、full repository `1298 passed`。本次
Project Log 策展只整理已存在的 QA 與 materialization 證據，沒有重跑測試，也不把這些結果解讀成
resolver accuracy、retrieval quality 或 manufacturer truth。

Post-materialization QA 曾在 specs 與 source manifest 並行更新的瞬間遇到一次 fixture
競態：首次 run 為 7 pass／23 fail，23 個 failure 皆來自 tasks hash 與 manifest binding 在複製時
暫時不一致。待並行更新完成後，binding 相等，穩定重跑 `30 passed`。因此最終為
**PASS WITH RISKS**；這項風險是 shared-workspace 更新競態，不是 Batch 4 decision state 錯誤，也沒有
被忽略或從紀錄中移除。

### 留下的邊界與下一步

目前仍有 11 筆 staged。下一步需對另一個 frozen batch 取得新的、明確 T5-G1 outcome，不能沿用本輪
authorization 或一般 continuation 指示；完成必要的 first-Gate events 後，才可另行提出 T5-G2
exact-authority request。Architect、security 與 performance review 在 Lite／Lean 模式下仍為 deferred。

## 2026-10-01 — T5-G1 Batch 3：bounded append 後累積 6 reviewed／14 staged

### 新執行了什麼，以及解決了什麼問題

本輪記錄 T5-G1 Batch 3，把 Subaru BRZ 的 packet ordinals `3`、`8`、`14` 從 `staged` 推進為
`reviewed`；Batch 2 的三筆 reviewed objects 保持不變。累積狀態成為 6 reviewed／14 staged、2 份
private batch authorizations、6 份 private attestations 與 6 個 public events。這解決了 recorder 原本只能
承接第一個 owner batch、無法在保留歷史的情況下安全追加下一批的問題。

本輪沒有把第一道 review 擴張成 exact approval：`approved_exact` 仍為 0，authority bundle／manifest
仍不存在，RHB-T5 authorization 仍為 false。日誌不重述、推導或硬編碼任何 trusted owner response 或
private identity。

### 修改了哪一部分，以及為何這樣決定

Decision recorder／CLI／tests 從單一 Batch 2 contract 擴充為明確限定 Batch 2 → Batch 3 的 ordered
append。Batch 3 必須先驗證完整 Batch 2 predecessor state，並為新 batch 建立一份 authorization、三份
逐筆 attestations 與三個 public `staged -> reviewed` events；這比建立一個可接受任意 batch 的通用入口更
容易限制授權範圍，也能阻止跳序、覆寫歷史或跨 Gate 重用。

既有 Batch 2 private ledger 使用早期 shape，因此讀取路徑加入 strict legacy migration。選擇單向正規化，
而不是就地重寫或同時永久支援兩套可變 schema，是為了讓後續 validation 只面對一個 canonical contract，
同時保留舊資料的 outcome、scope 與語意。四個 private／public outputs 維持 atomic promotion 和 rollback；
若中途寫入失敗，全部回復原始 bytes，避免 authority、attestation、candidate state 與 events 互相矛盾。

### 驗證、QA 發現與修復

Batch 3 第一次 materialization 回報 `created`，接著兩次 real checks 都回報 `unchanged`；驗證亦確認 Batch 2
objects 保留、累積 6／14 state 與 2／6／6 authorization-attestation-event counts。Privacy scan 同時覆蓋
歷史和新增 response，因為只掃描 Batch 3 會漏掉 migration、fixture 或 renderer 重新帶出舊 response 的
風險；公開 artifacts、tracked source、tests 和 docs 均不得包含 trusted response 或 private identity。

QA 的 changed-test strict MyPy 初次發現 7 個型別錯誤，修正後該 scoped check 為 0 errors。這代表本輪
changed-test typing 問題已清除，不代表全 repository 的既有 type debt 已消失。Atomic rollback、bounded
Batch 2 → 3 append、legacy migration、歷史＋新增 response public-leak boundary 也已納入驗證。本次
Project Log 策展沒有重跑測試。

獨立 QA 最終判定 **PASS**：focused `22 passed`、pre-materialization full repository `1290 passed`；
post-materialization 再驗證 6／14 state、2／6／6 counts、Batch 2 object preservation、permissions、Git-ignore
與 794 個 tracked／unignored files 的 privacy boundary。沒有 Blocker 或 Important finding；唯一 warning 是
既有 Starlette／AnyIO deprecation warning。

### 保留邊界與下一步

這次只完成另一個 T5-G1 first-Gate batch，不建立 manufacturer truth、resolver accuracy、benchmark
readiness、T5-G2 或 RHB-T5 結論。下一步仍需 owner 對另一個 frozen batch 提供新的明確 T5-G1 outcome；
不能把本輪 authorization 或一般 continuation 指示當成後續 batch 或 exact-authority 授權。

## 2026-10-01 — T5-G1 Batch 2：三筆 reviewed，17 筆維持 staged

### 新執行了什麼，以及解決了什麼問題

本輪在 T5-G1 contract 下記錄 Batch 2 的 owner review progress：只把 Draftnator 的 packet ordinals `2`、`11`、`18` 從 `staged` 推進為
`reviewed`，其餘 17 筆維持 staged。這解決了「一份 batch 回覆如何安全套用到三個明確 entries」的問題，但沒有把第一道 evidence review 擴張成
exact-authority approval：exact authority 仍為 `0`，`approved-authority.json`、`authority-manifest.json` 與 RHB outputs／authorization 仍不存在。

本日誌不重述或重建 trusted owner response，也不揭露 private identity。實際 private state 是一份 batch authorization 加三份 owner attestations；
public state 是三個 `staged -> reviewed` events，三者共享同一 authorization hash，並各自綁定 ordinal、candidate／catalog record、evidence 與 prior
state。這誠實表達「一次 batch authorization 覆蓋三筆」，沒有偽裝成 owner 說了三次不同的話。

### 修改了哪些部分，以及為何採 external expected Gate

實作新增 dedicated decision recorder／CLI 與 append-only validation，將 public `authority-candidates.json`／`review-events.json` 和 Git-ignored private
batch-authorization／attestation ledgers 分開。Private ledgers 為 `0600`，public artifacts 為 `0644`；public files 只揭露 bounded state、bindings 與 hashes，
不含 owner verbatim 或 private identity。第一次記錄回報 `created`，接著兩次 real checks 都是 `unchanged`。

Private ledger 不能自行證明 authorization。呼叫端必須另外提供 strict `ExpectedBatchOwnerAuthorization`，validator 會精確比對 T5-G1 Gate、
`staged_to_reviewed` scope、outcome、covered entries、external response hash 與 prior-Gate constraints。這個 positive external expectation 比搜尋關鍵字更安全：
即使有人重算 stored artifact hashes，只要與外部期待的 Gate／scope／entries／response 不一致，仍會 fail closed。相同 response 也不會因為已有三個
events 就取得 T5-G2 權限。

四個 materialized artifacts 的 final SHA-256 分別為 private authorization
`04fb14d4a3f8e43f31e59900ed7e573f7b46ffd1216c270a67c8457dc0dc272b`、private attestations
`49bdf299456179d6087c6276d372d7ed63b1037cef71b02a1034bfa318a55446`、public candidates
`1a844f73c875797fce907048a2e8ad9532090f01b356882d990ff07a20d204da` 與 public events
`a35c63d4a26a4a4f01be917a15b46ab56477f771e45f3181b6fc88985bbf44ae`。

### QA 發現的 privacy failure 與修復

獨立 QA 發現 test fixture 曾硬編碼 trusted owner response。即使 production private ledgers 沒有被 track，verbatim fragment 出現在 tracked test source
仍是 privacy leak，不能以「只是測試」忽略。修復移除真實回覆，換成明確標記 `TEST-ONLY` 的 synthetic Unicode／backslash text；production recorder
保持 response-agnostic，不把任何特定人類字句寫成產品邏輯。

Post-materialization QA 不只驗 temporary fixture，也直接驗真實 outputs：3 reviewed／17 staged、1 private authorization／3 attestations／3 public events、
一個 shared authorization hash、`0600`／`0644` permissions、parent bindings 與兩次 unchanged checks 全部成立。Repo-wide privacy scan 對 792 個
tracked／unignored files 確認 trusted-response fragments 為零。

### 最終 QA、邊界與下一步

最終獨立 QA 判定 **PASS**：focused `16 passed`、full repository `1284 passed`；Ruff、Ruff format、strict MyPy、compileall、fixture isolation、
permissions、privacy 與四個 artifact hashes 全部通過。沒有 blocker 或 important finding。本次 Project Log 策展沒有重跑測試。

下一步仍是對另一個 frozen batch 取得**新的 owner T5-G1 outcome**，不是啟動 T5-G2。Batch 2 reviewed 只證明 first-Gate progress，不建立 exact／
manufacturer truth、不授權 authority bundle、benchmark readiness 或任何 RHB stage，也不是 resolver accuracy 結論。

## 2026-09-30 — CAR-T5P：準備 20 筆 output-blind authority review entries，停在 T5-G1

### 新執行了什麼，以及解決了什麼問題

Catalog-v2 已有 20 筆 owner-reviewed catalog identities，但 catalog inclusion 不是 exact authority；直接沿用 generic continuation instruction 產生 review outcome
會替使用者做出從未給過的判斷。本輪因此只執行 CAR-T5P preparation：將 20 筆既有 UUID records 整理為 staged、output-blind review packet，按 7 個
family batches `[3,3,3,3,3,3,2]` 呈現，並生成每筆 6 個、合計 120 個 agreeing evidence rows。所有 color／edition 仍是 null；review events、owner
attestations、`approved_exact`、authority bundle、network requests 與 RHB-T5 authorization 均為 0，resolver／model output 也完全沒有被使用。

目前 continuation 的權限只涵蓋 preparation，沒有推定 T5-G1 或 T5-G2 outcomes。第一次 materialization 回報 `created`，後續兩次 real `--check`
皆為 `unchanged`。Private packet SHA-256 是 `1086fa0ea7ddd4fda2b7a4b021797e5630a7b55d9f840c3508c4744d9703fe2b`，private owner-review
Markdown SHA-256 是 `f1bfa2d7a296de06d132e019513b03745d7cf3062007f23e40bc9655c1260bf2`，public safe manifest SHA-256 是
`6b849f016a5c965397aaba7839e5c6c3d81acb44ed796e171355990c5b211053`。本日誌只記 hashes／counts，不公開 private owner text 或 product rows。

### 修改了哪些部分，以及為何這樣選

程式面新增 dedicated preparation CLI／builder、catalog-resolution bindings、private packet／public manifest strict contracts，以及為未來事件預先定義的
batch authorization、owner attestation 和 review-event v2 contracts；測試涵蓋 reconciliation、privacy、Gate transitions、atomic write 與 replay。
`.gitignore` 先加入 exact private workspace，再以 directory `0700`、files `0600` 產生 owner packet；tracked manifest 僅公開安全 aggregates、hashes、
attribution、license 與 next Gate。這讓人類可查看完整 evidence，同時不把問題、逐筆內容或未來 owner verbatim 放進 Git。

Frozen CAR-T4 candidates 沒有因 catalog-v2 已套用而被回寫。每筆另以 immutable binding 把 historical candidate／proposal hashes 接到 current
catalog-v2 UUID、canonical ID、release key 與 record hash，保留「當時 proposal 是什麼」和「現在 catalog identity 是什麼」兩條 lineage。這比直接
修改舊 packet 安全，因為後者會讓既有 hash／review evidence 失去歷史意義。

Owner flow 刻意拆成兩道不同 contract：T5-G1 只建立 `staged -> reviewed`（或明確 non-reviewed outcome），T5-G2 才能建立 `reviewed -> approved_exact`。
未來每個 batch 都必須對照 ledger 外部的 `ExpectedBatchOwnerAuthorization`；G2 必須引用獨立 G1 response hash，而且同一 response hash 不得跨 Gate。
這避免把「我看過」和「我批准 exact authority」壓成同一個模糊布林值。

### QA 如何找出設計漏洞並修正

最初若只以有限 generic blacklist 排除幾種 continuation 語句，未列入名單的模糊文字仍可能被誤認為授權；只要重算 mutable Gate fields／hashes，
同一 response 也可能被包裝到另一道 Gate。獨立 QA 重現此 cross-Gate rehash 風險後，設計改成 positive external expectation：精確比對 Gate、scope、
declaration、outcome 與 response hash，並以 prior G1 response hash 和「current 不得等於 prior」規則隔離 G2。授權因此來自 ledger 外部的明確 expectation，
而不是靠持續擴充禁用詞。

Materialization 後另發現 temp fixture 的 state coupling：fixture 已複製真實 T5P outputs，舊 setup 卻會刪除過多 parent inputs，使測試環境不同於正式
workspace。修正後 temp fixture 只移除三個 T5P outputs（兩個 private preparation files 與一個 public manifest），完整保留 catalog-v2、CAR-T4 與
CAR-T4A parents，再驗證 created／unchanged。這說明「測試全綠」仍必須確認測試準備本身沒有改變被驗對象。

### 最終 QA、仍保留的邊界與下一步

最終獨立 QA 判定 **PASS**：CAR-T5P focused `23 passed`、authority suite `199 passed`、full repository `1268 passed`；Ruff、Ruff format、strict
MyPy、compileall、permissions、privacy、canonical bytes、ignore behavior、parent immutability 與兩次 unchanged checks 全部通過。唯一訊息是既有、
無關的 Starlette deprecation warning。本次 Project Log 策展沒有重跑測試。

下一個合法動作只有 **Owner Gate T5-G1**：owner 必須對 frozen packet 明確給出 20 筆 outcomes，系統才可追加 `staged -> reviewed` events。準備完成
本身不授權 T5-G2 exact approval、authority bundle、CAR-T6／RHB re-audit 或 RHB-T5，也不建立 manufacturer truth、accuracy 或 benchmark-ready 結論。

## 2026-09-30 — CAR-T4A：以獨立 owner Gate 套用 20 筆 catalog proposals

### 新執行了什麼，以及解決了什麼問題

CAR-T4 的 20 筆 proposals 已完成 review，但前一輪刻意停在 `staged`，因為 proposal approval 不是 catalog write authorization。本輪取得另一道
明確的 catalog-application owner Gate，才將完整 batch 套用至 canonical namespace；owner exact response 只保存在 Git-ignored private event，
本日誌不公開該文字或 private candidate／review payload。Application 第一次執行回報 `created`，read-only check 回報 `valid`，相同輸入重播
回報 `unchanged`，解決了如何在不重做人工 review、也不擴張其授權範圍的情況下，把已核准 proposals 安全轉成可由 runtime 使用的 catalog rows。

資料面由 120-row `fixture-v1` parent 產生 140-row `catalog-v2` child：原 120 筆 synthetic regression rows 保持原順序與 record-level content，
後方依 packet order 追加 20 筆 community-snapshot rows。20 筆的 `color`／`edition` 全部維持 `null`，exact authority 仍為 `0`，RHB-T5
authorization 仍為 `false`。最終 catalog SHA-256 是 `e763c8739a76ab4cc9b66169aecd4aea241ee810d8a27cdfb7d05bcacd98562e`，data
manifest SHA-256 是 `38b7d3c0332bbbf757979576d796e08ace6659aa158de3e9466f5ed22dc2fac5`，public application manifest
SHA-256 是 `cf1c95ec8985f80f9ee48c2d8af8b297f5e7d771eff3bb07990034643e4b37b4`。

### 修改了哪些 code／data，以及為何這樣選

程式面新增 strict catalog-v2 schema、deterministic proposal materializer、catalog-only application CLI、private authorization／transaction journal、
public safe manifest 與 atomic recovery；既有 catalog loader、fixture validator／generator guard、in-memory ingestion 和 PostgreSQL ingestion 也擴充為
理解 catalog-v2。Alembic migration `0004` 加入 nullable `release_key`／`normalized_release_key` pair、normalized uniqueness 與 pair consistency，
讓 legacy 120 rows 不需偽造新欄位，同時能保存新 release identity。

資料面只修改 current catalog、data manifest、safe public application manifest 與必要 lineage/task status，沒有回寫 frozen proposal／review events。
Identity 採 owner-approved `release_key` 加 typed toy identifier，因為 20 筆中有多個 releases 共享 casting、year、series、collector 與 position，而實際
color／edition 又沒有證據。用明確 release fields 可保留不同 releases；用猜測顏色、edition、alias 或 rarity 來製造唯一性，則會把 catalog identity
錯寫成未經證實的 physical truth。歷史 RHB／CAR artifacts 仍綁定可重建的 120-row parent，避免 catalog 成長後偷換舊評估母體。

### QA 發現的失敗、修復與方法決策

Pre-apply QA 先後逼出四個不能用 happy-path tests 取代的問題。第一，hash 自洽不足以證明完整 review history，因此 application 另驗 Git
first-parent anchor，拒絕重寫 event 20 後重新雜湊。第二，staging 在 durable journal 前失敗可能留下 orphan；修復後 pre-journal failure 必須清乾淨，
retry 才能安全重來。第三，journal 若可自行描述 targets 會成為任意檔案 mutation surface，因此 recovery 改採四個 canonical targets 的 strict
allowlist，並在任何寫入前拒絕 unrelated、duplicate、omitted、reordered 或 swapped entries。第四，四個 child outputs 已完成 promotion、transaction
directory 已清除，但 journal unlink 中斷時，recovery 曾無法確認完成；修復後以完整 child hashes 辨識 committed child state、安全清理 journal，且
後續 check／replay 維持 idempotent。

最終 pre-apply QA 為 `47 passed` focused、`1243 passed` full suite；Ruff、format、strict MyPy、compileall、Source Gate、builders、ledger、fixture
validation、JSON、privacy／secret／symlink 與 diff checks 全部通過，只有既有 Starlette／AnyIO deprecation warning。Pre-apply 全綠仍沒有被當作
真實資料落地後的結果：post-apply 驗證發現 fixture／history tests 曾把 current 140-row child 當成 historical 120-row parent 的 test-state coupling。
修正後改由 generator 重建 immutable parent、比對 child 前 120 rows 並重算 canonical parent hash，使歷史 checks 與 current runtime 各自使用正確
狀態，而不是修改舊 evidence 迎合新 catalog。

同一輪也清理 9 個 scoped Ruff issues：兩個 shebang scripts 補 executable bit，七個 invalid-type paths 改用正確的 `TypeError`；這些修復未改變
資料或 application scope，affected tests 為 `21 passed`。最終獨立 post-apply QA 判定 **PASS**：真實 application `--check` 為 `valid`，temporary
replay 為 `unchanged`；140 rows 精確等於 immutable 120-row parent 加 packet-order 20-row suffix，且 20 筆 color／edition 全為 null。Loader、
`ResolverService`、in-memory ingestion 通過，PostgreSQL repository／migration／runtime standalone subset 為 `26 passed`；historical CAR／Fandom／RHB／
release／human-alignment checks 保持 `valid`、`unchanged` 或 byte-identical。

最終 focused tests 為 `201 passed`，full suite 為 `1245 passed, 1 warning`；Ruff／format（17 files）、strict MyPy（8 implementation／scripts）、
compileall、JSON／hash、privacy／secret、license、symlink 與 diff checks 全部通過。唯一 warning 仍是既有 Starlette／AnyIO deprecation；三個已記錄
application hashes 亦精確吻合。這完成 CAR-T4A Lean G3，但結論只涵蓋 catalog application，不涵蓋 exact truth、resolver accuracy 或 benchmark readiness。

### 留下的邊界與下一步

Catalog application 只表示 20 個 owner-reviewed identities 已進入 catalog namespace，不是 Mattel／manufacturer truth，也不代表 benchmark 已
ready。下一個產品 Gate 仍是**獨立 CAR-T5 exact-authority review**；不得因 catalog 已有 140 rows 就自動建立
`approved_exact` authority bundle、重判 RHB-T4 或啟動 RHB-T5。

## 2026-09-30 — Catalog proposal bulk owner review：完成 ordinals 5–20，但不自動套用 catalog

### 新執行了什麼，以及解決了什麼問題

Owner 以一段明確的 bulk attestation 完成 canonical queue 剩餘 ordinals 5–20 的審查。為避免公開文件擴散原始授權內容，本日誌不重述該
exact literal；原文只保存在 Git-ignored private ledger。系統也沒有把一段 bulk 回覆偽裝成 16 次使用者逐筆發言，而是將同一份已驗證授權
正確展開為 16 個分別綁定 ordinal、candidate、proposal、packet、product、六個 accepted mappings、null constraints 與 predecessor hash 的
decision events。既有 events 1–4 的 bytes 與 hashes 全部保持不變，解決了「一次確認全部剩餘資料」如何在不捏造對話、不改寫歷史的前提下
進入既有 append-only contract。

執行採逐筆 `record → precheck → commit → postcheck`，依序建立 Decision 05–20 共 16 個 local first-parent anchor commits。這是目前最安全的
做法，因為已驗證的 contract 明確要求每次 event count 只能 `+1`，且每個 introduction commit 都要錨定自己的 first parent；任一步失敗即可停在
最後一個有效 committed prefix，再從下一個 ordinal 安全續跑。沒有為了「一次批准 16 筆」改成 atomic multi-event append，因為那會要求放寬
one-event contract、history validator 與既有攻擊測試，削弱已建立的 provenance，而不是單純提升效率。

### 修改了哪一部分，以及為何先修完成狀態

真正執行 bulk review 前，先發現並修正 progress contract／renderer 的 finish-state bug：原邏輯在 20／20 完成時仍會把 `next_gate` 指向繼續
逐筆審查。修正後，只有完整 20／20 才能輸出 `separate_catalog_batch_application_owner_gate`；1–19 筆仍必須維持 sequential review Gate，
且 status、pending count 與 next Gate 不一致時 fail closed。這項修改先證明當時既有 4／20 public progress bytes 完全不變，再開始追加 events，
避免用 finish-state 修復暗中重寫已錨定的前四筆歷史。

每個 anchor 同步維護公開 progress／method；完成後 tasks 的 20／20 狀態與 source manifest 中的 tasks hash 亦已同步。最後狀態為 owner-approved
proposals `20`、pending `0`，但 20 筆 proposal artifacts 仍全部是 `staged`。Catalog applied=`0`、exact authority=`0`、RHB-T5
authorization=`false`；本輪既沒有更改 canonical catalog，也沒有把第三方 source proposal 宣稱成 Mattel 官方真值。

### 為何 review 完成仍不會自動修改 catalog

這次 owner 授權的 bounded scope 是完成 catalog proposal review，並允許 20 筆 staged proposals 進入下一道獨立 Gate；它不是 catalog write
authorization，更不是 exact-variant authority approval。讓 review event 自動 mutation catalog，會把「人已看過候選資料」與「批准寫入 canonical
namespace」兩種不同風險的決策合併，也會繞過原本要求的 separate batch Gate。因此完成狀態只改變 review progress，不改變 proposal staging、
authority metadata、resolver output boundary 或 RHB-T5 狀態。

### 最終 QA、留下的邊界與下一步

獨立 QA 判定 **PASS**：6／6 attack cases 全部拒絕；CAR focused tests 為 `150 passed`，完整 repository suite 為 `1201 passed`。Ruff、Ruff
format、strict MyPy、compileall、CAR-T1 Source Gate、兩個 builders、default decision check、privacy／secret scan、JSON parse 與 diff check
全部通過；catalog、proposal bundle 與 packet hashes 均未漂移。唯一訊息仍是既有 Starlette／AnyIO deprecation warning，與本輪變更無關。
這些結果來自已完成的獨立 QA；本次 Project Log 策展沒有重跑測試。

Decision 05–20 的 16 個 local anchors、finish-state 修復與最後同步 commit 均仍未 push，本日誌不逐一列出所有 SHA。下一個合法步驟是由 owner
另外明確授權 `separate_catalog_batch_application_owner_gate`；在取得該授權前，不得套用 catalog、建立 exact authority 或啟動 RHB-T5。

## 2026-09-30 — Remaining catalog review queue audit — prepare all records before approvals

### 新執行了什麼，以及解決了什麼問題

使用者要求先把本輪所有待審資料準備完整，再依 canonical order 逐筆確認；本輪因此只做剩餘 review queue 的唯讀稽核，沒有把「已準備」推定為
「已批准」。CAR-T4 frozen packet 原本就已包含 20 筆完整 proposal，private append-only ledger 則仍是該 packet ordinal 1–4 的精確
event prefix；兩者相減後，待審範圍明確是 ordinals 5–20，共 16 筆。這解決了後續審查前最重要的範圍問題：owner 可以逐筆檢視全部剩餘資料，
但系統不會因為 queue 已經整理完成，就替 owner 產生任何新的 decision event。

待審 view 不另存成第二份可漂移清單，而是唯讀推導為 `packet.entries[len(ledger.events):]`。稽核確認這 16 筆橫跨 7 個 casting families；每筆
candidate ID、proposal ID、deterministic UUID 與 release key 都唯一，並具備 casting、release year、series、collector number、series
position、identifiers 六個 evidence mappings。所有 records 都維持 `source=proposed`、`color=null`、`edition=null`；variant notes 只作
context，分布為 `2nd Color` 5 筆、`2nd Color - Zamac` 2 筆、`3rd Color` 3 筆，另有 6 筆沒有 note。每筆仍是 staged／unapplied，沒有
authority、reviewer metadata 或 owner decision，且 `resolver_output_consulted=false`。

### 為何沒有修改 code、data 或 spec

本輪沒有新增程式碼、重建 packet、改寫資料或調整規格。既有 packet、proposal set、公開 progress 與 source snapshot 已透過 deterministic
ordering 和 hashes 綁定；OWNER-REVIEW 與 private ledger 又是 fail-closed 的 append-only provenance。若為了呈現剩餘清單而重寫
OWNER-REVIEW、複製一份新的「pending truth」，或預先建立 16 個假 decision events，不只會產生兩份可能不一致的狀態，也會破壞已通過 QA 的
provenance chain。直接由 frozen packet 扣除 exact ledger prefix，能保留單一 canonical source，且把「尚未 review」維持為真正沒有事件的
狀態。

這也是本輪技術選擇的核心：queue preparation 是查詢，不是 mutation。Hash 自洽只用來確認目前 artifacts 沒有漂移，不被解讀為 owner
authorization；每一筆 approval 仍必須由 owner 提供明確、bounded 的回覆，再經既有 `ExpectedOwnerAuthorization` 與 Git first-parent
機制個別記錄。

### 驗證、留下的邊界與下一步

獨立 QA 判定 **PASS**：decision check 顯示 valid，狀態精確為 4 筆已記錄／16 筆 pending；兩個 builders 均回報 `unchanged`，CAR-T1
Source Gate valid，catalog／proposal／packet／progress hashes 全部符合，Git status 與 diff check 也保持 clean。因本輪沒有 code 或 data
mutation，完整 repository suite 刻意沒有重跑；這避免把未產生新風險的唯讀稽核包裝成一次新的功能驗收，也不會把先前測試結果錯記成本輪
執行。

目前 catalog application=`0`、exact authority=`0`、RHB-T5 authorization=`false`；16 筆 pending records 也全部維持 reviewer metadata
空白。下一個合法動作是由 owner 依序審查 ordinals 5–20，而不是先將 proposal 套用 catalog、升格 authority 或啟動 T5。只有新的明確 owner
回答才能讓 ledger 往前增加一筆；本輪稽核本身不授予任何批准。

## 2026-09-30 — Catalog Proposal Decision 04

### 新執行了什麼，以及解決了什麼問題

本輪收到 owner 對 canonical packet 第 4／20 筆的精確回覆：`批准第 4 筆，color 與 edition 保持 null。`。這筆 ordinal `4` proposal
對應 Nissan Skyline 2000GT-R LBWK／`HYX54`；六個 frozen mappings 為 casting=`Nissan Skyline 2000GT-R LBWK`、release year=`2025`、
series=`HW J-Imports`、collector number=`026`、series position=`1/5` 與 identifiers=`HYX54`，deterministic proposed UUID 為
`d2ee5fd2-006e-5758-bdc3-9cfd7f29bcc9`。Owner 的回答只核准這份 catalog proposal 可進入後續 batch Gate，沒有立即修改 catalog。

來源的 `3rd Color` 仍只是第三個顏色順序版本的 context text，不是實際色名證據，也不能建立 edition。因此它不進入六個 accepted mappings，
`color=null`、`edition=null` 繼續作為明確約束。這避免把 release marker 自動推導成產品外觀或 edition truth。

### 為何本輪不需要修改程式碼

Decision 04 直接重用 Decision 02 已建立、Decision 03 已驗證可重複使用的 generic `ExpectedOwnerAuthorization`。Precommit 階段仍由 ledger
外部提供 ordinal、candidate／proposal IDs、decision、exact owner response 與 bounded reason；commit 後仍由 Git first-parent introduction
anchor 保護已提交 event prefix。沒有為 Nissan／HYX54 或第四句回答新增專用分支，也沒有把 literal 硬編碼到產品程式。

同一套 control 能從 ordinal 2、3 延伸到 4，證明它是可重複使用的 owner-authorization contract，而不是只為單一測試案例設計。這降低後續
16 筆審查的重複碼與規則漂移風險，同時保留每筆回答都必須由外部 exact expectation 個別授權的要求。

### 決策範圍、最終 QA 與目前進度

公開進度更新為 owner-approved proposals `4`、pending `16`，held／rejected 為 `0`；20 筆 proposal artifacts 仍全部保持 `staged`。
Catalog applied=`0`、exact authority=`0`、RHB-T5 authorization=`false`。Events 1–3 與 catalog／packet／proposal hashes 維持不變，event 4
正確延伸 event 3；這筆核准不是 catalog application、`approved_exact` authority 或 Mattel 官方認證。

最終獨立 QA 判定 **PASS**：11／11 attacks 全部拒絕，涵蓋 identity、expected authorization、event chain、context／null boundary 與 rehash
攻擊；合法事件則確認 Nissan／HYX54、六個 mapping values、UUID、`3rd Color` context-only 及 `color`／`edition` null。CAR focused tests 為
`149 passed`，完整 repository suite 為 `1200 passed`；Ruff、Ruff format、strict MyPy、compileall、CAR-T1 Source Gate 與兩個 CAR-T4
builders 全部通過。唯一訊息仍是既有 deprecation warning，與 Decision 04 無關。這些結果來自已完成 QA；本次 Project Log 策展沒有重跑
測試。

Decision 04 的本機 anchor commit 為 `1ddef09`。目前本機 `main` 的所有 Decision 01–04 與相關文件 commits 仍全部未 push；本輪只更新
Project Log，不提交或推送。下一步仍須按 canonical order取得第 5／20 筆 owner 決定，不能提前套用 catalog、建立 exact authority 或啟動
RHB-T5。

## 2026-09-29 — Catalog Proposal Decision 03

### 新執行了什麼，以及解決了什麼問題

本輪收到 owner 對 canonical packet 第 3／20 筆的精確回覆：`批准第 3 筆，color 與 edition 保持 null。`。這筆 ordinal `3` proposal
對應 Subaru BRZ／`JBB55`，owner 接受的六個 frozen source-to-proposal mappings 是 casting=`Subaru BRZ`、release year=`2025`、
series=`HW J-Imports`、collector number=`048`、series position=`3/5` 與 identifiers=`JBB55`；proposal 的 deterministic UUID 為
`76188645-6430-559e-96a2-73a844524763`。Decision 03 因而可進入稍後 catalog batch Gate，但目前仍只是已審 proposal，不是已套用的
catalog record。

來源列中的 `3rd Color` 只表示來源如何標記第三個顏色順序版本，沒有提供實際色名，也不能證明 edition。因此它繼續以 context-only sequence
text 保存，不進入六個 accepted mappings；`color=null`、`edition=null` 仍是 owner 授權中的明確限制。這避免把「第三色」錯誤翻譯成某個
具體顏色，或把 release note 自動升格為 exact product field。

### 為何本輪不需要新增程式碼

Decision 03 沒有新增 decision-specific validator 或硬編碼第三句回覆。它直接重用 Decision 02 建立的 generic
`ExpectedOwnerAuthorization`：precommit 驗證由 ledger 外部明確提供 ordinal、candidate ID、proposal ID、decision、exact owner response 與
bounded reason，再逐欄比對唯一新增事件；提交後則沿用 Git first-parent introduction anchor，防止後續 rehash 或 code-only commits 洗白被
改寫的歷史。

這次不改程式碼本身就是設計證據。若每一筆 owner 回覆都要新增常數或專用分支，20 筆 review 會形成 20 套近似控制，容易讓其中一筆少驗
identity、reason 或 ancestry。現在相同 contract 能安全接受 ordinal 3 的新 exact literal，同時仍拒絕 ledger 自我授權，表示 Decision 02 的
修復已成為可重用機制，而不是只讓第二筆測試通過的特例。

### 決策範圍、QA 與目前進度

公開進度現在是 owner-approved proposals `3`、pending `17`，held／rejected 均為 `0`。20 筆 proposal artifacts 仍全部是 `staged`；catalog
applied=`0`、exact authority=`0`、RHB-T5 authorization=`false`。Event 01／02 保持不變，event 03 的 `previous_event_sha256` 正確指向
event 02；catalog、packet 與 proposal parent hashes 也未改變。即使這筆未來通過 batch application，也只會建立 catalog namespace record，
不會自動成為 `approved_exact` authority 或 Mattel 官方認證。

最終獨立 QA 判定 **PASS**。11／11 attacks 全部拒絕，涵蓋把 `color` 從 null 改成推測值、同步改寫 paraphrase 後完整 rehash、刪除 event
03、重排 events，以及錯誤 expected candidate／proposal IDs 等情境；合法事件則確認 Subaru BRZ／JBB55 identity、六欄 values、UUID、
context-only `3rd Color` 與兩個 null constraints。Decision tests 為 `31 passed`，其他 CAR focused tests 為 `149 passed`，完整 repository
suite 為 `1200 passed`；Ruff、Ruff format、strict MyPy、compileall、CAR-T1 Source Gate 與兩個 CAR-T4 builders 全部通過。唯一訊息仍是
既有 deprecation warning，與 Decision 03 無關。這些結果來自已完成 QA；本次 Project Log 策展沒有重跑測試。

Decision 03 的本機 anchor commit 為 `e0a0139`。目前本機 `main` 連同先前 Decision 01／02 與文件 commits 全部仍未 push；本輪只更新
Project Log，不提交或推送。下一步仍須按 canonical order取得第 4／20 筆 owner 決定，不能提前套用 catalog、建立 exact authority 或啟動
RHB-T5。

## 2026-09-29 — Catalog Proposal Decision 02：以外部 expected authorization 阻止未提交事件自我授權

### 新執行了什麼，以及解決了什麼問題

本輪收到 owner 對 canonical packet 第 2／20 筆的精確回覆：`批准第 2 筆，color 與 edition 保持 null。`。這筆 proposal 對應
Draftnator／`HYW70`，以 ordinal `2` 追加到 private decision ledger；六個 frozen mappings 為 casting、release year、series、collector
number、series position 與 identifiers，`color`、`edition` 仍強制為 `null`。Decision 02 因而記為可進入稍後 catalog batch Gate，但不會
立即套用 catalog record。

公開進度由 1／20 更新為 owner-approved proposals `2`、pending `18`，held／rejected 仍為 `0`。20 筆 proposal artifacts 繼續保持
`staged`；catalog applied=`0`、exact authority=`0`、RHB-T5 authorization=`false`。這一步解決的是第二筆 proposal 的 owner 決定與事件鏈
延伸，不是將 Draftnator／HYW70 宣告為 Mattel 官方真值或 benchmark authority。

### 修改了哪個契約部分，以及為何需要外部 ExpectedOwnerAuthorization

Decision 01 使用固定在程式中的 exact literal，因此 event 本身無法任意改寫 owner 文字；但 generic event 02 原設計同時從 mutable ledger 讀取
`owner_response_verbatim` 與 `authorized_exact_owner_response`。只要攻擊者把兩者同步改成同一段 paraphrase，再重算 authorization、event、
ledger 與 public progress 的所有 hashes，未提交狀態就可能自我宣稱「這正是被授權的原句」。QA 已實際重現這個 precommit acceptance，證明
兩個互相相等的 mutable fields 不是外部 authorization source。

修正後新增 strict `ExpectedOwnerAuthorization`，由 ledger 之外的呼叫端提供 ordinal、candidate ID、proposal ID、decision、完整 exact owner
response 與 bounded review reason。Precommit validator 必須把唯一新增事件逐欄對照這份外部 expectation；缺任一 expected value、candidate／
proposal 對錯、decision／reason 不符或 response 被改寫都 fail closed。這個方法保留 generic recorder 支援後續 ordinal 3–20，同時不必把每一句
owner 回覆都硬編碼進產品程式。

外部 expectation 解決的是**尚未提交**事件不能自我授權；event commit 完成後，前一輪建立的 Git first-parent 規則繼續負責**已提交**歷史。
Validator 會定位 progress 的 introduction commit，要求其 anchor 指向 introduction commit 的第一個 parent，並拒絕後續 code-only commit
洗白 rewrite。兩層分工很重要：expected authorization 證明「本次準備提交的文字確實是 owner 指定內容」，Git ancestry 則證明「提交後的事件
前綴沒有被重寫」。SHA-256 只負責 bytes binding，仍不被當成人類授權本身。

### QA 中途不穩定訊號、攻擊矩陣與最終結果

修復期間的一次中間 QA 曾遇到 duplicate CLI argument 與 test expectation mismatch，使檢查結果不穩定；這是 CLI／測試介面尚未同步，不能被
當作功能 PASS。最後將參數定義與測試 fixture 對齊後再完整重驗，避免用偶然通過或測試本身寫錯來放行。這也延續本專案的原則：測試數字只有
在 harness 本身穩定且能重現攻擊時才是有效證據。

最終 attack matrix 確認以下全部拒絕：刪除 event 02、將 event 01／02 重排、把 owner response 與 authorized response 同步改成 paraphrase 後
完整 rehash、改成錯誤 candidate、改成錯誤 proposal，以及缺少或提供錯誤 external expected values。合法 Decision 02 則確認 ordinal、
Draftnator／HYW70 identity、六個 mappings、`color=null`、`edition=null`、event 01 hash 不變，且 event 02 的
`previous_event_sha256` 正確指向 event 01。

最終獨立 QA 判定 **PASS**：catalog decision tests 為 `31 passed`，其他 CAR focused tests 為 `118 passed`，完整 repository suite 為
`1200 passed`。Ruff、Ruff format、strict MyPy、compileall、CAR-T1 Source Gate 與兩個 CAR-T4 builders 全部通過；private ledger 仍在
Git-ignored local directory，public artifact 仍只包含 aggregate 與 hashes。這些結果來自已完成 QA；本次 Project Log 策展沒有重跑測試。

Decision 02 的本機 Git anchor commit 為 `dcd21e4`。先前三個本機 commits `bb073f3`、`1f617a5`、`272afc3` 以及本次 `dcd21e4` 均
**尚未 push**；本輪只更新 Project Log，不提交或推送。下一步仍須按 canonical order取得第 3／20 筆 owner 決定，不能提前套用 catalog、
建立 exact authority 或啟動 RHB-T5。

## 2026-09-29 — Catalog Proposal Decision 01：記錄第一筆 owner 核准並以 Git 歷史錨定 append-only 證據

### 新執行了什麼，以及解決了什麼問題

CAR-T4 已產生 20 筆 staged catalog proposals，但它們仍全部等待 owner 判斷。本輪收到 owner 對 canonical packet 第 1／20 筆的精確回覆
`批准，color 與 edition 保持 null。`，並將這一筆記錄為 `approved_for_later_batch_gate`。這解決了第一筆 proposal 是否接受六個 frozen
source-to-proposal mappings 的待決問題，同時把 owner 明確保留的兩個空值寫成強制限制，而不是把「批准」擴張成自動補色、補 edition、
立即寫 catalog 或批准 exact authority。

決策完成後，公開進度為 recorded 1／20、approved-for-later-batch-gate 1、held 0、rejected 0、pending 19。這裡的 approved 表示「可以在所有
proposal review 完成後，進入另一個 catalog batch application Gate」，不是現在已建立 canonical truth。Proposal artifacts 仍保持 staged，
`data/catalog.json` 沒有套用變更。

### 修改了哪些契約部分，以及為何採 exact literal、private ledger 與 public aggregate

新增 catalog decision recorder／validator，將每次 owner 回答綁定 packet、proposal、product record、raw catalog、projection、前一個 event
與 UTC review metadata。Decision 01 採 **exact-literal authorization**：經 Unicode normalization 後，實際回覆必須完整等於
`批准，color 與 edition 保持 null。`，並且 authorization contract、固定 approval reason、六個 accepted field mappings、
`color_must_remain_null`、`edition_must_remain_null`、`catalog_application_deferred` 與 `authority_approval_not_granted` 都必須一起成立。選擇完整
字面契約而不是關鍵字分類，是因為 `批准` 出現在否定句、引用句或較長 paraphrase 中，不能被當成同一份人類授權。

完整 owner verbatim、candidate／proposal identity 與逐事件鏈保存在既有 Git-ignored local directory 的 private append-only ledger；Git 只提交
不含名稱、IDs、問題或 verbatim 的 public progress aggregate 與不可逆 hashes。這個 private/public split 讓後續 validator 可以驗證 decision
順序、packet binding 與 ledger 完整性，同時不把本機逐筆 review 內容擴大公開。公開 method 另明確寫出 1 approved、19 pending、0 applied、
0 authority 與下一個 Gate，避免只看 hash 就誤以為 catalog 已完成。

### 為何 hash 自洽仍不足以證明歷史，以及三輪 QA 如何修正

第一輪 QA 發現 substring／negation 風險：若 validator 只搜尋 `批准` 或允許較寬鬆文字，包含核准字樣的否定句、中文改寫或英文版本也可能被
誤認為 owner 原意。修正後 event 1 的 authorization literal 固定，owner response 必須精確一致；否定、paraphrase 與翻譯全部拒絕。這使
「程式覺得語意相近」不能替代 owner 實際給出的 bounded statement。

第二輪 QA 進一步證明，private ledger、public progress 與所有 inner／outer hashes 即使完全自洽，仍不能證明過去沒有被整份重寫：攻擊者
可以修改已記錄 event，再把每層 digest 一起重算。修正因此引入 Git commit 作為 JSON 外部的 immutable history anchor；新 progress 必須指向
已提交 predecessor，而不是只信任自己宣稱的 previous hash。這個設計使用 repository 原本就有的 commit DAG，不另建資料庫或簽章服務，
代價是 decision validator 必須同時驗證 Git history。

第三輪 QA 又找到 **code-only laundering**：若惡意 committed rewrite 在 commit M 當下會被拒絕，但 M 後再做一個沒有修改 progress 的普通
code-only child，單看目前 HEAD 可能錯把 child 當成可信 predecessor，讓被改寫的 history 洗白。最終修正沿 Git **first-parent** 向後走過
所有 progress bytes 完全相同的連續 commits，定位真正引入該 progress 的 introduction commit，再要求 progress 的
`anchor_commit_sha` 必須等於該 introduction commit 的第一個 parent。First-parent 是明確的 merge lineage；後續 code-only commits 不會改變
真正的 introduction point，也就不能消除 M 的錯誤 anchor。

這三輪演進保留了一個重要工程判斷：SHA-256 可以證明「現在這批 bytes 彼此一致」，不能單獨證明「歷史上從未被替換」。只有 exact human
authorization、append-only event chain、public/private hash binding 與外部 Git ancestry 同時成立，才能對 Decision 01 提供目前宣稱的歷史
完整性；這仍不是 Mattel 官方真值證明。

### 決策範圍、最終 QA 與目前狀態

Decision 01 只接受 casting、release year、series、collector number、series position 與 identifiers 六個 frozen mappings，並強制
`color=null`、`edition=null`。Catalog record 尚未套用，catalog mutations=`0`、exact authority=`0`、RHB-T5 authorization=`false`；剩餘
19 筆 proposals 仍 pending。即使未來這筆 catalog record 通過 batch application，它也只建立 namespace record，不能自動成為
`approved_exact` authority。

最終獨立 QA 判定 **PASS**：focused tests 為 `147 passed`，完整 repository suite 為 `1198 passed`；Ruff、Ruff format、strict MyPy、
compileall、CAR-T1 Source Gate 與兩個 CAR-T4 builders 全部通過。Git history attack matrix 也確認惡意 rewrite commit M、其 child 及
grandchild 都持續被拒絕，不能以後續普通 commit 洗白；相對地，連續合法 code-only commits 都能通過，不會因文件或程式演進而誤擋有效
Decision 01。這些結果來自已完成 QA；本次 Project Log 策展沒有重跑測試。

Decision 01 的初始 recorder／anchor 變更已形成本機 commit `bb073f3`，first-parent history hardening 為本機 commit `1f617a5`；兩者目前
**尚未 push**。本輪只追加 Project Log，也沒有提交或推送。下一步仍是依 canonical packet order取得第 2／20 筆 owner 決定，而不是套用
catalog、建立 authority event 或啟動 RHB-T5。

## 2026-09-29 — CAR-T4：建立本機 output-blind catalog proposal packet，仍維持 0 authority

### 新執行了什麼，以及解決了什麼問題

本輪延續 Lite／Lean Industrial 模式，完成 [CAR-T4 packet／catalog proposal tooling](../specs/canonical-authority-review-v1/tasks.md)：
從 CAR-T3 owner-approved primary 20 建立本機 output-blind catalog proposal review packet，產生 20 筆 deterministic staged proposals；
surplus 9 筆明確排除，不會在未經新決定下補進 primary。現有 catalog 中可用於真實 review 的 eligible UUID 為 `0`，因此 20 筆全部走
「缺少 canonical record、等待 owner 審查」路徑，而不是假裝找到 existing exact match。

這一步解決的是候選已選定、但尚無可安全綁定真實 release 的 catalog records。Git 只保存 safe manifest 的 hashes、counts、telemetry 與
下一個 Gate；20 筆逐列 proposals、review packet、空白 decision template 與 owner Markdown 全部寫入精確 Git-ignored 的
`data/authority-review/canonical-authority-review-v1/local-catalog-review-v1/`。Public／local split 讓 repository 可驗證工作確實建立，又不把
尚未決策的逐列 proposal 當成公開 authority artifact。

### 為何沒有沿用既有 UUID，以及為何新增 raw-bound projection V2

`data/catalog.json` 是本專案 canonical UUID namespace 的 parent，但離線重算確認其中 120／120 products 都有完整 synthetic-fixture
provenance；raw catalog 自己也明示只用於架構與測試驗證。它可以提供 namespace、版本與 collision universe，卻不能證明真實 Hot Wheels
release。另一份 `human_backed_catalog` 只有 casting-level／provisional draft context，包含尚待 canonical review 的名稱線索，同樣不能建立
exact release UUID。資料存在或名稱相似都不足以跨過 authority Gate，因此 existing eligible exact match 保持 `0`。

既有 CAR-T2 `FrozenCatalogParent` v1 要求非空 products，適合驗證已知 eligible canonical members；直接把它放寬成允許空集合，會默默改變
已通過的舊契約。CAR-T4 因此另建版本化 `FrozenCatalogProjectionV2`：它允許 `eligible_products=[]`，但同時綁定 raw file bytes SHA、catalog
version、120 product count、完整 raw UUID-set digest、synthetic exclusion count 與 projection hash。即使 120 筆都不 eligible，20 個
deterministic proposal UUID 仍必須對**全部 raw UUID**做 collision check。這個選型保留 v1 的既有安全語意，也讓「合法空 eligible set」成為
明確狀態，而不是把空集合誤當 catalog 尚未載入。

Raw catalog bytes 維持 SHA-256
`0d3ea55eab414e3845bf3bf72635707210f2d5c20d96b3d6b5940eb0ffc7d261`，本輪沒有修改 `data/catalog.json`，也沒有從 Mattel 或其他來源
新增官方真值。

### 修改了哪些程式部分，以及技術選型原因

共用模組 `canonical_authority_packet.py` 集中 strict raw catalog parsing、V2 projection、proposal／packet contracts、deterministic derivation、
cross-artifact validation、path policy 與 publication transaction；兩個 thin scripts 分別提供 catalog-proposal 與 review-packet 的 build／
`--check` 入口，但實際呼叫同一個 `publish_workspace`。選擇共用核心加薄 CLI，而不是複製兩套 builder，是為了確保兩個操作看到相同 parent
hashes、proposal bytes、partial-state policy 與 rollback 行為，不會日後其中一支少做 collision 或 output-blind 檢查。

每筆 proposal 使用固定 namespace 與 source row 產生 deterministic UUID，並建立六個 source-to-proposal pending mappings：casting、release
year、series、collector number、series position 與 `toy_number→identifiers`。這六筆 evidence 都逐列綁定 frozen source record，狀態是
`pending_owner_review`，不能冒充 owner agreement。`color` 與 `edition` 一律為 `null`；13 筆存在的 variant notes 只顯示為
`context_only_not_color_or_edition_evidence`，所以 `Zamac`、`2nd/3rd Color` 或 `Red Edition` 不會被轉成結構化真值。

Publication 支援第一次 `created`、相同輸入重跑 `unchanged`，以及只驗不寫的 `--check`。本機四個檔案先在同 parent 暫存目錄完整寫入並
`fsync`，public manifest 也先寫 staging file，再以 atomic replace 發布；若第二段失敗，會回滾本輪剛建立的 local directory。Public manifest
只留下 raw／projection／packet hashes、20 staged、9 excluded、120 synthetic、0 approved／applied／exact 等安全 aggregate。Tasks 因
CAR-T4 完成改成 `CAR-T1–T4 complete; catalog proposal owner review pending; T5+ not started`，綁定 tasks 的 Source Gate parent SHA 更新為
`01a92b4e9c87578f2e7137f8314b3e97ba8b0321fc1437326c27f41cab313e83`，但 Source Gate scope 本身沒有擴張。

### 首次 QA 為何 FAIL，以及如何修正

初版功能的正常建立、重跑與 artifacts tests 雖然全綠，獨立 QA 仍判定 FAIL。首先，自訂 local output 接受 absolute path，且只檢查 leaf
symlink，攻擊者可在中間 ancestor 放 symlink 把輸出導出 repository；其次，只有 public manifest、沒有 local packet 的 asymmetric partial
state 會被 builder 自動「修好」，掩蓋可能的遺失或篡改。這證明 happy-path determinism 不等於 filesystem boundary 安全，也不能把自動修復
partial state 當便利功能。

修正後 local output 必須是 repository-relative、CAR directory 下符合命名規則的 direct child，且必須被 `.gitignore` **精確**列出；從 repo
root 到 target 的每個 ancestor 都用 `lstat` 檢查 symlink，並同時驗證 lexical 與 resolved containment。Local／manifest 存在狀態採 XOR
fail closed：任一單獨存在都拒絕，不自行重建另一半；既有 bytes 有 drift 也不覆寫。這樣能把「第一次雙邊建立」與「事後修補可疑狀態」清楚
分開。

QA 也發現 machine-readable packet 雖完整，初版 owner Markdown 沒有逐欄列出 evidence、issues 與全部 13 筆 variant-note context；若人類只看
Markdown，就無法做與 JSON 等價的 informed review。修正後 20 個 entries 全部呈現六欄，共 120 條 evidence lines；每筆都有
missing／conflicting issues 與 pending owner question，13 筆 notes 也逐項標為 context-only。最後，strict MyPy 找到 5 個 typing errors，透過
正確 imports 與型別界線修正。這些失敗說明測試全綠仍可能只覆蓋「機器能生成檔案」，卻漏掉 hostile paths、跨檔 partial state、
human-readable completeness 與 static type contract；因此 QA attack harness 和工具鏈是必要的獨立驗證層。

### 最終 QA 證據、仍保留的邊界與風險

修復後獨立 QA 判定 **PASS**：9／9 targeted attack／path cases 通過；focused CAR／RHB 為 `194 passed`，API／catalog regression 為
`86 passed`，完整 repository suite 為 `1169 passed`。Ruff、Ruff format、strict MyPy、compileall、JSON parsing、CAR-T1 Source Gate、
secret scan 與 `git diff --check` 全綠；兩個 thin scripts 的 `--check` 都回傳 `unchanged`。Raw catalog SHA 保持不變，完整測試唯一訊息仍是
既有 Starlette `BlockingPortal` deprecation warning。這些結果來自已完成 QA；本次 Project Log 策展只執行 docs diff-check 與必要文字
檢查，沒有重跑測試。

仍有一項非阻擋風險：若有惡意本機程序精準地在 path 檢查與 atomic write 之間置換 filesystem objects，仍存在狹窄 TOCTOU window。現有
ancestor checks、direct-child policy、exact ignore、exclusive staging、atomic replace、XOR detection 與 rollback 已處理一般 drift／symlink／
partial failure，但沒有宣稱能抵抗同機 hostile process 的所有 race。對此履歷專案的本機、單使用者 workflow，QA 將它列為 deferred risk，
不是已解決的安全保證。

本輪結束時 20 筆 proposal 全部仍是 `staged`，`reviewed_by_role`、`reviewed_at`、`review_reason` 與 decisions 均為空；approved proposals=`0`、
applied catalog records=`0`、catalog mutations=`0`、exact authority=`0`，RHB-T5 authorization=`false`。建立 deterministic UUID 與六欄 mapping
只是提出 catalog record 草案，不是 catalog approval，更不是 exact authority 或 Mattel 官方認證。

### 真正下一個 Gate

下一步是 **owner catalog-proposal review Gate**，不是直接進入 CAR-T5 authority review，本輪也尚未執行。Owner 必須逐筆審查 20 個 proposals，
或給出範圍明確、仍可逐筆驗證的 bounded approval；每個缺 UUID proposal 經核准後，還要以 separate commit 套用 catalog mutation。Catalog
approval 只建立可引用的 namespace record，不會自動 promotion 成 exact authority。只有 proposal review／application 有合法結果後，才能另行
評估 CAR-T5 的 output-blind authority events 與 bundle freeze；目前不得建立 T5 review events 或啟動 RHB-T5。

## 2026-09-29 — CAR-T3：由固定 100-row 建立並核准 output-blind review queue

### 新執行了什麼，以及解決了什麼問題

本輪延續 Lite／Lean Industrial 模式，完成 [CAR-T3 owner Gate](../specs/canonical-authority-review-v1/tasks.md)：只從 CAR-T1 已核准的
固定 100-row Hot Wheels Wiki snapshot 中，建立一個可重現、可由 owner 審查的 candidate queue。Owner 核准的 primary queue 是
**20 筆候選、7 個 source-label families**，另保留 **9 筆候選、3 個 families** 作 surplus fallback。這解決了 CAR-T2 雖已具備 strict
contracts，卻仍不知道「接下來實際要先審哪些 rows」的問題；現在 CAR-T4 可以有明確輸入，但這 29 筆仍只是待審工作清單，不是正確
variant 清單。

這一步刻意把「候選數已達 20／families 已超過 4」和「authority 20／4 Gate 已通過」分開。前者只證明 queue 有足夠工作量，後者仍要求
每筆通過 catalog membership、逐欄 evidence、output-blind 人工 review 與 explicit approval。若把 candidate count 直接當 authority count，
就會重現 RHB-T4 已阻擋的問題：有資料列不等於有 independently grounded exact variants。

### 修改內容、deterministic selection rule 與 primary／surplus 取捨

`candidate-plan.md` 將選擇規則、queue composition、review warnings、owner Gate 與未授權事項寫成人可讀計畫；對應的
`candidate-plan.json` 保存相同邊界的 strict machine-readable companion；candidate baseline 則從固定 snapshot 重算 100-row membership、
family grouping、29 個唯一候選與 primary／surplus overlap。Tasks 狀態更新為 `CAR-T1–T3 complete; T4+ not started`，CAR-T3 checkbox 完成後，
Source Gate manifest 中綁定 `tasks.md` 的 parent SHA 也更新為
`ec98fe0607df23c139079e5fe232591e6aff63e3d3d8529968261ad756360d17`。這只是維持既有 parent binding；沒有改變來源授權或擴張
authority scope。

Selection rule 採 deterministic policy：先選出所有「三列、且三列都位於單一 source series」的 eligible families，依不分大小寫的
family label 排序，family 內再依 `source_record_id` 排序。這得到六個 families、18 rows；接著取 frozen source order 中最早符合條件的
兩列 single-series family，補到剛好 20 筆 primary。剩餘三個三列 families 因含 cross-series 或 special-release context，全部放進
9-row surplus。相同 snapshot 依同一規則重跑，會得到相同 7／20 primary 與 3／9 surplus，而不需要 resolver score、模型輸出或人工臨時
挑選。

Primary 與 surplus 分離，是為了讓「最低審查目標」不被 fallback rows 重複灌水，也讓較複雜的跨 series、`Red Edition` 或其他
special-release context 不必在第一批就承擔較高歧義。Surplus 不是次等 truth，也不能自動替換 primary；未來若要移入 primary，仍需新的
owner decision。這項取捨讓第一批 review 優先處理結構較單純的 groups，同時保留 9 筆備援，以免少數 primary rows 在 catalog／evidence
Gate 失敗後完全沒有替代候選。

### Owner 核准的精確語意與不擴張邊界

Owner 原訊息的語意明確批准 CAR-T3 candidate plan，並另外授權把完成內容 push 到 GitHub；核准時間記錄為
`2026-09-29T13:26:17Z`。其中 GitHub push 是 repository 操作授權，不是 data-authority Gate，也不會因程式碼被推送就讓候選成為真值。
本次 owner Gate 只涵蓋 20／7 primary、9／3 surplus，以及 `reviewer_role=project_owner`、
`confirmation_method=owner_attestation`、`resolver_output_consulted=false` 的 output-blind review method。

所有 casting labels 與 series 只作 `candidate_selection_only` grouping；`Zamac`、`2nd Color`、`3rd Color`、`Red Edition` 等字樣也只是後續
review warnings／context，不能填入 color、edition 或 exact release identity。29 筆候選的 `canonical_uuid` 全為 `null`，catalog lookup
都仍是 `pending_car_t4`；verified field values=`0`、exact variants=`0`、authority rows=`0`，color／edition authority 尚未建立，
RHB-T5 authorization 仍為 `false`。因此這一步最多能宣稱 owner 已核准「要審什麼與怎麼審」，不能宣稱 Mattel 官方真值、catalog 已完成
或 benchmark 已準備好。

### QA 發現、最終驗證與留下的限制

初版計畫曾用英文引號表達 owner approval，雖然語意正確，形式上卻可能被讀者誤認為 owner 的逐字英文引言。QA 指出後，文件改成可稽核的
語意摘要：只記錄 owner 明確批准 CAR-T3，以及 push 授權屬於獨立操作權限，不再製造看似 verbatim 的句子。這項修正很小，但重要原因是
approval artifact 不能把 agent 的英文改寫偽裝成人類原話；最終 QA 因此判定 **PASS**，無 Blocker 或 Important finding。

最終重算確認 29／29 candidate `source_record_id` 都唯一且屬於固定 100-row membership，candidate IDs 重複為 0，primary／surplus overlap
為 0。CAR-T1／T2 focused regression 為 `99 passed`，完整 repository regression 為 `1150 passed`；CAR-T1 Source Gate、candidate JSON
canonical/hash、Ruff、Ruff format、strict MyPy、compileall、JSON、secret／PII scan 與 `git diff --check` 全部通過。完整測試唯一訊息仍是
既有 Starlette `BlockingPortal` deprecation warning，與 CAR-T3 無關。這些是已完成 QA 的證據；本次 Project Log 策展只執行文件
diff-check 與必要文字檢查，沒有重跑測試。

### 下一步

下一個順序任務是 **CAR-T4 packet／catalog proposals**，本輪尚未開始。CAR-T4 要把 owner-approved queue 轉成 local-only、output-blind
review packet，並對缺少 canonical UUID 的候選準備 evidence-bound catalog proposal。每一個 missing UUID 都必須另行通過獨立 catalog
approval；catalog proposal 即使獲准，也不能自動 promotion 成 exact authority。CAR-T4 完成前不建立 review events、不凍結 authority
bundle，也不啟動 RHB-T5；architect、security 與 performance review 在 Lite／Lean 範圍內仍為 deferred。

## 2026-09-28 — CAR-T2：建立 canonical authority 的離線嚴格契約，四輪 QA 後放行

### 新執行了什麼，以及解決了什麼問題

本輪延續 Lite／Lean Industrial 模式，只完成
[CAR-T2 strict contracts](../specs/canonical-authority-review-v1/tasks.md)，把 CAR-T1 已核准的固定來源邊界延伸成一套可離線驗證的
candidate、逐欄 evidence、catalog proposal、owner packet、append-only review event、attestation 與 authority bundle 契約。CAR-T1
只能回答「哪份既有快照可進入人工審查」；CAR-T2 要解決的是下一層風險：即使每個 JSON 各自看似合理，錯誤來源列、無關 catalog、
截斷的 review history、重新排列後的 hash 或不完整 evidence 仍可能在跨產物組合時被誤認為 exact authority。

成果是一個不依賴 FastAPI、resolver、瀏覽器、網路或資料庫的 validation layer。它現在能在任何真實候選被建立前，先證明後續資料必須
同時符合來源 membership、catalog membership、欄位完整性、人工決策狀態與 deterministic manifest。這輪只交付 schema、validator、
合成 contract tests 與 artifact boundary 說明，沒有建立真實 authority row，也沒有執行 CAR-T3 的候選挑選。

### 代碼修改了哪一部分，以及為何這樣設計

新增 `src/product_variant_resolver/canonical_authority_review.py`。其中以 strict Pydantic models 定義 `AuthorityCandidate`、
`VariantFieldEvidence`、`FrozenCatalogParent`、`CatalogRecordProposal`、`OwnerReviewPacket`、`OwnerAttestation`、
`AuthorityReviewEvent`、`AuthorityBundle` 與 `AuthorityBundleManifest`；所有未宣告欄位都 fail closed，aware timestamp、固定 reviewer role、
SHA-256、UUID、publication scope 與 `resolver_output_consulted=false` 等限制由型別與跨 artifact validators 共同檢查。高階 validator 會把傳入的
巢狀 Pydantic object 重新序列化、重新 parse，避免呼叫端用預先 construct 或事後修改的 model 跳過內層驗證。

來源沒有另造一份平行規則，而是重用 CAR-T1 `canonical_authority_source_gate`，每次從固定 100-row snapshot 重新取得核准的
`source_record_id` membership。每筆 evidence 不只要引用該集合中的 row，還必須綁到**該 candidate 自己**的 row 並重現該來源欄位；不能
向同一份合法快照的另一列借值。Catalog 也改用包含 products membership 的 `FrozenCatalogParent`，由同一個 strict parent 導出 version 與
hash；existing UUID 必須真正在 parent 中，missing UUID 則必須走獨立、owner-reviewed proposal，且 catalog approval 仍不等於 authority
approval。這些選擇解決了「來源與 catalog 各自合法，但拼在一起其實不是同一個 release」的組合錯誤。

Review workflow 採 append-only state machine：只允許 `staged→reviewed|held`、補救後的
`held|conflicted|insufficient→reviewed`、`reviewed→approved_exact|conflicted|insufficient|held` 與
`approved_exact→revoked`，`revoked` 為終點。完整表單不會自動 promotion；每個 event 都必須另有
`project_owner` 的 output-blind `owner_attestation`，綁定 packet、catalog、record、時間、理由與 outcome。採用 event history 而不是直接
覆寫最終 status，是為了讓 held、衝突、補救與撤銷仍能被稽核，並防止只提交最後一個 `approved_exact` event 來隱藏缺失的前置步驟。

Bundle validator 會以 canonical JSON、固定 `VariantField` 順序、排序且唯一的 set-like lists、完整 parent digest set 與全域
`(candidate_id, reviewed_at, event_id)` 順序重算 hashes、effective status、distinct variants、family composition 及 20／4 shortfalls。
Revoked、held、conflicted、insufficient、duplicate 或 synthetic rows 都不能墊高 Gate。這個 deterministic 選型的目的不只是讓 checksum
一致，而是讓相同語意只有一種 byte representation；否則只改 list 順序就可能得到另一個看似獨立的合法 digest。

PII 與 publication 檢查採 fail-closed：公開 metadata、evidence values、理由、問題與 references 會拒絕 email、phone、seller／account
identity、credential、address、絕對路徑與 `..` traversal。Owner packet 必須是 local-only、Git-ignored，明列每個缺失／衝突欄位並保留
plain-language owner question；resolver candidate、predicted UUID、model score 與網路存取全部禁止。這比事後刪除敏感欄位保守，但可避免
私有資料先進入可提交 artifact 才被發現。

`tests/authority/test_canonical_authority_review_contract.py` 新增手工合成的正反案例，
`data/authority-review/canonical-authority-review-v1/README.md` 說明 public／local artifact 邊界與下一個 Gate。Tasks 將 CAR-T2 勾選完成，
因此綁定 tasks bytes 的 Source Gate manifest 也只更新對應 parent SHA；來源決策、100-row membership 與 authority 零值沒有改變。

### 四輪 QA：為何既有全綠測試仍不夠，以及如何修正

首輪實作的 focused tests 雖然全綠，獨立 QA 仍找到 **9 組跨 artifact 組合繞過**。問題不是單一 Pydantic 欄位缺少型別，而是各物件分開
驗證時，仍可能把無關的 catalog proposal parent、另一個核准 source row 的 evidence、不同 family／release 的 product、截斷 event
history、不完整 approved evidence、空 digest、錯誤 manifest parents 或空 owner packet 拼成表面自洽的結果。Phase 2 因此補上 candidate-
source-row 一致性、product family／release identity、完整 input-set 與 event-history 重算。這也說明 unit tests 全綠只代表已列出的單物件
路徑正常，不能取代 adversarial composition testing。

第二輪 QA 進一步指出 catalog parent 只有版本字串仍不足以證明 UUID membership，owner packet 也可能使用 stale catalog 或漏列
missing／conflicting fields。修正後 `FrozenCatalogParent` 必須帶有排序、唯一且 record-hash-bound 的 products；existing UUID、proposal 與
packet 都從同一 parent 驗證。Packet 的 issue markers 必須精確等於實際缺漏與衝突集合，且預先建構的 nested models 也會遞迴檢查未知
欄位。這輪同時補強「evidence value 必須等於綁定 source row」與 missing-UUID proposal 的完整路徑。

第三輪 QA 專查 nested ordering 與 PII 邊界。它證明 proposal、packet、event 內的 evidence 如果只驗集合、不驗 canonical order，或
selection refs、evidence refs、identifiers 可以任意排序，同一語意仍能產生不同 hash；也發現較短、無冒號的 `seller johndoe`、
`api key abc` 或地址形式需要被攔截。修正後 hash-bearing sequences 全部使用固定排序，packet issues 必須 sorted／unique，PII regex 也在
保留年份、toy number、分數等安全 catalog tokens 的前提下擴大 fail-closed 範圍。

第四輪 QA 結論為 **PASS WITH RISKS**：31 組獨立 mutations 中 29 組完全符合預期；剩餘兩組不是 authority bypass，而是保守 PII
規則可能把未來合法產品名稱 `Marvel Secret Wars` 與 `Secret Edition` 誤判為 credential／private-data 字串。QA 另掃描目前固定
100-row 與 catalog 的 1,985 個相關字串，沒有觀察到現有資料被誤擋，因此不阻擋 CAR-T2，但這是後續若擴充名稱資料時必須重新檢視的
precision 技術債。保留 `PASS WITH RISKS` 而不是改寫成無條件 PASS，可讓未來新增資料時知道應先改善 contextual PII detection。

### 最終驗證證據、目前真實進度與下一步

最終 contract focused suite 為 `58 passed`；CAR-T1／T2 合併為 `99 passed`；RHB／API／catalog regression 為 `162 passed`；完整
repository suite 為 `1150 passed`。第四輪另執行 31 組 mutations，其中 29 組完全符合預期。Ruff、strict MyPy、compileall、CAR-T1
Source Gate、artifact hashes、`git diff --check` 與 secret scan 全部通過。這些結果來自已完成的 task executor／QA 驗證；本次 Project
Log 策展只做文件 diff 與必要文字檢查，沒有重新執行測試。

工程契約已可放行下一個順序任務，但資料狀態刻意保持不變：真實 `approved_exact` variants 仍為 `0`、qualifying families 仍為 `0`，
沒有真實 authority row、owner candidate queue、catalog mutation 或 benchmark query。CAR-T3 以後均未開始，RHB-T5 也未獲授權；
`community_reference_snapshot_exact` 仍只表示相對 frozen Hot Wheels Wiki revision 的可審查上限，不能宣稱 Mattel 官方真值。

下一步是 **CAR-T3 owner Gate**：先從既有 context 提出至少四個 multi-release families 與足夠達到 20 variants 的候選計畫，清楚標示
surplus、duplicates、`candidate_selection_only` 與 `owner_attestation` 方法，再交由 owner 批准 queue。CAR-T3 本輪沒有執行；在 owner
明確批准前，不產生 review events、不修改 catalog、不建立 exact authority，也不進入 RHB-T5。architect、security 與 performance review
在 Lite／Lean 範圍內仍為 deferred。

## 2026-09-28 — CAR 規劃與 CAR-T1：把固定 Wiki 快照的可用邊界落成可驗證 Source Gate

### 新執行了什麼，以及解決了什麼問題

本輪延續 Lite／Lean Industrial 模式，先完成
[Canonical Authority Review v1 的規格](../specs/canonical-authority-review-v1/requirements.md)，再只執行
[CAR-T1 Source Gate](../specs/canonical-authority-review-v1/tasks.md)，沒有直接製造 canonical authority。RHB-T4 已證明現有
資料仍是 `0` 個合格 exact variants、`0` 個合格 multi-release families；因此這輪要解決的問題不是 resolver 找不到候選，
而是「哪一份既有資料可以進入人工 exact review、最多能宣稱到哪一層、如何阻止來源授權被誤讀成 exact UUID 已成立」。

CAR 規格把這條上游流程拆成七個順序任務：先凍結來源決策與權利邊界，再建立 strict contracts、讓 owner 批准候選 queue、
產生 output-blind 本機 review packet、逐筆 attestation 與 freeze，最後重新執行 RHB-T4。這樣安排的原因是來源可重用、欄位有
證據、catalog UUID 存在、人工同意與 benchmark Gate 通過，是五個不同決策；若在同一步自動串起來，資料看似完整就可能被
錯誤升格成 ground truth。這輪只打開 CAR-T2 的工程入口，CAR-T3 以後與 RHB-T5 仍需各自通過 Gate。

### 修改了哪些 spec、source decision、manifest、validator 與 tests，為何這樣設計

`specs/canonical-authority-review-v1/` 新增 requirements、design、tasks、source approval 與 QA review，將可觀測需求、離線
架構、owner Gates、claim tier、publication boundary 和停止條件寫成可追溯契約。資料面新增
`data/authority-review/canonical-authority-review-v1/source-decisions.json` 與
`source-decisions-manifest.json`：前者保存 owner 對來源、欄位、留存、發布、reviewer、attribution 與後續禁區的決策；後者
不複製新的私有或網路資料，而是以 parent paths、SHA-256、來源 membership、collection telemetry 與可重算統計凍結本次
Gate。將「決策內容」和「驗證 envelope」分開，是為了讓人可讀理由與機器可驗證完整性都存在，同時明確指出 checksum
只能證明 bytes 是否相同，不能自行授予權利或證明資料語意正確。

初版 tests 只從 artifact 外部檢查內容；QA 證明這不足後，Phase 2 新增專用離線模組
`src/product_variant_resolver/canonical_authority_source_gate.py`，對 decision、manifest、既有 normalized snapshot 與 source
manifest 逐層做 exact-key、固定常數、duplicate-key、parent SHA、row membership、欄位缺失統計與 spec binding 驗證。
`tests/authority/test_canonical_authority_source_decision.py` 則把正常路徑及 rehash 後的語意竄改都納入負向案例。選擇 dedicated
offline strict validator，而不是把規則藏進一般 JSON 讀取或 runtime resolver，是因為這是一個來源治理 Gate：它必須可以在
沒有 FastAPI、資料庫、瀏覽器、網路或模型的情況下獨立重現，也不能改變目前 resolver 行為。

### Owner 批准的來源範圍、技術取捨與不能擴張的宣稱

Owner 批准的只有已檢入、固定於 Hot Wheels Wiki `List of 2025 Hot Wheels` revision `790665` 的 100-row normalized text
derivative，source ID 為 `fandom-hot-wheels-2025-pilot-r790665-v1`。它只能作
`community_reference_snapshot_exact` **candidate**：後續人工確認的欄位，最多只能說是相對這個 frozen community revision
精確，不能宣稱是 Mattel／manufacturer-certified truth，也不能因 Source Gate PASS 就生成或批准 canonical UUID。這項定位
保留社群專門資料的實用價值，同時避免把第三方 reference 的可信度寫成官方認證。

既有文字衍生內容必須保留本次 decision 所記錄的 CC-BY-SA license URL、Hot Wheels Wiki contributors attribution、revision
資訊、normalized-derivative 說明與 share-alike 義務；未來每個 review row 還必須綁定 page、revision、timestamp、
`source_record_id` 和 snapshot checksum。本次批准只涵蓋已存在的 normalized artifact，沒有新增 scrape、Selenium、API、
browser、raw page、圖片、媒體或 OCR。歷史自動存取是否取得 Fandom 許可目前**未建立**，owner 的 reuse decision 也不會反向
宣稱曾獲 Fandom 授權。

可進入後續 review 的欄位只限 `casting_name→casting`、`toy_number→identifiers`、release year、series、collector number、
series position，以及僅作 context 的 variant note。100 rows 的 `color` 全為 `null`，`2nd Color` 只能表達有另一個色款，不能
推導色名；snapshot 也沒有可用的 edition mapping，因此 edition 仍須為空。1,763-row workbook 雖可幫助 family context 與
candidate selection，但未逐筆綁定 Wiki revision、attribution 和 checksum，所以仍是 context-only，不能證明 exact 欄位或
canonical UUID。這個取捨也回答了為何不直接把較大的 workbook 當 truth：資料量不能代替逐筆 provenance。

### Feasibility 結果，以及它為何還不是 authority

離線重算確認 frozen snapshot 有 100 rows、100 個 unique source IDs、38 個至少兩筆 release 的 casting families，其中共 85
rows；`toy_number`、casting、release year、series、collector number 與 series position 的缺失數都是 `0`。這表示資料結構
足以讓後續 CAR-T3 提出候選 queue，但僅是 `candidate_feasibility_not_authority`。本輪結束時
`approved_exact_count=0`、authority rows created=`0`、canonical UUID approvals=`0`、20 variants／4 families target=`false`、
RHB-T5 authorization=`false`。這些零值刻意保留，避免把「有足夠候選可審」誤寫成「已經有 ground truth」。

### 初次 QA 為何 FAIL，以及 Phase 2 如何修正

第一次 Lean QA 雖確認 artifacts 目前的內容誠實，仍判定 FAIL：把 unknown field 加入 decision 或 manifest 後，只要重算外層
hash，舊測試仍會接受；刪除實際 attribution text 後重新綁 hash 也能通過；此外 manifest 的 missing-field counts 雖然當下
正確，測試並未從 100 rows 全部重算。錯誤不在原始數字，而在完整性模型把「self-consistent checksum」誤當成「語意仍符合
已批准契約」，所以未知欄位、授權文字移除或未來統計漂移都有繞過空間。

依閉環回退 Phase 2 後，專用 validator 改為先驗證內層語意，再驗證外層 hashes：所有物件都使用 exact key set；JSON
duplicate keys、空白／缺失 attribution、manufacturer claim escalation、network flag 放寬、workbook promotion、color
inference、authority／UUID／20-4／RHB-T5 escalation 都 fail closed；row IDs、page/revision/source bindings、100／38／85 與
每個 missing count 皆由 frozen parents 重算。這個修正讓重新計算 checksum 不再等於重新取得 owner approval，也保留了
初次 FAIL 作為設計演進證據，而不是只留下最後綠燈。

### 最終驗證、仍留下的債與下一步

最終獨立 QA 判定 [CAR-T1 PASS](../specs/canonical-authority-review-v1/review.md)：原 25 個 mutations 與新增 9 個對抗案例合計
`34/34 rejected`；CAR-T1 focused tests 為 `41 passed`，CAR + RHB regression 為 `117 passed`，完整 repository 為
`1092 passed`（另有既有 warning）。Ruff check、Ruff format、strict MyPy、compileall、JSON parsing 與
`git diff --check` 全部通過。這些結果來自已完成的 QA，本輪 Project Log 策展沒有重新執行測試。

目前留下的不是 CAR-T1 工程缺陷，而是尚未建立任何逐筆 authority、canonical UUID approval、owner review queue 或 20／4
composition。下一步**只允許 CAR-T2**：實作 candidates、field evidence、catalog proposals、append-only review events 與
bundle manifest 的 strict contracts，且仍不建立真實 authority rows。CAR-T3、catalog mutation、人工 attestation、RHB-T4
reaudit 與 RHB-T5 都不能提前開始；architect、security 與 performance review 在 Lite／Lean 範圍內仍為 deferred。

## 2026-09-27 — RHB-T4：完成 canonical authority audit，工程通過但資料 Gate 正確阻擋

### 新執行了什麼，以及解決了什麼問題

本輪完成 [Representative Hard Benchmark v1 的 RHB-T4](../specs/representative-hard-benchmark-v1/tasks.md)：不先假設現有
catalog 就是真實 ground truth，而是離線稽核 repository 內每個可能提供 exact variant authority 的來源。這一步解決的
問題是，先前雖已有 synthetic catalog、Human-backed catalog、人工名稱、owner workbook staging 與 Wiki derivative，
但「有候選資料」不等於「有足以把真實 release 綁到 canonical UUID 的獨立證據」。稽核完成後，工程結果是 PASS；資料
Gate 則明確為 `blocked_insufficient_exact_authority`。這代表阻擋機制按設計運作，不代表 benchmark 已可繼續，也不是
resolver accuracy 結果。

### 修改了哪些程式、契約與產物，為何這樣設計

新增 `scripts/build_representative_hard_benchmark_canonical_authority.py`，由 frozen repository parents 建立
`canonical-authority.json` 與 `canonical-authority-manifest.json`；`src/product_variant_resolver/representative_benchmark.py`
加入 strict audit manifest contracts 與 cross-artifact validator；
`tests/evaluation/test_representative_benchmark_canonical_authority_audit.py` 用正反案例鎖定來源排除、threshold arithmetic、
parent checksum、record checksum、欄位 coverage、review metadata 與 downstream prohibition。task status 與 QA review 也
同步記錄為 **RHB-T4 COMPLETE — GATE BLOCKED**，並新增
[authority audit evidence](evidence/representative-hard-benchmark-authority-audit.md) 讓面試或交接時可以從結論追到
machine-readable artifacts。

選擇 deterministic offline builder，而不是人工複製統計，是為了讓相同 checkout 得到 byte-stable 結果，並讓任何上游
資料變更都必須重新驗證。Manifest 將排序後的 parent paths 與 SHA-256、authority artifact checksum/version/record order、
catalog counts、來源逐項排除理由、門檻與 shortfall 凍結在同一契約中；因此 stale parent、partial write、漏掉來源或竄改
decision 都不能沿用舊 Gate。若未找到合格 authority，系統刻意輸出 `records=[]`，而不是拿最近候選、family match 或
staged row 推測 UUID。

### 為何 provisional、family、Wiki 與 workbook 不能升格為 truth

`fixture-v1` 的 120 個 products 全部只有 synthetic provenance，所以 120/120 只能用於 regression；Human-backed catalog
雖涵蓋 97 個 castings 與 100 個 provisional variants，但 exact count 是 0，且所有 variants 仍需 canonical review。
RHB-T3 的 11 個 owner-confirmed sources 對 `exact_variant_authority` 也是 11/11 rejected，沒有任何來源取得 typed
canonical-authority permission。Human labels 與 family alignment 只描述 family 或 review knowledge；Wiki derivative 只
提供已保存 revision 的 context；owner workbook 是 release staging，不具 canonical links。這些資料可以在既定權限內幫助
檢索或審核，但都不能獨立證明哪一個真實 release 對應哪一個 canonical UUID。Owner 的使用許可也不能取代 release-level
truth evidence。

因此 audit 得到 eligible exact variants `0`、pilot-usable exact variants `0`、eligible same-casting multi-release families
`0`。相對於預先設定的最低門檻 20 variants／4 families，shortfall 是 `20 / 4`；authority artifact 保持空陣列，沒有為了
推進任務而製造 matched answer。

### QA、驗證證據與留下的資料債

QA 判定 [PASS (engineering) / DATA GATE BLOCKED](../specs/representative-hard-benchmark-v1/review.md)。除了驗證正常重建，
也確認 14 類 mutation 會被拒絕：stale authority SHA、stale parent SHA、partial status、unknown field、source count/order
mismatch、decision elevation、偽造 fixture authority、stale catalog-record checksum、缺少已填 variant-field coverage、
錯誤 reviewer role、timezone-naive review time、空 independent evidence，以及宣稱 consult resolver output。這些負向測試
說明 Gate 不是只對目前 JSON 寫死，而會拒絕常見的資料漂移與權限繞過。

最終 focused T1–T4 tests 為 `76 passed`，完整 repository 為 `1051 passed`（另有既有 Starlette deprecation warning）。
Ruff check、Ruff format、strict MyPy、compileall、JSON parsing、secret scan 與 `git diff --check` 全部通過；T1 builder check
回傳 `unchanged`，T4 builder 連續兩次 check 也回傳 `unchanged`。這些結果來自已完成的獨立 QA，本輪 doc curation 沒有
重新執行測試。仍留下的資料債不是程式缺陷，而是缺少合法、獨立審核的 exact release authority。

### 下一步邊界

下一步只可取得新的、合法且 independently reviewed 的 exact-variant authority，先重新通過 source/use/publication 決策，
再以 catalog version、canonical UUID、product checksum、所有已填 variant fields、獨立 evidence references、reviewer 與
aware timestamp 重跑 audit。RHB-T5、network collection、query/label authoring、matched pilot construction 與 canonical
promotion 均未授權、不得開始；在至少 20 個 pilot-usable exact variants 與 4 個 eligible same-casting/multi-release
families 通過 Gate 前，本 benchmark 必須停在 RHB-T4。

## 2026-09-26–27 — RHB-T3：完成 owner source decision Gate，將保守授權落成 fail-closed 契約

### 新執行了什麼，以及解決了什麼問題

本輪完成 [Representative Hard Benchmark v1 的 RHB-T3](../specs/representative-hard-benchmark-v1/tasks.md)，把 owner 明確
同意的來源使用邊界，從文字提案轉成 checksum-bound、machine-enforced 的 source decision Gate。這一步解決的不是
「哪些資料看起來可用」，而是「每個來源可否支援 query、evidence retention、reviewer identity、local benchmark、
public Git 與 exact authority」必須逐格決定、不可留白，也不能靠修改 inventory flag 或自由文字條件繞過。最終
`11 sources × 6 uses` 共 66 格，為 `23 approved / 43 rejected / 0 held`；對應 publication scopes 是
`10 local_only / 3 aggregate_only / 10 public_rows / 43 prohibited`。因此 Gate 的 PASS 只涵蓋這 23 個狹窄用途，
不是整份來源的概括授權，也不代表 benchmark cases 或 canonical answers 已建立。

### 修改了哪些 contracts、data 與 tests，為什麼這樣選

`src/product_variant_resolver/representative_benchmark.py` 新增 strict source-decision artifact 與 typed downstream
permissions，並把 decision overlay 綁定 T1 inventory 的 version、SHA-256、source IDs 與 authority eligibility；
`data/evaluation/representative-hard-benchmark-v1/source-decisions.json` 保存 owner-confirmed 的完整 66-cell matrix，
[source approval](../specs/representative-hard-benchmark-v1/source-approval.md)則保留人可讀的理由與限制。資料目錄 README、
task status 與 QA review 同步更新，避免 T3 已完成而操作說明仍寫成 pending。測試面新增
`tests/evaluation/test_representative_benchmark_source_decisions.py`，並擴充既有 benchmark contract tests，鎖住 unknown
fields、inventory drift、scope escalation、role identity、來源別 downstream capability、Wiki revision membership 與
preconstructed／nested-model composition bypass。

方法上沒有把 owner decision 回寫、覆蓋 T1 inventory 歷史，而是採獨立、不可省略的 overlay：inventory 回答「來源當時
是什麼」，decision artifact 回答「owner 准許它做什麼」。下游的 canonical authority、query pack 與 label validators
都必須同時驗證兩者，讓授權變更需要新的明示 artifact，而不能由呼叫端臨時放寬。自由文字 conditions 只保留給人閱讀；
真正的執行邊界由 typed permissions、allowed fields、publication scope 與 checksum／revision membership 決定。

### Owner 同意的保守方案與公開邊界

101 筆 human-labeled names 只允許 local-only query；其 owner-reviewed labels 也只可在本機形成 `ambiguous` 或
`no_match`，不得建立 `matched` 或 exact UUID。1,763 筆 workbook rows 只可用 `product_name`、`year`、`series`、
`color`、`collector_number`、`series_position` 六欄提供本機 `family_context`；raw rows 維持 local-only/untracked，
Git 只保存 schema、non-reversible hash、count、aggregate 與非敏感摘要，seller、contact、account 等身份資料排除。
既有 checksum-bound、保留 attribution 的 100 筆 Wiki derivative 只可支援 query／family context，不能擴張成新抓取、
scored label 或 canonical truth。需要人工身分的 artifact 一律只公開穩定角色 `project_owner`，不公開真名、email、電話或
帳號。

所有 live eBay、Mercari、Facebook Marketplace、Fandom 與其他網路來源仍禁止使用，
`network_collection_authorized=false`，因此本輪沒有授權 Selenium、crawler、API harvesting、圖片下載或 OCR。
現有來源的 exact authority 也全數 rejected：fixtures 只供 regression，human／alignment 最多支援 local query、有限
labels 或 family context，workbook 與 Wiki 仍只是 context／review evidence。Owner 同意來源用途，不能替代獨立的
exact-variant ground truth。

### 三輪 QA FAIL 如何修正 Gate 的技術邊界

第一次 QA FAIL 顯示，正確的 JSON 快照本身不等於可執行契約：decision file 當時只是 unvalidated `dict`，未知欄位、
PII allowlist 擴張與 rejected exact-authority 翻成 public/raw 都可被現有測試接受，也沒有 checksum 將決策綁到精確的
inventory revision。修正後新增 strict Pydantic contract、完整矩陣與 cross-field rules、inventory version／SHA／IDs／
eligibility binding，並讓 aggregate、raw rows、身份與 exact use 的不合法組合 fail closed。

第二次 QA FAIL 進一步發現 artifact 自身嚴格仍不夠：三個 downstream validators 的 overlay 是 optional，呼叫端可省略
owner decisions，再用被放寬的 inventory 建立 public human query／label 或 exact authority；同時 workbook
`family_context_only` 與 Wiki `existing checked-in revision only` 仍只是 free-text permissions，任意 unbound Wiki ref、
Wiki label 或 workbook label 仍可能通過。修正方式是把 decision overlay 與 inventory 改成下游必填依賴，加入 typed
source capabilities；Wiki query 必須對上既有 100-row revision 的真實 ID，Wiki／workbook 不得建立 labels，human 則
維持 local query 與 local `ambiguous`／`no_match` 的窄範圍。

第三次 QA FAIL 揭露的是 composition boundary：`validate_labels` 雖會檢查 label 自身，卻信任呼叫端已建好的
`QueryPack`，因此 shape-valid 但 permission-invalid 的 public human query、private ref 與非 `project_owner` author
仍能被包進合法 label flow；同類風險也會在未來 matched flow 信任預建 authority 時出現。最終修正是在 label join 前，
用同一份 checksum-bound inventory 與 owner decisions 將傳入的 query pack 和 canonical authority 序列化後重新走各自
high-level validator。這使先建低階 model、事後修改 nested author／reviewer 或注入未驗證 dependency 都會被拒絕。

### 最終驗證、限制與下一步

最終 QA 在第三次 recheck 判定 [PASS](../specs/representative-hard-benchmark-v1/review.md)。T1–T3 focused tests 為
`69 passed`，API／catalog regression 為 `66 passed`，完整 repository 為 `1044 passed`（另有既有 Starlette
deprecation warning）。touched Python files 的 Ruff check、Ruff format 與 strict MyPy 全部通過；compileall、inventory
`--check` 的 `unchanged`、JSON parse 與 `git diff --check` 也全部通過。這些 lint／typing 結果只涵蓋 RHB-T1–T3 touched
surface，不擴張宣稱 whole-repository Ruff／MyPy baseline。

下一步只獲准進入 **RHB-T4 catalog-ground-truth eligibility audit**，用獨立證據確認是否存在可用的 exact variants；
本輪沒有開始 T4，也沒有授權或開始 T5、network collection、query-pack／label authoring 或 canonical promotion。若 T4
找不到足夠 authority，matched pilot 必須記錄 shortfall 並停止，不能用 resolver output、family match、staging row 或
本次 owner approval 推導 UUID。

## 2026-09-26 — RHB-T2：建立 fail-closed 的代表性困難基準資料契約

### 新執行了什麼，以及解決了什麼問題

本輪完成 [Representative Hard Benchmark v1 的 RHB-T2](../specs/representative-hard-benchmark-v1/tasks.md)，把 RHB-T1
盤點出的來源邊界落成可執行的 strict benchmark contracts。新增的契約涵蓋 source inventory、canonical authority、
query pack、human labels、family-safe split、frozen manifest、label-blind raw results 與 scored results；目的不是開始製作
60-case pilot，而是先讓錯誤資料在進入 benchmark 生命週期前就被拒絕。例如未授權來源、未知欄位、不一致的
status／UUID、held 或 rejected rows 被計分、Test raw 洩漏答案、跨 split family leakage、過期 hash、缺少 parent artifact
或 partial write，現在都會 fail closed。RHB-T3 的 source owner approval Gate 尚未開始，本輪也沒有推定任何來源已獲准、
沒有蒐集外部資料，且仍不存在可供 representative pilot 使用的 real exact canonical authority。

### 修改了哪些程式與契約，為什麼這樣選

核心實作位於 `src/product_variant_resolver/representative_benchmark.py`，使用 Pydantic 的 strict、`extra=forbid` schemas
與跨 artifact validators，讓資料格式、權限、生命週期狀態與 checksum 關係都可由程式重現，而不只依賴文字規範；
`tests/evaluation/test_representative_benchmark_contract.py` 則以正反案例鎖住每一條邊界。RHB-T1 的 inventory builder、
source inventory、manifest、focused tests 與 evidence 同步加入 typed authority classification，原因是 canonical truth 是否
合格必須由不可任意解讀的欄位決定，不能只靠可被改寫的說明文字或 permission flags。資料目錄 README 另外說明 artifact
順序與 publication boundary；專案 README 則只恢復既有、可量測的 100-case fixture 與 neural comparison 說法，沒有新增
效能或準確率主張。

exact authority 採「依 catalog record 中所有非空 variant-defining fields 動態要求證據」的方式，而不是固定只檢查
casting 與 release year。現行欄位集合包含 casting、release_year、series、color、collector_number、series_position、
edition 與 identifiers；這項選擇會讓未來 catalog 多出已填值的變體特徵時，同一筆 authority 必須一併覆蓋，避免同車型、
同年份但顏色或編號不同的 release 被錯認為同一 variant。`AuthorityEligibility`、`AuthorityEvidenceLevel` 與明確的
`authorized_export` 邊界則把「可以使用資料」和「足以證明 exact identity」分開：family／Human Knowledge、owner staging、
Wiki staging、fixture regression 或 resolver/model 建議即使日後改成可使用，也不能因此升格為 canonical truth。

Publication scope 也按 artifact 粒度拆分。真正包含 query、authority 或 label rows 的契約只接受 `public` 或
`local_only`，不接受 `aggregate_only`；後者只適用於不含原始列的彙總／manifest。公開 row artifacts 的 reviewer、family、
reason、source/evidence references 等 metadata 會檢查明顯 email／phone PII，但 local-only metadata 仍可保留必要的內部
審核資訊。這個取捨同時保留可稽核性與資料最小化，不把「欄位名稱寫成 aggregate」誤當真正的隱私隔離。

### 初次 QA FAIL、回退修正與學到的契約邊界

初版雖通過 18 項 authored tests，Lean QA 仍判定 FAIL 並退回 Phase 2。第一個問題是 `approved_exact` 只要求 casting
與 release year，會漏掉 catalog 已存在的 series、color、collector number、series position、identifiers 或 edition；
修正後 required fields 由實際 bound catalog record 的所有非空變體欄位導出，並逐欄加入 omission negative tests。
第二個問題是 staging source 只要竄改 approval／use flags，就可能偽裝成 exact authority；修正方式不是再加自由文字，
而是加入 typed eligibility/evidence level，並以六個既有來源的 mutation tests 證明它們仍無法被提升。

第三個問題是 PII 防線最初只覆蓋 query text，公開 authority／label metadata 仍可接受 email 或電話；修正後所有可公開
metadata 都走同一類 fail-closed contact-PII validation。第四個問題是 row-level artifact 可標記 `aggregate_only` 後仍夾帶
原始 rows；修正後由獨立的 `RowPublicationScope` 在型別層拒絕。第五個問題是新測試的 nested collection indexing 未通過
strict MyPy，已調整測試型別而不降低 type-checking 強度。最後，完整測試發現先前 portfolio README 改寫遺失 measured-
artifact regression 所要求的精確、受限描述；本輪只恢復既有的 `100-case synthetic/curated fixture benchmark` 與相同
量測證據，沒有為了讓測試通過而改變數字或擴張 claim。QA 保留初次 FAIL 與最終 PASS，呈現 G3 失敗後實際回退 P2
修約，再重新驗收的閉環，而不是隱藏問題。

### 最終驗證、仍留下什麼限制與下一步

最終獨立 QA 判定 [PASS](../specs/representative-hard-benchmark-v1/review.md)：RHB-T2 focused tests `34 passed`、RHB-T1
regression `7 passed`、API／catalog regression `66 passed`，完整 repository 為 `1016 passed`。來源 inventory 的
`--check` 連續兩次都回傳 `unchanged`；Ruff check、Ruff format、strict MyPy、compileall 與 `git diff --check` 全部通過。
範圍檢查亦確認沒有修改 FastAPI、resolver service、runtime policy、canonical catalog 或 database code，contract module
沒有 network／browser／API／service imports。

這個 PASS 只代表 RHB-T2 的資料契約與防線完成，不代表來源已授權，也不代表 real-world benchmark 已有 exact answers。
下一步是尚未開始的 RHB-T3 source owner approval Gate：需要逐一確認 source × use × publication 的決策矩陣；在 owner
明確決定前，不得把 pending 當 approved、不得開始 case authoring 或外部 collection，也不得宣稱 representative hard
benchmark 已完成。

## 2026-09-26 — RHB-T1：凍結代表性困難基準的現況證據底線

### 1. 新執行了什麼、解決什麼 evidence 問題

本輪只完成[Representative Hard Benchmark v1 的 RHB-T1](../specs/representative-hard-benchmark-v1/tasks.md)，建立
offline、machine-checkable 的來源清單與checksum底線，先回答「目前到底有哪些資料、哪些已公開、哪些只有彙總、
哪些能證明canonical identity」；尚未開始RHB-T2，也沒有建立60-case pilot或宣稱代表性benchmark已完成。凍結結果為
100筆fixture cases、120個fixture products、101筆human-labeled scans，其中catalog alignment維持
`0 exact / 2 family-only / 99 unmapped`；owner release snapshot只有1,763筆observations的aggregate evidence，
checked-in Wiki pilot為100筆rows。所有上述來源目前合計仍提供`0`個可用的exact canonical authority。

這一步解決的核心問題是：先前不同資料集雖然存在，但「檔案存在」、「現在已在public Git發布」、「未來可否用於
RHB-v1／再發布」與「是否具備exact-variant ground truth」尚未被同一份可重算契約分開描述。如果不先封住這個邊界，
後續可能把family-only人工名稱、staging rows或有來源但無canonical UUID的Wiki rows誤當正式答案。

### 2. 修改哪些程式、資料契約與文件，原因是什麼

新增offline deterministic builder `scripts/build_representative_hard_benchmark_source_inventory.py`與7項專用測試，
由repository-local public inputs重算count、parent checksum、authority與publication boundary；新增
`data/evaluation/representative-hard-benchmark-v1/source-inventory.json`及manifest，作為後續contract的固定上游；
新增[公開證據說明](evidence/representative-hard-benchmark-source-baseline.md)，並由
[Lean QA review](../specs/representative-hard-benchmark-v1/review.md)對照RHB-R1、RHB-R7、RHB-R19驗收。這些修改只處理
evidence inventory與資料契約，沒有修改FastAPI、resolver、ranking、model、PostgreSQL schema或任何runtime default。

### 3. 技術與方法選型理由

Builder採offline deterministic設計：只讀repo-local artifacts、固定排序並以canonical JSON和SHA-256綁定來源與輸出，
重跑只能得到byte-identical結果或`unchanged`，發生drift則fail closed。這讓基準來源可以在乾淨checkout重現，也避免
網路頁面更新後無法說明當時驗收的是哪份資料。本輪network requests為`0`，且不讀或複製private owner rows；
1,763筆owner observations只從Git-tracked public manifest取得aggregate count與不可逆checksum，public inventory複製的
private rows為`0`。

Publication模型刻意把`current repository/publication reality`與`prospective benchmark use / redistribution permission`
分成不同欄位。原因是「某資料現在已被Git追蹤」只是現況，不能自動推導它獲得新的benchmark用途或再發布授權；反過來，
private owner rows也不能因為有checksum就被視為公開。所有未來用途仍等待RHB-T3的owner decision，而family-only、staging
與Wiki資料即使可見也維持`0 canonical authority`。本輪不讀private rows、不做network collection，正是為了在尚未通過
來源授權與canonical truth Gates前，不擴張資料使用範圍。

### 4. QA失敗、修正與最終驗證

RHB-T1前兩次QA都保留為有價值的契約修正證據。第一次FAIL的根因是把已公開、已Git追蹤的human rows現況，與未來
benchmark使用／再發布仍未授權混在一起；修正方式是每個source entry分開記錄current publication、known rights、
prospective use與prospective redistribution。第二次FAIL的根因是builder把gitignored local review summary當成必要的
tracked input，使fresh clone無法重現；修正後owner aggregate只讀
`reports/local-release-staging-v1/manifest.json`，ignored summary不再出現在required inputs或repository tracking contract。
第三次QA最終判定[PASS](../specs/representative-hard-benchmark-v1/review.md)。

驗證結果為RHB-T1 dedicated tests `7 passed`、related tests `37 passed`；Ruff check、Ruff format、strict MyPy、compileall與
`git diff --check`全部PASS。兩次連續`--check`皆回傳`unchanged`，fresh-clone-shaped public-input build也通過；實際讀取
network `0`次、複製private rows `0`筆，且沒有把任何來源提升為canonical truth。完整counts、checksums與限制保存在
[RHB-T1 evidence](evidence/representative-hard-benchmark-source-baseline.md)。下一步僅進入RHB-T2：建立strict benchmark
schemas與fail-closed validators；RHB-T3來源授權與RHB-T4 canonical authority Gates通過前，不得開始case authoring。

## 2026-09-26 — PP-T1–PP-T5：完成履歷定位與README portfolio landing page

### 1. 新執行了什麼、解決什麼問題

本輪完成[portfolio positioning v1規格](../specs/portfolio-positioning-v1/requirements.md)的PP-T1–PP-T5。
README由1,079行重整為192行的portfolio landing page，讓招募者可先看到問題、架構、決策、量測結果、限制與
啟動方式；新增[Portfolio Guide](PORTFOLIO-GUIDE.md)，提供恰好三條current-evidence履歷bullet、單一60–90秒
英文面試介紹、claim guardrails與future-only metric template；並以[QA review](../specs/portfolio-positioning-v1/review.md)
逐項封閉PP-R1–PP-R16。這解決原有README把技術證據、開發歷程與履歷敘事混在一起的溝通問題：讀者現在可在
主要閱讀路徑理解「解決什麼問題、如何決策、哪些結果已量測、哪些仍有限制」，再按需深入完整稽核證據。

### 2. 修改了哪些文件、原因是什麼

本里程碑修改`README.md`的hero、問題、架構、工程決策、量測結果、neural comparison、限制、最小啟動與
deep-evidence index；新增`docs/PORTFOLIO-GUIDE.md`；更新`docs/PROJECT-LOG.md`；並在
`specs/portfolio-positioning-v1/`保存requirements、design、[tasks](../specs/portfolio-positioning-v1/tasks.md)與
[review](../specs/portfolio-positioning-v1/review.md)。README縮短的是重複的稽核敘事，不是證據本身；Guide中的
現況數字直接連到fixture或neural comparison report。整個diff僅限文件與spec，沒有修改產品碼、API、資料、
模型、依賴、ranking、calibration或runtime設定。

### 3. 定位與技術選型理由

主定位改為`confidence-aware product entity resolution`，因為系統的可觀測成果是將noisy listing對應到
canonical variant，並在證據不足時輸出`ambiguous`或`no_match`；它不是由LLM生成答案。Dual RAG仍保留為
內部架構描述，用來說明canonical catalog與Human Knowledge之間的authority boundary，而不是專案headline。
同時將`hashing-v1`明確寫成deterministic、hashing-based、non-neural similarity representation，避免把預設
runtime誤述為learned neural embedding。MiniLM Pointwise與project-trained Listwise只屬shadow comparison；
三arms在12個matched fixture targets同為12/12、neural沒有增益，故依事前gate保留`winner: null`與RRF default，
而不是為了增加AI名詞而宣稱模型已上線。

### 4. 為何連結證據，而不是刪除證據

履歷首頁與面試稿需要精簡，但批次紀錄、checksums、PostgreSQL驗證、QA review與immutable reports仍是技術
主張能被追問與重現的依據。因此這次採用「短敘事＋直接證據連結」：Guide不複製或改寫原始report，也不刪除
任何`docs/evidence/`、`reports/`或`specs/`內容。這保留了完整audit trail，也避免濃縮文件與source of truth日後
產生兩套不一致數字。現有100-case synthetic/curated benchmark、120-product fixture catalog、21-case Test、
12 matched ranking targets與`winner: null`均保留scope限制；代表性real-marketplace metrics只提供future-only
空白模板，不能當成目前成果。

### 驗證方式、留下的限制與下一步

QA對照PP-R1–PP-R16全部判定PASS；54個README links加12個Portfolio Guide links，共66個本機Markdown連結
全部可解析，metric／denominator／latency與checked-in reports一致。`git diff --check`與
`.venv/bin/python -m compileall -q src`均PASS。因本里程碑是documentation-only，沒有重跑先前已通過的975項
產品測試，也不把compileall誤寫成runtime重新驗收。現有量測仍受synthetic／curated fixture、12個matched Test
targets、飽和baseline及非production concurrency範圍限制。下一步應另開一份代表性hard benchmark spec，定義
real-marketplace provenance、人工標註、family-safe split、hard negatives與新的evaluation gates，再決定是否
需要調整retrieval或neural reranking；不應在本文件里程碑直接擴張產品範圍。

## 2026-09-25 — NRC-T10：完成Pointwise／Listwise正式比較、誠實發布null result並封閉專案里程碑

### 新執行了什麼、解決什麼問題

本輪依Lite／Lean Industrial完成最後的NRC-T10。先重新驗證NRC-T9的label-blind raw、Pointwise/Listwise manifests、
checkpoint、implementation與config hashes，再執行唯一一次正式`--score`。這一步第一次把12筆matched Test labels
接到已封存的三arms ranks，計算Top-1、MRR@10、Recall@10/25、hard-negative accuracy、failure categories、paired
transitions、warmed latency與六個predeclared gates。計算完成後一次發布canonical JSON、Markdown與兩張SVG，第二次
score只允許回傳`unchanged`。

這解決專案最初留下的核心問題：不是只在文件上說明Pointwise與Listwise，而是用同一批候選、真實local MiniLM、
project-trained candidate-set attention head與隔離Test生命週期完成可重現architecture comparison。同時也驗證
系統能接受「更複雜模型沒有帶來價值」的結果，而不是為履歷效果硬選一個neural winner。

### 正式結果、gate判斷與為何是winner null

RRF、Neural Pointwise與Neural Listwise在12個matched Test targets上完全同分：Top-1都是12/12、MRR@10都是
12/12、Recall@10與Recall@25都是12/12；4個matched hard-negative cases也都是4/4。`identifier_noise`與
`marketplace_noise`各有6個matched cases，三arms在兩類都為6/6。Pointwise與Listwise各自12個paired transitions
全部是target rank 1→1，沒有improved、也沒有regressed。Listwise看見candidate-set context，但在這個Test沒有改進
任何正解排名。

延遲與錯誤並不是淘汰原因。RRF resolver p50/p95是1.009／1.398 ms；Pointwise為79.003／89.164 ms；Listwise為
79.399／89.583 ms。兩個neural arms都遠低於1,500 ms CPU budget，hard-negative、MRR、Recall@25與0-error gates
也全部通過。唯一失敗的是最重要的incremental-value gate：相對RRF的Top-1 absolute gain是0.00，未達0.05。

因為RRF baseline本來就是12/12，neural沒有空間展示提升。若此時用「Pointwise比較快」或「Listwise架構較進階」
選出winner，就會違反事前規則，還會在沒有品質收益時增加約88 ms p95。Deterministic selector因此輸出
`winner: null`，RRF維持default runtime。這不是實作FAIL，而是產品promotion FAIL與完整的negative experiment。

### 產物、測試與文件如何封閉

正式`comparison.json` SHA-256是`f0493fc5d7b30b5e57ee382cf14e06e4fddbcebc62228b9f4b5a0dcec45b3dd2`；Markdown、
reranker SVG與accuracy/latency SVG hashes分別是
`0a90e7803db1497584ef2ee2e6b78cd47e95f750db3b9697b447a7016a7ae0fb`、
`028f88117af4962d4d1d25a6c765e23b9143d84cf280641f6b6f78d4d54d87c6`、
`3a3156f3ba9f866c68afd435a1054ead2b29543c76cc452439df182a5f0dfe7c`。Report manifest再綁定原始
label-blind raw SHA-256，確保報告不能換掉Test輸出。

新增4項measured-artifact regression tests，鎖定report/raw hashes、12/12與4/4 exact denominators、兩個neural
arms只失敗Top-1 gain gate、24個paired transitions、candidate parity、raw label blindness與README一致性。相關
suite為62 passed，完整repository為975 passed、0 skipped，只有既有Starlette／AnyIO deprecation warning。
Ruff format/check、strict MyPy、compileall、CLI `--check`、artifact hashes與`git diff --check`全部通過。

新增`review.md`對照NRC-R1–R17逐項驗收，public evidence保存架構、生命週期、exact metrics、hashes與限制，
AI-eval從grounding、leakage、candidate parity、Pointwise independence、Listwise authenticity、selection integrity與
release safety評估模型輸出。README加入三arms結果表，而且明確說明100-case synthetic/curated fixture、12 matched
denominator、`winner: null`與「不能宣稱production accuracy」。

### 最終限制與履歷展示方式

這次結果不能解讀為神經reranker永遠沒有用。Test只有12個matched cases，而且RRF已到ceiling；一個case就會讓
Top-1改變0.0833，樣本不足以做statistical generality或real marketplace coverage宣稱。較好的履歷敘事是：
完成RRF／frozen neural pointwise／project-trained listwise attention的公平比較，建立model supply-chain、
family-disjoint lifecycle、one-time Test與immutable evidence；在baseline滿分時遵守value gate，保留RRF並發布
可重現null result。

本輪沒有修改FastAPI、`PVR_RERANKER_ENABLED`、confidence calibration、thresholds、Dual RAG、PostgreSQL、
canonical catalog、Human Knowledge、review families或release promotion。若未來要再次驗證neural upside，必須
先建立包含non-ceiling matched cases的新benchmark並另開v2 protocol；禁止用本次Test labels回頭調整v1。

## 2026-09-25 — NRC-T9：完成唯一一次formal label-blind Test collection並鎖定v1

### 新執行了什麼、解決什麼問題

本輪依Lite／Lean Industrial順序執行NRC-T9，也是v1第一次真正讓已選定的RRF、Pointwise與Listwise處理Test
queries。執行前先用完整`--check`重新驗證config、benchmark、catalog、兩份implementation sources、MiniLM
snapshot、protocol、Train／Dev pool、Pointwise manifest、Listwise manifest與checkpoint hashes，並確認Test `raw/`
與report directory都不存在；只有這些preconditions全部通過才執行正式`--collect-test`。

21個Test queries各呼叫一次既有canonical sparse＋dense＋structured→RRF retrieval，總計正好21 calls，沒有retry。
每題取得25 candidates，因此raw保存525個candidate observations；21 rows全部成功，retrieval/model error都是0。
每列只建立一份shared candidate list，RRF arm保持原始candidate順序，Pointwise與Listwise arms都包含完全相同的
25個canonical UUID，只能改變score與rank，不能增加、刪除、替換候選或補入正解。

### Artifact內容、隔離答案的方法與技術決策

`test-raw.json`只保存query、parsed signals、shared candidates、三arms的UUID／raw score／rank、signal/retrieval/
pointwise/listwise timings及error欄位。它不保存expected status、expected UUID、target、human label、accuracy、
metrics、eligibility或winner；遞迴key檢查結果為空。這個隔離很重要：目前即使打開raw也只能看到三種排序，無法
知道哪個排序比較接近人工答案，因此無法用Test結果回頭選模型或調hyperparameters。

Manifest明確記錄`label_blind=true`、`test_collection_executed=true`、`retrieval_call_count=21`、
`retrieval_error_count=0`，並綁定protocol、pool、Pointwise、Listwise、checkpoint和benchmark Test-query source
hashes。Raw SHA-256為`948582264e67ad6d686a4409a41100149118d12b6e4548bbdc1265d778756884`，manifest SHA-256為
`d52000451be8b844067f2ac20d4a170231c93a2fd64253c73488552c4e779105`。第二次執行collection直接回傳
`unchanged`，沒有再次retrieval或覆寫；完整`--check`回傳`valid`。

收集前後重新計算所有frozen hashes，config、benchmark、catalog、implementation sources、MiniLM、protocol、
pool、兩份model manifests與Listwise checkpoint逐一相同。這代表Test raw不是在看到輸出後由另一版程式或模型
產生。從此刻起，v1的source、config、model與hyperparameters全部鎖定；若未來想嘗試另一種feature或架構，必須
建立v2，而不能覆寫這組結果。

### 測試結果、目前不能下的結論與下一步

Related tests為58 passed，完整repository為971 passed、0 skipped，只有既有Starlette／AnyIO deprecation warning。
Ruff format/check、strict MyPy、compileall與`git diff --check`通過。正式reports仍不存在，也沒有執行label join、
Top-1、MRR、Recall、hard-negative、latency gates或winner selection。因此目前不能根據raw score大小宣稱RRF、
Pointwise或Listwise誰較準；不同模型的raw scores也不是可互相比較的calibrated probabilities。

下一步NRC-T10會對這份不可變raw做唯一一次Test label join，依預先凍結的metrics與六個gates計算結果。若沒有
neural arm同時通過Top-1提升、hard-negative／MRR／Recall不下降、p95 latency與0-error條件，就必須誠實發布
`winner: null`。之後才新增measured-artifact regression tests、`review.md`、public evidence、AI-eval、README
結果表、Decision／Project Log closure並整理GitHub交付狀態。

## 2026-09-25 — NRC-T8：完成正式Train／Dev scoring、Listwise fitting與不可變模型選擇

### 新執行了什麼、解決什麼問題

本輪依Lite／Lean Industrial順序在NRC-T7凍結的79筆Train／Dev共同候選池上執行唯一一次正式`--fit`。Frozen
MiniLM對每個query／candidate pair獨立打分，共涵蓋58 Train＋21 Dev cases、1,973個既有候選；之後只有matched且
正解已存在pool的Train cases能更新Listwise權重，Dev完全不參與gradient或normalizer fitting，只用來選擇epoch。
這解決「模型已下載、候選池已固定，但還沒有正式Pointwise outputs與project-specific Listwise checkpoint」的缺口。

36個matched Train cases全部eligible，另外22個ambiguous／no-match cases排除；12個matched Dev cases全部eligible，
另外9個ambiguous／no-match cases排除。兩個split的retrieval miss都是0，所以本輪不需要也不允許補入候選。
Pointwise manifest明確標記weights frozen、`test_labels_loaded=false`、`test_scored=false`；Test仍未被模型選擇流程
使用，也沒有建立Test raw或final report。

### 代碼執行了哪一部分、模型為何這樣選擇

本輪沒有修改ranking演算法，而是執行已在NRC-T5完成並由NRC-T6 CLI封裝的正式生命週期。Pointwise沿用
Apache-2.0 MiniLM固定revision與88 MB local snapshot，在CPU float32及strict offline模式下對每個pair產生logit；
同一個candidate無論batch順序都必須在`1e-6`內得到相同分數。Pointwise只看query和該候選文字，沒有讀取其他
candidates，因此它仍是純Pointwise對照組。

Listwise輸入是相同Pointwise logit，加上RRF、source rank、year、collector number、series position、color與series
match/conflict等固定21維features。只有Pointwise logit與RRF score用Train統計做normalization，另外19個具有固定
語意的binary／reciprocal-rank features不重新縮放。Head仍是21→32 candidate encoder、一層4-head self-attention、
64維feedforward與scalar score，沒有positional embedding；這樣模型可以比較候選間相對證據，但不能把輸入array
位置當成答案。

訓練history共11 epochs。Dev MRR@10從epoch 1開始就是1.0，直到epoch 11都沒有更高；雖然Train loss從
3.0723下降到0.0190，預先凍結的選擇規則只接受「strictly higher Dev MRR」，並在連續10次沒有改善後停止，因此
保留earliest epoch 1。這個決定很重要：如果因為看到較低Train loss而改選epoch 11，就是在沒有held-out改善時
偏好更貼合Train的模型，構成事後調參。Epoch 1是Dev證據支持下最早、也最保守的checkpoint。

三份正式檔案分開保存：Pointwise manifest記錄79 cases／1,973 logits與rank；Listwise manifest記錄eligibility、
Train-only normalizer、完整history、architecture、AdamW hyperparameters、seed `20260924`、Dev selection與所有
upstream hashes；`listwise-model.safetensors`只保存tensor，不包含pickle或optimizer state。Pointwise manifest
SHA-256是`af9f58c02ecb6c9a44b6438eb5b3493b41447e570830f74fbf61f9dfd973cd79`，Listwise manifest是
`647e82c1bcc2087de01688ff76481fb7e67bb56b9552d551ac00e08061fceab0`，checkpoint是
`9386c0593ec07ad2b9eb0f6daa613b66f7b117e0e6c5a33be2e8705dbe18aead`。

### 測試結果、限制與下一步

除了manifest validator，本輪也用真正的frozen MiniLM與selected Listwise checkpoint執行preflight。Pointwise
batch反轉後映射回相同identity仍在`1e-6`內；Listwise candidates反轉後分數能正確映射；同一組real candidates
加入masked padding後，非padding logits也在`1e-6`內不變。第二次`--fit`回傳`unchanged`，證明不重新score、
train或覆寫；完整`--check`回傳`valid`。

Related tests為58 passed，完整repository為971 passed、0 skipped，只有既有Starlette／AnyIO deprecation warning。
Ruff format/check、strict MyPy、compileall與`git diff --check`通過。正式`models/`已建立但只有276 KB；Test `raw/`
與`reports/neural-reranker-comparison-v1`仍不存在，沒有Test label、Test neural score、winner、API、Dual RAG、
PostgreSQL、canonical catalog或runtime變更。

下一步NRC-T9是風險最高的不可逆研究步驟：對21筆Test query各做一次label-blind canonical retrieval，讓RRF、
Pointwise、Listwise使用同一候選，保存scores／ranks／timings／errors但不接答案。成功後v1不得再改source、config、
model或hyperparameters；NRC-T10才會第一次加入Test labels並發布winner或誠實的`winner: null`。

## 2026-09-25 — NRC-T7：取得固定MiniLM並凍結正式protocol與Train／Dev共同候選池

### 新執行了什麼、解決什麼問題

本輪依Lite／Lean Industrial順序執行第一個會使用外部模型的正式階段。先把神經套件安裝在`Product Variant
Resolver/.venv`，沒有改動系統Python或讓Torch變成FastAPI預設依賴；接著取得唯一核准的Apache-2.0
`cross-encoder/ms-marco-MiniLM-L6-v2`固定revision，最後才建立正式protocol與label-free Train／Dev pool。
這解決先前NRC-T1–T6只有程式與temporary synthetic evidence、尚未證明真實Mac CPU環境能載入模型與重現
候選池的缺口。

正式freeze仍沒有讀取或收集Test輸出。Protocol只確認完整100題benchmark契約與family isolation，再把58筆Train
和21筆Dev query交給既有canonical sparse＋dense＋structured→RRF pipeline各執行一次。結果是79個rows、
1,973個候選，沒有empty candidate row，也沒有任何候選缺少source ranks；pool仍只含query、signals、retrieval
timings與候選證據，不含expected status／UUID、Pointwise或Listwise分數、metrics與winner。

### 代碼、依賴與artifact做了哪些調整，為何這樣決定

本輪沒有另寫一套retriever或改FastAPI產品碼，而是執行已在NRC-T1–T6完成的受控CLI。安裝版本維持規格選定的
Sentence Transformers 3.4.1、Torch 2.7.1與safetensors 0.5.3；原因是這三版已針對Python 3.12、macOS ARM64、
CrossEncoder離線介面與listwise attention primitive完成設計與合成測試，臨時升級到其他major version會把
「比較Pointwise與Listwise」變成同時比較依賴版本，破壞實驗歸因。

實際安裝後，`constraints/reranking-python312.txt`由原本3個direct pins擴充為33個direct／transitive exact pins，
包含Transformers、tokenizers、NumPy、SciPy、scikit-learn、Hugging Face Hub與HTTP／tensor依賴。這項調整不是
重新挑選模型，而是把reference Mac真正解析出的環境轉成可重建證據；若只保留三個頂層版本，未來相同指令仍
可能取得不同tokenizer或Transformers行為。`uv pip check`確認專案環境共74個packages彼此相容，33個constraints
也逐一比對實際metadata，沒有version mismatch。

Model acquisition只接受config中六個allowlisted檔案，拒絕pickle、remote code與額外檔案。發布後目錄約88 MB，
manifest SHA-256是`32f889bb415ef5a56760a299da0635e8e1704d46fe0b11ded06c563de896feb8`，其中
`model.safetensors` SHA-256是`821d1aa69520101d6e0737f78a042ae25b19e5cb9160701909d10434f4aeb0ae`。
以`HF_HUB_OFFLINE=1`和`TRANSFORMERS_OFFLINE=1`重新載入後，模型能完成兩組實際pair scoring；第二次acquire
直接回傳`unchanged`，證明日後驗證不需要網路，也不會以新下載內容覆寫固定snapshot。

正式protocol與pool分別以canonical JSON、manifest與SHA-256發布。Protocol記錄100／58／21／21 denominator、
14個family、120筆`fixture-v1` catalog checksum、source/code/config hashes、canonical retriever版本與實際核心
dependency versions；狀態為`frozen_pre_test`，明確標示`training_executed=false`、
`test_collection_executed=false`。第二次freeze回傳`unchanged`，完整`--check`回傳`valid`，因此不是只確認檔案
存在，而是重新驗證所有hash、schema、候選來源與label-blind contract。

### 測試結果、限制與下一步

安裝optional stack後，先前刻意skip的真實Torch permutation／padding／loss／repeatability tests全部轉為pass。
Neural focused tests為47 passed；加入catalog service的related tests為58 passed；完整repository為971 passed、
0 skipped，只有既有Starlette／AnyIO deprecation warning。Ruff format/check、strict MyPy、compileall與
`git diff --check`也通過。正式`models/`、Test `raw/`與`reports/neural-reranker-comparison-v1`仍不存在；沒有
Pointwise Train/Dev scoring、Listwise fitting、Test collection、winner selection，也沒有修改API、Dual RAG、
PostgreSQL、canonical catalog或runtime。

下一步NRC-T8會在目前不可變的79筆Train／Dev pool上執行正式Pointwise scoring，只讓matched且target已在pool的
Train lists擬合小型Listwise head，Dev只負責選earliest best epoch。完成後會保存Pointwise manifest、Listwise
selection manifest與safetensors checkpoint；仍不讀Test labels，也不建立Test raw或final report。

## 2026-09-25 — NRC-T6：完成一次性Test生命週期、決策閘門、可稽核報告與六階段CLI

### 新執行了什麼、解決什麼問題

本輪依Lite／Lean Industrial順序完成NRC-T6，但沒有碰正式benchmark結果。上一階段已能用Train擬合Listwise、
用Dev選epoch，仍缺少最後且最敏感的邊界：如何保證Test只檢索一次、三個架構看到完全相同候選、錯誤不被重跑
洗掉，以及只有在raw evidence凍結後才接上答案。現在`collect-test`只處理label-blind query與fitted models，
`score`才讀Test labels；兩者是不同的不可覆寫phase，而`check`會從來源、模型、raw、report一路重新驗證hash與內容。

收集前先以Train／Dev pool做Pointwise batch-order與Listwise candidate-permutation invariance preflight，再做warmed
timing，避免為了測試模型穩定性或初始化成本而偷看Test、也避免把第一次lazy load誤算成單題推論延遲。21筆Test
各自只呼叫一次既有canonical retriever，輸出一份shared candidates，三個arms只能沿用同一批UUID與候選順序；
Pointwise與Listwise只能新增分數和重排，不能自行檢索、補正解或移除困難候選。單題若失敗會保存error並留下空
rank，不會自動重試；因此denominator仍是完整12個matched Test案例，錯誤臂也一定被gate淘汰。

### 代碼修改了哪一部分、原因與技術選型

`neural_reranker_comparison.py`新增Test label投影、scorer protocols、preflight／warm-up、一次性raw collector、
raw/report manifests與validators、metrics/category slices/paired transitions、NRC-R12 gates、NRC-R13 deterministic
winner selection，以及JSON、Markdown和兩張SVG renderer。Raw schema遞迴禁止expected labels、metrics和winner；
scoring前後重新比對models與raw目錄的每個byte，使報告產生器不能改寫模型輸出，也不能在看過答案後修正raw。

門檻選擇維持已確認的保守策略：神經臂相對RRF的Top-1至少增加0.05，hard-negative accuracy、MRR與Recall@25
皆不可下降，resolver p95不可超過1500 ms，而且errors必須為0。這些條件反映履歷展示的重點不是強迫神經模型
獲勝，而是證明能做可信的architecture comparison；若沒有任何arm全數通過，正式結論就必須是`winner: null`。
多個arm都通過時才依hard-negative accuracy、Top-1、MRR、較低p95排序，完全同分則偏好較簡單的Pointwise，
避免以不穩定的dict順序或UUID決定研究結論。

報告額外保存每題shared candidates、三arms raw scores/ranks、各階段timing、evidence scope與模型版本，並明示
ranking score不是校準後match probability。SVG不是獨立手寫摘要，而是由同一canonical report資料生成並納入
manifest checksum；這讓圖表、Markdown與JSON無法各說各話。`pyproject.toml`註冊
`pvr-compare-neural-rerankers`，提供`--acquire-model`、`--freeze-protocol`、`--fit`、`--collect-test`、`--score`
與`--check`六個互斥phase，讓之後正式操作沿用同一條受驗證路徑。

### 測試結果、限制與下一步

新增11項synthetic E2E／failure tests，使comparison lifecycle suite共23項。測試證明21筆Test各一次retrieval、
raw完全無label/metric/winner、errored row不重試、scoring不改model/raw bytes、六種gate各自失敗都得到null、
tie-break穩定且偏好簡單arm、partial state與chart tamper被拒絕、合法repeat不覆寫，以及安裝後CLI help確實列出
六個phase。Focused為23 passed；related為56 passed／2 skipped；完整repository為969 passed／2 skipped（共971項）。
Ruff format/check、
strict MyPy、compileall、`git diff --check`與CLI help皆通過；兩個skip仍是依計畫留到NRC-T7 optional環境執行的
真實Torch tensor tests。唯一warning是既有Starlette／AnyIO deprecation，與本次功能無關。

所有生命週期測試都只寫入pytest temporary directories。Repository內正式`data/evaluation/neural-reranker-
comparison-v1`、`reports/neural-reranker-comparison-v1`與`model-cache/neural-reranker-comparison-v1`仍不存在；
沒有network、dependency/model download、正式Test collection/scoring，也沒有修改FastAPI、Dual RAG、
PostgreSQL、canonical catalog或runtime。下一步NRC-T7才會安裝optional dependencies、取得固定revision的本機
模型並凍結正式protocol與Train/Dev pool；由於會使用網路並下載約90 MB模型與Torch等套件，執行前仍需owner
另外明確授權。

## 2026-09-25 — NRC-T5：完成Train/Dev fitting與immutable model-selection生命週期

### 新執行了什麼、解決什麼問題

本輪依Lite／Lean Industrial順序只完成NRC-T5，把上一階段凍結的58筆Train與21筆Dev候選池接到可驗證的
Pointwise scoring與Listwise fitting流程。每個case的Pointwise模型只收到該query與各候選的allowlisted text，
輸出依原候選順序保存，再用固定score→RRF rank→UUID tie-break建立rank。這解決「候選池已公平，但兩個神經
架構尚無一致模型選擇流程」的缺口。

Train/Dev labels只在orchestration層加入：ambiguous與no-match不進入訓練；matched target若不在凍結pool，只增加
retrieval miss計數，不能把正解候選補回。只有matched且target已存在的Train list能更新Listwise權重；Dev list
只交給trainer計算MRR@10並選earliest best epoch。Test rows會在讀取label fields前跳過，而且fitting phase不再
呼叫會檢查Test labels的完整benchmark validator；它改以已凍結contract與benchmark bytes SHA-256驗證來源。

### 代碼修改了哪一部分、為何採用這些方法

`neural_reranker_comparison.py`新增Train/Dev label projection、Pointwise scorer／Listwise trainer／checkpoint
backend protocols、eligibility accounting、model manifests、三檔models目錄validator，以及
`fit_train_dev_models`／`check_fitted_train_dev_models`。Protocols讓本輪可用純合成adapter驗證生命週期，不必為了
測試提前安裝Torch或下載90MB左右的MiniLM；正式NRC-T8仍會使用既有`train_listwise_model`和safetensors backend，
所以測試替身沒有形成第二套產品演算法。

Pointwise manifest保存79個case的候選UUID、logit與deterministic rank，但不含expected UUID/status/family。模型
manifest hash在scoring前後及Listwise fitting後都重新探測，確保「frozen pointwise」不是只有文件宣稱。
Listwise examples由相同logit加既有20項RRF/source/structured fields形成固定21維feature；生成後重新用所有
eligible Train candidate rows計算expected normalizer，trainer若混入Dev統計就無法通過比較。

Listwise manifest記錄feature schema、21→32架構、AdamW learning rate／weight decay、batch size、epoch/patience、
seed、CPU float32環境、dependency versions、protocol/pool/pointwise hashes、Train/Dev eligibility、training-label
checksum、normalizer、每個epoch的Train loss與Dev MRR、selected epoch，以及nested safetensors manifest和checkpoint
SHA-256。選擇把logits與model-selection metadata分成Pointwise／Listwise兩份，是因為Pointwise權重完全不fit，
而Listwise才有project-specific訓練；混成單一manifest會模糊哪個模型從哪些資料學習。

整個`models/`先在同一filesystem的temporary directory完成三檔驗證，再一次rename發布。已存在且完整的models
只允許回傳`unchanged`，不再score或train；只有一部分檔案、任何upstream hash漂移、pointwise bytes變動、
checkpoint tamper或非canonical manifest都fail closed且不覆寫。這延續NRC-T4的phase transaction boundary，
避免研究結果因重跑而悄悄改變。

### 測試結果、限制與下一步

新增4項synthetic fitting integration tests，使comparison lifecycle tests共12項。測試刻意讓Train與Dev各有
一個matched target不在pool，驗證36個matched Train只形成35個training examples、12個matched Dev只形成11個
selection examples，miss不被注入；同時驗證79次Pointwise calls、Train-only normalizer、Dev early stopping、
Test validator絕不被呼叫、Pointwise weights不變、repeat為0額外scoring/training，以及partial/config/pool/model/
dependency/checkpoint drift拒絕且不覆寫。

相關測試為45 passed／2 skipped；完整repository共960項，結果958 passed／2 skipped。兩個skip仍是依計畫延至
NRC-T7 optional環境的真實Torch tensor tests。Ruff format/check、strict MyPy、compile與`git diff --check`通過，
唯一warning仍是既有Starlette／AnyIO deprecation。正式data、reports與model-cache仍不存在；沒有network、套件
安裝、正式fit、Test collection/scoring、API、Dual RAG、PostgreSQL或runtime改動。

下一步NRC-T6會完成one-time label-blind Test collection、三arms scoring/gates、JSON/Markdown/SVG reports與完整
CLI，但仍只以temporary synthetic E2E驗證，不建立正式artifact或揭露正式Test結果。直到NRC-T1–T6全部綠燈，
才會在NRC-T7重新說明並請求owner授權下載optional dependencies與pinned model。

## 2026-09-25 — NRC-T4：完成source-bound protocol與label-blind Train/Dev候選池生命週期

### 新執行了什麼、解決什麼問題

本輪依Lite／Lean Industrial順序只完成NRC-T4。新增一個隔離的experiment orchestration模組，將既有100題
benchmark中的58筆Train與21筆Dev查詢投影成可凍結的候選池；21筆Test完全跳過。每個納入的case只呼叫一次
現有canonical sparse＋dense＋structured→RRF retrieval，並保存同一份排序候選、來源rank／score、structured
match／conflict、RRF rank／score、解析signals與四段timing。這解決後續Pointwise與Listwise若各自重新檢索，
可能因候選集合不同而無法公平比較的問題。

這一步沒有執行真正的正式freeze。測試只在pytest temporary directory中建立合成生命週期檔案；repository內
的正式data、reports與model-cache路徑仍不存在，也沒有下載MiniLM、安裝Torch、執行training或讀取Test結果。

### 代碼修改了哪一部分、原因與技術選型

新增`neural_reranker_comparison.py`，把protocol建立、來源hash、候選凍結、schema validation、manifest與
exclusive-create publication集中在experiment層，而不修改`service.py`或FastAPI runtime。Canonical retriever
仍由既有`SparseRetriever`、`DenseRetriever(HashingEmbedding(192))`、`StructuredRetriever`與RRF組成；另寫一套
retrieval會讓實驗結果無法代表目前系統，所以此處只提供離線builder重用同一組元件。

Protocol不只記model名稱，也綁定config、benchmark、catalog、兩個implementation files、dependency versions、
catalog semantic checksum與未來本機pointwise manifest SHA-256。Pool再綁定protocol hash。選擇canonical JSON
加SHA-256，是因為本專案需要能判斷「內容完全相同」與「來源或bytes已漂移」，而不是只看檔名存在。整個
experiment directory先在同一parent的temporary staging建立，再以rename一次發布；既有完整狀態只允許驗證後
回傳`unchanged`，partial或衝突狀態一律拒絕，避免逐檔寫入留下半套artifact或默默覆蓋研究證據。

候選validator要求source ranks與scores同源且非空、rank為1–25整數、score有限、RRF分數能由固定`k=60`的
source ranks重算，候選RRF ranks連續，timings必須恰有sparse／dense／structured／fusion。Pool也會逐筆比對
benchmark原始Train/Dev的case ID、split、query與順序；因此即使JSON仍合法，查詢被改寫也會fail closed。
Recursive label-blind檢查同時禁止expected label、target、accuracy／winner及Pointwise／Listwise score欄位，
讓NRC-T4只保存模型尚未看過答案的共同輸入。

### 測試、風險邊界與下一步

新增8項lifecycle tests，覆蓋79次且每題一次retrieval、58/21 exact denominator、byte-stable ordered candidates、
完整來源證據、label/neural-output prohibition、合法重跑0額外retrieval、partial state、pool tamper、source drift、
family跨split leakage、缺少timing及錯誤rank型別。Related suite為41 passed／2 skipped；完整repository共956項，
結果954 passed／2 skipped。兩個skip仍是按計畫延至NRC-T7安裝optional環境後執行的真實Torch tests。Targeted
Ruff format/check、strict MyPy與compile通過；唯一warning仍是既有Starlette／AnyIO deprecation。

本輪未修改API、Dual RAG、PostgreSQL、canonical catalog、Human Knowledge或runtime設定。下一步NRC-T5只會
實作Train/Dev label join、frozen pointwise score、Train-only normalization、listwise fitting、Dev early stopping
與immutable model-selection artifacts，仍只用temporary synthetic fixtures；不下載模型、不執行正式fit、
不讀Test labels，也不建立正式repository artifacts。

## 2026-09-25 — NRC-T3：完成permutation-equivariant Listwise網路、trainer與checkpoint契約

### 新執行了什麼、解決什麼問題

本輪依Lite／Lean Industrial順序只完成NRC-T3，將原先文件中的Listwise概念轉成可執行、但仍保持lazy optional的
PyTorch implementation。這一步解決Pointwise只能各自看query/candidate pair、無法比較「同一候選集合內相對
關係」的限制：Listwise head會同時看最多25個候選的21維features，以self-attention讓每個candidate score能依賴
其他候選；同時不加入positional embedding，避免模型把原始RRF array位置誤當成答案。

實作前核對PyTorch 2.7官方API，確認`TransformerEncoderLayer`的`batch_first=True`形狀是
`[batch,candidate,feature]`，且`src_key_padding_mask`是正式padding介面；也核對AdamW 2.7參數與safetensors的
`save_file`／`load_file` CPU契約。沒有因測試需要而提前安裝Torch：確認project `.venv`、system Python及Codex
bundled runtime都沒有Torch／safetensors後，仍遵守NRC-T7才允許owner-approved install的既定供應鏈順序。

### 代碼修改了哪一部分、原因與方法選型

`neural_reranking.py`新增`FeatureNormalizer`、`ListwiseExample`、`TrainingEpoch`、early-stopping selection及完整
training result contracts。Normalizer API只接收Train rows，且只計算`pointwise_logit`與`rrf_score`的population
mean／standard deviation；constant欄位以1.0作安全尺度。其他19個presence、rank、match/conflict features完全
不標準化，因為它們本身已有固定0–1語意，若再次依小樣本縮放反而會讓跨split解釋不穩定。

`build_candidate_set_reranker`在真正呼叫時才import Torch。架構固定為
`Linear(21→32)+GELU+LayerNorm`、一層`TransformerEncoderLayer(32,4 heads,FFN 64,dropout 0)`及
`Linear(32→1)`；沒有position channel。Padding同時傳入attention mask，最終logit再以`-inf`遮蔽，確保padding
既不能被真候選attend，也不會進入softmax loss。Trainer固定CPU float32、seed `20260924`、deterministic
algorithms、AdamW learning rate `1e-3`／weight decay `1e-4`、batch 8、最多100 epochs；只有strictly higher Dev
MRR@10才替換best checkpoint，因此tie保留較早epoch，連續10 epochs無改善便停止。Train負責fit weights與
normalizer，Dev只選epoch，函式沒有Test輸入。

Checkpoint不用`torch.save`，只允許`.safetensors` model state；optimizer state刻意不保存，避免pickle與無用的
resume狀態變成release artifact。伴隨manifest綁定exact feature schema/hash、architecture、seed、selected epoch、
Train normalizer、每個tensor name/shape與checkpoint SHA-256。任何schema、architecture、shape或bytes漂移均
fail closed。寫入adapter同樣lazy load，因此缺少optional packages時會在建立artifact directory前給出明確安裝
提示。

### QA結果、限制與下一步

Focused suite目前24項：22項核心測試通過，2項真正Torch tensor測試因optional environment尚未安裝而明確
skipped。已通過的測試涵蓋Train-only statistics、僅兩欄normalization、exact layer wiring、無position、固定
seed/config、earliest-tie／patience、lazy dependency error、safetensors manifest及schema/hash drift。兩項已收集
但延後到NRC-T7執行的測試會用實際tensor驗證candidate permutation在`1e-6`內映射相同、padding不影響real
candidates、一步AdamW降低controlled loss，以及相同seed重現selected epoch與scores；目前不把skip誤報成pass。

相關測試為54 passed／2 skipped；完整repository 948項為946 passed／2 skipped。Targeted Ruff format/check、
strict MyPy、compileall與`git diff --check`通過，仍只有既有Starlette／AnyIO deprecation warning。正式data、
reports與model-cache目錄保持不存在，也沒有network、dependency install、retrieval、實際training、Test labels、
API、Dual RAG、PostgreSQL或runtime改動。

下一步NRC-T4只建立protocol、source binding、label-blind Train/Dev candidate-pool lifecycle及synthetic temporary
tests，包括exclusive-create、hash binding、one retrieval call與idempotent `unchanged`。真正Torch tests仍是NRC-T7
取得optional environment後、任何正式pool/model state建立前的hard precondition。

## 2026-09-24 — NRC-T2：完成MiniLM本機模型供應鏈與離線pointwise scoring邊界

### 新執行了什麼、解決什麼問題

本輪依Lite／Lean Industrial順序只執行NRC-T2，沒有提前進入listwise training或正式experiment。新增獨立的
`reranking` optional extra、Python 3.12 direct constraints與`config/neural-reranker-comparison-v1.json`，把
`cross-encoder/ms-marco-MiniLM-L6-v2`固定在immutable revision
`233902d25c440f23af6f7d6e94d2946bac0bee0a`及Apache-2.0授權。這解決「同一個model name日後可能指向不同
weights」、「預設安裝被Torch放大」，以及模型載入時可能偷偷連網或接受remote code的三個供應鏈風險。

實作前另外核對官方Sentence Transformers v3.4.1 source，而不是照目前最新版API猜測。確認該版CrossEncoder
使用`automodel_args`，並支援`local_files_only`與`trust_remote_code`；也核對指定revision的Hugging Face file
tree，確認所需六檔確實是`config.json`、`model.safetensors`、三個tokenizer JSON與`vocab.txt`，同時明確排除
repo內存在的`pytorch_model.bin` pickle weights。這讓設定和將來真正acquisition的來源一致。

### 代碼修改了哪一部分、原因與方法選型

`neural_reranking.py`新增typed config／manifest contracts、lazy dependency adapters、唯一network-capable的
`acquire_pointwise_model`、完整local model validator及`LocalPointwiseScorer`。Acquisition先要求owner明確確認
license，再把model ID、revision與exact allowlist交給downloader；任何`.bin`、`.pkl`、`.pt`、`.py`、額外檔案、
缺檔或不規則輸入都fail closed。Hugging Face cache可能以symlink指向immutable blob，所以只在下載邊界允許讀取
source symlink，發布到`model-cache`前一定複製成regular file；正式目錄本身完全拒絕symlink，避免日後hash所指
bytes被外部target替換。

每個發布檔案記錄path、size與SHA-256；manifest另外綁定model ID、revision、license與config SHA-256。有效的
既有目錄回傳`unchanged`且不重新下載，任何partial或tampered state不覆寫。Missing optional dependencies會在
建立project artifact directory之前提供明確的`product-variant-resolver[reranking]`安裝提示。選用獨立extra而不
合併既有`ml`，是因為NRC-T7尚未在reference Mac CPU驗證完整transitive resolution；本輪constraints只誠實固定
三個direct packages，不假裝已經擁有完整lock。

Offline scorer每次先重新驗證manifest與檔案hash，才lazy import Sentence Transformers／Torch；constructor固定
CPU、float32、one label、128 tokens、`use_safetensors=True`、`local_files_only=True`與
`trust_remote_code=False`。`score_pairs`把同一query的Top-25 pairs一次交給`predict`，檢查score數量與finite
values。Fake model的順序重排測試會以candidate identity對回分數，證明batch順序不改變identity-to-score map。

### QA結果、未做事項與下一步

新增後focused suite由9增至16項，涵蓋revision/license/trust設定漂移、explicit license、exact allowlist、pickle
拒絕、manifest missing hash、tampered bytes、missing dependency-before-write、secure loader kwargs、one-batch
scoring、順序不變性、錯誤count與NaN。16/16 focused、48/48 related與940/940完整repository tests通過；本次
修改檔案的Ruff format/check、target strict MyPy、compileall及`git diff --check`也通過。完整suite仍只有既有
Starlette／AnyIO deprecation warning；全repo Ruff仍會列出大量本task以前就存在的historical script格式問題，
因此沒有越界改寫那些檔案。

本輪沒有執行pip install、network、model download、retrieval、training或Test label access；
`model-cache/neural-reranker-comparison-v1`、formal data與reports目錄均不存在。下一步NRC-T3才會加入21→32的
permutation-equivariant candidate-set network、padding mask、listwise loss、train-only normalization與synthetic
trainer tests；同樣不會取得真實模型或執行正式benchmark。

## 2026-09-24 — NRC-T1：完成不依賴神經套件的比較契約與排序計量核心

### 新執行了什麼、解決什麼問題

Owner確認十項task plan後，Lite G1*正式關閉，本輪只執行NRC-T1。新增
`src/product_variant_resolver/neural_reranking.py`與9項focused tests，把後續Pointwise／Listwise都必須遵守的
資料形狀、模型輸入邊界、feature順序、排名規則與metrics先固定成dependency-free contract。這解決「等Torch
與模型都進來後才發現三個arms使用不同資料或分母」的風險，也讓核心API在沒有任何ML optional package的環境
仍可import與測試。

### 代碼修改了哪一部分、原因與方法選型

新增frozen `CandidateTextFields`、`FrozenCandidate`、`FrozenSignals`、`CandidatePoolRow`、`RankedCandidate`與
`ScoredCase` dataclasses。Candidate contract驗證UUID、Top-25連續RRF rank、finite scores、三個合法sources、五種
structured fields、unique identities與nonnegative timings；使用tuple而非可變list保存正式順序，避免後續模型
adapter無意改寫shared pool。

`render_candidate_text`只接受brand、casting、year、series、color、collector number、series position、edition、
sorted aliases與identifiers，根本不接受case ID、UUID、provenance、split或labels。這種function-signature allowlist
比先傳入整個catalog dict再刪除禁用欄位更安全，因為未來新增catalog欄位不會自動滲入模型。Missing value固定為
`<missing>`，大小寫與空白正規化，輸出field order不可變。

`candidate_feature_vector`把design中的schema固定為exact 21 fields：pointwise logit、RRF score/rank、三個source
presence/rank、五個match、五個conflict與兩個counts；任何NaN/Infinity都拒絕。`rank_scores`只依model score、
原RRF rank，再以UUID作最後deterministic tie-break，UUID從未成為feature。Metrics同時保存numerator、denominator
與value，並提供Top-1、MRR@10、hard-negative accuracy、Recall@10/25、failure-category與逐case paired rank
transition；target不在pool時保留`None`，不能由reranker補入。

Artifact validators會遞迴走訪任意深度JSON。Pool同時拒絕expected labels、winner/gates/metrics與任何pointwise/
listwise score；raw Test允許神經scores但仍拒絕labels與winner。Canonical JSON使用UTF-8、sorted keys、compact
separators、newline與`allow_nan=False`，SHA-256 helpers則讓後續每個phase能綁定相同bytes。

### 測試揭露的資料事實與修正決定

第一次focused run發現原先規格盤點中的「hard negative 12/4/4」只計算matched ranking cases；實際benchmark
還把全部ambiguous與no-match safety cases標為`hard_negative=true`，所以全體分布是Train/Dev/Test
`34/13/13`，其中真正參與ranking hard-negative accuracy的matched子集才是`12/4/4`。沒有修改資料或混合
denominator；validator現在同時凍結兩組counts，`ScoredCase` ranking metrics只接收matched targets。這個拆分
保留安全資料語意，也避免未來把non-match案例錯算成Top-1失敗。

### QA結果、未做事項與下一步

9/9 focused tests、27/27既有ranking/report/service related tests與933/933完整suite通過。Ruff format/check、
target-local strict MyPy、compileall、`git diff --check`與optional-import absence通過；唯一warning仍是既有
Starlette／AnyIO alias deprecation。`data/evaluation/neural-reranker-comparison-v1`、正式reports與model-cache
目錄全部不存在；沒有network、dependency install、retrieval、training、Test exposure、API、Dual RAG、
PostgreSQL、calibration或runtime修改。

下一步只執行NRC-T2：新增optional `reranking` dependency／constraints、pinned model config，以及explicit-license、
safetensors-only、offline local-only的model supply-chain adapter與fake/local tests。T2仍只寫機制，不連網、
不安裝套件、也不下載真實MiniLM。

## 2026-09-24 — Neural reranker comparison v1：確認design並拆成十個不可跨越的tasks

### 新執行了什麼、解決什麼問題

Owner以「繼續下一步」確認CPU neural reranker design，本輪因此把`design.md`狀態改為CONFIRMED並建立十項
`tasks.md`草案。任務不是把文件中的六個CLI commands直接排成六步，而是依「是否可能改變模型」與「是否
可能暴露正式Test」重新劃分責任：T1–T6完整建置所有contracts、模型adapters、artifact lifecycle與synthetic
E2E；T7才允許外部dependency/model acquisition及正式Train/Dev pool；T8只fit與freeze；T9只collect一次
label-blind Test；T10只join labels、score、記錄與closure。

這解決最容易破壞履歷實驗可信度的時序問題。如果一邊開發scorer一邊看21筆Test，任何bug fix、feature調整或
hyperparameter修改都可能暗中變成test tuning。現在T9之前必須完成所有產品source與synthetic tests；T9之後
product/model/config全部凍結，T10唯一允許新增的是measured-artifact regression tests與文件。Formal raw row若
出錯也不retry，避免只重跑不利case。

### 代碼與artifact工作如何拆分，以及原因

T1先做不依賴ML library的data contracts、candidate renderer、21 features、metrics與label-blind validators，讓
最重要的leakage規則可在任何環境測試。T2再做optional dependency與MiniLM supply-chain boundary，但只寫
acquisition／safetensors／offline validation機制，不連網。T3獨立處理Set-Transformer head、mask、listwise loss、
train-only normalization與permutation tests，避免神經網路bug與artifact orchestration混在一起。

T4–T6才建立protocol/pool、fit、collect/score/check和reports的完整phase controller，全部先在temporary synthetic
58/21/21資料驗證。這個順序讓G2能在`model-cache`與formal evaluation directories仍不存在時，證明整套機制
具備exclusive-create、hash binding、idempotent unchanged、partial-state rejection與null winner gates。

T7清楚列出約90 MB pointwise snapshot加Torch／optional packages，並要求執行時重新說明、取得network permission，
不因owner確認tasks就視為預先授權下載。T8 formal fit若permutation或Dev contract失敗，直接block T9，不改架構。
T9固定21次Test retrieval上限與三臂candidate equality。T10則把12 matched denominator、paired transitions、
winner/null gates、QA、AI-eval、README與GitHub交付綁在同一closure。

### 本步沒有做的事與下一步

本輪沒有建立任何product source、沒有修改pyproject dependencies、沒有安裝Torch、沒有下載模型、沒有retrieval、
沒有training，也沒有執行Test。Requirements與design已確認，但tasks仍是DRAFT，所以Lean G1*尚未關閉。
下一步由owner確認十項tasks；確認後只開始NRC-T1，不會一次跳到下載模型或正式experiment。

## 2026-09-24 — Neural reranker comparison v1：確認requirements並完成CPU模型design草案

### 新執行了什麼、解決什麼問題

Owner以「繼續下一步」確認17項Neural Reranker Comparison requirements，因此本輪把狀態從DRAFT更新為
CONFIRMED，並建立`design.md`。設計第一次回答了實作前最關鍵的問題：什麼才算真正的neural pointwise、
什麼才算真正使用候選集合上下文的listwise，以及如何在只有36個matched train queries與12個matched test
queries的限制下，避免把模型搜尋或test overfitting包裝成架構成果。

Pointwise選定Apache-2.0的`cross-encoder/ms-marco-MiniLM-L6-v2`，以immutable revision、safetensors、CPU
float32、`local_files_only`和`trust_remote_code=False`執行。V1不使用36題去微調2,270萬參數，而是凍結預訓練
Cross-Encoder，讓它作為真正的query-candidate pair neural scorer。這解決既有`heuristic-v1`只是token overlap、
卻可能在履歷敘述中被誤稱為neural reranker的問題；代價是MS MARCO與Hot Wheels domain mismatch可能產生
null result，但這比用小樣本過擬合後宣稱改善更可信。

### Listwise修改哪一層、方法選型與原因

Listwise不再選另一個逐candidate模型，而是在每個候選的frozen pointwise logit、RRF score/rank、三個source
presence/rank以及五種structured match/conflict上建立固定21維vector。模型是`21→32`投影、一層4-head
self-attention與逐candidate scalar head，沒有positional embedding；loss在整個candidate list上做masked softmax
cross-entropy。Self-attention讓每個candidate score依賴其他候選，移除position則讓輸入shuffle後的分數只跟著
identity一起shuffle。這個permutation-equivariance property會在test collection前成為hard gate，防止把array
順序當成學到的ranking訊號。

Listwise head只在target已出現在RRF pool的matched train lists上學習，用dev MRR@10 early stopping；continuous
normalization也只能fit train。固定seed、CPU float32、AdamW、100 epochs上限與10-epoch patience都在看到結果前
寫死。模型刻意保持很小，因為它要回答「candidate-relative context是否有額外價值」，不是展示參數量。

### Artifact生命週期、依賴與安全決策

設計把流程拆成`--acquire-model`、`--freeze-protocol`、`--fit`、`--collect-test`、`--score`與`--check`。只有
acquisition可連網且需明確license確認；之後全部local/offline。Train/dev pool與test raw都拒絕expected labels，
fit phase不能載入test label loader，test則在兩個models與protocol凍結後一次性collect，score才join labels。
任何partial state、hash drift、non-finite score、candidate差異或permutation failure都fail closed而不覆寫。

Neural packages維持optional，計畫新增獨立`reranking` extra，使用repo既有major range內的
`sentence-transformers==3.4.1`、`torch==2.7.1`與safetensors。第三方MiniLM權重只留在gitignored
`model-cache/`；repo保存model ID、revision、Apache-2.0、file hashes與一個很小的project-trained listwise
safetensors checkpoint。拒絕pickle與remote code的原因，是模型artifact也是不可信供應鏈輸入，不能只因來自
公開model hub就直接執行。

### 本步沒有做的事與下一步

本輪只完成design草案；沒有安裝Torch／Sentence Transformers、沒有下載約90 MB權重、沒有產生candidate pool、
沒有training、沒有讀test labels，也沒有修改`rerank.py`、`service.py`、API、calibration、Dual RAG、PostgreSQL
或canonical data。下一步由owner確認design後，再把六個phase、模型adapter、artifact validators、tests、正式
experiment與closure拆成原子化`tasks.md`；tasks確認前不開始build。

## 2026-09-24 — Neural reranker comparison v1：先固定三臂公平比較的requirements

### 新執行了什麼、解決什麼問題

HICS-v4已用可重現的historical FAIL結束identity-admission支線，本輪正式回到原始專案最重要但尚未完成的
Pointwise／Listwise主線。先重新核對最初的`Product Variant Resolver.md`、MVP brief、現行RRF／heuristic reranker、
fixture benchmark與roadmap，建立`specs/neural-reranker-comparison/requirements.md`。新規格把研究問題限定為：在
byte-identical的canonical RRF Top-25 candidate pool上，比較No Reranker/RRF、Neural Pointwise Cross-Encoder與
Neural Listwise，而不是同時更換retrieval、資料或confidence policy。

這解決現有README容易造成的技術落差。專案目前雖有名為`PointwiseReranker`的`heuristic-v1`，實際模型只是
token-set overlap加上source support、match bonus與conflict penalty，先前對RRF的Top-1增益也是0.0；它不能被
包裝成原始需求中的neural cross-encoder，也沒有任何listwise architecture evidence。新requirements明確要求三個
arm各自具名，並禁止把既有heuristic結果冒充神經模型比較。

### 資料與評估邊界，以及為何這樣決定

本輪確認`fixture-v1`共有100 cases，按casting family隔離為58 train、21 dev與21 test；全體包含60 matched、
20 ambiguous與20 no-match，但test真正可計算排序Top-1的matched只有12題，其中4題標為hard negative。因為樣本
很小，一個case就會讓Top-1改變約0.0833，規格不只要求Top-1、MRR@10、hard-negative accuracy與p95 latency，
也要求公開raw numerator／denominator、逐case rank transition與failure-category結果。這是為了避免把一兩題的
變化寫成廣泛市場準確率。

Candidate pool要求在任何neural scoring前由現行sparse+dense+structured+RRF路徑一次產生並凍結，而且不含
expected labels；三個arms只能重排，不能重新retrieve、補入target或刪除難例。Pointwise必須逐query-candidate
獨立評分，Listwise則必須真正使用整個候選集合並通過permutation-equivariance測試，不能只是把pointwise函式
改名。Train只fit train families、dev只選每個architecture的一組config、test則在兩個model都凍結後一次性比較。

### Gate、技術選型延後與本步刻意沒有做的事

R11既有產品承諾被具體化為預先聲明的value gate：神經arm必須相對RRF提高至少0.05 absolute Top-1、不降低
hard-negative accuracy與MRR@10、維持同一Recall@25，且warmed resolver p95不超過1.5秒。多個arm通過時先看
hard-negative、Top-1、MRR、latency再看部署複雜度；沒有任何arm通過時必須保存`winner:null`並保留RRF，不能
看完test後調參重跑。

本步只完成requirements草案與roadmap狀態，尚未決定實際cross-encoder／listwise library、沒有安裝ML dependency、
沒有取得外部model、沒有生成candidate pool、沒有training或evaluation，也沒有改API、Dual RAG runtime、
PostgreSQL、calibration或canonical data。具體CPU model與artifact設計刻意留給owner確認requirements後的
`design.md`，避免先選工具再倒推需求。

### 下一步

Owner先確認這份requirements。確認後才撰寫design，內容會回答：使用哪一個可在本機CPU重現且license可交付的
Pointwise Cross-Encoder、Listwise如何真正建模候選相對關係、如何把100-case pool與model artifacts分階段凍結、
以及如何在不讓test labels進入fit／selection code的前提下完成一次性比較。

## 2026-09-24 — HICS-T9：封存v4 null result並交回Pointwise／Listwise主線

### 新執行了什麼、解決什麼問題

HICS-T5已證明三個certificate profiles沒有一個能通過全部historical gates，但只有calibration artifacts仍不足以
讓面試官或後續維護者理解「程式成功、實驗失敗、runtime未授權」三者差異。本輪HICS-T9完成branch-aware
closure，把requirements coverage、實測metrics、artifact hashes、AI output rubric、release boundary與下一個
roadmap gate整理成可獨立閱讀的文件，並將v4明確標為最後一個identity-admission attempt。

這解決了兩種履歷風險。第一，不會因924項測試全綠就宣稱模型可上線；測試證明determinism與integrity，實測
gates仍判定FAIL。第二，不會把`winner:null`描述成「沒有成果」；它是可重現的negative result，證明pre-retrieval
gate阻止了32次不必要retrieval、private evaluation與unsafe runtime promotion。

### 文件修改、結構選擇與原因

新增`specs/human-knowledge-identity-certificate-development/review.md`，逐項映射HICS-R1–R16，並固定四個獨立
verdict：implementation PASS、historical eligibility FAIL、holdout NOT RUN、runtime NOT AUTHORIZED。拆成四層是
為了避免常見的二元「project pass/fail」誤解；一個工程實作可以正確執行，同時產品假設不合格。

新增`docs/evidence/human-knowledge-identity-certificate-development-v4.md`，公開source／inventory／三個artifact
hashes、142→139 authority mapping、460 claims、401 certificates、101 bridges、七個unresolved authorities與四個
profiles的完整量測表。另新增`docs/evidence/ai-evals/human-knowledge-identity-certificate-v4.md`，用grounding、
public/private separation、leakage、certificate/candidate independence、retrieval/evidence integrity、explainability、
positive preservation、negative safety、selection與release safety分開評分。Positive preservation唯一明確FAIL；
negative safety與selection integrity仍PASS，避免把一個維度的失敗擴寫成所有維度都無效。

README新增v4摘要與read-only`--check`方式；decision D90改為`CLOSED HISTORICAL FAIL`；roadmap標記HICS-T9
完成並新增下一個未開始項目：在同一凍結candidate pool比較No Reranker/RRF、Neural Pointwise與Listwise。
Requirements、design與tasks狀態也同步封版。V4 source在正式結果出現後沒有修改，HICS-T6–T8維持blocked，
也沒有建立v5 spec或偷跑下一個evaluation。

### QA、已知債與GitHub邊界

Read-only installed CLI`--check`重新驗證frozen artifacts，回傳`valid`、`historical_calibration_fail`與
`winner:null`。60/60 focused、181/181 related與924/924完整tests通過；Ruff format/check、target-local strict
MyPy、compileall、artifact hash/absence與`git diff --check`通過。唯一suite warning仍是既有Starlette／AnyIO
deprecation。Repository-wide strict MyPy仍有18個既有檔案共51個errors，主要是optional dependency stubs、舊
development modules inference、redundant casts與既有API/service typing；本輪沒有用無關重構掩蓋這些技術債。

Git交付只在`Product Variant Resolver`自己的repo root進行；parent workspace的`AGENTS.md`、`.codex`與其他
folders不在此Git working tree內。本機為修復macOS hidden `.pth`而加入的`.venv/sitecustomize.py`受gitignore
保護，不會推送。Commit包含v4 source/tests/specs、三個null calibration artifacts與closure docs，不包含private
evidence、holdout、raw retrieval、database資料或runtime設定。

### 真正下一步

Identity-admission路線到此結束，不因bounded profile接近168門檻就調參或建立v5。下一步應先建立新的Lite spec，
定義No Reranker/RRF、Neural Pointwise與Listwise共用的frozen candidate pool、train/dev/test leakage boundary、
metrics、latency與selection gates；在requirements、design、tasks逐份確認前，不修改runtime或執行新比較。

## 2026-09-24 — HICS-T5：正式historical gate為FAIL，安全停止holdout分支

### 新執行了什麼、解決什麼問題

HICS-T4只完成了可執行機制與synthetic lifecycle tests；本輪HICS-T5才第一次對真實公開證據執行正式branch
gate。執行前先重算25個historical input bindings、v4 source SHA-256
`cf2e207b97f395d2e4b334875ac17f2efa0500b1e675910e0242e562503b665a`、139 authorities、401 certificates與
certificate inventory checksum
`dafc709027af513e8bd6db20b80cc1c73e096461a05d13c69699b759f05edec7`。資料與source一致後，才執行一次：

`pvr-develop-human-knowledge-identity-certificate --root . --freeze-protocol`

命令回傳`calibration_failed_created`、`protocol_created:false`與`retrieval_executed:false`。這回答了v4最重要的
問題：corpus-wide minimal certificates雖能消除已知false positives，但沒有任何non-reference profile同時保留
全部既有positive gates。因此v4不能進入16+16 holdout，也不能被挑成「最接近」的winner。

### 正式量測結果，以及錯誤究竟在哪裡

Reference保留168/168 existing positives、24/24 required targets、10/10 anchor positives與12/12 HIC positives，
但它本來就不是survivor，而且仍放行11個anchor absent identities與10個HIC absent identities，兩個secondary
R32/R33對BNR34 veto也都是0/2。這再次證明只看原rank-1 anchor有recall，但沒有足夠的identity safety。

三個certificate profiles則呈現相反情況：它們全部達成0 existing forbidden candidates、0 unrelated output、0
anchor absent identities、0 HIC absent identities、2/2 secondary vetoes，以及0 retrieval、certificate
construction、query support、alias alignment、frame comparison與decision errors。然而：

- `certificate-exact`只保留42/168 existing positives、6/24 required targets、0/10 anchor positives與3/12 HIC positives；
- `certificate-structural`保留82/168、7/24、4/10與7/12；
- `certificate-bounded`雖提高到137/168 existing positives，required targets反而只有5/24，anchor與HIC positives也只有5/10與7/12。

所以失敗不是程式exception、retrieval error或negative leakage，而是模型規則的recall邊界：完整minimal certificate
要求仍對許多真實shorthand、alias與舊query過於嚴格。Bounded profile已是預先聲明的最寬版本，仍少31個existing
positive hits，不能在看到結果後新增relation、放寬context或改gate。那會把historical set變成training data，破壞
本次experiment的可驗證性。

### Artifact分支、代碼與測試修改

FAIL分支只建立：

- `historical-calibration.json`，SHA-256為`d9ca782bd47252af0a1047776da3add97a5b40b2709b8a5d44bf4e6ecd78cf96`；
- `historical-calibration-manifest.json`，SHA-256為`3bb89724f50f5a1229bf36023b84551fe7ee3cd27f5355f74d4fee1fd582ec95`；
- `historical-calibration.md`，SHA-256為`621ba4e10981790f1acda13d79aab2374a2a40ba2383a1a499e3ea6c65c5b4fb`。

Report保存exact 223／22／24 denominators、四個profiles全部16項gates、`winner:null`、空survivor list、0
retrieval與所有source hashes。`data/evaluation/human-knowledge-identity-certificate-development-v4`完全不存在；
protocol、inventory artifact、negative declarations、pack、raw、selection與private evaluation都沒有建立。

正式結果可見後沒有修改v4 product source或profiles。只在evaluation test加入兩個measured regressions：第一個
鎖定四個profiles的實測counts、selection metrics、zero-error gates與下游artifact absence；第二個鎖定report／
manifest hashes、`protocol_authorized:false`及Markdown null-branch文字。這種「先量測、後寫artifact regression」
避免把預期答案偷寫進正式演算法。

### Pre-freeze QA、環境問題與下一步

Targeted Ruff、format、target-local strict MyPy、compile、58 focused與179 related tests先通過。第一次完整suite
有一項舊family-evaluation subprocess test失敗；根因不是產品碼，而是macOS把虛擬環境editable `.pth`標為hidden，
使新開Python process找不到workspace `src/`。本機`.venv`加入gitignored `sitecustomize.py`恢復src-layout import後，
原失敗test與完整pre-freeze suite全綠；這個環境修復不進repo，也未改evaluation內容。加入兩個measured tests後，
60/60 focused、181/181 related與924/924完整suite全數通過，唯一訊息仍是既有Starlette／AnyIO deprecation；
HICS-T9 closure會把這些結果整理成正式QA evidence。

HICS-T6–T8現在依法blocked，不會author negatives、不會執行32次retrieval，也不會score holdout。下一步是HICS-T9：
完成FAIL branch review、requirements coverage、public evidence、AI-eval、README與GitHub delivery，然後回到原始
No Reranker/RRF、Neural Pointwise、Listwise比較主線。V4是已約定的最後一個identity-admission attempt，不建立v5。

## 2026-09-23 — HICS-T4：完成零檢索historical scorer與不可變artifact生命週期

### 新執行了什麼、解決什麼問題

HICS-T3已能對單一query產生certificate support並判斷Top-5 candidate，但當時只有in-memory primitives，還不能
安全執行正式experiment。HICS-T4補上從「讀取已公開證據」到「分階段凍結結果」的完整控制面：loader會綁定
223筆existing、22筆anchor-confidence v4及24筆HIC-v1 raw evidence與所有既有source/artifact hashes；scorer只
重算既有rows，不呼叫retriever。每個profile都輸出原有positive、merge、governance、unrelated、required-target、
absent-identity與R32/R33對BNR34 gates，並新增certificate construction、query support、alias alignment、frame
comparison、decision和retrieval的zero-error gates。

`reference-anchor`仍保留作comparison baseline，但`eligible_as_survivor`固定為false。三個certificate profiles
只有在全部16個historical gates都通過後才可留下；多個survivors的順序在看到結果前固定為：先比較negative
admissions，再比較positive abstentions，再比較non-exact operations，最後才依exact、structural、bounded排序。
這解決了「測量後再挑自己喜歡的門檻或policy」的selection bias，也不允許reference因數字較好而成為winner。

### 代碼修改了哪一部分、原因與技術選型

`human_knowledge_identity_certificate_development.py`新增`historical_calibration`與
`apply_certificate_profile`。每個query只建立一次candidate-independent support，candidate rows再依原始source
rank映射到authority membership和primary-frame preflight；輸出保留support checksum、candidate evidence、
admit/abstain及錯誤分類。Existing／anchor／HIC的summary函式沿用已凍結版本，原因是v4要更換admission核心，
不是重定義過去的成功指標。Reference則只重用v3 comparison policy，不能建立v4 certificate support。

Artifact lifecycle使用canonical JSON、SHA-256、exclusive-create及byte-for-byte recomputation。Historical FAIL
只能建立`historical-calibration.json`、manifest與Markdown，且`winner:null`；任何protocol、inventory、pack、raw、
selection或額外report檔都會使validation失敗。Historical PASS才同時凍結protocol與完整certificate inventory；
兩者只存在一邊會被視為partial state，而不是自動補寫。Protocol綁定source hashes、inventory checksum、profile
definitions、historical gates、winner order與holdout schema，避免後續看到holdout結果後更換規則。

Conditional pack builder要求16 positive加16 negative、四種challenge各4筆、32個唯一case IDs，以及positive／
negative family keys互斥。Negative declarations是獨立、post-freeze檔案，必須保存corpus-absent identity、預期
empty/ambiguous/conflict原因與family key。這個schema選擇讓HICS-T6日後能人工檢查hard negatives，而不是從
retrieval結果反向挑題。

Raw collection固定32次Top-5，任何error都原樣保存且不retry。Raw validator遞迴拒絕expected label、case class、
authority/family label、profile decision、eligibility、gate或winner等欄位，只允許query、ranked candidates、work
與error。第二次`--collect`先驗證既有bytes並直接回傳`unchanged`，所以errored row也不會被偷偷重抽。Scoring
只能讀取已凍結raw，再從pack join labels並套用historical survivors；selection同樣只建立一次且不可覆寫。

`pyproject.toml`新增installed command
`pvr-develop-human-knowledge-identity-certificate`，只提供互斥的`--freeze-protocol`、`--freeze-pack`、`--collect`、
`--score`與`--check`。本機package已重新安裝並以`--help`確認五個phase可用。沒有增加runtime dependency，
CLI仍使用既有FastAPI專案環境、Python dataclasses、JSON與SHA-256；這比另加workflow framework更容易稽核，也
避免開發experiment滲入API或Dual RAG runtime。

### 測試方式、結果與本步刻意沒有做的事

新增8項HICS-T4 tests，全部使用`tmp_path`、synthetic 223／22／24 rows及monkeypatched public loaders。測試會讓
任何retriever call直接失敗，因此能證明historical contract是0 retrieval；也覆蓋reference不可存活、exact
winner order、FAIL僅三檔且可重跑、PASS同時凍結protocol/inventory、raw深層label-blind檢查、error row不retry、
16+16 family-disjoint pack、partial/tampered freeze rejection與五階段CLI。Focused suite目前58/58，六個相關identity suites共179/179；targeted
Ruff、target-local strict MyPy、compileall及installed CLI help均通過。

正式`data/evaluation/human-knowledge-identity-certificate-development-v4`與
`reports/human-knowledge-identity-certificate-development-v4`仍不存在。本步沒有執行真實223／22／24 gate、沒有
建立negative declarations、沒有32次holdout retrieval、沒有讀取private evidence，也沒有修改API、Dual RAG、
PostgreSQL、canonical、release、color或physical-feature行為。下一步HICS-T5是先做pre-freeze QA，再且僅執行
一次正式zero-retrieval historical branch gate；結果若FAIL就停止HICS-T6–T8，若PASS才允許凍結後續holdout。

## 2026-09-23 — HICS-T3：先決定query authority，再讓Top-5只做membership與衝突檢查

### 新執行了什麼、解決什麼問題

HICS-T2已能證明哪些primary claim組合唯一，但還沒有把使用者query轉成可執行的decision。本輪HICS-T3新增
candidate-independent query support：完整query先對全體460 claims／401 certificates解析一次，得到`empty`、
`ambiguous`或`singleton` authority set及固定checksum；Top-5 candidates之後只能查自己是否屬於singleton，
不能用rank、score、UUID或candidate文字改寫support set。

三個non-reference profiles皆為categorical rules，沒有scalar threshold。`certificate-exact`只接受normalization
後exact claims；`certificate-structural`再加入compact segmentation與2/4-digit leading-year suffix；
`certificate-bounded`才允許global-unique prefix、alphabetic edit-1、same-frame`o/0`、repeated-digit restoration與
leading-year uncertainty`x`。`reference-anchor`明確只供下一步historical comparison，不可建立certificate
support，也永遠不能成為survivor。

### Query parser、context與數字frame為何這樣設計

Query atoms保存原始／normalized offsets、source token與compact segment位置。Context只來自凍結public lexicon；
若`model`等字同時參與primary identity，identity precedence會使它不能被丟成noise。Certificate只需完整滿足，
candidate完整車名中未出現在query的其他claims可保留為`omitted_primary_claim_ids`；這使`55 Chevy`能合法指向
`55 CHEVY BEL AIR GASSER`，而不要求query複製完整candidate名稱。

反向的額外query字則不能隱藏。`Honda Accord`、`BMW M4`與`Bugatti Divo`都得到`empty`，因為shared maker不構成
完整certificate，而且`accord`／`m4`／`divo`保留為unresolved discriminative atoms。`unverified 55 Chevy
listing`則得到singleton，只有`unverified`與`listing`以`frozen_context_wrapper`留下reason code。

初版compact probe曾把未知`R33`或`kat`過度切成單字母／單數字。修正後segmenter要求原digit runs逐段完全
守恆，禁止把`33`拆成`3 + 3`；普通純字母token也不能由一字母claims拼湊。合法的
`2020fordf150lariat`仍可切為`2020`／`ford`／`f`／`150`／`lariat`，structural profile得到singleton；exact
profile則保持empty。這個修正是一般結構規則，不是為Nissan寫例外。

Local-frame檢查會保留owner slots。`Nissan Skyline GTR R33`不能成為BNR34：bounded evidence為empty，保存
`r33`原子與對`r34`／`bnr34`的兩個primary numeric conflicts。另一方面`20 Ford F 150 Lariat`只在structural
profile以`leading_year_suffix`通過，`Mercedes Benz 5o0 E`只在bounded profile以`ocr_o_zero`通過。Focused
tests也逐一覆蓋unique prefix、edit-1、repeated digit與year uncertainty reason codes。

### Candidate decision、variant邊界與驗證結果

Candidate evidence綁定query support checksum、inventory checksum、profile、authority key、member knowledge ID、
source rank、primary frame comparisons、membership、reason codes與final decision。Empty／ambiguous support在rank 1
到5都直接abstain；singleton只可保留同authority文件。若同一casting authority有多筆provisional documents，
它們依原rank保留，但每筆都輸出`casting_authority_only`與`variant_not_resolved`，不會選擇具體release。

真實smoke evidence中，`unverified 55 Chevy listing` exact、`2020fordf150lariat` structural與
`Mercedes Benz 5o0 E` bounded皆為singleton；`Honda Accord`及R33 probe為empty。每個candidate decision重用完全
相同的query checksum，且source-order validator拒絕重排或重複rank。

Focused suite由27增至49項，加入profile contract、shared-maker negatives、partial shorthand、compact/digit-run
守恆、全部bounded relations、context precedence、ambiguity不tie-break、same-authority multi-document、rank 1/5
fail-closed、checksum/span/candidate tamper與禁止candidate state進query evidence。49/49 focused、包含HIC／HIE／
HICG的143/143 related tests，以及Ruff、strict MyPy、compile、artifact absence、`git diff --check`全數通過。

本步仍沒有執行223／22／24 historical calibration、沒有retrieval或正式artifact，也沒有修改API、Dual RAG、
PostgreSQL、canonical、release或physical-feature行為。下一步HICS-T4才會加入public evidence loaders、exact
historical scoring、phase-gated CLI與artifact lifecycle validators；正式branch gate仍留在HICS-T5。

## 2026-09-23 — HICS-T2：用完整corpus證明minimal certificates，不用variant欄位補唯一性

### 新執行了什麼、解決什麼問題

HICS-T1只回答「142 documents屬於哪139個authority」，還沒有證明query最少需要哪些identity evidence。本輪
HICS-T2把每個primary casting拆成position-bound claims，對完整139-authority corpus列舉所有ordered subsets，
只保留能唯一辨識一個authority且刪除任一claim後失去admissible uniqueness的組合。真實結果是460個claims、
401張certificates；95張使用一個numeric/alphanumeric或真正one-word claim，306張使用兩個claims。

這一步也讓T1的「normalized primary沒有完全同名碰撞」得到更嚴格修正。完整claim sequence若同時包含在較長
authority中，較短identity仍不能獨立成立。7個authority因此明確成為`unresolved_collision`：
`Chevy Bel Air Gasser`、`Dodge Challenger`、`HONDA CIVIC EF`、`Honda CR-X`、`Nissan Skyline RS`、
`Silverado Trail Boss LT`與`Toyota Supra`。例如`Toyota Supra`的完整claims同時出現在
`1997 Toyota Supra HKS`；系統沒有偷用series、color、source rank或release label拆開它們。

### 代碼修改了哪一部分、選型原因

同一個隔離v4 module新增`CertificateClaim`、`IdentityCertificate`、minimality/elimination proof、
`AliasBridge`與`CertificateInventory`。Alphabetic token各自成claim；純數字或英數token形成不可拆分的local
frame，保留frame kind、前後identity owners與原始digit runs。例如`2020 Ford F-150 Lariat`會保留leading-year
`2020`（owner after=`ford`）以及standalone-model `150`（owners=`f`／`lariat`），所以相同數字不能移到另一
個slot製造相等。

Certificate不是threshold或embedding similarity。每一張都保存完整competitor set、逐claim加入後剩餘的
authorities、最後唯一authority、每個one-claim deletion的結果與SHA-256。若primary casting有多個claims，
單一alphabetic claim即使在小corpus中剛好唯一也不合格；這避免`Honda`或其他maker-like token單獨代表較長
車名。Minimality因此定義成admissible uniqueness：刪除後必須成為non-unique、empty，或落入已禁止的
single-alphabetic form，且reason都寫入proof，不是暗中例外。

現有primary castings最多8 claims，低於設計上限12；超過會fail closed而不截斷。完整inventory checksum是
`dafc709027af513e8bd6db20b80cc1c73e096461a05d13c69699b759f05edec7`，並綁定T1 authority checksum
`148df20187e842434d335d0be3469fbd18db1404d989f8544d3d616d5644ccd8`。

### Alias bridge為何不等於新identity evidence

101個approved aliases全部建立bridge，沒有任何alias新增claim或跨authority引用claim。Bridge保存normalized
source positions、target claim IDs、relation、未映射atoms與checksum。公開資料共358個exact mappings與1個
leading-year-suffix mapping；所有101個bridges至少映射一個既有claim。Human label中的`premium`、series或
seller文字可留在unmapped evidence，但不能變成certificate claim。Synthetic tests另外覆蓋
`MercedesBenz`→`mercedes`+`benz` compact bridge及`5o0`→`500` OCR relation，證明來源與目標形式都保留，
target digit runs不會被改寫。

### 測試結果、限制與下一步

Focused suite由14增至27項，新增真實460／401／101 counts、local frames、one-word與multiword single-claim
規則、contained-primary unresolved、numeric owner proof、compact/OCR alias、12-claim ceiling、determinism、
independent uniqueness/minimality validation、certificate/bridge tamper與forbidden metadata tests。27/27 focused、
包含HIC／HIE／HICG的121/121 related tests，以及targeted Ruff、strict MyPy、compile、artifact absence與
`git diff --check`全數通過。

目前所有certificate資料仍只在memory建立；沒有寫正式inventory、protocol或report，retrieval仍為0，API、
Dual RAG、PostgreSQL、canonical、release與physical-feature行為不變。下一步HICS-T3才會用這份inventory將
query先轉成candidate-independent support set，之後才檢查candidate authority membership與all-rank numeric
conflict；本步沒有提前實作或量測admission結果。

## 2026-09-23 — HICS-T1：把142筆文件整理成可驗證的139個identity authorities

### 新執行了什麼、解決什麼問題

Owner確認九項task list後，本輪開始v4實作，但範圍只到HICS-T1。新增的public authority inventory先驗證
HIC-v1、HIE-v2與HICG-v3共9個frozen source／evidence hashes，再讀取3個既有corpus inputs。真實執行確認
142 documents可穩定映射為139 authorities：100個provisional documents形成97個casting authorities，42個
review-family documents形成42個review-family authorities，document excess正好是3。

這一步解決了「文件數是否等於可辨識identity數量」的邊界問題。`83 Chevy Silverado`的3筆provisional
documents與`Toyota Supra`的2筆documents各自保留原始knowledge ID／UUID，但共享casting authority；系統不會
把不同release錯當成不同casting，也不會因為分組就宣稱它們是同一個variant。目前139個normalized primary
castings之間沒有碰撞，因此全數標成`certifiable`；若未來兩個authority的primary casting正規化後相同，兩邊
都會明確變成`unresolved_collision`，而不是靠來源順序選一個。

### 修改了哪一部分、為何這樣設計

新增`human_knowledge_identity_certificate_development.py`，但沒有改動既有HIC／HIE／HICG frozen modules。
核心資料結構是`IdentityAuthority`與`AuthorityInventory`。Authority key只允許`casting:<casting_id>`或
`review_family:<review_family_id>`；member IDs/UUIDs依knowledge ID排序，inventory及所有input bindings使用
canonical JSON與SHA-256產生可重現checksum。本次實際inventory checksum是
`148df20187e842434d335d0be3469fbd18db1404d989f8544d3d616d5644ccd8`。

Alias allowlist只讀provisional的`human_label_names`與review-family的`aliases`，正規化後去重，並排除與primary
casting相同的重複surface；目前共保留101個future bridge surfaces。資料模型刻意不包含series、variant label、
pricing keyword、initial model text、source IDs、color、wheel、tampo、edition或packaging。原因是HICS-T1只應
建立casting/family authority lineage，若把release欄位帶進inventory，下一步certificate可能錯誤地利用它們
製造variant-level唯一性。

將inventory保留在memory而沒有寫入正式artifact也是刻意決定。HICS-T2尚未產生或證明minimal certificates；
只有T5 historical PASS才有權凍結正式inventory/protocol。現在先提供deterministic serialization與checksum，
可以測試重現性，但不會讓未完成結構被誤認為已凍結的evaluation evidence。

### 測試結果、修正與下一步

新增14項focused tests，覆蓋9個upstream hashes、142→139真實整合、兩個multi-member casting、固定排序／
checksum、forbidden fields、alias去重、review-family namespace、primary collision、group lineage conflict、
duplicate membership、count drift與checksum tamper。第一輪測試曾揭露兩個測試假設問題：暫存tamper case沒有
隔離其他upstream paths，以及規格把真實`83 Chevy Silverado`多寫了一個apostrophe；兩者均修正為與真實
資料一致，沒有放寬production validator。

最終14/14 focused與包含HIC／HIE／HICG的108/108 related tests通過；targeted Ruff、strict MyPy、compile、
v4 artifact absence及`git diff --check`也通過。正式certificate、CLI、calibration、protocol、pack、raw、
selection與retrieval仍為0，API、Dual RAG、PostgreSQL、canonical、release及physical-feature行為均未改動。
下一步HICS-T2才會從primary casting建立claims、完整列舉minimal certificates，並把101個aliases限制成只能
bridge到既有claim的證據。

## 2026-09-23 — V4 task草案：把最後一次identity admission變成有停損的九步執行鏈

### 新執行了什麼、解決什麼問題

Owner以「繼續下一步」確認v4 design後，本輪把已確認的certificate架構轉成九個原子化tasks。這一步解決的
不是identity演算法本身，而是「如何在Lite模式下實作、量測、失敗即停，而且一定回到Pointwise／Listwise」的
執行治理問題。若沒有明確分支，團隊很容易把建置、正式calibration、holdout與runtime誤當成同一個連續工作，
或在historical FAIL後仍為了完成清單而花費32次新retrieval。

任務因此固定為三段：HICS-T1–T4只建置authority inventory、minimal certificates、candidate-independent
support/admission，以及historical／CLI lifecycle；HICS-T5才第一次正式執行223／22／24 public rows的
zero-retrieval branch gate；HICS-T6–T8只有PASS時才能建立16+16 pack、exactly-once收集32筆Top-5 raw及評分。
HICS-T9是兩個分支都必走的closure，確保FAIL也會留下QA、evidence、AI-eval、README／decision／log與GitHub
交付，而不是只留下難以解讀的JSON。

### 修改了哪些文件、為何這樣拆分

新增`specs/human-knowledge-identity-certificate-development/tasks.md`，每一項都回指HICS-R1–R16、列出owner、
變更檔案和可測量acceptance。Requirements與design狀態同步標成已確認；roadmap與D90改為「task list等待
owner確認」。本步沒有新增source、tests、CLI或artifact，也沒有執行retrieval，因為Lite spec gate要求先確認
任務邊界，才能開始HICS-T1。

把authority inventory、certificate derivation和query/candidate decision拆成三項，是因為三者有不同的失敗
語意：T1要證明142 documents確實只有139個可辨識authority；T2要證明每張certificate在完整corpus中唯一且
最小；T3才回答query support set與candidate membership。若把它們寫成一個大型task，測試失敗時無法判斷是
資料分組、最小性證明還是decision logic出錯，也不利於履歷面試時逐層說明架構。

T4只用synthetic／temporary inputs驗證CLI和artifact lifecycle，正式223／22／24 gate留到T5。這個選型避免
在程式仍可修改時意外先看到正式結果。T5 PASS後source、inventory、profiles、protocol與input hashes一起
凍結；FAIL則只能保存三個null calibration artifacts並直接進T9，禁止用已看到的結果調整v4。這延續前幾版
成功阻擋unsafe promotion的證據治理，而不是為了產生winner降低門檻。

### 固定停損與後續主線

V4不論PASS或FAIL都不自動產生v5。T9完成後，下一個Lite spec固定比較同一frozen candidate pool上的
No Reranker／RRF、Neural Pointwise Cross-Encoder與Listwise Reranker。這保留owner原始要求的神經
Pointwise／Listwise展示，也讓v4只負責可解釋的identity admission，不把兩種不同技術問題繼續混在一起。

目前task list仍等待owner確認，因此HICS-T1尚未開始；API、Dual RAG、PostgreSQL、canonical identity、
release、color、wheel、tampo、edition與packaging行為全部不變。

## 2026-09-22 — HICG-v3需求草案：把正例誤殺與secondary數字衝突拆開處理

### 新執行了什麼、解決什麼問題

HIE-v2已合法結束為`winner: null`，本步沒有修改失敗實驗，而是唯讀分析其公開historical calibration，
並建立全新namespace的v3 requirements草案。分析要回答的不是「再把threshold調鬆一點」，而是為何最接近
安全目標的`envelope-bilateral`仍同時漏掉正例、又留下兩個hard negatives。

公開證據顯示該policy把既有正例從168降到146、v4正例從10降到9、HIC-v1正例從12降到10；常見誤殺來自
前置年份與seller context、`5o0`／`500`類局部OCR、多組數字共存、縮寫／單字編輯，以及compact spelling。
另一方面，剩下的兩個負例是`R32`或`R33`query對`BNR34`candidate；它們位於secondary rank，因舊流程直接用
`identity-token coverage >= 0.75`放行，繞過rank-1才有的結構衝突判斷。這次分析因此把recall與safety視為
兩個結構問題，而不是一個共用分數門檻。

### 規格修改了哪個部分、為何做出這個決定

新增`specs/human-knowledge-identity-claim-graph-development/requirements.md`，要求每個query先產生唯一且
candidate-independent的identity-claim graph。Graph要明確保存identity anchors、context、未解的辨識詞，
以及frame-local數字／英數結構；年份簡寫、OCR、縮寫和小幅編輯只能透過事前凍結且可稽核的一般規則處理。
採用graph而不是再延伸單一envelope，是因為同一句query可能同時包含年份、型號數字、maker/model與seller
語境，線性截取一段文字不足以表達它們各自的角色和關係。

最重要的政策變更是universal hard-conflict veto：rank 1至5都必須先檢查保留下來的model-number衝突，之後
secondary candidate才可使用既有coverage規則。這直接修正`R32/R33`被`BNR34`放行的控制流程缺口，且沒有
新增Nissan專用例外。正例則以local frame、公開corpus aliases、candidate-independent context boundary處理，
避免為了擋負例而再次大幅犧牲recall。

### 閘門、技術邊界與下一步

v3仍採public-only與historical-first。它必須先在既有223／v4 22／HIC-v1 24 rows同時達到168/168正例、
4/4 merge、24/24 prior required、10/10 v4正例、0/12 v4負例、12/12 HIC正例、0/12 HIC負例、兩個已知
secondary numeric conflicts都abstain且零錯誤。若沒有non-reference survivor，必須保存null result並維持
0個新retrieval；只有歷史gate全過，才可凍結source/protocol rules並建立新的32題family-disjoint holdout。

本步沒有寫產品碼、沒有建立design/tasks、沒有產生protocol/pack/raw/selection，也沒有修改API、Dual RAG、
PostgreSQL、canonical、color或variant行為。Requirements先以draft等待owner確認。

Owner以「進行下一步」確認HICG-R1–R16後，本輪新增`design.md`，但仍沒有寫產品碼或建立任何evaluation
artifact。設計把query處理拆成public identity grammar、candidate-independent claim graph、candidate comparison
與all-rank hard-conflict preflight四層。和HIE-v2最大的差異不是換一個threshold，而是數字不再形成global tuple：
leading year、standalone model與alphanumeric model各自在相鄰identity anchors定義的local slot比較，所以
`20`／`2020`可以在year frame等價，同一句中的`1500`仍獨立守恆，而`R33`／`BNR34`會在terminal model slot衝突。

為保留正例，設計先對完整query分詞，不再先刪noise；公開context vocabulary只有在atom未參與winning
corpus-wide identity hypothesis時才生效，避免把`Tesla Model S`的`model`誤刪。Compact segmentation、唯一prefix
abbreviation、alphabetic Damerau-Levenshtein edit 1、leading-year suffix、`o/0` OCR、重複digit復原與year後綴`x`
都有固定結構限制與reason code。這些規則掃描完整公開corpus，不讀Top-5 candidates或expected labels。

Candidate的approved alias可改善正向alignment，但不能隱藏primary casting中的數字衝突；每個non-reference
policy都先對rank 1–5執行相同hard-conflict veto，之後secondary才可進入coverage 0.75 gate。四個policy由寬到嚴
比較conflict-only、bilateral residual、query conservation與完整decision list；reference只作比較，不能成為survivor。

流程仍採historical-first：先離線重算223／22／24 rows，若無survivor，只能保存新的null calibration並維持
0 retrieval；有survivor才凍結source/protocol、建立16+16 family-disjoint pack並exactly-once collect。目前
design先等待owner確認；`tasks.md`、source、CLI、tests、protocol、pack、raw與selection當時全都尚未建立。

Owner再以「繼續下一步」確認design後，本輪新增八項依序tasks。HICG-T1只建立public grammar與immutable
query graph；T2加入candidate evidence、primary-casting不可被alias隱藏的all-rank conflict preflight及四個
non-reference policies；T3才補historical calibration、五階段CLI與完整artifact validators。前三步是唯一可修改
V3 source的區間，而且都禁止執行retrieval。

HICG-T4是正式分支gate。它先通過targeted static checks與related regressions，再用既有223／22／24 rows執行
0-retrieval calibration。若無survivor，T5–T7必須標為blocked，保存null calibration後直接進T8完成失敗證據、
QA與GitHub交付；若通過，source/protocol從此凍結，T5才可建立16+16 pack、T6 exactly-once收集32 rows、T7從
frozen bytes評分。這次把T8設為兩個分支都必走，避免技術實驗失敗時文件交付變成規格外工作。

每項task都有變更檔案、需求回指、owner與可測量acceptance。T8也保留owner要求的Project Log內容標準與
Product-Variant-Resolver-only GitHub邊界。Task list先等待owner確認，在確認前沒有開始HICG-T1或建立artifact。

Owner以「繼續幫我下一步」確認task list後，HICG-T1已完成。新增獨立的
`human_knowledge_identity_claim_graph_development.py`與focused test；新模組只接受公開
`HumanKnowledgeDocument`，不讀evaluation pack、private projection或runtime資料。它先保留完整normalized/raw
token provenance，再從公開casting與approved identity forms建立candidate-independent grammar；目前142 documents
可穩定建立240 forms與475個identity atoms。

舊HIE先用noise policy刪字，再取一段linear envelope，導致年份、context與多組數字容易混在同一比較。本次改成
immutable graph：每個atom有identity anchor/model、numeric frame、context或unresolved角色；leading year、
standalone model、alphanumeric與compact model各有local owner、digit runs、edges和canonical JSON checksum。
`20 Ram 1500 Rebel`因此把`20`／`2020`當同一year frame，但仍把`1500`保存在獨立model slot；候選比較之後
只能回答這張graph，不能重寫它。

正例保護沒有使用vehicle exception。完整corpus先決定compact segmentation與唯一性：`smallbloc`可拆為context
`small`加identity `bloc`；`de`／`deora`、`su`／`super`必須有另一個exact identity atom且corpus expansion唯一；
alphabetic typo只允許Damerau-Levenshtein edit 1。年份suffix、`o/0`、重複digit復原與year uncertainty `x`也都
保存rule name與原始form。若prefix在corpus中不唯一，它維持unresolved而不假裝等價。

T1新增20項focused tests，全數通過；包含實際142-document public corpus整合、checksum重現、context precedence、
compact digits、五組縮寫／typo、四組numeric equivalence、ambiguous prefix、unanchored query及`R33`守恆。
加上既有identity／anchor／HIC／HIE回歸共165項全部通過，只有既有Starlette／AnyIO deprecation warning。
Targeted Ruff format/check、Mypy `--follow-imports=skip`與compileall也通過。

本步沒有實作candidate decision或policy，沒有建立CLI、calibration、protocol、pack、raw或selection，也沒有
retrieval及API／Dual RAG／PostgreSQL／canonical／color變更。下一步HICG-T2才會比較primary casting與aliases、
加入all-rank hard-conflict preflight與四個non-reference policies。

Owner接著要求繼續下一步，HICG-T2現已完成。這一步把T1建立的query graph真正拿來逐一檢查候選：每個
candidate都會保存primary casting、approved aliases、被選中的正向identity form、每個form與query claims的
alignment、local numeric/alphanumeric frame比較、未配對claims、residual、completion、hard-conflict、source
rank與最終reason codes。同一批候選會依原始rank順序輸出，policy只能判斷admit或abstain，不能重新排序。

這次解決的核心問題是舊HIE decision branch先看rank。rank 2–5曾直接進入`coverage >= 0.75`，所以query明確
寫`R32`或`R33`時，secondary `BNR34`仍可能被放行。本次把hard-conflict preflight移到所有rank policy之前，
rank 1與rank 4都會先得到`hard_numeric_model_conflict`並abstain；coverage只有在結構規則通過後才有資格執行。
這不是針對Nissan寫例外，而是比較相同local frame內守恆的數字／英數model claim，所以同一規則可套用到
其他casting。

代碼中特別分開「primary casting safety evidence」與「best approved form positive alignment」。Alias可用來
證明縮寫、spacing或公開別名與query相容，但若primary casting本身帶有衝突數字，選到一個省略數字的alias
也不能遮蔽衝突。做這個決定是因為alias本來是recall工具，不應變成繞過safety gate的方式。正向等價仍只
允許exact、leading-year suffix、`o/0` OCR、repeated-digit restoration與leading-year uncertainty `x`；任意不等
數字不會因字面相近而通過。Form tie使用結構品質優先、最後以identity lexical order固定結果，避免執行順序
改變判斷。

Policy選型不是再找一個scalar threshold，而是固定一個reference與四種由寬到嚴的categorical policies：
`claim-conflict-veto`只守hard conflict，`claim-bilateral`再限制雙向residual，
`claim-query-conservation`要求query claim不被遺漏，`claim-decision-list`只接受完整或明確bounded且無residual的
form。`reference-anchor`保留舊rank/coverage行為作比較，但不能成為survivor。這種設計的理由是每個差異都能
對應到可閱讀的結構條件，後續historical calibration若失敗，可以知道是recall、query conservation或residual
哪一個gate造成，而不是只能看到一個分數不足。

HICG-T2新增後focused suite為34/34 PASS，含primary alias non-bypass、rank1/rank4 `R33`對`BNR34`、年份/OCR/
重複數字/uncertainty正例、abbreviation evidence、policy差異、secondary gate、source order及fail-closed evidence
validation。包含API、anchor、HIC、HIE在內的related suite共179項全部通過；targeted Ruff format/check、Mypy
`--follow-imports=skip`與compile也通過。唯一訊息是既有Starlette／AnyIO deprecation warning，與本次邏輯無關。

本步仍未建立CLI、historical calibration、protocol、pack、raw或selection，retrieval calls維持0，也沒有改動
API、Dual RAG、PostgreSQL、canonical identity、color或release behavior。下一步HICG-T3會實作唯讀historical
loaders、exact calibration scoring、phase-gated CLI與artifact lifecycle validators；正式執行historical branch
gate則仍留在HICG-T4。

Owner要求繼續後，HICG-T3已完成，但刻意沒有執行正式historical calibration。本步新增的是實驗執行機制，
不是調整T2 policy：程式現在能唯讀載入既有223筆public rows、22筆anchor-confidence v4 rows與24筆HIC-v1
rows，對五個policy離線重算每個candidate的graph/evidence/decision，再逐項產生HICG-R11要求的14個exact gates。
其中包含168/168既有正例、4/4 merge、24/24 prior required、10/10 v4正例、0/12 v4負例、12/12 HIC正例、
0/12 HIC負例、兩個R32/R33 secondary BNR34 veto，以及retrieval/graph/alignment/decision error皆為0。

這解決的問題是「演算法寫完後，如何確保實驗不會跳步、改資料或看到holdout結果後再調規則」。正式graph
建立前，loader必須先驗證五個凍結HIC/HIE hashes，再計算所有corpus與public evidence inputs hashes；後續
calibration、protocol、pack、raw與selection manifests都綁定這些bytes和目前V3 source。若舊證據被修改、筆數
不再是223/22/24，或source在freeze後改動，validator會fail closed而不是自動覆寫。

`pyproject.toml`新增已安裝的`pvr-develop-human-knowledge-identity-claim-graph`入口，且只提供五個互斥phase：
`--freeze-protocol`、`--freeze-pack`、`--collect`、`--score`與`--check`。選擇分階段CLI而不是一鍵跑到底，是因為
historical FAIL時依法只能保存deterministic null calibration；只有non-reference survivor存在，才能凍結source/
protocol。Pack仍需等post-freeze negative declarations，collect只能在32題pack完整後exactly once執行，score
只能讀已凍結raw bytes。這使每一階段都有明確的授權來源和停止點。

Artifact lifecycle實作採「create once或byte-identical unchanged」。既有directory若缺檔、多檔、hash stale或
內容不同，就報錯而不覆寫。FAIL branch只准留下historical calibration JSON、manifest與Markdown，不能出現
protocol/pack/raw/selection。PASS branch的pack builder則先驗證16 positive + 16 negative、四類各4筆、positive
使用16個不同documents與16個不同families、不得重用v4/HIC positive資料、negative identity必須不在corpus且
不得重用舊negative query。真實公開資料的唯讀availability preflight確認目前有足夠候選可滿足四類各4筆，
但沒有把它materialize成pack。

Raw schema只允許query、原始ranked candidates、retrieval work與errors；`expected`、case label、policy decision、
gates和winner在任何深度都會被拒絕。Collector若看到既有且驗證通過的raw，直接回`unchanged`且不呼叫retriever；
error rows會原樣保存而不retry。Scorer只有在raw已凍結後才join pack labels，並依negative admitted較少、positive
abstained較少、non-exact equivalence較少、最後least-restrictive policy的固定順序選winner。

測試採synthetic/temporary evidence驗證正式流程，因此沒有提前看實際policy結果。Focused suite現為49/49 PASS，
新增涵蓋五個immutable hashes、exact denominators與14 gates、離線policy application、FAIL/PASS protocol分支、
phase order、四類16筆negative schema、四類positive graph proof、raw label-blind、repeat collection與winner ordering。
包含API、anchor、HIC、HIE在內的related suite為194/194 PASS；targeted Ruff、Mypy與compile通過。CLI以本機package
安裝後可直接顯示五階段help；現有Starlette／AnyIO deprecation warning仍是唯一警告。

本步沒有建立V3 calibration、protocol、pack、raw或selection，retrieval calls維持0，也沒有改API、Dual RAG、
PostgreSQL、canonical、release或color行為。下一步HICG-T4會先做pre-freeze QA，之後才第一次正式執行
223/22/24 historical branch gate；結果若FAIL就保存`winner:null`並停止，若PASS才凍結source與protocol。

Owner再次要求繼續後，HICG-T4先重新執行pre-freeze QA，而不是直接看calibration結果。49項focused tests與
總計194項API/anchor/HIC/HIE相關回歸全部通過；targeted Ruff format/check、Mypy、compile與`git diff --check`
也通過。五個固定HIC/HIE hashes仍完全一致，V3 source在正式gate前固定為
`998f5af0983517d5ead54cf5fddaf46a57056245f92ac6d0c00c3279260ab173`，且V3 artifact directories當時不存在。

隨後第一次正式執行`--freeze-protocol`。它只重算既有223/22/24 public rows，retrieval calls為0，結果是
`historical_calibration_fail`、`winner: null`、0個non-reference survivors。因此分支依法只建立三個檔案：
historical calibration JSON、manifest與Markdown；沒有建立protocol、16+16 pack、raw或selection。第二次執行
同一命令回`calibration_failed_unchanged`，獨立`--check`回`valid`，證明結果byte-identical且可重算。

量測結果顯示一個清楚的recall/safety分界。Reference保留168/168既有正例、10/10 v4正例、12/12 HIC正例，
但v4負例仍有11/12 nonempty、HIC負例10/12 nonempty，兩個已知secondary BNR34 conflicts都未擋下。
`claim-conflict-veto`稍微犧牲recall至166/168與9/10，卻仍留下相同11與10個負例，而且兩個secondary conflicts
也沒有成功veto。這表示單靠目前的primary local-frame hard conflict仍不足以覆蓋公開row中的BNR34表示方式。

三個較嚴格policy則達到安全面：`claim-bilateral`、`claim-query-conservation`與`claim-decision-list`全部把v4與
HIC negative nonempty降至0/12，且兩個R32/R33 secondary conflicts都abstain；graph/alignment/decision errors
也全部為0。但它們的正例保存分別只有既有134/168、129/168、131/168，v4為4/10、3/10、4/10，HIC為
8/12、8/12、8/12；既有24個required targets也只剩19、8、3。它們雖安全，recall損失遠超exact gate，不能
被選為survivor。

這次沒有採取「挑最接近的policy」或看到結果後調threshold，因為requirements要求所有gate同時通過；放寬
嚴格policy會重新引入negative risk，放行loose policy則明知仍不安全。選擇保存null result能在花費32次新
holdout retrieval前停止，也讓履歷專案展示完整的實驗治理：技術實作本身可重現，不代表產品policy合格。

三個artifacts的SHA-256分別為JSON
`d2d94334d311c84e17c98b2f7d38876674ecf9def1c0dda6c889fbc822a7b1c2`、manifest
`9666ff2b5c63677fbc6f74daf9f4490e191c9a209151c798e44e75cccb2cac5f`及Markdown
`16f5b425c6c3e4f7947f868112663a1e024c0270484ebea34fcfe7f583b460a5`。HICG-T5–T7現在依法blocked；沒有
private evaluation或API/Dual RAG/PostgreSQL/canonical/release/color變更。下一步直接進HICG-T8，補齊FAIL
branch review、技術evidence、AI-eval、README與Product-Variant-Resolver-only GitHub交付。新增兩項量測artifact
regressions鎖定null branch、各policy counts、source/artifact hashes與禁止downstream artifacts；最終focused為
51/51、related為196/196 PASS。

## 2026-09-22 — HIE-v2 repository closure：發布失敗證據，不假裝完成holdout

### 新執行了什麼、解決什麼問題

HIE-T3已因historical calibration沒有任何survivor而停止，HIE-T4–T7的successful-holdout branch不能再執行。
本步改走獨立repository closure：新增QA review、技術evidence、AI-eval rubric與README摘要，讓GitHub上的
讀者能分辨「實作可以重現」與「policy不能promotion」。這解決失敗結果只存在10MB JSON與Project Log、
難以被面試官或下一位開發者快速審查的問題。

Review逐項映射HIE-R1–R14，將結果拆成implementation PASS、historical eligibility FAIL、new holdout NOT RUN
與runtime blocked。Evidence固定source與三個calibration artifact hashes，列出五個policy的223／22／24
精確結果；AI-eval則把data disclosure、leakage、retrieval integrity、auditability、positive preservation、
absent-identity safety與release safety分開評分。README只呈現必要摘要，沒有把null result包裝成新功能。

### 代碼／文件修改位置與選型原因

Product code與已凍結HIE source完全沒有改動。本步只新增`review.md`、`docs/evidence/`與`ai-evals/`文件，
更新README、spec checkpoint、decision與roadmap。採用「publish negative result」而不是刪除失敗實驗，
因為pre-holdout gate成功節省32次沒有價值的新retrieval，本身就是可展示的ML／RAG治理能力。

HIE-T7仍沒有被勾成successful branch completion，因為它的原始前提是protocol PASS後完成pack、raw與
selection；目前這些artifact依法不存在。Tasks另加一個明確的repository closure項目，避免Git commit被
誤讀成HIE product gate通過。

### 完整QA結果與誠實保留的技術債

完整repository suite為813/813 PASS，只有既有Starlette／AnyIO deprecation warning；HIE focused 25項、
related 77項也全綠。Targeted HIE Ruff format/check、targeted MyPy、compileall、兩次CLI `--check`、artifact
hashes與`git diff --check`通過。

Repo-wide static checks沒有被誤報為全綠。全repo Ruff指出83個歷史檔案會被重新格式化；全repo MyPy指出
51個既有／跨模組問題，其中包含HIE source在完整dependency graph下的1個`payload["text"]`型別推論。
因source hash已由FAIL manifest綁定，本closure不在看到結果後修改source或重寫calibration。該型別債與
全repo formatting應另開behavior-neutral maintenance task，不能混入本次實驗證據。

## 2026-09-22 — HICG-T8：用可審查的失敗證據完成v3封版

### 新執行了什麼、解決什麼問題

HICG-T4已得到可重現但不合格的`historical_calibration_fail`。本步沒有繞過gate繼續做holdout，而是完成
historical-FAIL專用的repository closure：新增HICG-R1–R16 QA review、immutable evidence摘要、AI/RAG
evaluation rubric，並更新README、requirements/design/tasks checkpoint、roadmap與decision record。這解決
原始10MB等級calibration JSON雖完整、但一般reviewer難以快速分辨「軟體正確」與「policy不安全」的問題。

文件把結論拆成四層：implementation integrity PASS、historical eligibility FAIL、holdout NOT RUN、runtime
NOT AUTHORIZED。這個拆分很重要，因為864項測試全綠只能證明程式依規格重算，不能證明任何policy達到產品
品質。HICG-T5–T7仍保持未勾選和blocked，避免GitHub交付被誤解為32題holdout或上線已完成。

### 修改了哪些部分、為何這樣決定

產品判定程式與三個正式calibration artifacts完全沒有修改；V3 source SHA-256維持
`998f5af0983517d5ead54cf5fddaf46a57056245f92ac6d0c00c3279260ab173`。新增的review逐項映射R1–R16，
evidence固定source與artifact hashes並用一張表呈現五個policy，AI-eval則分別評估grounding、public/private
separation、leakage、integrity、explainability、positive preservation、negative safety與release boundary。

選擇發布null result，而不是挑「最接近」的policy，是因為量測呈現不可忽略的recall/safety trade-off。
`reference-anchor`與`claim-conflict-veto`保留較多正例，但仍留下11/12 v4及10/12 HIC absent-identity輸出；
三個嚴格policy把兩組負例降至0/12，也擋下2/2 BNR34 conflicts，卻只保留129–134/168既有正例、3–4/10
v4正例與8/12 HIC正例。任何best-effort選擇都會違反事前固定的exact gates，且使履歷專案產生錯誤能力宣稱。

方法上沿用版本化offline experiment與hash-bound evidence，而沒有導入cross-encoder或新dependency。這保留
每個atom、frame、equivalence、conflict和decision可追溯的優勢，也誠實接受規則系統目前無法同時取得recall
與safety。若要繼續研究，必須建立新的spec/source/evidence namespace；不能看到V3結果後直接改規則重跑。

### QA、失敗邊界與下一個gate

HICG focused 51/51、相關API/anchor/HIC/HIE regressions 196/196，以及完整repository 864/864 tests全部
PASS；唯一warning是既有Starlette／AnyIO deprecation。Targeted Ruff format/check、target-local strict MyPy
（跳過imports）、compileall、installed CLI、重複freeze/check、SHA-256與artifact shape、`git diff --check`
均通過。完整dependency graph仍顯示6個既有模組的18項跨模組型別問題，而全repo MyPy是18個檔案51項
既有技術債；本次沒有修改frozen source或順手重構無關模組。Exactly三個calibration files存在，
protocol/pack/raw/selection不存在，retrieval維持0。

因此本次HICG-v3研究已封版，但功能並未進入Dual RAG runtime。更大的產品roadmap下一個必要gate仍是：若
提出新的identity algorithm，先建立新版public experiment並通過historical與family-disjoint holdout；只有再
通過獨立private shadow evaluation後，才可另規劃opt-in API/runtime整合。Color、wheel、tampo、edition與
packaging辨識也仍屬後續variant-level工作，不能由本次casting identity結果推論。

## 2026-09-22 — V4 requirements草案：用最小identity certificate處理v3的recall／safety斷層

### 新執行了什麼、解決什麼問題

HICG-v3封版後，下一步沒有合格winner可直接進shadow evaluation或Dual RAG runtime。為避免看到FAIL就原地
調threshold，本輪先唯讀分析已凍結的public calibration，再建立全新v4 requirements草案。分析確認兩類相反
問題：寬鬆policy只憑`Honda`、`BMW`、`Bugatti`等共通字就誤收不存在於corpus的車型；嚴格policy則因候選
完整名稱比query多字，或query含未分類wrapper，而誤拒`55 Chevy`、`fishdchipd`、`kick kat`等有效簡寫／雜訊。

新草案把問題改寫成「query是否完整滿足某一個knowledge identity的最小唯一證據」，而不是「query與candidate
整串文字是否雙向完整」。每個identity certificate由完整public corpus預先計算，必須是能排除其他knowledge
IDs的最小atom／local-frame組合；query先獨立產生support set，只有set恰好包含一個ID，而且retrieved candidate
確實屬於該ID、primary frame也無衝突，才可能admit。

### 修改位置、選型原因與沒有執行的內容

新增`specs/human-knowledge-identity-certificate-development/requirements.md`，定義16項EARS-style requirements，
涵蓋public-only boundary、prior evidence immutability、certificate minimality/provenance、candidate-independent
support set、bounded equivalence、ambiguity fail-closed、exact historical gates、conditional holdout、完整解釋欄位
與release boundary。Roadmap新增等待確認項目，decision D90維持PROPOSED。

選擇certificate set而不是另一個scalar threshold，是因為v3失敗不是單一分數切點，而是「共通token不代表
同一identity」和「合法partial name不必等於完整candidate name」兩個結構問題。最小唯一證據可以直接列出
哪些claim排除了哪些競爭identity，比opaque reranker更容易審查；代價是142-document corpus可能產生過度特化
或不穩定certificate，所以新版本仍必須先用既有223／22／24 rows做zero-retrieval exact gate。

本步只有需求草案。沒有v4 design、tasks、source、artifact或retrieval，也沒有讀private five-family evidence、
修改HICG-v3、調整API／Dual RAG／PostgreSQL／canonical或color行為。下一個gate是owner先確認requirements；
確認後才撰寫design，不能把本次「繼續」擴張成整個新演算法已獲准實作。

## 2026-09-23 — V4 design草案：確認最後一次admission嘗試並修正document／identity邊界

### 新執行了什麼、解決什麼問題

Owner確認先完成v4，再回到原始Pointwise Cross-Encoder／Listwise Reranker主線；同時要求最終成果必須可作
履歷展示。本輪因此把v4 requirements標記為confirmed，並建立完整design草案，但仍依Lite gate等待design
確認後才寫tasks或程式。V4也被明確設為最後一個identity-admission版本：不論得到winner或null，都先完成
branch-aware closure，再切回reranking，不自動建立v5。

設計前唯讀檢查發現原requirements的「每個knowledge ID一張唯一certificate」在資料上不可行。現有142個
documents中，100個provisional variants只對應97個casting IDs，42個review families對應42個family IDs，
所以實際是139個可由casting文字辨識的authority keys。`83 Chevy Silverado`有三個documents，`Toyota Supra`
有兩個；若強迫certificate拆開這些文件，就只能偷用series、color或variant label，違反identity-field boundary。

### 修改了哪些部分、為何採certificate authority

Requirements已修正為`casting:<casting_id>`與`review_family:<review_family_id>`兩種authority keys。Certificate
只從primary casting建立；human label與review-family aliases只能作為query到既有casting claims的bounded
bridge，不能創造新的唯一證據。Singleton support set可以保留同casting的多個source documents，但必須輸出
`casting_authority_only`與`variant_not_resolved`，不能假裝知道具體release。

新增design定義四層資料模型：IdentityAuthority、CertificateClaim、IdentityCertificate與AliasBridge。每個
primary casting目前最多8個normalized tokens；設計以12 claims為fail-closed上限，依subset size完整列舉並
證明每張certificate的最小性。這比score threshold成本高，但能直接展示每個claim排除了哪些競爭identity，
也避免`Honda`一個共通字成為`Honda Civic EG`的certificate；單一alphabetic claim只有在完整casting本來就
只有一個claim時才可成立。

Query先對完整frozen inventory建立authority support set，再看Top-5 candidates。未匹配的context可保留，
任何其他alphabetic/numeric residual都會移除該authority；這讓`Honda Accord`不能因`Honda`誤接Civic，卻
允許完整滿足certificate的`55 Chevy`不必補齊candidate完整尾詞。空集合與多authority集合一律abstain；
singleton仍須通過primary numeric conflict preflight，而且不再用secondary coverage shortcut。

### 方法選型、驗證順序與下一個gate

V4凍結`certificate-exact`、`certificate-structural`與`certificate-bounded`三個categorical profiles，而不是
再調scalar threshold。它先以既有223／22／24 public rows做0 retrieval historical gate；FAIL只保存null
calibration並封版，PASS才凍結protocol並建立family-disjoint 16+16 holdout。Holdout若執行，32個Top-5 rows
仍是exactly once、label-blind raw first。即使public winner通過，也只取得另立private shadow spec的資格，
不能直接改runtime。

本步沒有新增source、tests、CLI、artifact或retrieval，也沒有讀private evidence或修改API／Dual RAG／
PostgreSQL／canonical／color行為。下一個gate是owner確認design；確認後才建立原子化tasks。V4 closure完成後，
roadmap下一個固定里程碑是No Reranker／RRF、Neural Pointwise與Listwise的同candidate-pool比較。

### 交付邊界與下一步

本步準備把目前所有Product Variant Resolver變更commit並push到既有GitHub `main`。Staging會使用明確
repo-relative paths，不包含父資料夾的`AGENTS.md`、`.codex`或其他workspace設定。推送後GitHub保存的是
一個可重現的null experiment：winner仍為null、0個新retrieval、0個runtime／database／canonical／color
changes。若繼續演算法研究，下一步必須是新的v3 requirements；若先處理工程品質，則應另開static-debt
maintenance，兩者都不能修改這份v2 failure evidence。

## 2026-09-21 — HIE v2需求啟動：從candidate-specific span改為query-global identity envelope

### 新執行了什麼、解決什麼問題

HIC v1已完成且合法得到`winner: null`，因此本步沒有把失敗結果直接改成runtime規則，而是開始
一個新的Lite規格階段。先對公開selection evidence做唯讀分析，確認單一bilateral-residual
threshold之所以無法通過，不只是門檻沒選好，而是candidate-specific span可以對不同候選選擇
不同的query子片段，並把關鍵數字排除在比較之外。

具體而言，正確的`88 Jeep Wagoneer`對`1988 Jeep Wagoneer`會把`88`與`1988`當成雙側殘差，
在0.50門檻下被錯殺；反過來，`Nissan Skyline GT-R R33`對`BNR34`候選又可以透過compact
alignment選到沒包含`33`的span，讓candidate的`34`只留在單邊，不形成bilateral contradiction。
這兩個失敗方向同時說明下一版必須修正證據結構，不能只微調0.50、0.75或1.00。

### 新requirements改了哪個方向、為何這樣選

新建`human-knowledge-identity-envelope-development/requirements.md`，核心是每個query先建立一個所有
candidates共用的identity envelope，而不是讓每個candidate自己選最有利的span。與model frame相鄰的
digit run必須被保留，compact/fuzzy matching不得吞掉或繞過它；同frame數字不同要形成明確衝突。

同時需求允許一個可稽核的兩位／四位前置年份簡寫規則，但只能使用identity文字內的token結構，
不能讀release year欄位，也不能寫`Jeep`專用exception。政策選擇也改為預先宣告的結構狀態組合，
不允許又用另一個單一scalar threshold當主角。這保留v1的可解釋性，但直接處理已量到的結構缺口。

### 新資料如何避免重用與過擬合

唯讀可行性盤點顯示，排除v4與HIC-v1已用source cases後，仍有144筆公開正確rank-1案例。
如果連過去pack出現過的document families都排除，仍有93筆、24個全新documents；四種challenge styles
各有22至24筆。因此新需求固定32題family-disjoint holdout：16筆positives來自16個未曾使用的
documents，另加16筆全新corpus-absent identities。

實驗仍要在新retrieval前凍結envelope rules、policy grid、selection rules、hashes、gates與winner order；
32題各只retrieve一次，raw先label-blind儲存。新policy必須同時重算既有223、v4 22、HIC-v1 24
與新32題，任一正例掉落或任一負例非空都不合格。目前只完成requirements draft；在owner確認前不會
寫design/tasks、建新pack、執行retrieval或修改runtime。

Owner以「繼續下一步」確認14項requirements後，已新增`design.md`。設計最重要的流程變更是先在
既有公開223／v4 22／HIC-v1 24資料上做historical calibration；至少一個非reference policy必須先
通過所有歷史gates，否則直接停止，不浪費32次新retrieval。若calibration通過，先凍結source、
protocol與holdout-selection rules，之後才物化32題pack。這與v1的pack-first不同，是為了讓新案例變得可見
之後，程式碼與policy已經不能改。

Envelope建構只執行一次。系統從142-document casting／alias建立public anchor index，以全corpus forms
而不是某個Top-5 candidate選定query anchor。Envelope從anchor開始，但會保留緊貼在前的兩位或四位
數字；邊界內的unknown model atoms也不能因候選不支援就被刪掉。每個candidate都得到同一個
envelope checksum，從資料結構上阻止「各自挑最有利span」。

數字不再只是殎dual分數，而是`none/equal/year_suffix_equivalent/conflict/query_only/candidate_only`
六種狀態。只有同anchor前的兩位與`19xx`／`20xx`四位數字、尾兩位一致時才是年份簡寫；
`R33`／`R34`、`M2`／`M4`不得使用這個規則。Compact/fuzzy alignment只能對齊alphabetic部分，
不能吞掉不同digit run。

固定policy family為一個reference加四個結構策略：`envelope-numeric`、`envelope-bilateral`、
`envelope-safe-form`與`envelope-decision-list`。它們使用anchor relation、numeric relation、form completion、
alignment strength、model residual與compact digit guard等離散狀態，而不是另外找一個最好看的殘差threshold。
Rank2至5繼續沿用coverage 0.75，所有source order不變。

設計仍可能失敗：某些車型的第一個identity atom不是穩定maker/model anchor，導致global envelope包進
context或漏掉重排identity。因此multiple-anchor、unanchored、leading context、trailing noise與數字縮寫都列為
強制adversarial tests。目前design等待owner確認；尚未寫tasks、code，也沒有新建protocol/pack或執行retrieval。

Owner再次指示「繼續下一步」後，design已確認，並新增七項依序tasks。HIE-T1先只實作public anchor
index、query-global envelope、numeric-frame conservation與year shorthand；HIE-T2才完成policies、historical calibration、
pack/collection/scoring validators與五階段CLI。這兩步都不建新holdout artifact，是最後可修改source的區間。

HIE-T3是分支gate，不是「測試有跑完就一定前進」。新policies必須先在既有公開223／v4 22／
HIC-v1 24上至少有一個完全通過；若全失敗，必須保存calibration failure、維持0新retrieval，並將
T4至T7標成blocked。只有PASS分支才能凍結source/protocol，並從那一刻開始禁止修改development module。

HIE-T4故意把16筆negative declarations放在protocol freeze之後的獨立JSON，而不是先寫進source。
Protocol只先凍結schema、路徑、challenge數量與validators；T4才建立實際declarations，pack manifest綁定其精確
hash。如此看到新負例後不能再改policy code。其後T5只收集一次32-query raw，T6才加labels評分，
T7進行完整QA、文件與GitHub交付。

Owner接著以「幫我繼續完成」確認task list並授權依序實作。HIE-T1已完成，但仍刻意沒有建立
negative declarations、protocol、pack、raw或selection report，也沒有執行任何HIE retrieval。

### HIE-T1新執行了什麼、解決什麼問題

新增`human_knowledge_identity_envelope_development.py`，先完成所有後續policy共用的最小證據層。
`IdentityEnvelopeIndex`只從已提交142-document public corpus的casting與approved aliases建立anchor forms；
每個query只選一次corpus-wide anchor並產生immutable `QueryEnvelope`。這解決HIC v1讓不同candidate各自
選query span、因而可能避開關鍵model digits的結構問題。Envelope保存normalized core、原子邊界、
字元offset、anchor位置與SHA-256 checksum；後續候選比較只接收同一物件，無法反向改變query範圍。

### 代碼修改了哪裡、為何採用這個方法

本步重用HIC v1已測試過的`atomize`、`IdentityEvidenceIndex`與ordered alignment，而沒有修改HIC source。
這個選擇保留既有token規則和public IDF權重，避免新版本在沒有證據時偷偷發明第二套normalization。
Envelope從最佳anchor開始，只有當anchor緊鄰一個純兩位或四位數字時才向前包含該數字；anchor後方的
unknown model atoms則全部保留，不能因某個candidate沒有該字而刪除。

新增的`numeric_evidence`把結果分類為`none`、`equal`、`year_suffix_equivalent`、`query_only`、
`candidate_only`或`conflict`，並抽出每個alphanumeric model frame的alphabetic skeleton與digit runs。
唯一允許的簡寫是同anchor、純leading number、`19`／`20`世紀前綴且末兩位一致，例如`88`對`1988`；
`R33`／`R34`、`R33`／`BNR34`及`M2`／`M4`都會保留原token並成為conflict。這是一般結構規則，
沒有讀release year、series、color、case ID或private labels，也沒有vehicle-specific exception。

### 驗證結果、邊界與下一步

新增focused tests覆蓋public-only anchor index、leading context移除、leading year保留、candidate-independent
envelope、multiple anchors、unanchored query、unknown model atom、年份簡寫及三組model-number conflicts。
Ruff format/check、MyPy與compile全部通過；11項新focused tests加上52項既有HIC／anchor相關回歸測試，
合計63項全數通過。HIC v1 source SHA-256仍為
`167c03a5e19fae47eb867b8101c26f1c5bf49ca2c80fb2eb9a4e8bfa0660825f`，證明本步沒有改寫凍結實驗。

HIE-T1的作用只是建立證據primitive，不表示新policy已有效。下一步HIE-T2才會實作五個categorical
policies、重算既有223／v4 22／HIC-v1 24 rows的historical calibration、phase-gated CLI與完整validators。
在HIE-T3真正跑完calibration以前，仍是0個新holdout artifacts、0次新retrieval、0個runtime changes。

### HIE-T2新執行了什麼、解決什麼問題

HIE-T2把T1的query envelope primitive接成一套完整但尚未凍結的development engine。新增五個固定
rank-1 policies、candidate-level categorical evidence、既有269 rows的historical rescoring、protocol／
pack／raw／selection artifact builders、phase-order與hash validators，以及
`pvr-develop-human-knowledge-identity-envelope`五階段CLI。這解決的是「規則可以被單元測試」到
「整個實驗可以按照freeze → pack → collect → score → check順序重現」之間的工程缺口。

所有rank 2–5仍只使用既有identity coverage `>= 0.75`並維持source order。Rank 1才依序比較
numeric conflict、compact digit guard、anchor relation、form completion、alignment strength與雙側model
residual。每個candidate evaluation保存完全相同的query envelope checksum、candidate identity、ordered
alignment、未配對atoms、numeric frames、reason codes與admit／abstain，讓後續結果可以逐候選重算。

### 代碼修改、技術選型與一次語義修正

主要程式仍集中在`human_knowledge_identity_envelope_development.py`，沒有讓runtime module import它。
Historical calibration直接讀取並驗證既有reranker selection、anchor-confidence v4與HIC-v1 frozen raw，
再用新policy離線重算；沒有重新建立retriever或執行network／model call。Protocol builder只有在至少一個
non-reference policy通過時才允許寫檔；pack builder則強制protocol先存在，並要求16個positive來自16個
過去未使用documents，以及16個post-freeze declarations符合四類各四題與corpus-absence規則。

第一次唯讀calibration暴露一個實作語義錯誤：`compact_digit_guard`被寫成任何`query_only`或
`candidate_only`數字都fail，這會把「query沒寫candidate casting中的前置年份」錯當成compact吞數字。
設計真正要求的是不同的conserved digit runs不能被compact/fuzzy隱藏，因此修正為只有明確`conflict`
才fail；`query_only`／`candidate_only`仍保留為可稽核state，由較嚴格policy的其他規則判斷。這不是新增
threshold或vehicle exception，而是讓程式回到已確認的categorical contract。

### Historical calibration量測、代表的問題與下一個gate

修正後完整唯讀calibration精確重算223＋22＋24 rows、執行0次retrieval且0個envelope errors。結果仍是
`historical_calibration_fail`：reference保留168/168 existing、10/10 v4與12/12 HIC positives，但v4與
HIC negatives仍分別有11與10題nonempty。`envelope-numeric`降到7／7 negatives，但existing positives只剩
160/168、v4 9/10、HIC 11/12；`envelope-bilateral`把兩組negative各降到1，卻只保留146/168、9/10、
10/12 positives。更嚴格的safe-form與decision-list同樣各留1個negative，正例損失更大。因此目前0個
non-reference survivor，沒有任何policy可凍結。

HIE-T2本身仍完成，因為engine、validators與fail-closed protocol gate都按規格運作；但這不授權修改
policy再試。下一步HIE-T3要把這個歷史FAIL保存成public calibration evidence，確認protocol／pack／raw
都不存在，並正式把HIE-T4–T7標成blocked。只有新版本與新規格才能再改方法。

### 驗證結果與環境限制

23項HIE focused tests與52項既有HIC／anchor相關回歸測試合計75項全綠；Ruff format/check、MyPy、
compile與`git diff --check`通過，HIC-v1 source hash維持
`167c03a5e19fae47eb867b8101c26f1c5bf49ca2c80fb2eb9a4e8bfa0660825f`。正式console entry已寫入
`pyproject.toml`，本機命令的`--help`也驗證五個互斥phase。因既有`.venv`沒有pip/setuptools且sandbox
無網路，無法重新做editable build；使用同格式的gitignored local entry並以`PYTHONPATH=src`驗證。
這個環境限制不影響可提交的packaging definition，T7仍須在最終交付環境再次驗證安裝。

### HIE-T3正式執行：historical calibration FAIL並停止新holdout

HIE-T3先重跑pre-freeze QA，75項HIE／HIC／anchor相關測試、Ruff format/check、MyPy與compile全部通過，
確認失敗不是語法、型別或舊功能回歸造成。隨後執行installed CLI的`--freeze-protocol`。系統重算既有
223＋22＋24筆public rows，得到與T2唯讀驗證完全相同的0 survivors結果，因此沒有建立protocol，而是
回傳`calibration_failed_created`與`protocol_created: false`。

這個分支新增三個public evidence artifacts：完整machine-readable calibration JSON、面試／人工審查可讀的
Markdown摘要，以及綁定source／upstream hashes、denominators與zero-downstream-effects的manifest。第二次
執行同一命令回傳`calibration_failed_unchanged`；`--check`離線重算後回傳`valid`、
`historical_calibration_fail`與`winner: null`。這證明失敗證據是deterministic，而不是一次性console輸出。

### 錯誤在哪裡、為何不能繼續HIE-T4

本次不是crawler、資料庫、FastAPI或retriever故障，也不是出現計算error；所有五個policies的
`envelope_errors`都是0。真正失敗是安全與召回無法同時成立。最寬鬆reference完整保留positives，卻讓
v4 11/12與HIC 10/12 absent identities仍有結果。最接近安全的bilateral policy把兩組negative各降到1/12，
但existing、v4、HIC positives分別只剩146/168、9/10、10/12，違反「不能犧牲任何必要正例」的固定gate。

因此protocol freeze被拒絕。沒有protocol就不能在事後新增16個negative declarations或選16個positive
families，也不能執行32次Top-5 retrieval。這個順序正是為了避免看到新holdout後繼續修改policy。HIE-T4、
T5、T6與實驗內T7現已標記blocked；API、Dual RAG、PostgreSQL、canonical、release與color仍完全不變。

### Artifact完整性與後續技術決定

Calibration JSON、manifest與Markdown SHA-256分別為
`fbdc5171f3b1bfbe3f07b207acb56bd9608e2a3136bdff1acb9175e99f1557ce`、
`03eee815b2cb4110e158f2ff02bf51d8b582282c1f050358c3be117ee238eeb5`與
`7e0fbd7e1f92cf0d043949e0c0fdee69bd4d53f0a9f40fe1a41d466f6b5039be`。被綁定的HIE source hash是
`c91d8e253f1cd19cf59b626e794673defe2e28aea6c993cbce350d1698e83a5e`；HIC-v1 source仍維持原hash。
新增的2項artifact regression tests把HIE focused總數提高到25，與52項既有相關測試合計77項全綠；
CLI `--check`、三個artifact hashes與source hash也在最終驗證中保持不變。

下一個動作不能是調整本版policy或放寬gate。若要繼續技術研究，必須建立新的versioned requirements，
重新定義能保留合法縮寫／拼字變形又能處理最後兩個false positives的證據結構。若只是把目前失敗成果
推送GitHub，則應走獨立的repository closure/delivery步驟，不得假裝HIE-T7的conditional PASS branch已完成。

## 2026-09-21 — HIC規劃啟動：把下一個問題改成candidate-specific identity contradiction

### 新執行了什麼、解決什麼問題

Anchor-confidence v4已證明單一threshold無法把正確拼字變形與相似錯誤車款分開。本步先進入Lite規格
階段，建立`human-knowledge-identity-contradiction-development/requirements.md`，把下一個問題改寫成：
「query是否包含與某一candidate互相矛盾的casting identity證據」。例如`R32`對`R34`應被視為數字
model conflict，而不是因為大部分字元相似就通過。

公開資料可行性盤點顯示，排除v4已使用的10筆低coverage positives後，仍有156筆既有公開正確rank-1
案例可供新正例選擇。因此需求要求新pack使用12筆未被v4用過的正例、至少10個不同documents，並搭配
12筆全新的corpus-absent identities；不需要讀取private資料，也不需要把private failures改造成測試題。

### 為何先寫需求、尚未直接改程式

本輪會新增one-to-one alignment、unmatched identity-bearing tokens、numeric conflict與reason codes，技術
決定會直接影響哪些合法拼字應保留。若先寫code再定義gate，很容易看到結果後降低標準。因此依Lite
`spec-dev-loop`先固定11項可驗收requirements，包括24題先凍結、每題只retrieve一次、只允許casting／
approved aliases、禁止case-specific exceptions、完整舊／新recall與zero-negative gates，以及無winner時
fail closed。Requirements已由owner以「繼續下一步」確認；確認前沒有把design、tasks或實作視為已批准。

確認後已新增`design.md`。設計不再用候選整體similarity直接決定，而是先從query選出與casting／alias
最吻合的連續identity span，再做ordered one-to-one atom alignment。雙方無法對齊的identity atoms依公開
142-document corpus IDF加權，只有query與candidate兩側都留下證據時才形成bilateral contradiction；這可
避免單純seller文字或candidate可省略前綴造成誤殺。

數字型號另設優先規則：相同alphabetic model frame但digit run不同，例如`R32`／`R34`或`M4`／`M1`，
不能被高character similarity掩蓋；`o`／`0`與`i`、`l`／`1`只有在替換後完全一致時才記為OCR substitution。
固定grid包含baseline、numeric-only與五個bilateral residual門檻，rank2–5仍沿用coverage 0.75。Raw retrieval
會先獨立保存且不含expected labels，之後才score；如此可稽核「先觀察模型輸出、後讀答案」的順序。
Design已由owner以「請繼續執行」確認，尚未凍結pack／protocol或執行任何新retrieval。規格階段接著
新增`tasks.md`，把工作拆成六個依序gate：先建立未凍結pack constructor，再完成alignment／collection／
scoring與integrity engine；只有靜態與focused QA通過後才能凍結pack和protocol，接著才能一次性collect，
最後才score、做完整QA與文件／GitHub交付。

這個順序特別把「程式碼可修改」邊界放在freeze之前。Task 3綁定source hash後，後續不得再修改development
module；如果此時發現產品碼錯誤，必須保留v1證據並開新version，不能覆寫raw或偷偷重跑。Tasks目前等待
owner以「請幫我繼續執行」確認，G1*因此完成並記錄D79；HIC-T1開始，但仍不凍結artifact或執行retrieval。

HIC-T1正例採四種既有public challenge styles各3筆，總計12筆且分屬12個knowledge documents；這些
source case ID都未被v4的10筆anchor-positive使用。負例也固定四類各3筆：同manufacturer換model、同stem
數字衝突、compact／punctuation衝突、跨manufacturer descriptor overlap。初步exact normalized identity
盤點確認12個新名稱都不在142-document corpus；builder仍會在每次執行時重新驗證，而不信任這次口頭盤點。

HIC-T1現已實作完成。新增的development module目前只負責讀取committed public corpus、既有public pack、
公開v2 raw report與v4 pack，重新驗證正例確實是correct source-rank-1，再建立expected target；負例則逐筆
驗證完整normalized identity不存在於任何casting／approved alias，且identity與query都沒有重複v4。選擇
explicit source IDs而不是執行時任選前12筆，是為了讓案例順序、document分布與challenge balance可稽核；
builder仍會以upstream bytes驗證這些選擇，來源漂移時fail closed。

本步新增4項focused tests，覆蓋12+12分母與唯一ID、12個distinct positive documents、四種正／負challenge
各3筆、corpus absence、v4 exclusion、deterministic output、private-path isolation與零retrieval implementation。
Ruff、format、MyPy、compile與4/4 focused tests通過。沒有建立pack directory、沒有凍結source hash，也沒有
執行retrieval；下一步HIC-T2才會在freeze之前完成alignment、collection、scoring、CLI與integrity engine。

HIC-T2的第一輪focused alignment tests在freeze前發現原design tie-breaker會偏好residual較少的過短span：
`Honda Prelude`對`Honda Civic EG`可能只選`Honda`，使query residual錯誤歸零；`Tesla Roadster`也可能由
`08 Tesla Roadster`的compact similarity吞掉缺少的`08`。這是設計錯誤，不是資料結果，因此在任何pack／
protocol／raw artifact建立前回到design修正。新規則先最大化candidate identity被解釋的IDF比例，再比較
matched weight與query／candidate atom數差；compact fuzzy若digit runs不同也不得match，合法`o`／`0` OCR
完全替換仍保留。修正已同步到design，沒有使用任何private evidence。

HIC-T2現已完成完整但尚未凍結的engine。`atomize`先使用既有identity-core normalization，再把`R32`、
`MX-5`等拆成保留source token與offset的alphabetic／numeric atoms；ordered dynamic programming只允許
不交叉、不重用的exact、prefix、atomic fuzzy、compact與OCR alignment。IDF只由142份public documents
計算，unknown query atom使用最大權重；最終bilateral residual取query與candidate residual較小值，確保
單側多出的seller wording或可省略candidate prefix本身不會造成拒絕。

新增七組固定policies、rank2–5 coverage 0.75、label-blind raw schema、pack／protocol／raw／selection
manifests、byte-idempotent freeze helpers、exactly-once collection、existing 223＋v4 22＋new 24 rescore、
deterministic winner/null selector與五階段CLI。`--collect`只寫raw，`--score`只能讀既有raw；`--check`
只驗證並重算，不含retrieval。Scoring exception會形成明確failed gate，不會被當成abstention success。

本功能17項focused tests覆蓋pack、atom offsets、ordered one-to-one alignment、R32／R34 numeric conflict、
Fiat`5o0e` OCR保留、alias span、bilateral residual、secondary gate、七組protocol、24次collection且raw無
expected label、byte-idempotence、source order、reason codes、nonfinite tamper、CLI contract與12/12＋0/12
新gate。連同三個既有相關evaluation modules共51/51 tests通過；Ruff、format、MyPy、compile皆通過。
離線對既有223與v4 22 raw rows建立evidence時contradiction errors皆為0。仍未建立任何v1 data directory，
下一步HIC-T3會先做pre-freeze QA，再依序凍結pack與protocol；freeze之後development source不得再修改。

### HIC-T3：通過pre-freeze gate並凍結pack與protocol

本步先重跑所有會在凍結前影響設計判斷的驗證：Ruff format/check、MyPy、compile、17項
HIC focused tests、51項HIC與既有anchor/admission/reranker regression tests，以及完整787項
repository tests全數通過。唯一警告來自第三方Starlette TestClient使用已棄用的AnyIO alias，
與本次identity contradiction邏輯無關，也沒有失敗測試。

驗證通過後才依序執行`--freeze-pack`與`--freeze-protocol`。Pack固定12筆positive
preservation與12筆absent-identity contradiction，四種正例與四種負例challenge都是各3筆；
protocol固定7個policies，並綁定既有公開223題、v4 22題與新24題的分母。這個順序解決
「先看retrieval結果再改題目或門檻」的污染風險；兩個artifacts皆明確記錄
`status: frozen_before_retrieval`、`retrieval_executed: false`與`private_local_artifacts_read: false`。

為了證明凍結不是「每次重生一個差不多的檔案」，兩個freeze commands都立即重跑，回傳
`unchanged`且四個JSON/manifest的bytes與SHA-256完全不變。Pack與manifest hashes分別為
`e86bb87f5c37b951482a782af09742617bc1820fe4bca3faacf122beb0f8e08c`與
`fe4cab04f3e45142f3d5160e5405d94fe5cbddfd2c75b34493b6a5e507f6ae9f`；protocol與manifest為
`eeb30a56e0207dad41e7fa5a6889cef9a8377c05250f31508431e836946a6818`與
`e6c5c262525868b4917e8bf6efd0c0b37c797fa4c9d3e3ebfe23f88a0f45ad0e`。Development source hash在凍結
前後均為`167c03a5e19fae47eb867b8101c26f1c5bf49ca2c80fb2eb9a4e8bfa0660825f`，從現在到HIC-T6
都不得再修改這支source；若之後發現產品碼錯誤，必須保留v1並開新version。

本步沒有執行`--collect`，因此raw與report directories仍不存在，retrieval調用數仍為0。
下一步HIC-T4才是第一個不可逆的資料收集gate：對已凍結的24個queries各執行一次Top-5
retrieval，先儲存不含expected labels的raw bytes，之後才能在HIC-T5評分。

### HIC-T4：一次性收集24題label-blind raw retrieval

本步先重新檢查source、pack、protocol與兩個manifests的SHA-256，並重跑兩個freeze commands確認
仍為`unchanged`。在raw與report directories均不存在的前提下，才執行唯一一次
`--collect`；系統對凍結的24個queries各執行一次Top-5 retrieval，回報`created`與
`retrieval_calls: 24`。這解決了不同policy若各自重跑檢索，可能因輸入漂移而無法公平比較的問題；
HIC-T5的七個policies將共用這一份raw bytes。

Raw artifact共有24 rows與42 candidates：12筆positive-preservation與12筆absent-identity-contradiction
都完整，retrieval error為0。個別query可能只有0至5個candidates，這是Top-5的上限而不是強制
補齊；保留空結果比用低品質候選補滿更能真實反映retriever的行為。內建validator逐筆檢查
candidate的public corpus UUID、source rank、dense/sparse/character分數與query work；24筆全部通過。

Raw schema只含query、candidate、rank、retrieval work與error。遞迴欄位掃描找不到任何`expected`或
`label`，manifest也明確記錄`expected_labels_present: false`與`private_local_artifacts_read: false`。
這樣設計是為了證明「先固定模型看到的檢索結果，之後才用答案評分」，不讓expected target
進入collection階段影響結果。

第二次執行`--collect`時，collector因raw directory已存在而只執行validation，立即回傳
`unchanged`；沒有新的retrieval call。Raw與manifest SHA-256分別固定為
`3ea4a12f36e671b2acfd5d0b7e2ad1cc9ac4705a8b6ad796f7e18dd3a3301995`與
`2c895516c071f14cca778ec7e5ee87249925f606977203e35a28c60ca1c5bc01`。Development source仍是
`167c03a5e19fae47eb867b8101c26f1c5bf49ca2c80fb2eb9a4e8bfa0660825f`，沒有在freeze後修改。

17項focused tests、Ruff format/check、MyPy與compile再次通過。本步仍未執行`--score`，所以目前不知道
哪個policy通過gates，也沒有winner。下一步HIC-T5將只讀取這份已凍結raw資料，評分七個
policies並依預先凍結的規則選擇winner或誠實記錄null winner。

### HIC-T5：七個identity-contradiction policies全部未通過，產品結論為null winner

本步在評分前再次用內建validators確認24-case pack、7-policy protocol與24-row raw，並核對
source、pack、protocol、raw與manifest hashes。確認selection report原本不存在後，執行唯一一次
`--score`。Scorer沒有呼叫retriever；它只把七個已凍結policies套用到同一份raw bytes，並重算
既有公開223題、anchor-confidence v4 22題與新24題的所有gates。

評分成功建立`selection.json`與人類可讀的`selection.md`，但結果是`winner: null`。Baseline
可保留既有positive 168/168、v4 positive 10/10與新positive 12/12，卻仍讓v4的11/12與新的
10/12 absent identities輸出候選。這證明未加contradiction的原行為不安全。Numeric-only仍留下
10/12與10/12負例，同時既有recall已掉到167/168，因此數字衝突不足以解決一般車名替換。

最嚴格的`contradiction-050`將v4與新absent-identity nonempty都降到1/12，但代價是既有
positive只剩164/168、v4 positive 9/10、新positive 11/12。`contradiction-075`也同時誤殺三組
positives。較寬的1.00、1.25與1.50保住v4 10/10與新positive 12/12，但既有recall仍只有
167/168，而且v4仍有6至7個、新負例仍有5個非空。因此沒有任何threshold能同時滿足「不誤殺
合法拼字變形」與「不接受相似但錯誤車型」兩個要求。七個policies的contradiction errors均為0，
表示這是證據能力不足的產品結果，不是scoring exception或資料格式錯誤。

這個結果保留fail-closed：不啟用API、Dual RAG runtime、PostgreSQL或private evaluation，也不從失敗案例
發明case-specific exception。第二次`--score`回傳`unchanged`；`--check`從凍結inputs獨立重算後回傳
`valid`且winner仍為`null`。Selection JSON與Markdown SHA-256分別為
`3f72ab6e3e33d92b1f8fdef2b7872fec0ac7a6835da6609e39f34715ecb51589`與
`9322b6ffbe4b8a62ffaea3ebb277a8cdb539c112814f7caddf1b116fbde9f637`。Raw與development source hashes也維持不變。

測試檔新增一項real-artifact regression test，鎖定七個policies的實測counts、全部
`eligible: false`與deterministic `winner: null`，並在每次測試時呼叫`module.check()`重算，而不是只讀
報告文字。18項focused tests與52項相關regression tests全部通過。下一步HIC-T6會進行完整Lite
QA、requirements-to-evidence review、AI eval、decision/roadmap/README與project log收尾，安裝後測試CLI，
最後只把`Product Variant Resolver`資料夾內的變更commit並push到GitHub。

### HIC-T6：Lite QA與交付收尾

本步把「程式會跑」與「產品可上線」分開驗收。新增`review.md`把HIC-R1至R11逐項對應到
pack、protocol、raw、selection、tests與邊界證據，結論是implementation PASS、policy selection FAIL。
Evidence文件保留所有關鍵SHA-256與七策略量測表；AI eval則用dataset disclosure、leakage、
retrieval integrity、auditability、recall、safety、selection與release boundary作rubric，避免用測試全綠
掩蓋產品gate失敗。

Decision D80因此正式拒絕v1 promotion，保留`winner: null`。README補上新手可讀的實驗摘要與
`--check`命令；roadmap則將candidate-specific contradiction從「規劃中」更新為「已完成但無合格
policy」。這些文件不會把失敗實驗包裝成runtime能力：API、Dual RAG、PostgreSQL、canonical與
release/color邏輯全部不變。

安裝驗證時先發現這個`uv`精簡虛擬環境沒有`pip`，editable install所產生的`.pth`也未被該
Python runtime載入，造成entry point存在但package import失敗。這是安裝環境問題，不是identity
source錯誤；因此沒有修改凍結source，而是改用正常non-editable wheel安裝作最終使用者路徑驗證。
安裝後CLI正確顯示五個phases，連續兩次`--check`都回傳`valid`與`winner: null`。

最終QA為18/18 focused、52/52相關regression與788/788全專案tests PASS；Ruff format/check、MyPy、
compileall、installed CLI、重複integrity checks與`git diff --check`全部通過。唯一警告仍是既有
Starlette/AnyIO deprecation，與本功能無關。Development source SHA-256仍為
`167c03a5e19fae47eb867b8101c26f1c5bf49ca2c80fb2eb9a4e8bfa0660825f`，證明freeze後未被修改。
交付只包含`Product Variant Resolver`專案的source、tests、specs、docs與public evaluation artifacts，不包含上層
workspace的`AGENTS.md`、`.codex`或其他agent設定。

## 2026-09-21 — HKAC-T1–T4：公開rank-1 confidence實驗完成，但沒有策略通過安全門檻

### 新執行了什麼、解決什麼問題

前一版private shadow evaluation證明`secondary-075`雖能清掉錯誤的secondary candidates，卻會無條件
保留錯誤rank 1。本輪沒有把那兩筆private failure拿來調參，而是回到公開資料建立獨立v4 development：
先從既有公開案例選出10個「rank 1正確、但identity coverage低於0.75」的有效noise anchors，再人工定義
12個確定不在142-document corpus中的casting identities，要求系統對它們完全abstain。這同時測試兩種
相反風險：不能因拼字、黏字或縮寫錯殺正確第一名，也不能因manufacturer或相似model名稱而接受錯誤車款。

22題pack與十個門檻的protocol先後凍結，兩個artifact都記錄`retrieval_executed: false`；之後才一次性
執行22次Top-5 retrieval，得到42個raw candidates。所有門檻重用同一批bytes，並同步重算既有223筆公開
development rows，因此沒有因重跑搜尋或只看新題而得到偏差結果。整個程式沒有private evaluation路徑，
也沒有讀取private query、label、candidate或rank。

### 代碼修改了哪裡、原因與技術選型

新增`human_knowledge_anchor_confidence_development.py`與CLI
`pvr-develop-human-knowledge-anchor-confidence`。Rank 1 confidence固定為identity-token coverage與bounded
character similarity兩者較大值，因為公開正例顯示coverage最低可到0.333，但字元相似仍能保留拼字／空格
證據；若直接沿用0.75 coverage會重演已知false negatives。Rank 2–5繼續使用v3已選出的0.75 coverage，
保持來源順序，不改retriever排序，也不讓Top 5外候選被提升。

固定grid為0、0.5、0.55、0.575、0.6、0.61、0.625、0.65、0.7與0.75。0.61是公開正例最低
confidence附近的保守上界；後續較高門檻用來確認是否存在能清除hard negatives的分界。選用可解釋的
deterministic signals而不是新增neural dependency，是因為這階段要先驗證現有證據是否足以作admission，
而不是讓不透明模型掩蓋資料與標籤不足。Pack、protocol、raw result、source hashes與deterministic
rescore都可由`--check`驗證；重跑run則回傳`unchanged`，不覆寫一次性結果。

### 實際結果、問題在哪裡與做出的決定

程式、資料完整性與可重現性都通過，但產品策略沒有winner。門檻0.61仍保留168/168既有positives、
24/24 prior required與10/10新anchor positives，卻有10/12個不存在的casting query仍輸出候選。提高到
0.625時，missing-identity錯誤仍是10/12，正確召回卻先降為167/168與9/10；即使0.75仍有4/12錯誤
非空。這表示token coverage與character similarity在「有效拼字變形」和「同品牌相似車名」間高度重疊，
取兩者最大值再套單一threshold無法分離兩群。

因此本輪保留`winner: null`，不啟動另一輪private evaluation，也不修改API、Dual RAG runtime、
PostgreSQL、canonical、release或color行為。下一版不能只微調同一數字，應在全新的公開資料上研究
candidate-specific contradiction或identity span：例如query明確出現候選未能解釋的model token時，
把它當拒絕證據，而不是只計算「有多少token碰巧相同」。新資料與規則仍須先凍結，private failures
繼續只作最終測試，不得轉成development labels。

### 驗證結果

9項focused tests覆蓋confidence邊界、rank1／secondary分流、22次exactly-once retrieval、pack／protocol
byte-idempotence、private-path isolation、frozen artifact重算與null-winner證據。Ruff、format、MyPy、
compile與installed CLI檢查通過；完整suite為770/770 PASS。唯一訊息是既有Starlette／AnyIO
deprecation warning，與本次功能無關。

## 2026-09-21 — LRAE-T1–T4：新版private gate保留正確召回，但rank1誤召回使結果FAIL

### 新執行了什麼、解決什麼問題

公開development已選出`secondary-075`，但那只能證明在199+24題上有效。本輪建立新的versioned private
shadow evaluation，回答「這個已凍結policy能否在未參與選型的五個local review families上同時保留正確
召回並移除hard negatives」。舊v1的20題query、benchmark、raw result與FAIL result全部保持原位，不覆寫、
不重跑，也不把private內容複製到公開repo。

新protocol先綁定v3 winner、threshold 0.75、v3 protocol/selection hashes，以及舊v1 private/public evidence、
projection和source hashes。正式scoring只讀一次既有raw Top5 rows，使用147-document shadow catalog重算
candidate identity coverage並套用policy；new retrieval calls固定為0，因此沒有因重試得到不同candidate的風險。

### 代碼修改位置、方法選型與原因

新增`release_casting_review_anchor_evaluation.py`與CLI
`pvr-evaluate-local-release-review-family-anchor-admission`。程式把rank1直接admit，rank2–5需coverage>=0.75，
source order不變；每個private case保存admitted/abstained source ranks與coverage供本機稽核。新的private
`result.json`使用獨立gitignored v2目錄，公開manifest/report只含hash、aggregate counts、metrics、gates、
policy、limitations和downstream zero counts。

除原有Recall@5、Recall@1、family coverage、forbidden hits與retrieval errors外，本輪預先增加
`hard_negative_forbidden_rank1_hits=0`和`admission_errors=0`兩個gate。原因是v3最大未知風險就是anchor可能
保留錯誤第一名；若只看總forbidden而不特別記錄rank1，就無法判斷失敗是secondary threshold還是anchor
設計造成。

### 實際結果、失敗原因與技術決定

Positive Recall@5維持15/15，Recall@1為13/15，五個local families全部覆蓋；retrieval與admission errors都是0。
44個source candidates中保留26個、abstain 18個。Hard-negative forbidden hits從舊v1的3個降到2個，表示0.75
secondary gate確實移除一個錯誤secondary candidate。

然而剩餘2個forbidden都在source rank1，因此被anchor規則保留，兩個hard-negative gates同時FAIL。這不是
把0.75提高到1.0能解決的問題，因為rank1不讀secondary threshold。Frozen verdict保留FAIL；本輪拒絕看著
private case新增例外、修改anchor或重跑retrieval。Runtime integration和API change繼續被阻擋。

### 驗證、邊界與下一步

新增10項focused tests，覆蓋rank1 anchor、secondary gate、unknown candidate fail-closed、完整PASS fixture、
rank1 forbidden雙gate、public privacy、create-once protocol、真實aggregate FAIL與check不重跑。完整761/761
tests PASS；targeted Ruff/format、MyPy、compileall、protocol/report/check全部通過，唯一訊息仍是既有
Starlette/AnyIO deprecation warning。

Private query、label、candidate identity、coverage、rank與case result都沒有進Git；API、Dual RAG runtime、
PostgreSQL、canonical catalog、release/color truth全部未改。下一步必須回到public development資料建立
anchor-confidence v4，另外蒐集合法的wrong-rank1與valid-low-coverage-rank1 development evidence；這次
private兩個失敗只能當test evidence，不能拿來調參。

## 2026-09-20 — HKAA-T1–T4：anchored admission在公開development取得合格策略

### 新執行了什麼、解決什麼問題

v2已證明只調整candidate順序無法解決Top5誤召回，因為大部分pool本來只有2–4筆。本輪改為真正的
admission／abstention：原始rank1作為anchor保留，rank2–5則必須有足夠identity-token coverage才輸出。
這解決「錯誤candidate即使降到第4名仍在Top5」的結構性問題，同時避免v1全域hard filter刪除低coverage
但排名第一的正確typo candidate。

正式v3 scoring沒有重新檢索，而是先把既有v2 selection JSON、protocol、source hashes、八個thresholds與
winner ordering凍結，再離線重用223個public development raw pools。這讓v3只測量admission差異，不混入
retrieval變動，也完全沒有讀取private五-family projection或20題final evaluation。

### 代碼修改位置、方法選型與原因

新增`human_knowledge_anchor_admission_development.py`與CLI
`pvr-select-human-knowledge-anchor-admission`。Policy固定保留source rank1；rank2–5只在coverage大於等於
threshold時保留；輸出順序仍是原始source order，rank5以後不能被提升。選擇anchor exception，是因為v1
已證明全域coverage會誤刪正確答案；公開dev同時顯示24個新required全在rank1，而三個舊target在rank2時
coverage為1、1與0.75，因此secondary gate仍可被完整驗收。

Grid固定比較0、1/3、0.4、0.5、0.6、2/3、0.75與1.0。Eligibility繼續要求168舊positive、4 merge、24新
required全部保留，既有hold/merge violation、unrelated result與error全部為0。合格者才依forbidden最少、
threshold最低選擇，避免事後挑過度嚴格但沒有額外收益的設定。

### 實際結果、技術決定與限制

Threshold由0提高時，forbidden cases依序為18、16、8、7、2、2、0、0。到0.75仍保留168/168舊positive、
165/168 rank1、24/24新required、4/4 merge與所有治理gate；它從329個source Top5 candidates保留212個、
abstain 117個。Threshold1.0雖同樣零forbidden，卻把舊positive降成167/168，因此不合格。

Frozen rule選出`secondary-075`，status是`qualified_for_new_private_shadow_evaluation_only`。這不是最終PASS：
rank1永遠保留，所以若未見query把錯誤family排第一，policy仍會放行。公開development結果只授權建立一份
新的versioned private shadow evaluation；不能覆寫舊20題FAIL、依舊結果調整0.75或直接改runtime。

### 驗證、邊界與下一步

新增12項focused tests，覆蓋rank1 anchor、secondary threshold、source order、rank5 boundary、非法threshold、
upstream-bound protocol、private-path隔離、winner ordering、create-once protocol、真實winner與check不重跑。
完整751/751 tests PASS；targeted Ruff/format、MyPy、compileall、protocol/report/installed CLI check全部通過，
唯一訊息仍是既有Starlette/AnyIO deprecation warning。

`HumanKnowledgeIdentityRetriever`、API、PostgreSQL、canonical catalog與Dual RAG runtime全部未改。下一步是
先凍結一個新的private shadow-evaluation version，再套用`secondary-075`評估positive recall、family coverage、
forbidden hits與wrong-rank1風險；若FAIL回到development設計，只有PASS才能規劃opt-in runtime integration。

## 2026-09-20 — HKRR-T1–T4：relative reranker完成，但候選池太小而無法改善Top-5安全性

### 新執行了什麼、解決什麼問題

前一版global coverage filter能移除錯誤candidate，卻同時刪掉正確的縮寫與拼字差異。本輪改測不刪除
candidate的相對懲罰reranker：先把每題raw pool從Top5擴為最多Top25，再依candidate自己的identity-token
coverage調整原始RRF分數，最後重新取Top5。目標是回答「能否只把unsupported neighbor往後排，同時完整
保留既有recall」，而不是再試另一個固定hard threshold。

Protocol在正式collection前固定七個weights（0、0.05、0.1、0.25、0.5、1、2）、公式、223題denominator、
Top25 pool、Top5 output與winner ordering。正式執行只建立一個v4 retriever，對199個既有development cases
與24個safety cases各呼叫一次；七個configurations全部重用相同raw candidates，private 20題沒有被開啟。

### 代碼修改位置、方法選型與原因

新增`human_knowledge_reranker_development.py`與CLI `pvr-select-human-knowledge-reranker`。每個candidate保留
sparse、dense、character與RRF rank/score、matched tokens和identity coverage；新分數為
`rrf_score / (1 + weight * (1 - coverage))`。Fully supported candidate不受懲罰，unsupported部分越多，分數
下降越多。選用乘法penalty而不是coverage加分，是為了保留retriever原有evidence比例，也避免coverage值
直接壓過RRF的小數尺度。

Winner必須先通過168個舊positive、4個merge、24個新required、零治理違規、零unrelated nonempty與零error。
合格者才依forbidden最少、舊／新rank1最多、weight最低排序。這防止把「只回傳第一名」誤當安全改善，因為
現有舊資料仍有3個正確target不在rank1。

### 實際結果、錯誤原因與技術決定

七個weights全部保留168/168舊positive、165/168舊rank1、24/24新required和所有治理gate；但七組也全部
留下18/24 forbidden cases，安全率維持0.25。Frozen selector因此回傳baseline，而且
`improves_over_baseline=false`，明確表示沒有合格mitigation。

失敗原因不是weight不夠大，而是candidate-pool boundary。223題中只有5題得到超過5個raw candidates；
24個safety pools的median只有3，9題只有2個candidate、8題只有3個，只有2題超過5。Reranker可以把錯誤
candidate從第2名降到第3或第4名，但當整個pool只有2–4筆時，它仍會出現在Top5。看到結果後再放大weight
沒有意義，也會違反frozen protocol；下一版必須明確判斷candidate是否應被admit／abstain，而不只是排序。

### 驗證、邊界與下一步

新增13項focused tests，覆蓋baseline不變、relative penalty、非法weight、frozen protocol、private-path隔離、
223次exactly-once Top25 collection、winner ordering、create-once protocol、真實失敗結果、sparse-pool證據與
check不重跑。完整739/739 tests PASS；targeted Ruff/format、MyPy、compileall、protocol/report check都通過，
唯一訊息仍是既有Starlette/AnyIO deprecation warning。

本輪沒有更動`HumanKnowledgeIdentityRetriever`、API、PostgreSQL、canonical catalog或Dual RAG runtime，也
沒有重跑private evaluation。下一步應另開admission v3，設計query-candidate compatibility與明確abstention，
同時保護三個舊target不在rank1的案例；在public development取得合格winner以前仍不得進private gate。

## 2026-09-20 — HKAD-T1–T4：coverage grid完成，但沒有合格的誤召回修正方案

### 新執行了什麼、解決什麼問題

上一階段已用24個development pairs量到18個forbidden admissions。本輪沒有直接改runtime threshold，而是
先凍結五組identity-token coverage策略：0、0.5、2/3、0.75與1.0。Grid同時納入舊199題positive／merge／
hold／unrelated development cases與新24題required／forbidden cases，解決「只降低誤召回，卻不知道正常
拼字錯誤會損失多少」的盲點。

Collector只建立一個現有v4 retriever，對223題各呼叫一次Top 5；五個coverage settings全部重用相同raw
candidates。這避免某個設定因重跑順序或不同候選樣本獲得不公平優勢，也把比較範圍限制為post-retrieval
admission，不混入新的embedding、index或neural dependency。

### 代碼修改位置、策略設計與選型原因

新增`human_knowledge_admission_development.py`與CLI
`pvr-select-human-knowledge-admission`。Coverage只讀candidate的casting與approved aliases，先沿用
identity-core noise policy，再以exact、compact containment、至少2字元prefix abbreviation、numeric suffix或
SequenceMatcher>=0.8對齊每個identity token。這些模式是在protocol凍結前定義，目的是同時容忍`stel`類拼字、
`st`類縮寫、compact文字與年份數字變形。

Eligibility不是看單一平均分數，而是要求舊168 positives、4 merge controls、新24 required全部保留，既有
hold／merge forbidden violations與unrelated nonempty都維持0，retrieval errors也為0。合格設定才依new
forbidden cases最少、coverage threshold最低排序。這個選擇規則避免事後為了某一個漂亮安全數字接受未揭露
的recall損失。

### 實際結果、失敗原因與技術決定

Baseline保留168/168舊positive、24/24新required，但仍有18/24 forbidden cases。Coverage 0.5降到7個
forbidden，卻漏1個舊positive；2/3降到2個，卻漏3個。Coverage 0.75與1.0都把forbidden降到0，但分別只
保留159／152個舊positive，而且新required也降到23／22。所有nonzero mitigation都違反預先固定gate。

Frozen selector因此回傳baseline，因為它是唯一eligible configuration；這只代表fallback，不代表修正成功。
本輪拒絕把baseline稱為新policy，也拒絕在看到結果後把168 gate降成167。Global hard coverage filter的問題是
把「candidate缺少重要model token」與「query用了縮寫／拼錯」視為同一種缺口，因此安全提升必然伴隨
false negatives。下一版應研究candidate-relative penalty或reranking，而非直接刪除candidate。

### 驗證、邊界與下一步

新增15項focused tests，覆蓋五種token matching、coverage、protocol grid、private-path隔離、223次exactly-once
collection、winner ordering、create-once protocol、real result tradeoff與check不重跑。完整726/726 tests PASS；
targeted Ruff/format、MyPy、compileall、protocol/report `--check`與`git diff --check`通過，唯一訊息仍是既有
Starlette/AnyIO deprecation warning。

Private 20題沒有被讀取或重跑，`HumanKnowledgeIdentityRetriever`、API、PostgreSQL、canonical catalog與
Dual RAG runtime全部未改。下一步是另開admission v2 spec，以relative penalty/reranking方式保留weak-but-valid
typo candidates，同時將wrong neighbor往Top 5之外推；v1必須作為失敗alternative保留，不能覆寫。

## 2026-09-20 — HKFP-T1–T4：建立獨立false-positive development baseline

### 新執行了什麼、解決什麼問題

前一步的private 20題evaluation已經揭露3個hard-negative誤召回，但它是不可拿來反覆調參的test evidence。
若直接根據那三題修改threshold再重跑，得到的改善只代表記住測試題，不代表模型真的比較安全。本輪因此
建立另一份development-only pack，只使用repo原有142份公開Human Knowledge documents，讓後續可以合法
比較false-positive mitigation，而不污染private final evidence。

Pack包含24題，每題同時指定required target與forbidden neighbor。兩個文件必須是不同ID／UUID，但至少共享
一個identity-core token，例如相同manufacturer或model lineage；query加入marketplace／collection context，
不能逐字等於任一indexed identity。Builder在retrieval前先凍結pack、input hashes、case order與固定v4設定，
manifest明確記錄`retrieval_executed=false`和`private_local_artifacts_read=false`。

### 代碼修改、方法選型與原因

新增`human_knowledge_false_positive_development.py`與CLI
`pvr-develop-human-knowledge-admission`。`--freeze-pack`只載入既有human catalog與42-family projection，解析
24組typed IDs、檢查shared core tokens、non-exact query和source hashes，不建立retriever。Pack固定後，default
模式才用既有Human Knowledge RAG v4（floor 0.5、character RRF weight 1.0、hashing-v1/192）執行Top 5 baseline。

每題同時保留「應找得到」與「不應混入」兩個方向，是為了避免下一步使用最簡單但錯誤的方法：把所有
ambiguous candidates全部過濾掉。只看forbidden下降會鼓勵過度abstain；只看required recall則重複目前
高召回、低排除的問題。後續policy grid必須同時守住既有199題positive development與這24題的safety。

沒有直接修改`HumanKnowledgeIdentityRetriever`，也沒有新增runtime env flag。Baseline階段的目的只是建立
可重現的before measurement；此時選threshold、reranker或token coverage rule都會把診斷與解法混在同一個
commit，失去比較基準，因此明確延後到下一個versioned experiment。

### Baseline結果、測試與下一步

24/24 required targets全部排名第1，required Recall@5為1.0，retrieval errors為0；同時18/24 cases把指定
forbidden neighbor放入Top 5，forbidden-case rate為0.75，safety accuracy只有0.25。這把原先3/5的現象擴展
為更一般的same-make／related-model admission問題，也證明目前主要瓶頸不是「找不到」，而是「排除不夠」。

新增12項focused tests，覆蓋pack counts、typed pair/non-exact/shared-core contract、source hashes、private-path
隔離、exactly-once collection、exception不retry、required/forbidden獨立denominator、create-once pack、partial
state拒絕、real artifact與check不重跑。完整711/711 tests PASS；targeted Ruff/format、MyPy、compileall、
artifact `--check`與`git diff --check`通過，只有既有Starlette/AnyIO deprecation warning。

本輪沒有讀取或重跑private 20題，沒有新增mitigation、winner或PASS claim，也沒有改API、PostgreSQL、
canonical catalog或Dual RAG runtime。下一步是針對這24題與舊199題建立admission policy grid，例如比較
identity-token coverage或unmatched-distinctive-token penalty；選型時必須同時維持positive recall和降低
forbidden admissions，選完後才可規劃新的versioned final evaluation。

## 2026-09-19 — LRFE-T1–T4：一次性shadow retrieval揭露3個hard-negative誤召回

### 新執行了什麼、解決什麼問題

上一階段只證明五份private `review_family` documents能以固定schema建立，尚未證明實際搜尋時能在雜訊中
找到正確family，也未驗證相似但不同的名稱會不會被錯誤吸入。本輪建立local release review-family retrieval
evaluation，先凍結15個非逐字positive questions與5個near-confusable hard negatives，再把5個local candidates
以shadow方式加入現有142-document Human Knowledge corpus，形成147-document離線競爭環境。

正式收集每題只執行一次。Collector只讀不含答案的query pack，保存20筆raw candidate outputs後，才載入
另一份private benchmark計分。這解決了「先看答案或結果再改題」的洩漏風險；一旦raw results存在，CLI
只允許`--check`或驗證既有結果，不能再次檢索。

### 代碼修改哪一部分、原因與技術選型

新增`release_casting_review_evaluation.py`與CLI
`pvr-evaluate-local-release-review-families`。Shadow catalog不是另寫一套相似度演算法，而是直接重用目前
Human Knowledge RAG v4：character identity postings、exact token evidence、192-dimensional `hashing-v1`
dense retrieval與RRF fusion，固定character floor 0.5和weight 1.0。選擇重用正式候選器，是為了測量若未來
接入時實際會遇到的ranking competition；若另寫簡化lexical matcher，結果無法回答runtime風險。

Corpus包含100個provisional variants、既有42個review families與新5個local families，共147 documents；
不是只讓5個新文件互相比賽。Query contract要求每個local family三個positive和一個hard negative，positive
正規化後不能等於casting或alias。Hard-negative只禁止指定local family，允許existing corpus回傳其他合理
候選；這避免把沒有完整標註的142 documents誤當成「全部都應空結果」。

五個gate在執行前固定：Recall@5必須1.0、Recall@1至少0.8、family coverage@5必須1.0、forbidden hits和
retrieval errors都必須0。沒有以平均分數或事後threshold取代hard-negative gate，因為本功能的主要風險正是
新增family擴大誤召回。Private query/label/raw/result全部加入gitignore；public manifest/report只含hash、
configuration、aggregate metrics、limitations與zero downstream effects。

### 實際結果、為何保留FAIL，以及下一步

一次性結果為positive Recall@5 `1.0`（15/15）、Recall@1 `0.8667`（13/15）、family coverage@5 `1.0`
（5/5），retrieval errors為0；這四個gate通過。但5個hard negatives出現3次forbidden local-family hits，
要求為0，因此整體結論是**FAIL**。這顯示新文件容易被找到，卻也會因共享manufacturer、數字型號或
generic body-style文字而過度匹配。失敗後沒有刪題、降低gate、調整0.5 threshold或重跑。

新增13項focused tests，覆蓋20題/3+1 per-family contract、exact-query拒絕、固定gate、collector不能讀
labels、每題一次、exception不retry、scoring denominator、negative/error failure、public privacy、既有raw
不重跑、partial output拒絕與candidate-rank tamper。`PYTHONPATH=src .venv/bin/pytest -q`完整699/699通過；
focused Ruff check/format、targeted strict MyPy、compileall、CLI `--check`、privacy scan與`git diff --check`
通過。完整repo Ruff/format仍有大量本次以前的baseline違規，因此不宣稱全repo lint綠燈；既有唯一測試
訊息仍是Starlette/AnyIO deprecation warning。

Runtime documents、canonical promotions、reviewed colors、PostgreSQL writes、API changes與network requests
都是0。下一步不能把5個documents接入Dual RAG；應另建development-only false-positive mitigation資料與
spec，評估更嚴格的identity admission或reranking，再以本次不可變20題作最終回歸，而不能拿它直接調參。

## 2026-09-12 — T48.3 turns owner confirmation into a frozen but unscored benchmark

### What was executed and what problem it solves

The previous handoff presented the complete frozen query pack, linked a human-readable review, and
explained that the next step required project-owner confirmation before labels could exist. The
owner's instruction to proceed therefore authorized exactly T48.3 against the unchanged
`26e244c0…4358733` query checksum. This closes the attribution gap between an AI-authored question
and the human-approved relevance expectation that will later score it.

All 105 cases now have a separate project-owner decision with timestamp, approval, reason, and
type-correct expectation. The builder combined those decisions with the frozen questions only after
verifying every checksum and source boundary. The output is a labeled benchmark, but no retrieval
was run: candidates, ranks, scores, aggregate metrics, and PASS/FAIL remain absent.

### Code and artifact changes, reasons, and method selection

`scripts/record_family_retrieval_owner_decisions.py` records the current approval as a reproducible
artifact rather than leaving it only in chat history. The approved query checksum is hardcoded in
the script, so rerunning it after any question change fails immediately. The script also revalidates
the query pack and manifest before constructing decisions; this duplicates a small amount of guard
logic intentionally because attribution must never attach to a stale or widened pack.

Expected labels are derived only from the already adjudicated registry/reference relationship, not
from retrieval output. Positive cases expect their referenced review-family ID. Merge controls
expect the existing human-backed casting ID and explicitly forbid a duplicate family ID. Hold
controls require `expected_materialized=false`. Unrelated controls expect zero candidates. Reasons
are tailored to the case type and, for positives, the challenge style; every item retains
`decided_by=project_owner` and the same second-precision UTC decision time.

`owner-decisions.json` stores 105/105 approvals and is checksum-bound to the prior commit's query
pack. `benchmark.json` joins each frozen question with its separately approved expected branch.
`benchmark-manifest.json` freezes the query, owner decision, registry, projection, human catalog,
and their manifests plus the system-under-test code/version block. The benchmark hash is
`440246fb6a3b38f56fc25c1ec939d53d6cfc4457fed738aad561899325808afd`; its explicit exclusions still
prohibit canonical decisions, calibration, threshold selection, query rewriting, retriever tuning,
release truth, PostgreSQL ingestion, and production-accuracy claims.

Two actual-artifact tests were added. The first reconstructs the official benchmark through the
strict builder, compares both JSON objects exactly, checks all 105 approvals, and asserts that no
candidate/rank/score/metric/verdict fields exist. The second runs the owner-decision and benchmark
`--check` commands and proves all three frozen output hashes remain unchanged. Existing negative
tests continue to reject partial, duplicate, stale, changed, or incorrect labels.

Decision D35 explains why the owner's bounded proceed instruction is sufficient authority here and
why it does not widen scope. The new T48.3 evidence document records hashes, class semantics,
absence of scoring, and the next gate. Specs and README now distinguish a frozen labeled benchmark
from a completed retrieval evaluation.

### Verification, current impact, and next step

Focused validation passes 10/10. The complete repository suite passes 194/194 in 2.203 seconds on
the final tree. Python compilation, owner-decision and benchmark byte reproduction, the configured
100-character code-line check, `git diff --check`, and the repository-root scope check pass. Ruff is
not installed on this host, so no Ruff result is claimed. The suite emits only the known non-failing
Starlette legacy-`httpx` environment warning.

No runtime module, API, canonical catalog, calibration/policy artifact, PostgreSQL row, or existing
resolver result changed. T48.4 is now the only next task: implement the read-only evaluator, retrieve
against the already frozen `human-knowledge-hybrid-v2`, compute the precommitted metrics, and publish
PASS or FAIL without tuning this v1 holdout.

## 2026-09-12 — T48.2 freezes 105 independent queries without looking at retrieval output

### What was executed and what problem it solves

T48.2 created the first official evaluation questions for the 42 family documents added in T47.
The earlier 42/42 smoke test asked the index for each family's exact own name, which proves loading
but not robustness. This task replaces that circular test shape with a separately authored,
one-time holdout: 84 positive queries, 4 merge controls, 7 held-identity controls, and 10 unrelated
zero-overlap controls. Every case is fixed to the test split.

The work was deliberately performed without calling the Human Knowledge retriever, resolve API,
debug UI, or any evaluation runner. Only identity references, existing source files, and the T48.1
static validator were read. Consequently, no candidate, rank, score, or PASS/FAIL observation could
influence how a query was worded. The resulting query pack was then checksum-frozen before labels.

### Code and data changes, reasons, and method selection

`scripts/author_family_retrieval_query_pack.py` preserves the hand-authored query wording in a
deterministic source map keyed by existing review IDs. This extra source file was chosen instead of
manually maintaining a 77 KB generated JSON document: it makes missing IDs, ordering mistakes, and
accidental text edits reproducibly detectable. It does not generate wording from a template and
does not import or instantiate the retriever. The script first verifies its 42/4/7 keys exactly
match the registry, assembles allowlisted case fields, asks the T48.1 validator to reject invalid
content, and only then writes atomically. Its `--check` mode is read-only.

The 42 marketplace cases retain recognizable model identity among realistic condition, card,
colour, year, series, auction, and seller words. Their purpose is to test whether ranking survives
extra marketplace language. The 42 lexical cases were individually composed with abbreviations,
misspellings, number-word substitutions, punctuation removal, or spacing changes and are required
to break the full normalized casting phrase. This two-style decision avoids reporting success on
easy exact-name wrappers while hiding spelling weaknesses.

Bogzilla, Crescendo, Draftnator, and Haulerback are single-token family names. Their lexical cases
use `bogzila`, `crescndo`, `draftn8r`, and `haulerbak`; this intentionally may remove every shared
identity token. The current retriever may fail them, but simplifying them after anticipating failure
would bias the holdout. Merge queries express four already accepted links to human-backed castings.
Hold queries express seven identities that must not become review-family documents. Ten invented
single-token strings were selected only after the validator proved zero overlap with all searchable
tokens in the 142-document corpus.

`query-pack.json` is the official 105-case artifact. `query-pack-manifest.json` freezes its SHA-256
`26e244c04325f7909fb222b6cdd32ee2301253db17f0b8b97cf2f63ac4358733`, exact class/style/group
accounting, authoring declaration, test-only exclusions, catalog/projection inputs, and source-code
checksums. The manifest was built with `--freeze-query-pack` and reproduced with
`--check-query-pack`; neither path reads labels or calls retrieval.

Two tests were added to the T48.1 suite. One loads the actual pack and recomputes every validation
and manifest field while asserting that output/rank/expected-label fields do not exist. The other
runs the authoring and manifest check commands and proves their input hashes do not change. The
human-readable evidence file lists all positive and governance-control queries so the owner can
review semantics without seeing retrieval output.

### Verification, limitations, and next step

Focused validation passes 8/8. It confirms exact 105/84/4/7/10 counts, 42 complete two-style groups,
all control identities, four single-token challenges, sorted unique IDs and queries, broken lexical
phrases, zero unrelated overlap, frozen versions/checksums, absence of retrieval-output fields, and
byte-reproducible authoring/manifest checks. The complete repository suite passes 192/192 in 2.250
seconds on the final tree. Python compilation, the configured 100-character code-line check, and
`git diff --check` pass. Ruff is unavailable on this host, so no Ruff result is claimed. The suite's
only message is the known non-failing Starlette legacy-`httpx` environment warning.

Static rules can prove structure and obvious copying, not whether each noisy query is a fair human
expression of its referenced family. That semantic judgment remains intentionally separate. The
next action is project-owner confirmation of the frozen 105 query/reference pairs. T48.3 cannot
create `owner-decisions.json` or a benchmark until that approval binds the exact hash above, and
T48.4 cannot run retrieval until T48.3 succeeds.

## 2026-09-12 — T48.1 builds the evaluation guardrails before any official query is written

### What was executed and what problem it solves

The project owner's instruction to continue confirmed the T48 Lite requirements, design, and task
order. Work therefore advanced by exactly one bounded task: T48.1. The problem being solved is not
retrieval accuracy yet; it is preventing a future accuracy number from being produced with changed,
leaking, incomplete, or self-approved test data.

A new benchmark builder now separates three events that previously existed only in the design. The
query author can validate and freeze a 105-case query pack without labels or retrieval. A separate
project-owner artifact must then approve every frozen case against the exact query-pack checksum.
Only after both artifacts and all source manifests validate can the script create a labeled
benchmark. This order means editing one query after approval, omitting one decision, or changing the
retriever implementation stops the build before it touches prior output.

No official T48 query was authored during this task. The six tests generate temporary synthetic
fixtures solely to exercise the contract, then delete them. No retriever was called, so T48.2 can
still be performed output-blind and no metric or accuracy result exists.

### Code areas changed, reasons, and decisions

`scripts/build_family_retrieval_benchmark.py` is the new single source of truth for the frozen data
contract. It uses field allowlists rather than accepting arbitrary JSON because additional fields
could silently carry retrieval output, training flags, or unreviewed identity data into the test.
It enforces the exact 105/84/4/7/10 case accounting, both required positive styles for every one of
the 42 accepted families, complete merge/hold coverage, ten unique zero-overlap controls, sorted and
unique case IDs/queries, second-precision UTC attribution, and the declaration that no retriever
output was viewed.

The leakage checks compare normalized query text with approved family names, indexed brand/casting
and alias strings, and existing human-label/initial query text. Lexical cases additionally must
break the full normalized casting phrase and declare a spelling, abbreviation, punctuation, or
spacing challenge. Unrelated controls are checked against the token vocabulary of all 142 current
Human Knowledge documents. Automated equality checks cannot judge whether a paraphrase is
semantically fair, which is why they supplement rather than replace the later project-owner review.

The system-under-test block freezes more than a friendly model name. It records the two data
versions/checksums, `human-knowledge-hybrid-v2`, offline `hashing-v1`, 192 dimensions, RRF constant
60, Top-5 limit, and checksums for the normalization, embedding, and retriever source files. This
decision was made because unchanged JSON with changed Python logic is still a different experiment.
The owner-decision schema separately validates expected IDs by case type: positives target review
families, merges target existing provisional-variant castings and forbid duplicate families, holds
remain unmaterialized, and unrelated cases expect zero candidates.

Output files use a temporary file in the destination directory, flush it to disk, and then use
`os.replace`. Validation finishes before either benchmark output is written. This standard-library
approach was selected over adding a database or schema dependency because the artifacts are small,
version-controlled JSON files and Lite mode benefits from a dependency-free reproducible command.
`--check` compares exact bytes without writing; separate `--freeze-query-pack` and
`--check-query-pack` modes exist because T48.2 must freeze questions before owner labels exist.

`tests/test_family_retrieval_benchmark.py` constructs a complete valid contract only inside
temporary directories. Its negative cases deliberately introduce copied text, retained lexical
phrases, unrelated-token overlap, viewed output, dev-split use, removed PostgreSQL exclusions,
changed RRF parameters, stale query checksums, missing/duplicate approvals, and wrong identity
labels. Sentinel-output subprocess tests prove failure does not overwrite a previous benchmark.
`data/evaluation/family-retrieval-v1/README.md` documents the handoff order while intentionally
leaving the formal query/decision/benchmark files absent.

The confirmed spec status and T48.1 checkboxes were updated, README now distinguishes implemented
guardrails from unmeasured quality, Decision D33 records why query freezing is a separate phase, and
the new evidence record captures the acceptance result and limitations.

### Verification, current impact, and next step

The focused contract suite passed 6/6. The complete repository suite increased from 184 to 190 tests
and passed 190/190 in 2.027 seconds on the final tree. Python compilation and `git diff --check`
passed. Ruff is not installed in this host environment, so no lint result is claimed; the code was
checked for the configured 100-character line limit separately. The suite retains one known
non-failing Starlette legacy-`httpx` environment warning.

This change creates no canonical entity, provisional variant, PostgreSQL row, calibration change,
official evaluation label, or retrieval score. T48.2 is now the only next task: independently author
the formal 105-case query pack, validate and freeze its checksum without running retrieval, and
present that frozen pack for project-owner review before T48.3 can add labels.

## 2026-09-11 — T48 defines how family retrieval will be tested without testing on its own names

### What was executed and what problem it solves

T48 begins with a Lite specification rather than immediately creating a benchmark or changing the
retriever. T47 proved that all 42 accepted review families are present and retrievable when queried
with their own exact names. That result is necessary for wiring, but it cannot answer the product
question the next phase actually cares about: whether noisy marketplace wording still retrieves the
right family and avoids unsafe identities.

The new specification converts that ambiguity into a controlled evaluation. It proposes 105 fixed
test cases: 84 positives covering every family twice, 4 accepted-merge controls, 7 held-family
controls, and 10 unrelated queries. Positive cases are split into marketplace noise and lexical
variation so easy queries with extra seller words cannot hide failures on abbreviations, spacing,
punctuation, or misspellings. Queries must be written and committed before anyone views retriever
output; all labels require a separate project-owner decision file before scoring.

### Files added or changed, and why

`specs/family-retrieval-evaluation/requirements.md` defines sixteen EARS requirements covering the
frozen system under test, output-blind authorship, exact case composition, complete family/control
coverage, non-triviality, owner verification, deterministic manifests, test-only isolation,
read-only scoring, metrics, gates, truthful failure, reports, privacy, and full regression.

`design.md` turns those requirements into an artifact and execution architecture. It separates the
pending query pack, owner decisions, frozen benchmark, evaluator, and report so changing one layer
invalidates downstream checksums rather than silently changing the test. The proposed evaluator
retrieves before it reads expected labels and writes ordered candidate/rank evidence from which all
aggregate metrics can be recomputed.

`tasks.md` divides implementation into five auditable stages. T48.1 builds the contract, T48.2
authors and freezes queries without retrieval, T48.3 records owner labels, T48.4 evaluates the
unchanged v2 retriever, and T48.5 closes QA. This ordering is intentional: combining authoring and
scoring in one task would let observed failures influence the supposedly held-out questions.

Decision D32 records the chosen composition, rejected alternatives, precommitted gates, 10x scale
impact, and most likely failure. The README, MVP brief, QA risk list, and a dedicated specification-
evidence document now state that T48 is only a draft contract—there is no new accuracy result.

### Source and method choices

Repository inspection found that the 2025 Fandom normalized rows explicitly declare
`staging_only_not_evaluation_or_canonical`. The T47 family projection also declares itself excluded
from evaluation ground truth. Reusing either as a convenient test dataset was rejected because it
would rewrite a frozen governance decision after the fact. Identity references may define what the
review question is, but scored query wording must be separately composed and human-approved.

Live marketplace scraping was also rejected for this first benchmark. It would introduce changing
results, unclear reuse rights, possible personal information, and irreproducible queries. Large
automatic typo generation was rejected because thousands of templated strings do not create
thousands of independent judgments. A smaller 105-case set is reviewable in Lite mode while still
covering every accepted, merged, and held family outcome.

The corpus feasibility check found 42 unique normalized family identities: 4 single-token, 15 two-
token, and 23 with at least three tokens. Haulerback, Crescendo, Bogzilla, and Draftnator are the
single-token cases. They must receive lexical challenges even though the current shared-token
eligibility rule may return nothing after a full-token misspelling. Exposing that weakness is the
reason for an independent evaluation; removing difficult cases would defeat it.

### Metrics, thresholds, and decision rationale

Recall@5 is the primary quality measure because this source presents bounded review suggestions,
not an automatic family decision. Recall@1 and MRR@5 still measure ranking usefulness. Family
coverage@5 prevents frequent/easy families from hiding families that never work, and metrics are
separated by query style. Merge controls must find their existing provisional-variant casting,
held identities must never appear as materialized review families, and unrelated zero-overlap
queries must remain empty.

The gates are frozen before data or results: Recall@5 at least 0.85, Recall@1 at least 0.65, MRR@5
at least 0.75, each query style Recall@5 at least 0.75, family coverage@5 at least 0.90, merge control
Recall@5 exactly 1.0, and zero held-family or unrelated-query violations. These thresholds decide
only whether PostgreSQL scale experimentation is justified. They do not authorize canonical or
production matching.

If v1 fails, the report must remain FAIL with raw cases and error categories. The team may use those
errors to design a new retriever, but the now-known v1 test cannot serve as final proof for that
replacement; a new v2 holdout is required. This costs additional authoring effort but avoids tuning
until a small benchmark says what the team wants to hear.

### Current impact, verification, and next step

This specification step changes no runtime code, model, index, data artifact, PostgreSQL state,
canonical behavior, or evaluation score. Static feasibility accounted for all 42 new families, 79
accepted release references, 4 merges / 9 references, and 7 holds / 12 references. The existing
184-test T47 baseline remains the executable starting point. A fresh rerun passed 184/184 in 1.637
seconds; static checks also confirmed all sixteen requirements are represented in task traceability,
all required design sections exist, and the repository diff has no whitespace errors. The known
non-failing Starlette legacy-`httpx` environment warning remains unchanged.

The next action is for the project owner to confirm the T48 requirements, design, and task order.
After confirmation, T48.1 can implement the strict benchmark builder and negative tests. T48.2 must
then freeze the query pack without running retrieval; results remain prohibited until all 105 labels
are separately approved in T48.3.

## 2026-09-11 — T47 closes with a requirement-by-requirement Lite QA verdict

### What was executed and what problem it solves

T47.4 verifies the entire family-level Human Knowledge RAG feature instead of treating the passing
implementation tests from T47.1–T47.3 as sufficient by themselves. The risk being addressed is a
false sense of completion: a family suggestion can look correct in the browser while its source
artifact is stale, a hold slipped into the index, the canonical decision changed, or documentation
quietly overstates exact-name retrieval as real-world accuracy.

The final QA therefore follows the feature from the original 100-row external pilot through review,
six owner-decision events, the stable family registry, the runtime projection, typed retrieval,
debug API/UI, and the independent canonical decision boundary. The result is PASS for T47's stated
Lite scope: family evidence is reproducible, typed, bounded, observable, safe to render, and unable
to become canonical identity. This pass does not promote any family or release variant and does not
approve PostgreSQL persistence or production retrieval quality.

### Code and documentation changes, affected areas, and reasons

No product code, runtime configuration, or data artifact needed modification in T47.4. Changing the
implementation during its closing QA would have mixed verification with another build step and
made the evidence harder to attribute. Instead, this task adds
`specs/family-level-human-knowledge/review.md`, which maps every FHK-R1–FHK-R16 requirement to a
specific test, artifact invariant, runtime observation, or repository diff result. The verdict is
worded as PASS for the debug-only integration boundary rather than an unrestricted product pass.

`docs/evidence/ai-evals/dual-rag-human-knowledge-v2.md` is added because the project rules require
AI/ranking outputs to have an explicit rubric record. It documents the 100-variant plus 42-family
corpus, the retrieval method, canonical isolation, API/UI safety, failure behavior, and the exact
limits of the available measurements. The central decision is to mark independent family
retrieval quality as `NOT EVALUATED`: the 42 smoke queries repeat the indexed approved names, so
using their 42/42 result as Recall or Top-1 accuracy would be leakage. The shared rubric now links
both the canonical scored evaluation and this separate v2 safety assessment.

The feature requirements, design, task list, main MVP brief, README, decision record, accumulated
evidence, and main QA review are updated from “final QA pending” to implemented and verified. These
changes give future reviewers one consistent state and make T48—not another T47 subtask—the clear
next dependency. Historical T47.1–T47.3 evidence remains intact so the sequence of decisions and
test-count growth can still be audited.

### Verification method and why it was selected

The QA uses three complementary evidence classes. First, executable tests exercise positive and
negative behavior: 184 unit, integration, API, evaluation, data, and UI tests passed. Second,
deterministic builders re-read the frozen artifacts and compare freshly constructed bytes, proving
the long external-data chain remains internally consistent. Third, a baseline diff compares the
implemented T47 feature with pre-T47 commit `785bb8d`, directly checking that prohibited canonical,
benchmark, calibration/policy, migration, and PostgreSQL implementation paths did not change.

This layered method was selected instead of relying only on the full test count. Tests demonstrate
behavior but do not automatically prove that a forbidden data file was untouched; a Git scope diff
does. Conversely, a clean diff cannot prove runtime behavior; service/API/UI tests do. The frozen
canonical evaluation supplies a third independent regression signal for the first RAG, while the
family smoke matrix tests only the second-RAG wiring.

Evaluation reports were generated in a temporary directory instead of overwriting checked-in
reports. T47 did not change the canonical benchmark or policy, so replacing historical report
artifacts merely because timing samples naturally vary would create noise and imply a new model
release. The fresh temporary report is used as QA evidence while the immutable catalog and
benchmark SHA-256 values remain the authoritative comparison.

### Detailed execution results

The fresh inventory contained exactly 100 provisional variants and 42 review families, totaling
142 documents with 142 unique IDs and UUIDs. Every approved brand/family exact query recovered its
expected document within Top-5; worst rank was 2. The existing BMW M3 GT2 result stayed a
`provisional_variant` at rank 1. Proton Saga appeared as a `review_family` debug candidate while the
canonical status remained `no_match` with null ID.

The complete suite passed 184/184 in 1.423 seconds. The deterministic chain passed fixture and
100-row pilot validation; pilot review; base queue; priority-one evidence and decision; five
research batches; five cumulative priority-two decision checkpoints; the 42-new / 4-merge / 7-hold
family registry; and the 42-document runtime projection. Python compilation, JavaScript syntax,
default and PostgreSQL-profile Compose parsing, and whitespace checks also passed.

The fresh 21-case synthetic canonical report preserved Recall@25 `1.0`, Top-1 `1.0`, hard-negative
accuracy `1.0`, precision `1.0`, false-match rate `0.0`, and coverage `0.8333`. Its direct-pipeline
p95 was `2.3898 ms`; warmed in-process HTTP/ASGI p95 was `2.675 ms`. These timings exclude Docker,
TCP, PostgreSQL, concurrent load, and production infrastructure and are recorded only as fixture
smoke evidence.

Diff inspection from `785bb8d` through the implemented T47 commit `d4fad68` found no change in
`data/catalog.json`, `data/benchmark.json`, calibration/policy artifacts or implementation,
migrations, or PostgreSQL implementation. The family projection retained SHA-256
`8615cbb99b453673599e1f9baf54f6900314d7ba64e53a31ea7891c71810b9d7`.

The first data-chain invocation stopped at its second command because that batch had not exported
`PYTHONPATH=src`, so the validator could not import the local package. This was an invocation error,
not a failed product assertion. The environment was corrected and the complete chain was restarted
from its beginning; every stage then passed. The only remaining suite message is the already known,
non-failing environment-wide Starlette legacy-`httpx` warning. Ruff and MyPy are unavailable in the
host environment, so neither is claimed as completed evidence.

### Remaining risk and next step

T47 is complete, but the second RAG's family accuracy remains deliberately unknown. Exact approved
names are useful for proving that all documents can be found; they do not tell us how misspellings,
seller abbreviations, extra release details, related casting names, or unseen noisy titles behave.
That is the most important unresolved risk because scaling a weak retrieval policy to PostgreSQL or
3,000 rows would make errors larger and harder to diagnose.

The recommended next task is T48: design and freeze an independently authored, casting-grouped
family holdout dataset, define metrics and error categories, and evaluate the current sparse /
`hashing-v1` / RRF second RAG without using the indexed names as its answers. T49 PostgreSQL and
pgvector measurement should proceed only after that quality result is understood; additional yearly
catalog ingestion follows those gates.

## 2026-09-11 — Family evidence becomes visible without being mistaken for a variant

### What was executed and what problem it solves

T47.3 completes the public debug boundary for Human Knowledge RAG v2. T47.2 already searched one
combined pool of 100 provisional variants and 42 review families, but the response model still
required variant-specific IDs. Its temporary serializer therefore hid family results to avoid
claiming that an accepted casting family was a reviewed release variant. That was safe, but it made
the new family retrieval impossible to inspect through the API and browser console.

The debug response can now carry both knowledge levels in their honest forms. Every item declares
either `knowledge_type=provisional_variant` or `knowledge_type=review_family`. A Proton Saga query
returns a family suggestion with its review-family identity, alias, and source references; it does
not receive casting/variant UUIDs that do not exist. The same request still ends as canonical
`no_match` with null canonical ID and UUID. The second RAG is therefore more observable without
gaining authority over the first/canonical RAG.

### Code changes, affected components, and reasons

`src/product_variant_resolver/schemas.py` replaces the single variant-only debug model with two
strict Pydantic models. A shared base contains only fields that genuinely apply to both document
types: review status, brand/casting display data, sparse/dense/RRF evidence, and matched tokens.
`HumanVariantKnowledgeCandidateDebug` adds casting and provisional-variant identities plus reviewed
label/example/case data. `ReviewFamilyKnowledgeCandidateDebug` instead adds review-family identity,
approved aliases, and source-record provenance. An annotated union uses `knowledge_type` as its
discriminator, so validation and generated OpenAPI describe the same two legal shapes. The debug
payload also gains `review_family_knowledge_version`, allowing a captured response to identify the
exact frozen family projection that produced it.

`src/product_variant_resolver/service.py` removes the T47.2 family filter. It first takes one slice
of the combined ranked candidates using `debug_candidate_limit`, then passes every candidate in
that slice to a type-aware converter. The converter constructs the matching strict model and raises
on any unsupported internal type. Slicing before conversion preserves one comparable ranking and
one bound across both sources; it avoids two lists that could each return the full limit. Explicit
construction also means no generic dictionary can quietly leak fields from one identity level into
the other.

`ui/index.html` renames the section to Human-knowledge candidates, adds a Type column, and states
that neither provisional variants nor review families can become the final answer. `ui/app.js`
branches only on the API discriminator. Variant rows retain their existing reviewed name and
series/variant text. Family rows use approved aliases and display `family only — variants
unreviewed`, making the missing variant a deliberate review state rather than an empty or fabricated
value. The catalog label now shows both the human catalog and family projection versions.

`tests/api/test_api.py` verifies both branches end to end. It checks family-only and variant-only
fields are absent from the opposite type, the family projection version is present only inside
debug, the combined list obeys a one-result limit, Proton Saga remains noncanonical, and OpenAPI
publishes the expected discriminator mapping. `tests/ui/test_debug_ui.py` supplies both candidate
types to the DOM harness and verifies their labels, family-only wording, version display, and table
shape. Markup-looking strings are placed in both a variant human label and family alias and remain
literal text.

### Technology and method choices, alternatives, and trade-offs

A discriminated union was selected instead of one large model containing many optional fields.
The optional approach would make contradictory payloads technically valid—for example a family
with a provisional-variant UUID, or a variant with only a family ID—and clients would have to infer
the intended shape from missing values. The discriminator gives FastAPI/OpenAPI clients one stable
switch and lets each branch keep its own required fields. A small inherited ranking base avoids
duplicating common evidence while still keeping identity fields separate.

The existing `human_knowledge_candidates` list and request limit were retained rather than adding a
second `review_family_candidates` list. Both document types already compete inside one RRF ranking;
splitting the response after ranking would obscure their relative position and could accidentally
double the amount of debug data. The trade-off is that a small limit may show only one type for a
particular query, which is the correct representation of the shared ranking rather than guaranteed
type quotas.

The UI continues to use DOM element creation and `textContent` rather than template strings or
`innerHTML`. Family aliases originate from externally researched data, so treating them as inert
text is a trust-boundary decision, not only a display preference. This approach is more verbose than
building an HTML string but makes markup-shaped data unable to create elements or event handlers.

### Decision and runtime impact

D31 is now implemented through projection, combined retrieval, and public debug presentation. The
change affects diagnostic output only. It does not change the 120-product canonical catalog,
canonical retrieval/ranking, calibration model, policy thresholds, confidence computation,
PostgreSQL schema/data, or evaluation ground truth. Family objects remain excluded from the final
identity path, and requests with `debug=false` still omit the entire debug object and all associated
knowledge/version metadata.

### Verification evidence

Seventeen focused API/UI tests passed in 0.277 seconds. Runtime assertions confirmed the two exact
response shapes, one shared result bound, generated OpenAPI mapping, family version metadata,
default omission, family/canonical isolation, existing variant behavior, loading/error states, and
text-safe rendering. The complete host suite passed 184/184. The suite's existing environment-wide
Starlette legacy-`httpx` deprecation warning remains non-failing and was not introduced by this
change.

### Incomplete work, risks, and next step

The implementation makes family suggestions inspectable; it does not prove they generalize to noisy
or unseen marketplace titles. The current 42-query result is exact-name self-retrieval against the
same family names used to build the index. Shared words can still retrieve unrelated families, so
it is not an accuracy claim and cannot justify canonical promotion, PostgreSQL rollout, or the
planned roughly 3,000-row expansion.

The next task is T47.4, the final Lite verification/documentation closure. It will rerun the entire
deterministic data chain and frozen canonical evaluation, map every FHK requirement to measured
evidence, close the feature review, and verify the repository diff remains within the Product
Variant Resolver folder. Only after that gate should T48 create an independently authored,
casting-grouped family retrieval evaluation.

## 2026-09-11 — Human Knowledge RAG v2 now searches 100 variants and 42 typed families

### What was executed and what problem it solves

T47.2 activates the frozen T47.1 family projection inside the second RAG. Before this change, the
Human Knowledge retriever understood only provisional variants and used their UUID field directly
as its index key. Passing a family through that shape would require a nonexistent variant ID and
would blur the boundary between an accepted casting family and an unreviewed release variant.

The runtime now loads 100 existing provisional-variant documents and 42 review-family documents as
two distinct internal types, then searches all 142 through one hybrid ranking pool. A family hit is
still review evidence only: the canonical retrievers, RRF, calibration, policy, confidence, and
response identity continue to operate exclusively on the 120-product canonical fixture catalog.
The `Hot Wheels Proton Saga` verification demonstrates the separation: the family is retrieved in
the human pool while the API remains `no_match` with null canonical UUID/ID and product.

### Code changes, affected components, and reasons

`src/product_variant_resolver/human_knowledge.py` now defines
`HumanVariantKnowledgeDocument` and `ReviewFamilyKnowledgeDocument`. Both expose common read-only
properties—`knowledge_type`, `knowledge_id`, `knowledge_uuid`, and `searchable_text`—without placing
family data into variant fields. The existing variant type retains casting and provisional-variant
IDs, series/variant labels, human names, pricing terms, initial names, and source cases. The family
type contains only its review identity, approved name/alias, and source-record provenance.

The same module adds a strict projection/manifest loader. It checks the exact schema/version,
projection checksum, allowed top-level/document/source fields, input references, 42/4/7 and
79/9/12 accounting, zero variant/canonical/PostgreSQL fields, debug-only eligibility, all exclusion
boundaries, source revision/license, UUIDv5 identity, deterministic order, alias policy, source-ID
format/uniqueness, and global knowledge ID/UUID uniqueness. The service cannot construct unless it
receives exactly 100 variant plus 42 family documents.

Sparse scoring, 192-dimensional `hashing-v1` dense scoring, and RRF now key both types by the common
knowledge UUID. This replaces every former direct reference to `provisional_variant_uuid` in the
index/ranking algorithm while leaving its formula and limit unchanged. The resulting index reports
`human-knowledge-hybrid-v2`.

`config.py`, `.env.example`, `Dockerfile`, and `docker-compose.yml` add explicit projection and
manifest paths. This makes local, environment-configured, and container startup follow the same
dependency contract instead of relying on an implicit current working directory.

`service.py` loads both frozen family files during construction and records bounded total, variant,
and family candidate counts on the existing human-retrieval trace span and privacy-safe completion
log. `api.py` exposes a `review_family_knowledge` readiness dependency with the projection version
and the explicit description `family-only review suggestions; never canonical identity`. Missing
or corrupt input prevents service construction, so health and resolve return 503 without identity.

The public `HumanKnowledgeCandidateDebug` model is intentionally unchanged in this task because it
requires provisional-variant fields. The transitional serializer therefore emits only variant
instances from the already bounded combined results. It does not coerce family IDs into variant
IDs, use null placeholders, or create a second unranked response list. T47.3 will replace this
temporary compatibility boundary with the specified discriminated union and safe UI rendering.

Tests now cover environment path selection, strict family loading, exact 100/42/142 counts, 142
unique IDs/UUIDs, all 42 exact family queries, searchable-field isolation, merge/hold absence, the
existing BMW regression, family/noncanonical service behavior, health versions, missing/corrupt
readiness, transitional debug safety, and privacy-safe per-type trace counts.

### Technology and method choices, alternatives, and trade-offs

Two frozen dataclasses plus a union were chosen over one large optional-field record. An optional
record could technically hold both types, but it would make invalid states—such as a family with a
variant ID or a variant without one—representable. The common properties give the ranking algorithm
the small interface it needs while each identity type keeps mandatory, meaningful fields.

The current deterministic sparse/hashing/RRF stack is reused rather than adding a neural embedding
model or a second family-only index. Reuse isolates the effect of the new data and preserves offline
operation. One shared pool also gives variant and family evidence comparable ranks under one limit;
separate indexes would need another fusion policy before their results could be meaningfully mixed.
The trade-off is changed human-pool document frequency and rank order, which is accepted only with
the BMW regression and 42-query smoke matrix and still requires independent T48 evaluation.

Loader validation is deliberately stricter than ordinary permissive JSON parsing. This artifact is
a trust boundary derived from external data, and silently accepting extra searchable fields or a
wider eligible-use list could connect held evidence to runtime. Future legitimate schema or alias
changes therefore require a visible version update. This increases upgrade work but makes accidental
scope expansion fail during readiness rather than silently changing search behavior.

The transitional family filter was chosen instead of implementing part of T47.3 inside this task.
Returning family objects through the current Pydantic model would either fail serialization or
fabricate variant fields. Filtering keeps the v2 internal integration testable and safe, but family
suggestions are not yet visible to API/UI users. That temporary limitation is explicit and removed
by the immediately following task.

### Decision and runtime impact

D31 is now implemented through its data-loading and retrieval layers. The second RAG has moved from
100 variant documents on v1 to a 142-document typed v2 index. The first/canonical RAG, canonical
catalog, final decision path, calibration artifacts, policy thresholds, PostgreSQL schemas/data,
and evaluation labels are unchanged. Family projection failure is now a required readiness failure
rather than a fallback to the older 100-document index.

### Verification evidence

Thirty-five focused tests passed in 0.635 seconds. The two existing UI harness tests also passed
after their model-version fixture moved to v2. The complete host suite passed 182/182 in 1.712
seconds. Runtime inspection found 100 variant documents, 42 family documents, 142 unique IDs and
UUIDs, 42/42 exact family queries within Top-5 with worst rank 2, and the BMW provisional variant at
rank 1. Proton Saga remained canonical `no_match` with null identity.

The canonical fixture evaluation remained Recall@25 `1.0`, Top-1 `1.0`, hard-negative accuracy
`1.0`, precision `1.0`, false-match rate `0.0`, and coverage `0.8333`. Python compilation,
projection/registry deterministic checks, fixture validation, Docker Compose configuration, and
whitespace checks passed. MyPy and Ruff were unavailable on this host, so neither is reported as a
passing gate. The only suite warning is the already documented machine-wide Starlette legacy-
`httpx` TestClient warning.

### Incomplete work, risks, and next step

The family candidates are now searched but remain intentionally hidden from the legacy debug
schema. This is safer than returning false variant fields, but it means v2 retrieval is not yet
fully observable through the public API or browser UI. Exact-name self-retrieval also remains only
a wiring smoke test; shared generic words can still surface unrelated families.

The next task is T47.3: add a Pydantic discriminated union, expose the family projection version in
debug responses, render variant and family candidates distinctly with text-safe DOM operations,
and prove default responses and markup-shaped external values remain safe. T47.4 then performs the
final Lite QA/evidence closure before T48 independent evaluation or any PostgreSQL/3,000-row work.

## 2026-09-11 — The accepted family layer becomes a frozen, debug-only knowledge projection

### What was executed and what problem it solves

T47.1 implements the first confirmed family-level second-RAG task. The T46 registry deliberately
mixes three review outcomes—42 new family identities, 4 links to existing human families, and 7
holds—and carries detailed decision and release evidence. Loading that audit object directly would
make held or variant-level material available to runtime code and would contradict the registry's
own `excluded_from=runtime_retrieval` boundary.

The new builder derives a separate 42-document knowledge projection. It accounts for all 53 family
decisions and all 100 Wiki release references before selecting only the 42 accepted creations. The
result retains 79 accepted source-record IDs as non-searchable provenance and creates zero
provisional variants, canonical promotions, and PostgreSQL rows. This gives T47.2 a small, explicit
runtime input without changing the running Dual-RAG system yet.

### Code and data changes, the affected parts, and why

`scripts/build_review_family_knowledge.py` is the new trust boundary between audit data and future
retrieval data. Its input validator checks the registry and manifest filenames, schemas, versions,
checksum, identity namespace, 42/4/7 family accounting, 79/9/12 row split, 100 unique release
references, and zero-promotion constraints. Every projected family must also keep its source-stable
UUIDv5, family-only identity level, accepted/unreviewed status, normalized family key, and explicit
`create_new_casting` decision with variants still held.

The builder does not copy whole registry entries. It constructs each document from an explicit
nine-field allowlist: type, family ID/UUID, identity level/status, brand, casting, aliases, and
source-record IDs. Only brand, casting, and aliases are declared future searchable fields. Release
objects, toy and collector numbers, series, variant notes, decision reasons, and evidence URLs are
therefore absent by construction rather than relying on later code to remember to ignore them.

`data/review_family_knowledge.json` contains the 42 sorted documents. Its companion manifest freezes
both T46 input hashes, the projection hash, allowed document/search fields, permitted debug-only
use, forbidden canonical/evaluation/PostgreSQL uses, 42/4/7 family counts, 79/9/12 row counts, and
the original 100-row source total. Because the projection is a generated artifact, it contains no
build timestamp; the same inputs reproduce identical bytes.

`tests/test_review_family_knowledge_projection.py` adds six tests around the trust boundary. The
positive cases verify exact selection, unique IDs/UUIDs, the field allowlist, all 79 accepted source
references, frozen checksums, and byte reproduction. Negative cases mutate checksums, family count,
UUID, aliases, eligibility, exclusions, and output freshness. The overwrite test preloads known-good
files and proves both an invalid build and a failed `--check` leave those bytes untouched.

### Technology and method choices, alternatives, and trade-offs

The implementation uses the Python standard library rather than adding a data-build dependency.
`json.dumps(..., sort_keys=True)` plus sorted documents/aliases/source IDs provides deterministic
serialization; SHA-256 connects each output to exact inputs; UUIDv5 validation confirms identity is
derived from the immutable review ID rather than editable display text. T46 v1 permits exactly the
display name as its sole alias; accepting an added alias under the same version would silently widen
retrieval language, so the builder rejects it and requires a future reviewed version change.
Temporary files are fully written and `fsync`ed before `os.replace`, so validation failures never
truncate accepted outputs.

An alternative was to put a `searchable_text` string inside every document. That would duplicate
normalization policy and could let a future builder accidentally append evidence or release fields.
The projection instead freezes the three searchable source fields and leaves text construction to
the strict loader planned for T47.2. Another alternative was to copy the T46 registry and filter it
at query time; that would enlarge the trusted runtime surface and make a forgotten filter capable
of indexing holds. The smaller allowlisted projection makes the safe state observable in the data
itself.

Atomic replacement is performed per output file rather than through a database transaction. That
is appropriate for two checked-in local artifacts because the manifest checksum detects any
interrupted or mixed pair at the next `--check`/load. T47.2 will fail readiness on such a mismatch.
No PostgreSQL write is used here because persistence would combine an identity-boundary change with
an unevaluated retrieval and scaling decision.

### Decision and runtime impact

D31 moves from proposal to partial implementation: the separate projection is now real and frozen,
but the proposed 142-document index is not. Configuration, service construction, human-knowledge
models, API schemas, health output, UI, canonical ranking, confidence, calibration, and database
contents are unchanged. The currently running second RAG therefore still contains only the 100
human-backed provisional variants and still reports its v1 index.

### Verification evidence

The builder produced exactly 42 documents and its non-mutating check reproduced both outputs. Six
focused tests passed in 0.150 seconds. Python compilation, the T46 registry check, the fixture
validator, and a 100-character source-line check passed. The complete host suite passed 174/174 in
1.612 seconds. It emitted only the already documented non-failing Starlette legacy-`httpx`
TestClient warning; this task changes no web dependency. Ruff was unavailable in the host
environment, so no Ruff result is claimed.

### Incomplete work, risks, and next step

The projection is deliberately dormant. Until T47.2 adds strict loading and manifest validation,
these 42 documents do not participate in retrieval and cannot appear in debug output. The 79 source
references establish provenance but do not prove any release variant. The earlier exact-name
simulation is still a wiring smoke result rather than independent search-quality evidence.

The next task is T47.2: add settings, typed variant/family document models, strict projection
readiness, and one combined 142-document sparse/hashing-dense/RRF index while proving that all human
candidates remain outside canonical identity and confidence. API/UI discrimination stays in T47.3;
independent retrieval quality remains T48, before PostgreSQL or the roughly 3,000-row expansion.

## 2026-09-11 — Family-level second-RAG integration is specified as a typed projection

### What was executed and what problem it solves

T47 analyzes how the 42 stable T46 review-family identities can become useful search suggestions
without being mislabeled as variants or allowed to affect canonical answers. The current second RAG
contains 100 human-confirmed provisional-variant documents; every internal document and debug item
requires a provisional variant ID. Reusing that shape for family-only knowledge would reintroduce
the exact fabricated-variant problem T46 avoided.

The new Lite specification defines a separate family-knowledge runtime projection plus a typed v2
human-knowledge index. The projection selects only 42 accepted new families. Four merge links do not
become new documents because their existing human-backed families are already searchable; seven
holds and all held release details remain outside the index. This resolves the schema and ingestion
design question while preserving current runtime until the owner confirms implementation.

### Code and documentation changes and why they were made

`specs/family-level-human-knowledge/requirements.md` adds sixteen EARS requirements covering a
deterministic runtime projection, exact selection, searchable-field allowlisting, typed documents,
unified retrieval, exact-name smoke and existing-variant regression, hold/merge behavior, canonical
isolation, debug API/UI, readiness, observability, persistence/evaluation limits, and reproducibility.

`design.md` maps those requirements to the current implementation. It identifies affected settings,
loader/retriever, service, API health, Pydantic schemas, UI, and tests. It defines
`pvr-review-family-knowledge-v1`, the `provisional_variant` / `review_family` discriminated debug
union, a single 142-document sparse/dense/RRF pool, projection/version fields, fail-closed startup,
safe UI rendering, and the absence of any edge from human candidates to canonical policy.

`tasks.md` separates the future build into four bounded units: projection generation, typed v2
retrieval/readiness, debug API/UI integration, and QA/documentation. Every FHK requirement is mapped
to at least one implementation or verification task. The main MVP brief, QA review, README,
decision register, and T47 spec evidence now link the same proposed boundary.

### Technical choices, alternatives, and trade-offs

The T46 registry will not be loaded directly. It is an audit artifact that intentionally contains
hold explanations and held release provenance and declares itself excluded from runtime retrieval.
Rewriting that artifact would invalidate its frozen evidence; loading it would risk making
non-searchable fields available to future code. A small allowlisted projection creates a new,
explicitly authorized runtime contract while leaving adjudication history immutable.

The two document types will share one human-knowledge index and one result limit. A separate family
retriever/list would minimize changes to the existing variant schema, but callers could not compare
its ranks with variant ranks and the UI would need two competing second-RAG sections. A discriminated
union retains type-correct fields while one sparse/dense/RRF pool provides deterministic ordering.

Family searchable text is restricted to brand, approved name, and aliases. Source record IDs remain
available as bounded debug provenance but do not affect scoring. Series, toy numbers, variant notes,
decision reasons, evidence URLs, and held names are excluded because none was approved as family-
level search language.

The current hashing-v1 embedding and RRF algorithm are retained instead of selecting a neural model
or new ranker. The purpose of T47 is safe wiring, and the existing deterministic method makes change
effects traceable. A new model would mix identity integration with an unmeasured algorithm change;
T48 exists to determine whether stronger retrieval is actually needed.

### Decision changes

No family, variant, canonical, or database decision changes. The new architectural proposal derives
a 42-document runtime projection from T46 rather than making the T46 registry itself runtime data.
The projected families and existing variants become typed peers inside the second RAG, but remain
debug-only and completely outside canonical confidence and identity.

T47 is complete only as a proposed specification. Runtime implementation, API/UI changes, and data
projection generation remain blocked by the Lite G1* confirmation step.

### Verification evidence

A read-only simulation used the current `HashingEmbedding`, sparse scoring, and RRF formulas over the
100 existing human variant documents plus the proposed 42 family documents. All 142 UUIDs were
unique. All 42 exact `Hot Wheels + family name` queries recovered the intended family within Top-5;
the worst rank was 2. The existing BMW M3 GT2 Neon Speeders provisional variant remained rank 1,
and the `'67 Chevy C10` merge query continued to return its existing variant without a duplicate
family document.

The same simulation showed the most important unresolved risk: `Power Wheels Dune Racer` did not
return a held Power Wheels identity—none exists—but shared `racer` language could return another
accepted family. This is not a contract violation, yet it demonstrates why self-retrieval cannot be
reported as quality. T48 must measure false and useful suggestions on independently written queries.

No product code or data changed. A fresh complete host run passed 168/168 tests in 1.628 seconds.
It emitted only the already documented Starlette legacy-`httpx` TestClient deprecation warning;
the warning is unrelated to this documentation-only change and remains non-failing. Documentation
structure, 16/16 requirement traceability, whitespace, and repository scope were also verified
before commit.

### Incomplete work, risks, and next step

The runtime projection, v2 typed loader, discriminated debug models, readiness dependency, and UI
rendering do not yet exist. Adding 42 documents will change human-source document frequencies and
may reorder debug suggestions even though canonical output remains isolated. Exact-name success on
the source labels is not evidence for noisy marketplace text.

After the project owner confirms requirements, design, and tasks, the next immediate step is T47.1:
build and freeze the 42-document family-knowledge projection. T47.2–T47.4 then integrate, render,
test, and document v2. T48 independently evaluates retrieval before T49 PostgreSQL work or expansion
toward roughly 3,000 reviewable rows.

## 2026-09-09 — Accepted family decisions become stable review entities without fake variants

### What was executed and what problem it solves

T46 implements the owner-confirmed family-materialization contract. Before this step, the 42
accepted `create_new_casting` outcomes existed only inside a long adjudication queue; they had
decisions and evidence but no standalone, database-compatible review identity. The new registry
makes those family concepts directly inspectable and reproducible without claiming that any of the
100 associated Wiki releases has been reviewed as a variant.

The generated result contains 42 new family entities over 79 source rows, 4 links to existing
human-backed families over 9 rows, and 7 explicit hold exclusions over 12 rows. Every source row is
represented exactly once and remains `held_for_variant_review`. The registry therefore closes the
family-identity materialization gap while keeping the release-level backlog visible.

### Code changes and why they were made

`build_review_family_registry.py` verifies six inputs before building: the final adjudicated queue,
its manifest, the normalized 100-row staging dataset, its source manifest, the 97-family human-
backed catalog, and its manifest. It checks filenames, versions, SHA-256 values, queue completion,
source revision/license, family/row accounting, decision vocabulary/scope, promotion hold, exact
staging-row equality, and existing human-family identities. This prevents a stale or hand-edited
input from quietly becoming a new identity registry.

For each accepted creation, the builder reuses `family_review_id` as the public review ID and derives
a UUIDv5 from the fixed `product-variant-resolver:review-family:fandom-hot-wheels-wiki` namespace.
For each accepted merge, it resolves the exact existing human `casting_id` and `casting_uuid` and
does not mint another UUID. Holds retain names, reasons, evidence, and release references with
`retrieval_eligible=false`.

The builder emits `data/review_family_registry.json`, a checksum/count manifest, and a readable
Markdown report. JSON serialization and list order are deterministic and have no build timestamp.
Write mode fully validates and prepares all content before replacing outputs; `--check` builds
expected content in memory and compares all three files without writing.

`test_review_family_registry.py` adds nine tests. They verify exact 42/4/7 family and 79/9/12 row
splits, unique UUIDv5 values, one approved alias per new family, exact merge targets, all seven named
holds, 100 unique held releases, complete decision/source provenance, frozen hashes, deterministic
reproduction, and non-mutating check mode. Mutated checksum, partial queue, widened variant scope,
duplicate source row, missing merge target, and collision with an existing human family all fail.

`validate_fixture_data.py` now treats the registry and manifest as part of project-wide integrity.
It repeats the high-value checksum, counts, UUID, alias, merge-target, hold, source provenance, row
coverage, and zero-promotion/index/persistence checks so routine validation cannot ignore the new
artifact.

### Technical choices, alternatives, and trade-offs

UUIDv5 was selected instead of random UUIDv4 because identical reviewed input must yield identical
identities on every machine. The UUID input excludes display name and registry version: punctuation
or a future label correction can change presentation without replacing identity, while a genuinely
different source family keeps a different immutable review ID.

The registry keeps full release references—including year, toy/collector number, series position,
and variant note—but none becomes an alias or variant object. Discarding them would lose the path to
later release review; indexing them now would make unverified release details influence search.
Keeping them as held provenance supports future work without weakening today's claim.

All seven holds appear in the registry as exclusions rather than being omitted. Omission would make
the 100-row accounting incomplete and allow a future importer to rediscover the same unsafe names.
Conversely, an exclusion cannot be indexed. Power Wheels Dune Racer therefore remains visible as a
renamed-lineage problem without silently becoming a Bogzilla alias.

The outputs are prepared in temporary sibling files and then replaced after validation. This is
safer than writing each artifact incrementally and meets the invalid-input preservation goal. It is
not described as a multi-file database transaction: an operating-system or power failure between
final replacements remains a recoverable stale-output condition detected by `--check`.

Runtime integration remains deliberately separate. Extending the existing variant-based
`HumanKnowledgeDocument` now would combine data materialization with API/debug schema and ranking
changes. T46 gives that future work a stable, validated input while keeping the currently proven
Dual-RAG path unchanged.

### Decision changes

The T45 proposal is now owner-confirmed and implemented. The 42 accepted families change from
decision-layer concepts to stable review-family entities; the 4 merges become explicit links. This
does not change their family decisions, and the 7 holds remain non-materialized exclusions.

No release changes from hold to accepted. No canonical or existing human-backed runtime identity is
rewritten. Provisional-variant creation, canonical promotion, runtime indexing, and PostgreSQL row
creation all remain exactly zero.

### Verification evidence

The focused registry suite passed 9/9. The complete host suite passed 168/168 in 1.500 seconds on
Python 3.14.6; only the already documented legacy-`httpx` TestClient warning appeared. The project
fixture and Wiki pilot validators, review/base queue/priority-one chain, all five research batches,
all five priority-two decision checkpoints, registry `--check`, Python compilation, default and
PostgreSQL Compose configurations, and whitespace check all passed.

Registry SHA-256 is
`3f289b802cc2e8280ed5c3586d87cfabbee7ce37b10ae79504b5aa6b8837367d`; manifest SHA-256 is
`ae9eda741aa2ec7cb9354424e17b789ba73c05890859e73d19cd845c5cab3ff2`; readable report SHA-256 is
`5312f2b86b3209c815def09417628a0248a8e50251f88ec3a48aeb7ed03203b5`. The combined fixture
checksum including the registry is
`2c72ca83a74e090d8e89e6df124fb1520355643fd8629f71535f099269d45972`.

### Incomplete work, risks, and next step

The family registry is not loaded by `src/product_variant_resolver`; it does not alter current
Dual-RAG candidates, API responses, health state, or PostgreSQL. The 100 release references still
need separate variant review, and the seven held family names still need tool- or lineage-qualified
decisions. Text-source evidence may contain upstream inaccuracies.

The next immediate task is T47 specification: define a distinct family-level human-knowledge
document, its debug fields, ranking inputs, hold exclusion, readiness checks, and the invariant that
a family suggestion can never populate canonical identity. Only after implementation and an
independent casting-grouped holdout evaluation should this registry be considered for PostgreSQL or
the expansion toward roughly 3,000 reviewable rows.

## 2026-09-09 — Family materialization is specified without inventing variants

### What was executed and what problem it solves

T45 turns the post-adjudication question—“how do 42 accepted family decisions become usable
entities?”—into a Lite specification that can be tested before data is changed. The final queue has
complete family decisions, but its 100 release rows still lack variant-level approval. The new
requirements, design, and task plan make that distinction executable instead of leaving the next
developer to infer it from prior reports.

The specification accounts for the complete queue: 42 accepted new-family outcomes covering 79
source rows, 4 accepted merges covering 9 rows, and 7 holds covering 12 rows. A read-only comparison
against the 97 existing human-backed families found no exact normalized collision for the 42 new
names, and the proposed readable labels do not collide with each other. These checks support the
current packet but are not used as the permanent identity mechanism.

### Code and documentation changes and why they were made

`specs/review-family-materialization/requirements.md` adds thirteen EARS-style requirements. They
cover frozen input verification, the closed decision vocabulary, stable family identities, merge
links, hold exclusion, conservative aliases, complete provenance, deterministic output, exact
accounting, fail-closed validation, runtime/database boundaries, and a non-mutating check mode.

`design.md` defines a separate `pvr-review-family-registry-v1` with three sections: 42 new entities,
4 merge links, and 7 hold exclusions. Accepted source releases are stored only as
`held_release_references`; the schema intentionally has no `provisional_variants` field. It also
defines CLI inputs/outputs, UUIDv5 identity, manifest fields, a ten-stage build algorithm, atomic
write behavior, security constraints, and test coverage.

`tasks.md` breaks the next implementation milestone into builder/artifact work, fail-closed
validation/tests, and QA/documentation. The main MVP brief marks T45 complete only as a proposed
specification and leaves T46 implementation pending owner confirmation. The QA review, decision
register, and this log now point to the same boundary and measured 42/4/7, 79/9/12 totals.

### Technical choices, alternatives, and trade-offs

The key choice is a separate family registry rather than adding rows directly to
`human_backed_catalog.json`. The existing catalog contains 97 castings and requires each one to have
at least one human-confirmed provisional variant. Creating an `unclassified` placeholder for each
Wiki family would be convenient for the current loader, but it would fabricate 42 variants and make
family approval look like release approval. Allowing empty variant arrays would weaken an existing
fail-closed invariant and still leave runtime document semantics unclear.

The immutable `family_review_id` is reused as the public review ID. A UUIDv5 derived from a fixed
project/source namespace plus that ID provides a database-compatible key. Display names and slugs
are excluded from identity derivation because names may later need punctuation corrections or tool-
qualified disambiguation; using them would either change identity after correction or collide as
the dataset grows.

The four merges do not receive new UUIDs. They link to the already frozen human catalog family,
which avoids duplicating one casting under a second source-specific identity. The seven holds remain
visible as audit exclusions but cannot be indexed. In particular, Power Wheels Dune Racer is not
silently added as a Bogzilla alias because the owner authorized a hold, not a merge.

The specification stops before Dual-RAG and PostgreSQL. Bundling those changes could make progress
appear faster, but it would combine data identity, API/debug semantics, retrieval quality, schema
migration, and scale testing in one difficult-to-audit change. The Lite sequence keeps each question
small: establish stable review entities first, then design family-level retrieval, evaluate it, and
only afterward persist/scale it.

### Decision changes

No T44 family decision changes. The new decision is architectural: accepted family-only outcomes
will be materialized in a dedicated review registry, not as fake provisional variants or immediate
PostgreSQL products. The 42 creates remain accepted, the 4 merges retain their existing targets, the
7 holds remain excluded, and all 100 release references remain held.

T45 is complete as a specification proposal, not as implementation approval. The project owner must
confirm the three spec documents before T46 begins, as required by the Lite spec gate.

### Verification evidence

Static inspection verified the current queue is `adjudicated` with 53 completed and zero pending
families. Recomputed partition counts are 42 create, 4 merge, and 7 hold; source-row totals are 79,
9, and 12 respectively and sum to 100. The 42 proposed creations have zero exact normalized
brand/casting collisions with the 97 existing human-backed families and zero collision under the
current readable-ID form.

No product code or data artifact changed. A fresh complete host rerun still passed 159/159 in 1.418
seconds; the machine-wide Python 3.14 interpreter emitted only the already documented legacy-`httpx`
TestClient warning. Documentation whitespace and repository-scope checks passed. An explicit
traceability table maps all thirteen RFM requirements to implementation and verification tasks and
records deferred Dual-RAG, evaluation, PostgreSQL, and approximately 3,000-row work.

### Incomplete work, risks, and next step

The specification has not yet been confirmed by the project owner, and
`build_review_family_registry.py` does not exist. UUID namespace spelling, output filenames, and
the family/merge/hold model become implementation contracts only after confirmation. External text
sources may still contain errors, and a family-level identity remains weaker than a physically
verified release variant.

After confirmation, the next immediate task is T46.1: implement the deterministic registry builder
and generate its three checksum-frozen artifacts. T46.2 will add fail-closed tests and validation;
T46.3 will run QA and document measured results. Runtime Dual-RAG integration remains T47 rather
than being assumed by registry creation.

## 2026-09-09 — Final owner decisions close family review while all variants remain held

### What was executed and what problem it solves

T44 converts the project owner's request to proceed into a durable decision record for the exact
final T43 packet. The packet was already bounded to nine families and disclosed as six machine
creation recommendations plus three evidence-based holds. Storing the response in the repository
solves two problems: the decision no longer depends on transient conversation history, and the
system can distinguish a human-authorized family outcome from the preceding machine research.

The accepted creation outcomes are Proton Saga, Small Bloc, Super Twin Mill, The Vanster, Twin Mill
Gen-E, and X-34 Landspeeder. Nissan Skyline GT-R (BNR32), Power Wheels Dune Racer, and Standard Kart
remain held. The cumulative queue is now closed at family scope: all 53 families have outcomes,
including 4 existing-family merges, 42 accepted new-family decisions, and 7 holds. This resolves
the current 100-row pilot's family-review backlog without pretending that its release variants are
ready for production.

### Code changes and why they were made

`priority-2-batch-05-decisions.json` is the human authority layer. It copies the exact frozen T43
recommendations, names the project owner as decision maker, timestamps the decision, retains every
source reference, and explicitly limits scope to family decisions. Decision data stays separate
from both machine research and generated output so that provenance can be inspected and invalid
input can be rejected instead of silently rewriting history.

`apply_fandom_priority_two_decisions.py` now routes `--batch 5` from the batch-04 cumulative queue
through a new versioned result. The generic result-status rule reports `adjudicated` only when no
family remains pending; earlier checkpoints continue to report `partially_adjudicated`. The
readable result adds the final six accepted family names, the three retained holds and their
reasons, and the explicit statement that the 53-family queue is complete while release variants
remain held.

The generated cumulative queue, manifest, and Markdown result are checked in as reproducible build
artifacts. `test_fandom_priority_two_decisions_batch_five.py` adds six tests for the exact nine-
family packet, exact six-create/three-hold split, 13 current release rows, all 53 accumulated
decisions, six ordered history events, family-only scope, 100 held variants, zero promotion,
frozen hashes, and deterministic regeneration. It also supplies altered, incomplete, duplicate,
and widened decision inputs and requires each to fail closed.

README, the external-data guide, MVP task brief, QA review, decision register, and T44 evidence now
use the same totals and boundary wording. This avoids a future maintainer reading “53 completed” as
“53 records inserted into PostgreSQL” or “42 new searchable products.”

### Technical choices, alternatives, and trade-offs

The final status is derived from the count of pending decisions rather than hard-coded to batch 5.
That makes the state describe the data: batches 1–4 remain partial, while any valid future terminal
queue can become adjudicated for the same reason. It avoids special-case business logic tied only
to a filename, while preserving byte-for-byte reproduction of earlier artifacts.

The three holds are accepted as completed decisions instead of being left pending. “Hold” means the
owner has decided that current evidence is insufficient or points to a conflicting identity; it is
not unfinished paperwork. BNR32 still spans a separate same-scale RLC tool, Standard Kart still
spans character-bearing and driverless tools on one page, and Power Wheels remains a renamed
Bogzilla release for which an automatic new family or silent merge would both exceed the evidence.

The six accepted creations are not written directly into `human_backed_catalog.json`, the canonical
fixture, or PostgreSQL. Immediate insertion would be faster, but it would require unmade decisions
about deterministic IDs, aliases, renamed lineages, provenance, and how family approval relates to
individual year/color/toy-number variants. A separate stable review-family contract is the smaller
and safer next design step, especially before scaling toward roughly 3,000 rows.

### Decision changes

The six T43 creation recommendations change from pending machine proposals to completed,
project-owner-attributed `create_new_casting` decisions. The three T43 proposed holds likewise
become completed owner holds without changing their evidence or reasons. No earlier family outcome
is modified; all five earlier owner batches are preserved and the new batch is appended as history
event six.

The resulting totals change from 44 completed / 9 pending to 53 completed / 0 pending. Accepted
new-family decisions increase from 36 to 42 and completed holds increase from 4 to 7; accepted
existing-family merges remain 4. Held release rows increase from 87 to all 100 because the thirteen
rows in the final packet now belong to completed family decisions but still have no variant-level
authorization. Promotion remains zero.

### Verification evidence

The focused T44 module passed 6/6. The complete host suite passed 159/159 in 1.440 seconds on Python
3.14.6. All five research packets and all five priority-two cumulative decision checkpoints
reproduce; the decision checkpoints report completed/pending totals of 14/39, 24/29, 34/19, 44/9,
and 53/0. Fixture/pilot validation, base review/queue/priority-one checks, Python compilation,
default and PostgreSQL Compose configuration, and `git diff --check` also passed.

The decision file checksum is
`a5dc269b2ced7b8423fd0cf321ab470922c12b7520c88944f99539cbdad2626b`; the final cumulative queue is
`989bc914f9493051a071472c9defd352fe1cb8cc217c062e1f479bdcb9c6e4d8`; the readable result is
`245ded3d564a94eccc017a942189eb38a40f4c5a08652d724be3dc759e2ddb10`; and the manifest is
`6b532978c86adf39dbc2f41222d41ca9b765b1c615dce5453a0ba04955a9f6ff`. The known machine-wide
Python 3.14 legacy-`httpx` TestClient warning remains documented; the constrained Python 3.12
container path was previously verified with `httpx2`.

### Incomplete work, risks, and next step

Family adjudication is complete, but materialization and release-variant adjudication are not. The
42 accepted new-family outcomes do not yet have stable review IDs and are not Dual-RAG candidates;
the 7 holds still require tool-qualified or lineage-specific resolution before they can enter that
source. None of the 100 Wiki rows is canonical or promotion-eligible.

The next immediate step is to write a Lite specification for the stable review-family
materialization contract. It should define deterministic IDs, aliases, provenance, lineage links,
hold exclusion, idempotent generation, and the boundary between family acceptance and later
release-variant review. Only after that contract is accepted should implementation update the
human-backed retrieval source or PostgreSQL, and only then should yearly-list expansion continue
toward roughly 3,000 reviewable rows.

## 2026-09-09 — Final priority-two research preserves renamed and multi-tool identity boundaries

### What was executed and what problem it solves

T43 verifies the exact T42 cumulative checkpoint and selects all nine remaining pending priority-2
families in their existing queue order. Earlier research batches assumed ten-item slices; this one
uses the true remainder rather than duplicating a family, skipping a family, or padding the work
with a record outside the current 100-row pilot.

The packet covers thirteen Wiki release rows across Nissan Skyline GT-R (BNR32), Power Wheels Dune
Racer, Proton Saga, Small Bloc, Standard Kart, Super Twin Mill, The Vanster, Twin Mill Gen-E, and
X-34 Landspeeder. Six names have a dedicated single-casting page plus non-Fandom exact-name
corroboration and receive machine `create_new_casting` recommendations. Three remain held because
their text names do not identify one safe physical lineage.

### Code changes and why they were made

`priority-2-batch-05-source-notes.json` freezes the nine-family research input. Each entry retains
the queue ID and display name, a concise Wiki observation, and at least one observation from a
separate publisher. The independent sources are Hot Wheels Collectors News Catalog, All Hot
Wheels, Wheel's Garage, and Hot Wheels Collectors. Only source URLs and paraphrased text claims are
stored; no images or external page copies are added to the repository.

`build_fandom_priority_two_research.py` now accepts `--batch 5`, reads the batch-04 adjudicated
queue and manifest, and passes an explicit `batch_size=9`. The builder still defaults to ten for
batches 01–04. Its selection metadata is generated from the actual bounded size, so the artifact
states exactly what was selected rather than preserving an inaccurate “first 10” label.

The source-page vocabulary adds `renamed_existing_casting` and `multi_casting_page`. A renamed
release is held because its marketing/display name points back to an existing casting lineage; a
multi-casting page is held because one page contains more than one tool under the same display
name. These are distinct from a formal `disambiguation` page and from `homonymous_castings`, where
a separate page exposes the conflict. Each class has its own fail-closed recommendation reason.

The initial implementation briefly reused the new multi-tool wording for the legacy
`disambiguation` branch. The cross-batch `--check` immediately detected that batch 01 would no
longer reproduce byte for byte. The branches were separated, restoring the original text for old
batches while keeping the new classification for batch 05. No checked-in prior artifact was
rewritten.

`test_fandom_priority_two_research_batch_five.py` adds six tests. They require the exact final nine
families and thirteen rows, the six-create/three-hold split, the named hold set, Bogzilla lineage
for Power Wheels, both Standard Kart tool numbers, the distinct Nissan RLC tool, two-host evidence
for every creation, preserved related-lineage context, pending reviewer fields, variant hold, zero
promotion, hashes, and deterministic regeneration.

### Technical choices, alternatives, and trade-offs

Power Wheels Dune Racer is not treated as a new casting. HYX52 appears on the Bogzilla page as a
release named Power Wheels Dune Racer, and an independent listing pairs both names. Automatically
creating a Power Wheels family would duplicate the FJV61 physical lineage; silently merging it to
Bogzilla would also exceed a machine research step. A named `renamed_existing_casting` hold keeps
the likely relationship visible for the owner and later entity design.

Standard Kart is not treated as one family merely because both tools share one page. The evidence
separates a character-bearing 2019 GBG26 tool from the driverless mainline GRX17 tool whose 2025
release is HYW83. The current toy number identifies the latter release, but a name-keyed family
would remain ambiguous. `multi_casting_page` records the evidence shape without pretending the page
is a formal disambiguation index.

Nissan Skyline GT-R (BNR32) is held because the main page maps HYY72 to the Jun Imai lineage while
a separate 2026 RLC page documents a completely different opening-hood JJY54 tool at the same 1:64
scale. The RLC qualifier provides useful context, but the base display name remains shared. This is
stricter than the earlier Mercedes XL case, where the separate page was explicitly an upscaled
1:43 product rather than a competing same-scale tool.

The other six names remain separate when their relationship is expressed through a different
name, a documented continuous retool, or a distinct product line. The Vanster retools stay in one
page lineage; Twin Mill Gen-E and Super Twin Mill retain names distinct from the original Twin Mill;
the wheeled X-34 Landspeeder remains distinct from the differently named Starships product. This
avoids both over-splitting every tooling change and over-merging all related designs.

### Decision changes

No project-owner decision changed. All nine T43 records remain pending machine research. Proton
Saga, Small Bloc, Super Twin Mill, The Vanster, Twin Mill Gen-E, and X-34 Landspeeder receive
creation recommendations. Nissan Skyline GT-R (BNR32), Power Wheels Dune Racer, and Standard Kart
receive proposed holds.

The T42 cumulative queue therefore still reports forty-four completed and nine pending family
decisions, including four merges, thirty-six accepted new-family decisions, and four completed
holds. Eighty-seven release rows under completed family decisions remain variant-held. The thirteen
current research rows are also held. No stable ID, catalog object, PostgreSQL row, Dual-RAG result,
calibration input, evaluation label, or promotion status changed.

### Verification evidence

The focused T43 module passed 6/6. The complete host suite passed 153/153 in 1.418 seconds on Python
3.14.6. All five research batches reproduce byte for byte; the first four remain unchanged after
adding the bounded final-size and evidence-class support. The known legacy-`httpx` Starlette
TestClient warning remains limited to the machine-wide environment, while the constrained Python
3.12 runtime was previously verified with `httpx2`.

The source-note checksum is
`f230b8c5ec5f6bd5b7569659ab23925f2c6d56c6e7e689df1de2067da5c6ca13`; research JSON is
`a49ad2f32f255f800d32ab5466640e2b8138b6ff743e601f58d74feee622626a`; the readable report is
`d782096f9dd2c3959e5d9321ce16fdcbb906ff2d2c2cf228cd4c34934254454f`; and the manifest is
`03a180d7e7ec919b6a9f880a12a05bf77287d233dd1a37d77a63fb22af972426`. Final data-chain,
compilation, Compose, and whitespace checks are recorded in the T43 evidence and QA review.

### Incomplete work, risks, and next step

The research sources can change, collector catalogs may inherit upstream mistakes, and text claims
do not replace physical-tool verification. None of the six creation recommendations is an owner
decision. The three holds need an explicit choice about tool-qualified IDs, aliases, or target
lineages before materialization.

The next immediate task is T44: present the exact six-create/three-hold packet to the project owner
and, only after authorization, append the final priority-2 decision batch. That will close the
current 53-family adjudication queue at family scope while every release variant remains held. A
new specification must then design stable review entities and the expansion path toward roughly
3,000 reviewable variants without inserting provisional research directly into production data.

## 2026-09-09 — Batch-04 research becomes an attributable eight-create/two-hold decision layer

### What was executed and what problem it solves

T42 converts the project owner's bounded follow-up authorization into a repository-owned decision
record. The immediately preceding T41 handoff identified the exact eight creation recommendations,
the two held names, why those names remain ambiguous, and that every release variant would stay
held. Recording the response separately prevents the system from confusing a machine research
recommendation with a human decision or relying on transient conversation history.

The eight accepted review-layer families are Lamborghini Huracán Sterrato, Max Steel, Mazda
Autozam, Mazda REPU, Mercedes-Benz 500 E, Monster High Ghoul Mobile, Morgan Super 3, and Nerve
Hammer. Mazda MX-5 Miata and Nissan Skyline 2000GT-R LBWK remain held. The cumulative queue moves
from thirty-four completed / nineteen pending families to forty-four completed / nine pending,
while all twenty-three rows in the current batch remain variant-held.

### Code changes and why they were made

`priority-2-batch-04-decisions.json` is the new immutable authorization input. It records
`project_owner`, an ISO-8601 UTC decision time, conversational provenance, and one decision for each
T41 packet. Each entry uses `casting_family_only`, keeps `target_family_id` null, gives a written
family-specific reason, references the frozen research packet and supporting sources, and sets
`variant_decision` to `hold`. Keeping the decision input separate from both research and output
makes the actor, time, scope, and evidence independently inspectable.

`apply_fandom_priority_two_decisions.py` now accepts `--batch 4`. The new mapping reads the T40
cumulative queue, T41 research, and T42 decision input, then emits batch-04-specific filenames and
version metadata. Its Markdown generator now explains the eight-create/two-hold result explicitly,
including both unresolved names. Earlier batch branches remain unchanged so batches 01 through 04
continue to reproduce from one validation implementation.

The generated `priority-2-batch-04-adjudicated-queue.json` uses copy-on-write rather than changing
the T40 checkpoint. It appends a fifth ordered decision event and recalculates cumulative counts.
The readable result explains the boundary for a non-code reviewer, while the manifest binds every
input and both outputs by SHA-256. This combination allows people to read the result and tests to
detect any later silent edit.

`test_fandom_priority_two_decisions_batch_four.py` adds six focused tests. They require exactly ten
decisions with eight creations and the two named holds, verify all twenty-three release rows stay
held, preserve every earlier decision group and history entry, and reproduce the frozen output.
Negative cases deliberately change an outcome, remove one family, reuse an earlier batch ID, and
try to promote a release variant. Each alteration must fail closed.

### Technical choices, alternatives, and trade-offs

The owner response is treated as bounded authorization because it followed a handoff that stated
the complete proposed split and named T42 as the next step. The decision file repeats that scope
instead of recording only “approved.” This makes later review possible without reconstructing the
conversation, although conversational attribution is still weaker than a cryptographic signature.

The Mazda and Nissan holds are preserved even though the current toy numbers point to the newer
Mazda and Tooned Nissan pages. Toy numbers help identify current rows, but the queued entity key is
still the shared display name. Automatically creating name-keyed families would encode collisions
with older or non-Tooned same-scale tools. The chosen hold sacrifices immediate coverage so later
materialization can introduce a tool-qualified name or lineage key deliberately.

The accepted outcomes are not materialized. Creating UUIDs or PostgreSQL rows in the same step
would combine two different decisions: whether the source evidence supports a family, and how that
family should be represented in searchable data. Separating adjudication from materialization
keeps rollback simple, avoids inventing release colors or canonical variants, and preserves the
Dual-RAG boundary. The trade-off is that accepted families are still not searchable.

### Decision changes

Eight T41 recommendations change from `pending` machine research into completed, attributable
`create_new_casting` decisions. The proposed Mazda MX-5 Miata and Nissan Skyline 2000GT-R LBWK
holds become completed owner holds; they are not discarded and remain visible for later identity
design. All ten decisions are family-only.

The cumulative state is now forty-four completed and nine pending family decisions. It contains
four accepted existing-family merges, thirty-six accepted new-family decisions, and four family
holds. Eighty-seven release rows fall under completed family decisions, but their variant state is
still hold and promotion eligibility remains zero. No canonical UUID, human-backed catalog entity,
PostgreSQL row, runtime behavior, calibration input, or evaluation label changed.

### Verification evidence

The focused T42 module passed 6/6, and decision checkpoints for batches 01 through 04 reproduced
byte for byte. The complete host suite passed 147/147 in 1.611 seconds on Python 3.14.6. The known
legacy-`httpx` Starlette TestClient warning remains limited to the machine-wide environment; the
constrained Python 3.12 runtime was already verified with `httpx2`.

The decision-file checksum is
`172775063922d1ab2ae999ddcea43a09826b02f4f01c97fbb1c3e0b9671c8dbf`; the cumulative queue is
`123e7432bc68710e9f3c6c01393b07456ff018c54619ea2111825c27f2ff5847`; the readable result is
`f83431ed2febf8607bb692a146142f0e874812bc9124e7ee1db1f16d9627eff3`; and the manifest is
`34c61547ea3ef76fd97fb46a54667272a99c2dce23f8c87568969d5df90136a9`. Final fixture, Wiki-pilot,
research, decision, compilation, Compose, and whitespace checks are captured in the T42 evidence
and QA review.

### Incomplete work, risks, and next step

Nine priority-2 families remain pending in the current 100-row pilot. The thirty-six accepted new-
family outcomes still lack stable review entity IDs and therefore are not part of either Dual-RAG
retrieval source. The two newest holds cannot be resolved safely with display-name equality; they
need a tool-qualified identity design.

The next immediate task is T43: use the checksum-verified T42 cumulative queue to research the
remaining nine pending families as the final bounded packet. T44 will require a separate owner
response. Only after all 53 family items have attributable outcomes should a new specification
design how accepted families become stable review entities and how larger yearly imports advance
toward approximately 3,000 reviewable variants.

## 2026-09-08 — Batch 04 separates same-name tools from retools and scale-qualified products

### What was executed and what problem it solves

T41 advances research from the exact T40 cumulative checkpoint. It verifies the latest queue and
manifest, skips all thirty-four completed decisions, and selects the next ten still-pending
priority-2 families in queue order. This keeps research aligned with actual adjudication state and
prevents earlier families from being selected again.

The batch covers twenty-three Wiki release rows across Lamborghini Huracán Sterrato, Max Steel,
Mazda Autozam, Mazda MX-5 Miata, Mazda REPU, Mercedes-Benz 500 E, Monster High Ghoul Mobile, Morgan
Super 3, Nerve Hammer, and Nissan Skyline 2000GT-R LBWK. Eight names have a dedicated casting
lineage plus non-Fandom exact-name corroboration and receive machine `create_new_casting`
recommendations. Mazda MX-5 Miata and Nissan Skyline 2000GT-R LBWK remain held because each display
name is reused by separate same-scale casting tools.

### Code changes and why they were made

`priority-2-batch-04-source-notes.json` records the bounded research input. Each family keeps its
stable queue ID, exact display name, a dedicated Wiki-page observation, and at least one concise
observation from another publisher. The non-Fandom evidence comes from Hot Wheels Collectors News,
All Hot Wheels, LastDodo, Football Stickipedia, Hot Wheels Database, and Diecast Radar. Only URLs
and paraphrased text claims are stored; no external images or full pages were copied.

The Mazda MX-5 record links the 2025 HYW18/HYX57 Chimera page to the separate 1991–2003 1:64 tool
2920 that uses the same displayed casting name. The Nissan record maps HYW79/HYY30/HYX54 to the
2024 Tooned page while retaining the regular 2022 HCW32 tool, which uses the same display name at
the same scale. Both are classified `homonymous_castings`, forcing family-level holds even though
the individual toy numbers explain which current page contains the staged rows.

Two contrasting cases are also made explicit. Nerve Hammer has multiple documented retools, but
one dedicated page treats them as a continuous lineage, so ordinary tooling revisions do not
create artificial families. Mercedes-Benz 500 E has a related Hot Wheels XL page, but that page is
explicitly suffixed and documents a 1:43 upscaled product; the queued releases and main page are
1:64. The relationship remains visible without turning a scale-qualified product into a false
same-tool conflict.

`build_fandom_priority_two_research.py` now accepts `--batch 4`, binding the build to
`priority-2-batch-03-adjudicated-queue.json` and its manifest and assigning batch-04 output names
and version metadata. The same builder still defaults to batch 01 and retains the explicit mappings
for batches 02 and 03, so all research batches share one validation policy without losing frozen
compatibility.

`test_fandom_priority_two_research_batch_four.py` adds six tests. They verify the next-ten queue
slice, ten-family/twenty-three-row/eight-create/two-hold totals, both conflicting pages and tool
numbers, two-host creation evidence, Mercedes scale context, Nerve Hammer retool continuity,
pending reviewer state, variant hold, zero promotion, checksums, and deterministic regeneration.

### Technical choices, alternatives, and trade-offs

Family identity remains stricter than release-page lookup. The Nissan toy numbers clearly identify
the Tooned page, and the Mazda numbers identify the 2025 page, but the current adjudication key is a
normalized display name intended for later retrieval. Accepting a name-only family while that same
name denotes another 1:64 tool would preserve the current rows but create an ambiguous future
entity. Holding the family costs review velocity but avoids encoding a collision that would later
need migration.

Retools are not automatically split. Treating every body/base revision as a new family would make
Nerve Hammer several identities even though the source catalog maintains one lineage. Conversely,
merging every exact display name would collapse the two Mazda and two Nissan tools. The chosen
method uses dedicated source-page lineage, scale, suffix, tool number, and exact queued name
together, rather than relying on text equality alone.

The research stays a ten-family bounded packet instead of crawling the remaining nineteen or a new
year in one run. Smaller batches keep sources and edge cases reviewable, but require more owner
round trips. That is appropriate in Lite mode because the highest-risk operation is identity
assignment, not fetching large quantities of strings quickly.

### Decision changes

No project-owner decision changed. The cumulative adjudication queue remains thirty-four completed
and nineteen pending families, including four existing-family merges, twenty-eight accepted new-
family decisions, and two holds. Sixty-four release rows under completed decisions remain variant-
held and promotion remains zero.

Within the unconfirmed research layer, eight families now have creation recommendations:
Lamborghini Huracán Sterrato, Max Steel, Mazda Autozam, Mazda REPU, Mercedes-Benz 500 E, Monster
High Ghoul Mobile, Morgan Super 3, and Nerve Hammer. Mazda MX-5 Miata and Nissan Skyline 2000GT-R
LBWK receive proposed holds. These statuses must not be counted as new human labels until T42
records an explicit owner response.

### Verification evidence

The T41 focused module passed 6/6. The complete host suite passed 141/141 in 1.491 seconds on the
available Python 3.14.6 interpreter. Fixture and 100-row Wiki-pilot validation, deterministic
review/queue/priority-one evidence, all four priority-two research batches, all three cumulative
priority-two decision checkpoints, Python compilation, default and PostgreSQL-profile Compose
configuration, and `git diff --check` all passed.

The batch-04 source-notes checksum is
`06616c879b3d8fa5d293338669b9497a29703a8055d44fce45c115e82efd6761`; research JSON is
`07ae79197f81f3595b5323a38834fbfd776fd7043180bd3f6961c3a03d2c9673`; the readable report is
`cb9ae7e45b670d64ae6c2d4831a13eee4d6a70d5f9edf3aa16a032f8a98415c4`; and the manifest is
`930f6bd72361501e93a792dae493d8b762325fe8df5a11625cd57f08b7a38923`. All four research `--check`
commands passed without changing the first three artifacts. The host suite emitted the documented
legacy-`httpx` Starlette TestClient warning on machine-wide Python 3.14; the constrained Python
3.12 runtime was previously verified with `httpx2`.

### Incomplete work, risks, and next step

All ten T41 reviewer blocks remain pending. The eight creation recommendations have no stable
review-catalog IDs and are not searchable through Dual-RAG. The two holds require a tool-qualified
family name or explicit lineage key; toy number alone does not repair the current name-key
collision. No color, release-level identity, catalog entity, PostgreSQL row, runtime behavior,
calibration data, or evaluation label changed.

The next immediate task is T42: present the exact eight-create/two-hold packet to the project owner
and, only if authorized, record it as a separate decision file. Nine priority-2 families will remain
after that batch, allowing one final bounded research packet before designing materialization and
the later expansion toward approximately 3,000 reviewable records.

## 2026-09-08 — Batch-03 research becomes an attributable owner decision layer

### What was executed and what problem it solves

T39 ended with an exact ten-family proposal and explained that the next step, T40, would accept
those `create_new_casting` recommendations only at casting-family scope. The project owner then
asked to execute that step. T40 records this bounded authorization instead of leaving it as an
implicit conversation state or pretending that machine research was already a human decision.

All ten T39 families are now completed owner decisions: Draftnator, Fiat 500e, Fish'd & Chip'd,
Ford Mustang GTD, Ford Performance SuperVan 4, Haulerback, Hirohata Merc, Kei Swap, Kick Kart, and
Kowloon'd Hypervan. Their eighteen release rows remain variant-held. The cumulative queue advances
from twenty-four completed / twenty-nine pending families to thirty-four completed / nineteen
pending, while promotion eligibility stays zero.

### Code changes and why they were made

`priority-2-batch-03-decisions.json` stores the authorization as its own immutable input. The batch
identifies `project_owner`, records the UTC decision time and conversational provenance, and covers
every frozen T39 packet exactly once. Each item repeats the approved `create_new_casting` outcome,
uses `casting_family_only` scope, leaves `target_family_id` null, holds variants, gives a
family-specific reason, and references both its packet and source evidence. Fiat 500e and Hirohata
Merc also retain the related-casting links that motivated T39's lineage boundary.

`apply_fandom_priority_two_decisions.py` now supports `--batch 3`. The new option binds the T38
cumulative queue and manifest, T39 research and manifest, and T40 decision file, then emits a
batch-03 queue, report, and checksum manifest. It reuses the existing validation path so the same
requirements apply to all priority-2 owner batches: exact packet coverage, outcome agreement,
valid reviewer/time/provenance, held variants, no existing-family target, evidence, and no duplicate
history ID.

The readable report previously described a fixed nine-create/one-hold split because that was true
for batches 01 and 02. The rendering branch now gives batch 03 accurate ten-create/zero-hold wording
without rewriting the two earlier reports. Batch 01 remains the default CLI behavior, batch 02 keeps
its original input mapping and Batman explanation, and checks prove their frozen bytes did not
change.

The derived `priority-2-batch-03-adjudicated-queue.json` is a copy-on-write checkpoint rather than
an edit to the T38 queue. Its manifest freezes every input and output hash. A new six-test module
checks the cumulative summary, all-ten approval, current eighteen-row variant hold, project-owner
attribution, preservation of the three prior batches and four-entry history, rejection of changed,
incomplete, and duplicate batches, and deterministic output reproduction.

### Technical choices, alternatives, and trade-offs

Approval remains an append-only adjudication layer instead of immediate materialization into
`human_backed_catalog.json`, the canonical fixture, or PostgreSQL. Immediate insertion would make
the newly researched names searchable sooner, but the owner only confirmed casting-family
existence. Stable entity IDs, alias policy, release grouping, color, and canonical variant identity
remain separate decisions. Preserving that boundary costs another later materialization step but
prevents family-level evidence from silently becoming variant ground truth.

The implementation continues to use one batch-aware applier instead of one script per batch. A
configuration-driven arbitrary batch engine was considered, but three explicit, validated CLI
choices remain easier to audit in Lite mode and fail closed on unknown filenames. Reuse reduces
drift in validation logic; the compatibility cost is handled by running `--check` on every earlier
batch whenever the shared code changes.

Complete batch coverage is mandatory even though all ten outcomes are identical. Allowing partial
application might look more flexible, but the owner's response referred to the displayed packet as
a whole. Requiring all ten exactly once proves that no family was silently omitted, substituted, or
assigned a wider scope. A batch ID already present in history is rejected to prevent accidental
double application.

### Decision changes

The ten T39 packets move from pending machine recommendations to completed project-owner family
decisions. No item changes its recommended outcome: all ten are accepted as new review-layer
casting families. This raises the cumulative accepted-new-family count from eighteen to
twenty-eight. The four earlier existing-family merges and the two earlier holds remain unchanged.

The history now contains four ordered owner events: priority 1, priority-2 batch 01, priority-2
batch 02, and priority-2 batch 03. Sixty-four Wiki release rows sit under completed family
decisions, but every one still has a variant hold. Therefore the catalog size, PostgreSQL contents,
Dual-RAG candidate sources, calibration data, evaluation labels, and runtime outputs are unchanged.

### Verification evidence

The T40 focused suite passed 6/6. It verified 34 completed / 19 pending families, 4 merges, 28
accepted new-family decisions, 2 holds, 64 held release rows, four ordered decision batches, and
zero promotion. Negative cases altered a creation to a hold, removed one decision, and reused the
batch-02 ID; all failed closed.

The complete host suite passed 135/135 in 1.425 seconds on the available Python 3.14.6 interpreter.
Fixture and 100-row Wiki-pilot validation, deterministic review/queue/priority-one evidence, all
three priority-two research batches, all three cumulative priority-two decision checkpoints,
Python compilation, default and PostgreSQL-profile Compose configuration, and `git diff --check`
all passed. The known machine-wide Starlette TestClient warning for legacy `httpx` remains; the
project's constrained Python 3.12 runtime was previously verified with `httpx2`.

The owner decision checksum is
`ecd3af4c0b003d3458e719109eff9b41c546787d3cd5c5bb5d313dd4d316dd8c`; the cumulative queue is
`edee360faccb43b4bea58a91d5be67b511d9e41ea6a76f21ec4648bae83190b9`; the readable result is
`523af3b17045ee2f3322fdad57d5666f9fbc0c634d957aad7c32e32bc41d7bde`; and the manifest is
`8adc3ba56d7b55e03958de335c2c8a82c351094636fd496d54cd430422b00704`.

### Incomplete work, risks, and next step

Conversation provenance is auditable in the repository but is not a cryptographic signature. The
twenty-eight accepted new families still have no stable review-catalog IDs and cannot be retrieved
by either Dual-RAG source. The sixty-four held release rows have not gained verified color or
canonical variant identity, and no new PostgreSQL-scale accuracy or latency evidence was produced.

The next immediate task is T41: research the next ten of nineteen pending priority-2 families from
the new T40 cumulative queue using the same two-source, disambiguation, homonym, and related-lineage
safeguards. Only after all priority-2 family decisions are attributable should the project design
how accepted families become stable review-catalog entities before expanding toward the planned
3,000-row dataset.

## 2026-09-08 — Batch 03 researches related castings without turning research into approval

### What was executed and what problem it solves

T39 advances the external-data review from the T38 cumulative checkpoint rather than returning to
the original 53-family queue. It verifies the latest queue checksum, skips all twenty-four
completed family decisions, and researches the next ten pending priority-2 families in their
existing deterministic order. This prevents duplicate work and keeps every new conclusion tied to
the exact adjudication state that produced it.

The batch covers eighteen 2025 Wiki release rows across Draftnator, Fiat 500e, Fish'd & Chip'd,
Ford Mustang GTD, Ford Performance SuperVan 4, Haulerback, Hirohata Merc, Kei Swap, Kick Kart, and
Kowloon'd Hypervan. Each name has a dedicated Hot Wheels Wiki casting page and at least one
non-Fandom source confirming the exact casting name. The resulting packet therefore recommends
ten `create_new_casting` family outcomes and zero holds. These are deliberately still machine
recommendations: reviewer confirmation remains pending, all eighteen release variants remain
held, and promotion eligibility remains zero.

### Code changes and why they were made

`priority-2-batch-03-source-notes.json` is the structured research input. Every record repeats the
stable family review ID and exact queue name, then stores a concise observation from the dedicated
Wiki page and a separate exact-name observation from another publisher. The sources include Orange
Track Diecast, All Hot Wheels, South Texas Diecast Collectors, Hot Wheels Collectors News, Old Cars
Weekly, and Hot Wheels Database. Only HTTPS URLs and short paraphrased claims are stored; no images
or full third-party pages were copied into the repository.

Two records preserve extra identity context. Fiat 500e retains the separate Fiat 500 page so a
future reviewer does not collapse the electric-model casting into a nearby name. Hirohata Merc
retains the older `'51 Merc` page and a source explanation that the current mainline release uses a
newer tool. The code classifies both current exact names as `single_casting` because neither queued
name is shared by the related tool. This differs from the batch-02 Batman case, where separate tools
use the same display name and must remain held.

`build_fandom_priority_two_research.py` now accepts `--batch 3`. That option binds the research to
`priority-2-batch-02-adjudicated-queue.json` and its manifest, applies the existing rule to the first
ten still-pending priority-2 families, and emits batch-03-specific JSON, Markdown, and manifest
files. The default remains batch 01 and batch 02 keeps its previous input mapping, so the extension
does not alter earlier frozen artifacts or introduce a second implementation with different
validation behavior.

`test_fandom_priority_two_research_batch_three.py` adds six focused tests. They prove that batch 03
is exactly the next ten items after T38; freeze the ten-family, eighteen-row, ten-create result;
require Fandom plus a distinct source host; retain both related-casting distinctions; keep every
reviewer, variant, and promotion boundary closed; and reproduce the JSON, report, manifest, and
hashes byte for byte.

### Technical choices, alternatives, and trade-offs

The project continues to use a small, auditable source packet rather than a broad autonomous web
crawl. A crawler could gather more pages quickly, but it would increase licensing, page-quality,
rate-limit, and identity-matching risks before the current 100-row workflow is fully adjudicated.
The bounded approach costs manual research time but makes the exact evidence and transformation
easy to review and reproduce in Lite mode.

The creation rule remains a dedicated Wiki page plus exact-name evidence from at least one
publisher outside Fandom. This is not a claim that collector sites are authoritative for every
paint, base, or release detail; it is a cross-source check that the casting name is not merely an
unmatched string in the local catalog. Requiring manufacturer-only documents was considered too
restrictive for historical and fantasy models, while accepting Fandom alone would create a
single-source failure point.

Related pages are treated as lineage evidence rather than a universal hold trigger. Automatically
holding every related casting would block legitimate uniquely named tools such as Fiat 500e and
Hirohata Merc. Automatically merging them would erase physical-tool distinctions. The chosen rule
looks at whether the exact queued display name uniquely selects the current tool, while recording
the related page for later human review. The trade-off is that this remains text-source identity
evidence, not inspection of the physical casting.

### Decision changes

No project-owner decision changed in T39. The cumulative adjudication state remains twenty-four
completed and twenty-nine pending families, with four existing-family merges, eighteen accepted
new-family decisions, two holds, forty-six held variants under completed decisions, and zero
promotion. Batch 03 is a separate research artifact layered on top of that unchanged state.

What did change is the research policy's documented boundary. Batch 02 established that distinct
tools sharing one display name must be held. Batch 03 now records the complementary case: a related
or predecessor tool with a different stored name does not automatically invalidate a unique exact
current name. The relation must remain visible, but a family creation recommendation can proceed
when the current identity still meets the two-source rule.

### Verification evidence

The new T39 module passed 6/6. The complete host suite passed 129/129 in 1.499 seconds on the
available Python 3.14.6 interpreter. Fixture and 100-row Wiki-pilot validation, deterministic
review/queue/priority-one evidence, all three priority-two research batches, both cumulative
priority-two decision checkpoints, Python compilation, default and PostgreSQL-profile Compose
configuration, and `git diff --check` all passed.

The batch-03 source-notes checksum is
`6f2753b7e736145970096660ba07ce4553ebd423b1f551c7780dc7b91274cf86`; research JSON is
`1d38a7bbffbf905283d4c7be6a24495547df425723ef610539c1f3eee07c432d`; the readable report is
`44472564cac68bb3073c0ceeab2dbc663994cb859318a7cab5f5f0f5b3d4c940`; and the manifest is
`92dae730213f9928dd5811d8a43657038a037bd85462653fc2639db44a33e97b`. All three research-batch
`--check` commands passed without changing the two earlier hashes. The host suite emitted the
already documented legacy-`httpx` Starlette TestClient warning on machine-wide Python 3.14; the
project's constrained Python 3.12 runtime was previously verified with `httpx2`.

### Incomplete work, risks, and next step

The ten recommendations have not been approved by the project owner and are not searchable family
entities. None has a stable review-catalog ID, verified color, canonical release variant, or
PostgreSQL row. Remote source pages can change after the recorded research date, and the stored
paraphrases do not replace physical-casting verification.

The next immediate task is T40: present this exact frozen ten-family result to the project owner.
Only an explicit response to that packet should be translated into a separate attributable
batch-03 decision file. If approved, the decision applier can then derive a new cumulative queue
while still keeping all release variants and catalog/database promotion held.

## 2026-09-08 — Batch-02 recommendations become attributable owner family decisions

### What was executed and what problem it solves

T37 produced ten source-backed recommendations but intentionally left every reviewer field
pending. The project owner then asked to execute the explicitly stated next step after being shown
the exact outcome: accept nine `create_new_casting` recommendations and keep `Batman and Robin
Batmobile` held. T38 records that bounded authorization and applies it to the latest cumulative
queue.

This solves two different audit problems. First, a machine recommendation is no longer confused
with the owner's choice: the recommendation file remains unchanged and the approval has its own
actor, time, provenance, reasons, and evidence. Second, batch 02 does not overwrite the fourteen
earlier decisions. The resulting checkpoint contains twenty-four completed family decisions and
twenty-nine pending families while retaining the full three-event decision history.

### Code changes and why they were made

`priority-2-batch-02-decisions.json` records the `project_owner` decision batch at
`2026-09-08T18:55:38Z`. It covers every T37 family exactly once. Nine records accept
`create_new_casting`; the Batman record accepts `hold` and cites both the current page and the
separate 2004 100% Hot Wheels tool page. Every record says `casting_family_only`, leaves
`target_family_id` null, holds release variants, provides a family-specific reason, and links to
its frozen research packet plus source evidence.

`apply_fandom_priority_two_decisions.py` was generalized from a batch-01-only command to a
batch-aware applier. `--batch 2` binds the T36 cumulative queue, T37 research and manifest, and the
new owner decision file. It derives batch-02-specific queue/report filenames and version metadata.
The validation method now receives the actual research filename so evidence references cannot
silently point to batch 01.

The history logic was also corrected for a true cumulative input. Batch 01 begins with a legacy
single `decision_batch` object and converts it to a list; batch 02 begins with the existing
`decision_batches` list. The applier now accepts either representation, preserves every prior item,
and appends the current batch. It rejects a malformed prior history instead of replacing it. The
same batch ID is also rejected if it already exists in history. The default batch-01 behavior and
frozen report wording remain unchanged, while batch 02 renders the Batman-specific unresolved
lineage.

The derived `priority-2-batch-02-adjudicated-queue.json`, readable result, and manifest capture the
new cumulative state and checksum every input/output. A dedicated six-test module checks counts,
the nine-create/one-hold split, attribution and scope, preservation of both earlier decision sets,
three-entry history, fail-closed changed/incomplete batches, and deterministic regeneration.

### Technical choices, alternatives, and trade-offs

Approval is kept as an append-only decision layer rather than inserted directly into
`human_backed_catalog.json` or PostgreSQL. This means accepted families are not searchable yet,
which is a deliberate cost: family existence, stable entity materialization, and release-variant
identity are separate claims with different evidence. The current owner response authorizes only
the first claim.

The applier reuses one validated implementation for both priority-2 batches instead of copying a
nearly identical batch-02 script. Reuse reduces divergent validation rules, but it requires
explicit batch configuration and backward-compatibility checks. Both batch outputs are therefore
tested byte for byte. A fully generic arbitrary-batch configuration file was considered
unnecessary at two batches; adding only the two validated CLI choices keeps Lite scope small and
prevents accidental application against an unreviewed filename.

Complete ten-packet coverage remains mandatory. A partial approval format could support more
granular owner choices, but the actual authorization referred to the entire displayed proposal.
Requiring all ten exactly once ensures that the hold is recorded rather than silently omitted and
that no creation outcome changes while the batch is applied.

### Decision changes

Nine T37 families have moved from machine recommendation to completed project-owner family
decisions: `'94 Audi Avant RS2`, `Alpha Pursuit`, `Bogzilla`, `Crescendo`, `Custom '53 Chevy`,
`Custom Cadillac Fleetwood`, `Deora III`, `DMC DeLorean`, and `Donut Drifter`. `Batman and Robin
Batmobile` has moved from proposed hold to an accepted hold because HYW60/HYX61 still lack a
tool-specific mapping.

Across all owner batches, the cumulative state is now four accepted existing-family merges,
eighteen accepted new-family decisions, and two held family decisions. Twenty-nine families remain
pending. Forty-six release rows belong to completed family decisions, but all forty-six remain
variant-held and no family is promotion eligible. These numbers describe the adjudication layer,
not a catalog-size increase.

### Verification evidence

The combined batch-01 and batch-02 focused decision suite passed 12/12. It verified 24 completed /
29 pending counts, 4 merges, 18 accepted new families, 2 holds, 46 held releases, and zero
promotion. It also proved that the current batch contains exactly nine creations plus the Batman
hold, all records are attributable and family-only, the prior four plus ten decisions remain
unchanged, and history has three ordered entries.

Negative tests changed an approved creation to hold, removed one decision, and reused the prior
batch ID; the applier rejected all three cases. Batch-01 and batch-02 `--check` commands both
passed. The new cumulative queue checksum is
`81911e948fd00e76e6da7255ab1174c1697871ac59c3bf674dc5bae645fbc497`; the report checksum is
`f6bad5ae831d17bf1ab279c55a46a0dfe176755acfb8c20f512c504af884a392`; and the owner decision file
checksum is `7350ad739d80999690a74ca1713e86e9509f3c88b038158da45a25e67f094481`.

The complete host suite passed 123/123 in 1.422 seconds on the available Python 3.14.6
interpreter. Fixture and Wiki-pilot validation, T31–T38 deterministic regeneration, Python
compilation, default and PostgreSQL-profile Compose configuration, and `git diff --check` all
passed. The host suite emitted the already documented Starlette TestClient warning because the
machine-wide Python 3.14 environment exposes legacy `httpx`; the previously verified constrained
Python 3.12 runtime uses `httpx2` warning-free. This task did not execute PostgreSQL, change
resolver behavior, or add evaluation labels.

### Incomplete work, risks, and next step

Conversation provenance is auditable in this repository but is not a cryptographic signature.
The eighteen accepted new-family decisions across both batches still lack stable catalog entity
IDs, and no accepted family can be returned by the runtime. The Batman hold is unresolved at the
tool level, and no release has verified color or canonical variant identity.

The next immediate task is T39: research the next ten of twenty-nine pending families using the
T38 cumulative queue. After all priority-2 families have attributable outcomes, a separate
materialization design can decide how accepted family entities enter the review catalog without
inventing release data or bypassing canonical review.

## 2026-09-08 — Batch 02 advances the queue and catches a same-name casting conflict

### What was executed and what problem it solves

T36 left a cumulative review queue with fourteen completed family decisions and thirty-nine still
pending. T37 continues the research from that exact checkpoint. It selects the first ten pending
priority-2 families in the T36 queue, examines one casting-specific Hot Wheels Wiki page plus at
least one publisher outside Fandom for each name, and emits a new frozen review packet. This avoids
both re-researching the ten batch-01 families and treating “not found in our small catalog” as
proof that a new casting should be created.

The observable result is a ten-family / eighteen-release batch. Nine names have sufficient
two-source, exact-name evidence for a machine `create_new_casting` recommendation. The tenth,
`Batman and Robin Batmobile`, demonstrates why exact text is not enough: the current mainline name
is also used by a separate 2004 100% Hot Wheels casting tool G5513. That family remains held until
the staged releases can be mapped to a tool-specific lineage. All ten reviewer confirmations are
still pending, every release variant is held, and promotion eligibility remains zero.

### Code changes and why they were made

`priority-2-batch-02-source-notes.json` is the human-readable research input in structured form. It
keeps the queue family ID and exact name beside concise observations and HTTPS evidence. Sources
include Mattel Consumer Services and independent collector/catalog publishers such as Orange Track
Diecast, 164Custom, Hot Wheels Collectors News, Hot Wheels Database, and HW Treasure. The Batman
record additionally stores the related 2004 page and its G5513 distinction, so the hold is based on
an explicit conflicting identity rather than a vague lack of confidence.

`build_fandom_priority_two_research.py` was extended from a batch-01-only command to a shared
batch-aware builder. `--batch 2` binds the input to
`priority-2-batch-01-adjudicated-queue.json` and its manifest, then names the outputs with the
batch-02 prefix and version. Default invocation remains batch 01, so the existing frozen contract
and checksums remain compatible. The validator now accepts `homonymous_castings` as a distinct
source classification and maps it to a mandatory hold; the older `disambiguation` wording remains
unchanged so batch 01 reproduces byte for byte.

The generated JSON stores the ten machine recommendations, complete source rows, evidence hosts,
pending reviewer blocks, and explicit family-versus-variant scope. The Markdown report presents
the same information for owner review. The manifest binds the T36 queue, its manifest, the new
source notes, research JSON, and report with SHA-256 checksums. A dedicated six-test module verifies
later-batch selection, counts, evidence hosts, the Batman homonym, non-promotion boundaries, and
deterministic outputs without weakening the six existing batch-01 tests.

### Technical choices, alternatives, and trade-offs

The later batch reads the latest cumulative queue instead of the original T34 queue. A manual
“skip the first ten” convention would be shorter code, but it would become wrong as soon as a hold
is revisited or batches are applied in a different order. Selecting records whose actual reviewer
status is still `pending` lets the decision artifact, rather than positional memory, define what
work remains. The trade-off is that each research batch is cryptographically coupled to the latest
queue checkpoint and must be rebuilt or deliberately migrated if that upstream artifact changes.

The evidence policy remains two-source rather than manufacturer-only. Manufacturer documentation
is preferred where available, but historical and fantasy castings are often documented more
completely by established collector catalogs. Requiring an exact-name corroboration outside
Fandom reduces single-source dependence without falsely claiming those publishers independently
verified every physical detail. Remote pages can change, which is why the repository freezes URLs,
claims, date, transformed outputs, and checksums rather than pretending it owns an immutable copy
of every source page.

`homonymous_castings` is separate from `disambiguation`. A disambiguation page openly lists several
tools under one title; a homonym can have a dedicated page for the current tool while another page
uses effectively the same display name. Treating both as safe creations would collapse physical
lineages. Treating every related scale or premium release as a conflict would be overly strict, so
the hold is used only where evidence shows a separate casting tool with the same name; Donut
Drifter's separately named Hot Wheels XL product, for example, does not erase the dedicated 1:64
identity.

### Decision changes

Before T37, the builder understood only a dedicated single-casting page or an explicit
disambiguation page, and only batch 01 could be selected from the command line. It now models a
third failure-safe case—distinct tools sharing a display name—and can deterministically build
either research batch from its proper upstream queue. This is a schema-compatible extension:
batch-01 data and output hashes did not change.

Nine new names now have source-backed machine recommendations, but none has moved to completed
review status: `'94 Audi Avant RS2`, `Alpha Pursuit`, `Bogzilla`, `Crescendo`, `Custom '53 Chevy`,
`Custom Cadillac Fleetwood`, `Deora III`, `DMC DeLorean`, and `Donut Drifter`. Batman and Robin
Batmobile is explicitly held. The cumulative adjudication queue itself remains at fourteen
completed / thirty-nine pending because research does not impersonate an owner decision.

### Verification evidence

The combined batch-01 and batch-02 focused suite passed 12/12. It proves that batch 02 equals the
next ten pending items in the T36 queue and excludes a completed batch-01 family; that the output
contains ten families, eighteen rows, nine proposed creations, and one homonymous hold; that the
separate 2004 G5513 tool is retained in evidence; that creation recommendations span Fandom plus a
different host; and that all reviewer, variant, and promotion boundaries remain closed.

Both `python3 scripts/build_fandom_priority_two_research.py --batch 1 --check` and `--batch 2
--check` passed. The batch-02 research checksum is
`e0814c8017361049c2fa3b712198a22968e9818c2db273c49af668c2639050dc`; its readable report checksum
is `86444256ded953b6ed5e329dccfdf531e5f2565df7212370178fb1a45d81a7ca`; and its upstream T36 queue
checksum is `2b82ca5023439857f186aa0ab122f0b4511290bb4d1303ac533df5c96fbc6790`.

The complete host suite passed 117/117 on the available Python 3.14.6 interpreter. Fixture and
Wiki-pilot validation, T31–T37 deterministic regeneration, Python compilation, default and
PostgreSQL-profile Compose configuration, and `git diff --check` all passed. The host suite emitted
the already documented Starlette TestClient deprecation warning because this machine-wide Python
3.14 environment still exposes legacy `httpx`; the project's constrained Python 3.12 environment
uses `httpx2` and was previously verified warning-free. T37 changed no runtime dependency, and this
research run does not upgrade web-page review into live database or resolver evidence.

### Incomplete work, risks, and next step

These are AI-assisted research recommendations, not human labels. Source accuracy and future page
changes remain risks, and the Batman evidence proves only that the name is ambiguous between tools;
it does not yet prove which tool HYW60 and HYX61 represent. No accepted catalog family, stable
entity ID, canonical variant, PostgreSQL row, or searchable Dual-RAG record was created.

The next immediate task is T38: present this exact ten-item batch to the project owner, record the
owner's accept/hold decisions in a separate attributable file, validate complete agreement and
scope, and derive a new cumulative queue. Only then should batch 03 select the next pending ten.

## 2026-09-08 — Owner approval converts batch-01 research into ten attributable family decisions

### What was executed and what problem it solves

T35 answered the research question for ten possible-new families, but deliberately left the
reviewer fields empty. The project owner then asked to execute the stated next step after being
shown the exact proposal: approve nine `create_new_casting` family outcomes and keep `'55 Chevy`
on hold. T36 records that response as a separate decision event and calculates the new cumulative
queue state.

This closes the gap between “a machine found supporting sources” and “the project owner accepted
the family decision.” It also prevents the short approval message from being interpreted too
broadly. The resulting authority covers exactly the ten displayed recommendations and only casting
family identity; it does not approve colors, releases, canonical UUIDs, database rows, or the other
39 families.

### Code changes and why they were made

`priority-2-batch-01-decisions.json` records the stable batch ID, `project_owner` role, UTC time,
conversation provenance, and ten decisions. Each item cites its T35 research packet and external
evidence, states a family-specific reason, uses `casting_family_only`, has no existing-family
target, and keeps `variant_decision=hold`.

`apply_fandom_priority_two_decisions.py` verifies both the T34 queue checksum and T35 research
checksum before accepting the decision file. It requires valid batch attribution, unique complete
coverage of all research packets, an outcome identical to the approved recommendation, a direct
packet reference, family-only scope, and variant hold. For each creation it rechecks that the Wiki
page was classified as one casting, at least one independent source exists, evidence spans two
hosts, and the earlier exact-match indexes contain no catalog family.

The applier deep-copies the T34 queue and preserves its four priority-1 merge decisions. It replaces
the older single batch field with an ordered two-entry decision history, applies the ten new
decisions, recalculates cumulative counts, and writes a new batch-specific queue, Markdown result,
and checksum manifest. The older all-pending and T34 four-decision queues remain unchanged, so each
stage can be reproduced and compared.

### Technical choices, alternatives, and trade-offs

The code treats approval as an append-only decision layer instead of immediately materializing
nine catalog objects. This adds another artifact in the chain, but it keeps three very different
claims separate: a family probably exists, the owner accepts that conclusion, and a canonical
variant is safe for runtime matching. Collapsing those claims would make source review look like
product-level ground truth.

Complete batch coverage is required rather than accepting a partial list. The user's authorization
referred to the previously displayed ten-item proposal as one set, so all ten outcomes must be
present exactly once. A future correction can use another explicit decision event; silently
dropping an item or changing one recommendation during application is rejected.

The new output has an explicit filename rather than overwriting `adjudicated-queue.json`. This is
slightly more verbose for downstream scripts, but it gives Git a clear audit trail and lets T37
select from the true latest queue without destroying the T34 checkpoint.

### Decision changes

Nine families have moved from machine recommendation to accepted project-owner decisions: 1988
Jeep Wagoneer, 2020 Ram 1500 Rebel, `'21 Ford Bronco`, `'22 Ford Maverick Custom`, `'66 Buick
Riviera`, `'69 Corvette Racer`, `'80 El Camino`, `'87 Audi quattro`, and `'90 Honda Civic EF`.
`'55 Chevy` has moved from proposed hold to an accepted hold because the exact casting lineage is
still unresolved.

The cumulative review queue now contains fourteen completed decisions: four merges from T34, nine
new-family decisions, and one hold. Thirty-nine priority-2 families remain pending. This is not yet
a catalog-count increase; the nine accepted families still exist only as decisions attached to
their source rows.

### Verification evidence

Six focused tests verify the 14/39 cumulative counts, nine-create/one-hold batch, attribution,
family/variant boundary, preservation of all four earlier merges and both decision batches,
fail-closed changed outcome, fail-closed incomplete coverage, hashes, and deterministic rebuild.
The first focused run failed because the new test expected the wrong historical Priority 1 batch
ID. Inspection showed that the product data correctly retained
`fandom-2025-priority-1-owner-confirmation-v1`; the test expectation was corrected and all focused
tests then passed 6/6.

The complete host suite passed 111/111. Fixture and Fandom staging validation, T31–T36 deterministic
checks, Python compilation, default and PostgreSQL Compose configuration, and whitespace checks all
passed. The new cumulative queue checksum is
`2b82ca5023439857f186aa0ab122f0b4511290bb4d1303ac533df5c96fbc6790`; its readable report checksum
is `fe00de56e8c425fa5f80c06722deb702f4fb357d1e40495efb4548830bcfaff9`.

### Incomplete work, risks, and next step

The conversation provenance is auditable inside the repository but not a cryptographic signature.
The underlying external sources can also change. More importantly, the accepted creations have not
been assigned separate catalog entity IDs or made searchable; doing so safely needs its own schema
and must not turn unknown release colors into canonical variants.

The next immediate task is T37: use the T36 cumulative queue to research the next ten of the 39
pending priority-2 families. Keeping research and adjudication in repeated small batches will expose
more ambiguous names before any larger catalog materialization or 3,000-row ingestion begins.

## 2026-09-08 — The first ten possible-new families now have bounded source evidence

### What was executed and what problem it solves

T34 left 49 priority-2 names in the honest state “not found in our current catalogs.” That state
does not prove a name represents a new casting: it can also mean the local catalog is incomplete,
the name is an alias, or one display name hides several physical casting tools. T35 researches the
first ten pending families in the adjudicated queue instead of treating absence as proof.

The research found nine names that each resolve to one dedicated Hot Wheels Wiki casting page and
also appear under the exact Hot Wheels casting name at a publisher outside Fandom. It also found a
counterexample that validates the need for this step. `'55 Chevy` is a disambiguation title for
three distinct tools introduced in 1982, 1998, and 2006; creating one family from that name would
erase a real identity distinction. Batch 01 therefore proposes nine `create_new_casting` outcomes
and one `hold`, while leaving all ten reviewer confirmations pending.

### Code changes and why they were made

`priority-2-batch-01-source-notes.json` records the bounded research input: stable queue ID, exact
casting name, dedicated Wiki page classification, non-Fandom publisher, source type, HTTPS URL,
and a concise paraphrase of the observed claim. The file states that the process was AI-assisted
and does not attribute any identity decision to a human. It stores text notes only and downloads no
images.

`build_fandom_priority_two_research.py` first verifies that the derived T34 queue still matches its
manifest. It then selects exactly the first ten priority-2 families whose reviewer status is still
pending. The source notes must cover those same IDs and names in the same order. Each family must
have a Fandom casting-page classification and at least one exact-name source from another host; a
Fandom URL presented as “independent” is rejected.

The recommendation is derived from this narrow rule rather than typed into the notes. One
`single_casting` page plus the independent confirmation yields `create_new_casting`; a
`disambiguation` page yields `hold`. The generated JSON, readable Markdown report, and manifest
preserve the 19 staged release rows, source links, decision reason, pending reviewer block, variant
hold, and zero promotion eligibility. Six tests lock selection, counts, the `'55 Chevy` exception,
source independence, fail-closed behavior, checksums, and deterministic regeneration.

### Technical choices, alternatives, and trade-offs

A two-source rule was chosen because the yearly list and each casting page share the same community
ecosystem. Requiring another publisher does not make the evidence infallible, but it is materially
stronger than copying a name from one table. Manufacturer evidence is preferred when available;
established collector databases and archived Hot Wheels case documents are used for older or less
visible models where a current Mattel product page is not available.

The batch size is ten so a non-programmer can inspect the report without reviewing all 49 names in
one sitting. The cost is more batches and manifests. That cost is intentional: small diffs make it
easier to notice exceptions such as the three `'55 Chevy` tools before an incorrect family becomes
part of the catalog.

Remote pages were not copied wholesale. The repository freezes concise observations and URLs,
which avoids unnecessary third-party content duplication and keeps the evidence readable. The
trade-off is that a later audit may find that a remote page has changed or disappeared; the research
date and checksummed notes make that limitation visible instead of implying a permanent snapshot.

### Decision changes

Before T35, all 49 unmatched groups had the same undifferentiated “research required” state. The
first ten now have evidence-backed machine recommendations, but they have not become reviewer
decisions. This distinction matters: the project owner has not yet accepted the nine creations or
the one hold, so the adjudicated queue correctly continues to show 49 pending priority-2 decisions.

The identity boundary is unchanged. A proposed family creation answers only whether a distinct
casting family appears to exist. It does not validate the 2025 color, series, collector number,
toy-number release identity, or any canonical UUID. All 19 release rows therefore remain held.

### Verification evidence

The new batch contains exactly 10 families and 19 Wiki rows in deterministic queue order. Nine
packets propose `create_new_casting`; the single `hold` is `'55 Chevy`. All packets have at least
two distinct source hosts, reviewer status `pending`, variant decision `hold`, and
`promotion_eligible=false`. The focused tests passed 6/6, and the full host suite passed 105/105.

Fixture validation, Wiki staging validation, T31–T35 deterministic checks, Python compilation,
both default and PostgreSQL Compose configurations, and whitespace checks passed. The research JSON
checksum is `a802f64478b73a0c40f43c1d43fa44b182ebdbcde9f67d3d0c97f237c92a241c`; the readable report
checksum is `acdd94dc89abee72f0c2e197bf4392fc2c13671b2282cc68e5765d6dbca9669f`.

Ruff and mypy were not rerun in this host session because they are not installed in the global
Python environment and the sandboxed `uv` attempt could not reach PyPI. This did not prevent the
105-test suite, compilation, data validators, deterministic checks, Compose checks, or whitespace
check from completing.

### Incomplete work, risks, and next step

The strongest remaining risk is confusing source agreement with owner approval. Collector sources
can repeat each other's errors, and the remote pages are not immutable. The nine recommendations
are suitable for an explicit family-level review, not for automatic canonical promotion. The
`'55 Chevy` rows need additional identifier evidence that maps the 2025 release to one of the three
known casting lineages.

The next step is to present these ten outcomes to the project owner for acceptance or correction.
Once the owner provides an explicit decision, a priority-2 decision applier can record the nine
family creations and one hold—still with all release variants held. Batch 02 can then research the
next ten of the 39 priority-2 families not yet examined.

## 2026-09-08 — Four owner-approved family links are recorded without variant promotion

### What was executed and what problem it solves

T33 ended with a precise proposal: connect four exact-name Wiki groups to their existing
human-backed casting families, but keep all nine release variants held. The project owner then asked
to execute the next step. T34 records that follow-up authorization as an auditable decision batch
and applies it through a validator rather than silently editing generated queue data.

The resulting state now distinguishes three facts. Four casting-family relationships are completed
decisions; 49 possible-new-family decisions remain pending; and none of the Wiki releases is a
verified canonical variant. This lets the project honestly say some manual family review has
occurred without overstating the catalog or changing Dual-RAG output.

### Code changes and why they were made

`priority-1-decisions.json` records a batch ID, `project_owner` reviewer role, UTC timestamp,
conversation provenance, and four family-specific decisions. Each includes the stable family-review
ID, exact human target, `casting_family_only` scope, `variant_decision=hold`, a reason explaining
the release differences, and references to the evidence packet, human family, and every relevant
Wiki source row.

`apply_fandom_adjudication_decisions.py` validates both upstream checksums before reading the batch.
It requires a supported schema, named batch/reviewer, valid UTC timestamp, provenance, unique known
family IDs, permitted outcome, written reason, evidence references, family-only scope, and variant
hold. For a merge, the target must already be one of that family's exact pre-review candidates.
The original all-pending queue is deep-copied rather than modified.

The derived `adjudicated-queue.json` marks those four reviewer decisions completed, retains all
other entries as pending, and keeps `promotion_eligible=false` everywhere. A readable result and
manifest capture the 4 completed / 49 pending / 9 variant-held / 0 promotion-eligible counts and
freeze the queue, evidence, decision input, and outputs. Tests also inject a wrong merge target and
prove that application fails closed.

### Technical choices, alternatives, and trade-offs

Decisions are stored as data separate from both the machine-generated queue and the resulting
state. This event-like design adds files, but it preserves the before state, reviewer action, and
after state independently. Editing `adjudication-queue.json` in place would be shorter yet destroy
deterministic regeneration and make it hard to tell whether a field came from code or a reviewer.

The reviewer is recorded as the role `project_owner`, not an invented personal name. The provenance
accurately states that the owner requested execution after receiving the explicit merge/hold
proposal. This is traceable repository evidence, although it is not a cryptographic signature or
external identity proof.

Completing a family merge still does not make the family promotion eligible. That may look
conservative, but the human target is itself provisional and the Wiki rows still lack verified
colors. The accepted outcome is therefore a knowledge relationship inside the review layer, not a
new canonical entity.

### Decision changes

T32's queue contract allowed four outcomes, while T34 deliberately narrows this particular batch to
family scope with variant hold. This prevents a broadly worded follow-up request from accidentally
granting release-level approval. Future priority-2 batches may use create/hold/reject, but they must
pass their own evidence requirements.

The project also moves from “zero human decisions” to “four project-owner family decisions,” while
leaving the accuracy/evaluation boundary unchanged. Documentation now distinguishes family linkage,
variant verification, canonical promotion, and evaluation labels as separate states.

### Verification evidence

Four completed decisions target the exact human candidates for `'67 Chevy C10`, `Purple Passion`,
`Subaru BRZ`, and `Tesla Model S Plaid`. Forty-nine decisions remain pending. Nine Wiki release
variants remain held, and promotion-eligible and newly canonical records both remain zero.

The decision checksum is
`ef17632c486850ab8f39604462e474c8c0e97894a8a8fc0003aef58b5fab03f0`; the adjudicated queue
checksum is `6ab11ddef990e31918e507372c451cc0bfce531d7c9ec41e91ecc680288d0082`;
the readable result checksum is
`bd916df6b82866f87766c5ab038646d6aee90c4dd69e93a57120aef91cbaf023`.

Five focused tests passed, including the invalid-target failure. The complete host suite passed
99/99. T30–T33 deterministic checks, fixture validation, Python compilation, both Compose
configurations, and whitespace checks passed. T34 made no network request, PostgreSQL write,
canonical catalog edit, runtime change, or AI-evaluation mutation.

### Incomplete work, risks, and next step

The four relationships point to a provisional human-backed catalog, not the canonical catalog.
They cannot yet answer which 2025 toy number corresponds to which color or whether a Wiki release
matches the existing human provisional variant. The conversation-based owner provenance is
auditable but not signed.

The remaining work is the 49 priority-2 families. Before any `create_new_casting` decision, the
project needs independent text-source confirmation that the normalized Wiki name is a real distinct
casting rather than an alias, punctuation difference, or incomplete catalog coverage. That research
should be performed in bounded batches before any database scaling.

## 2026-09-08 — Four side-by-side packets make the first decisions reviewable

### What was executed and what problem it solves

T32 created a clean 53-family queue, but the four priority-1 entries still pointed to IDs rather
than showing why a reviewer should accept or reject them. T33 assembles the evidence needed for
those first bounded decisions. For each exact-name family it places every Wiki release row beside
the retained human label, original source name when available, structured series/variant fields,
source case IDs, provisional variant ID, and target human casting ID/UUID.

The evidence reveals an important boundary that a name-only table hides. All four pairs clearly
refer to the same named casting family, but their releases are not automatically the same variant.
The 2015 green `'67 Chevy C10` human record differs from the 2025 HW Hot Trucks rows; the Purple
Passion human label says 2026/pink while the Wiki rows are 2025 HW Designed By; Tesla's human red
label lacks matching Wiki color evidence. Subaru BRZ shares a 2025/Zamac clue, but its human series
is Walmart Exclusive while the Wiki series is HW J-Imports.

### Code changes and why they were made

`build_fandom_priority_one_evidence.py` validates the T32 queue checksum and pending-state boundary,
requires exactly one human casting candidate per priority-1 family, rechecks normalized brand and
casting equality, and joins the family with `human_backed_catalog.json`. It retains both
`human_label_names` and `initial_names`; this matters because the initial text carries year or
listing context that a cleaned human label may omit.

The builder emits `priority-1-evidence.json`, a human-readable Markdown report, and a manifest that
freezes the queue, queue manifest, human catalog, and both outputs. It calculates only explicit
facts: source rows, release years, series sets, exact normalized family equality, and shared tokens
between the Wiki variant notes and human variant labels. It does not infer colors, dates, or release
identity from the prose.

Each packet contains two deliberately separate recommendations. The casting-family recommendation
is `merge_existing_family`, targeting the exact human casting. The variant recommendation is
`hold`, with `variant_identity_verified=false`. Reviewer confirmation fields remain empty, and the
family remains promotion-ineligible. Five tests freeze the four families, nine Wiki rows, exact
targets, retained evidence, Subaru `zamac` fact, family/variant boundary, hashes, and deterministic
regeneration.

### Technical choices, alternatives, and trade-offs

The evidence packet reuses frozen repository inputs rather than fetching four more web pages. The
purpose of this decision is to judge whether the two already-governed sources refer to the same
casting family; the exact names and recorded provenance are sufficient to pose that limited
question. Additional web research would be necessary for release/color promotion, which is
explicitly outside this packet.

The code reports shared variant tokens but does not turn them into a match score. A score would look
precise without a validated relationship to correctness. Showing `zamac` directly for Subaru is
more honest: it helps the reviewer understand why the release may be related, while differing
series labels and null Wiki color keep the variant held.

A single yes/no family question per packet was chosen instead of asking the user to interpret raw
UUIDs or decide every Wiki release at once. This keeps the immediate review small without weakening
the audit boundary. The trade-off is that even an accepted family merge will not increase the
canonical release count yet.

### Decision changes

The previous queue treated all evidence references as future reviewer work. T33 now pre-assembles
the repository evidence for priority 1 so the reviewer does not need to search across files. It
does not populate the reviewer's evidence field, because selecting which evidence justifies a
decision remains part of the reviewer-owned act.

The earlier shorthand “merge these four” is also narrowed to “recommend merging the casting family
only.” Variant identity remains held even for Subaru. This prevents a valid family conclusion from
silently granting invalid year/color/series equivalence.

### Verification evidence

Four packets cover nine unique Wiki source rows and exactly four human casting targets. Each target
passes exact normalized brand/casting equality, has retained human source cases and provisional
variant evidence, recommends a family-only merge, holds the variant, and remains pending and
promotion-ineligible. Only Subaru has a shared explicit variant token: `zamac`; its series sets are
not exact.

The packet checksum is
`4d6ede8ba1bbb3447f2d403885d4d68bb9d71893cbf012994b2be37e77ad8294`; the Markdown checksum is
`077d9b078514b8628b99244936f426652a46679f4e74642858c00c8067db98ab`.
The deterministic `--check` passed, five focused tests passed, and the complete host suite passed
94/94. T30–T32 checks, fixture validation, Python compilation, both Compose configurations, and
whitespace checks passed. No network request or database/runtime mutation occurred.

### Incomplete work, risks, and next step

No human decision has been recorded. The evidence packet uses stored labels and does not prove the
source listings themselves are still available. Exact family naming can support the proposed
family relationship but cannot establish individual release identities or resolve missing colors.

The next step is for the project owner to accept or reject the four family-only recommendations.
Acceptance means only “these Wiki rows and this human draft belong to the same named casting
family”; all nine release rows remain variant-held. Once the answers are given, a validator can
record reviewer/time/reason/evidence and update the queue without creating canonical database rows.

## 2026-09-08 — A 53-family queue makes human adjudication explicit

### What was executed and what problem it solves

T31 reduced 100 Wiki rows to 53 casting-family relationships, but its row-level JSON was still a
machine pre-review rather than a practical human workflow. T32 prepares the actual adjudication
queue. It groups every source row under one stable family-review ID, puts the four exact
human-catalog candidates first, places the remaining 49 research-required groups second, and emits
both a machine-readable queue and a Markdown worksheet that a non-programmer can inspect.

This solves two different risks. First, it prevents a reviewer from issuing the same casting
decision two or three times merely because one model has several release/color rows. Second, it
makes the absence of completed human review visible: all 53 decision objects are pending, their
reviewer fields are empty, and none is eligible for promotion or PostgreSQL ingestion.

### Code changes and why they were made

`build_fandom_adjudication_queue.py` validates the T31 report against its manifest, rejects
duplicate source IDs or rows that have already crossed the review boundary, groups by the frozen
normalized family key, unions exact candidate IDs, preserves every contributing toy/collector/
series/variant row, and assigns stable SHA-derived family-review IDs. Exact-candidate groups receive
priority 1; groups requiring source research receive priority 2.

The generated `adjudication-queue.json` defines a closed decision contract:
`merge_existing_family`, `create_new_casting`, `hold`, or `reject`. A completed decision must state
who decided it, when, why, and which evidence supports it. Creating a new casting additionally
requires independent source confirmation. `adjudication-queue.md` renders the same queue as two
plain tables, making the work accessible without editing or understanding the larger JSON files.

The queue manifest freezes both T31 input files plus the JSON and Markdown outputs. Build mode
writes all three outputs; `--check` rebuilds them in memory and rejects any byte difference. Five
tests verify complete one-time source coverage, stable unique family IDs, priority ordering, the
four exact human candidates, the closed decision contract, all-pending safety, hashes, and
determinism.

### Technical choices, alternatives, and trade-offs

The unit of human work is a casting family, not a Wiki row. This reduces the decision count from 100
to 53 while retaining nested release evidence. It does not merge the releases themselves: a family
decision can confirm that two sources discuss `Subaru BRZ`, but color, series, toy number, edition,
and rarity remain separate variant questions.

The queue is stored as JSON plus Markdown instead of adding a database admin UI. JSON provides a
strict future automation contract; Markdown gives the project owner a readable worksheet and clean
Git diff. A full UI could improve ergonomics later, but building authentication, concurrent edits,
and audit storage before validating the decision model would expand this Lite milestone without
improving identity evidence.

No entries were filled on behalf of the user. Although an AI can suggest that an exact name should
be reviewed for merge, recording that as `human verified` would create false provenance. Empty
reviewer fields are intentionally treated as meaningful safety state, not incomplete formatting.

### Decision changes

The prior next step was described broadly as human adjudication. Implementation clarified that the
project first needed an artifact a human could actually adjudicate. T32 therefore completes queue
preparation while leaving the substantive decisions open. This is a narrower claim, but it creates
a defensible separation between AI-assisted organization and human-owned labels.

The decision contract also changed from an informal request for a reason to a required four-part
audit record: reviewer, timestamp, reason, and evidence references. This makes future promotion
decisions reproducible and allows a validator to reject anonymous or unsupported approvals.

### Verification evidence

The queue contains 53 stable family IDs and nests all 100 unique source rows exactly once. Four
families are priority 1 and 49 are priority 2. Completed decisions and promotion-eligible families
are both zero. The queue checksum is
`638f35d36bbf25ec0767210c038e6ee3c1e097f4f3e67d78a9bbef4a8dd45558`; the worksheet checksum is
`748ce49c0c54afe0b60e2cc7d25275a990462f8116060f105059c4dc000acd36`.

The queue's deterministic `--check` passed, five focused tests passed, and the complete host suite
passed 89/89. Fixture validation, T30 staging validation, T31 review verification, Python
compilation, both Docker Compose configurations, and whitespace checks passed. The milestone made
no network request, database write, catalog mutation, or AI-evaluation change.

### Incomplete work, risks, and next step

Every substantive decision remains pending. The Markdown worksheet is readable but not a multi-user
approval interface, and the current builder deliberately refuses to infer human identity. A later
decision validator still needs to enforce target IDs for merges, evidence for new castings, and the
required audit fields before a promotion artifact can exist.

The next step now genuinely requires reviewer input, beginning with the four priority 1 families.
After those decisions are recorded, the 49 priority 2 names require independent source checking.
Only validated decisions—not the queue or pre-review suggestions—may feed future canonical and
PostgreSQL ingestion.

## 2026-09-07 — Cross-catalog review turns 100 Wiki rows into 53 review groups

### What was executed and what problem it solves

T30 produced a safe 100-row staging dataset, but a reviewer would still have needed to open three
large JSON files and compare every name manually. T31 builds the missing bridge: a deterministic
row-level report that checks each Wiki candidate against both the canonical fixture and the
human-backed draft, while preserving the rule that only a person may approve identity promotion.

The result also exposes why “100 imported rows” is not the same as “100 new car models.” Those rows
collapse to 53 distinct normalized casting families because many models have a base release and a
second-color or other variation. Nine rows, representing four families, already have an exact
human-backed family candidate. Ninety-one rows, representing 49 families, have no exact candidate
in either reviewed catalog. None exactly match the intentionally narrow synthetic canonical
fixture.

### Code changes and why they were made

`review_fandom_catalog_pilot.py` loads the frozen Wiki staging file, `catalog.json`, and
`human_backed_catalog.json`. It builds indexes on normalized brand plus casting and emits a review
record for every source row. Each result includes the input fields needed for review, normalized
family key, match reason, exact canonical/human candidate IDs, recommended review action, and three
remaining checks: confirm casting identity, classify release versus variant, and resolve color
without image inference.

The same command supports `--check`. In build mode it writes `review.json` and a manifest; in check
mode it regenerates both entirely in memory and requires byte-for-byte equality with the committed
files. The manifest hashes all three inputs and the output, so changing the Wiki snapshot or either
catalog makes the old review demonstrably stale instead of silently reusing it.

Five tests freeze row coverage, source order, status/family counts, the four current human-family
names, candidate boundaries, disabled unsafe matching options, all-hold decisions, checksums, and
determinism. README, attribution, MVP requirements, QA review, AI-eval exclusions, evidence, and the
decision log were updated so the report cannot be mistaken for model evaluation or database
ingestion.

### Technical choices, alternatives, and trade-offs

The matcher uses NFKD ASCII normalization, case folding, and alphanumeric tokens, then requires an
exact brand/casting key. This mirrors the project's conservative human-label alignment philosophy
and handles harmless punctuation differences such as curly apostrophes. It deliberately does not
use embedding similarity or fuzzy edit distance. Those methods could surface useful suggestions,
but without a verified threshold they could merge related yet distinct Skyline, Camaro, or model-
year castings and make a review shortcut look like ground truth.

Collector number was also rejected as a stand-alone identity key. In the Wiki data, multiple color
rows share collector numbers, and the canonical fixture uses a different synthetic scope. A number
match without matching source semantics would therefore be a coincidence, not sufficient identity
evidence.

Even exact human-family matches remain non-promoting. The human catalog itself is provisional, and
the Wiki row still lacks verified color. The report consequently chooses
`review_existing_human_family` as a recommended action while keeping canonical UUID/ID null. For
unmatched rows it says `review_possible_new_casting_family`, not “new casting,” because absence of
an exact match may be caused by spelling or coverage gaps.

### Decision changes

The previous next-step wording proposed a promote/merge/reject review of all 100 rows. Implementation
showed that automatic final decisions would overstate the available evidence. T31 therefore splits
review into two stages: deterministic pre-classification now, human adjudication later. This still
reduces the workload to 53 family groups and gives every decision an evidence trail, without
claiming that code can replace source-aware review.

This also changes the practical review order. The four exact human-family groups should be examined
first because they already have related human-labelled evidence. The 49 unmatched groups follow as
possible new families. Release/color classification remains separate within each family so a
second-color row cannot accidentally create a second casting.

### Verification evidence

The frozen report contains 100 rows across 53 families. Row counts are 9
`exact_human_casting_family` and 91 `no_exact_casting_family`; family counts are 4 and 49. The
matched families are `'67 Chevy C10`, `Purple Passion`, `Subaru BRZ`, and `Tesla Model S Plaid`.
All 100 decisions are `hold_for_human_review`, and canonical promotion count is zero.

The report checksum is
`720292870a04656df0a7a61ab7d649457990e09a19172b450f4557ad878f0c4e`. The `--check` regeneration
passed, five focused tests passed, and the complete host suite passed 84/84. Fixture validation,
Wiki staging validation, Python compilation, both Compose configurations, and patch whitespace
checks also passed. T31 made no network request and no PostgreSQL or runtime-catalog write.

### Incomplete work, risks, and next step

The report is machine pre-review, not human verification. Exact spelling does not prove that a
2025 release belongs to the same variant, and no exact spelling does not prove that a family is
new. Color remains unresolved for all 100 source rows. The human-backed catalog is itself a review
draft, so its four matches cannot grant canonical identity.

The next step is human adjudication beginning with those four matched family groups. Each group
needs a recorded merge/hold/reject decision and reasoning, followed by the 49 possible-new-family
groups. Only approved rows should feed a separate promotion artifact and PostgreSQL transaction;
the raw review JSON must never be ingested directly.

## 2026-09-07 — A governed 100-row Wiki pilot starts catalog expansion

### What was executed and what problem it solves

The project previously had two useful but deliberately limited sources: 120 synthetic/curated
canonical variants and 101 human-reviewed noisy names whose identities mostly remain provisional.
Neither source tests how a larger public catalog would enter the system. T30 introduces the first
external catalog intake without prematurely treating community data as canonical truth.

The Hot Wheels Wiki robots endpoint returned HTTP 403, so the work did not begin an HTML crawler or
try to bypass that response. A single identified MediaWiki site-information request was used to
confirm the API and its reported `CC-BY-SA` rights metadata. A second request retrieved the complete
2025 mainline list at frozen revision `790665`. Because the revision response contained the whole
table in roughly 93 KB, the pilot required no individual model-page or image requests.

### Code changes and why they were made

`fandom_ingestion.py` contains the bounded network adapter and pure table parser. The adapter uses a
fixed HTTPS API origin, URL-encoded parameters, an identifying User-Agent, a 30-second timeout, a
3 MB response ceiling, and strict response/license checks. The parser selects the first sortable
table, cleans Wiki and HTML presentation syntax, preserves source markers, and splits descriptions
such as “2nd Color - Zamac” into a separate variant note. It never reads the photo cell into the
normalized record.

`fetch_fandom_catalog_pilot.py` writes three artifacts: the raw revision, 100 normalized staging
records, and a checksum manifest. Its `--raw-input` mode can rebuild normalized output from the
frozen revision without another network call. This was added after the first fetch so parser fixes
or schema reviews do not create unnecessary requests or silently move to a newer Wiki revision.

`validate_fandom_catalog_pilot.py` enforces the accepted boundary: exactly 100 records and unique toy
numbers, sequential source rows, matching raw/normalized checksums, the expected license, null
colors, null canonical UUIDs, review-only status, and no copied `File:` reference in normalized
records. Parser tests cover Wiki links, HTML, templates, series values, color-variation suffixes,
determinism, limit errors, and insufficient table rows.

The source attribution README links the exact revision and contributor history, describes every
normalization change, and states that the source-derived files retain CC-BY-SA terms. The external
directory is excluded from the runtime Docker build: the repo retains review evidence, while the
shipping API cannot accidentally load the staging snapshot.

### Technical choices, alternatives, and trade-offs

The pilot uses one completed yearly list instead of walking thousands of casting pages. A yearly
table is closer to the required product-variant grain because it includes year, toy number,
collector number, series, and series position in one revision. It also sharply reduces load and
makes the exact source reproducible. The trade-off is that the table does not contain a trustworthy
text color field and some suffixes describe release variations without fully defining their color.

Unknown color therefore remains null. Inferring “green” or “red” from a photo filename would turn
presentation metadata into unreviewed product truth, while downloading the image would introduce a
different copyright boundary because Fandom explicitly warns that media need not share the Wiki
text license. This reduces immediate field completeness but prevents a much harder-to-detect data
quality and licensing failure.

The records were not appended to `data/catalog.json` and were not inserted into PostgreSQL. A Wiki
row is a release/variation candidate, not automatically a unique casting or a canonical identity.
The accepted architecture treats collection as reversible staging and promotion as a later human
decision. This preserves the existing resolver benchmark and prevents external knowledge from
leaking into test labels.

### Decision changes

The earlier plan described future catalog expansion at approximately 3,000 rows but had no accepted
source adapter or promotion boundary. That is now narrowed into two separate milestones: first
prove revision-frozen, attributed, review-only intake; only then define promotion and scale. The
project can now reproduce external extraction, but it still cannot claim a 220- or 3,000-row
canonical catalog.

The first generated parser counted the header chunk when assigning `source_row`, making the first
data record appear as row 2. Review caught that ambiguity before acceptance. The parser now numbers
valid data rows from 1, the raw revision remains unchanged, and normalized/checksum artifacts were
regenerated offline. This decision makes source-row references understandable without another API
request.

### Verification evidence

The accepted dataset is `fandom-hot-wheels-2025-pilot-r790665-v1`. It contains 100 records with 100
unique toy numbers, sequential rows 1–100, and 45 explicit variant notes. All 100 colors and
canonical UUIDs are null. The raw checksum is
`67521e8544de2dd15527e6d2234598c7c70a1e6d9e6597fde06c88bf95854510`; the normalized checksum is
`e5e0384afcf9fb2c7924a30fd9e308ea713a785be6e1d103bde54251cbd6b9a6`.

The dedicated frozen validator passed, the complete host suite passed 79/79, Python compilation
passed, and patch whitespace checks passed. No image file was downloaded. The checked-in raw and
normalized files total under 200 KB, and neither is part of the Docker runtime context.

### Incomplete work, risks, and next step

The 100 rows still need human review before promotion. The largest unresolved field is color, and
the identity policy must distinguish a new casting, an ordinary yearly release, a second color, a
store exclusive, Treasure Hunt, and Super Treasure Hunt. Assigning UUIDs before those rules exist
would produce durable but potentially wrong identities.

CC-BY-SA attribution/share-alike obligations apply to the source-derived directory, and this record
is not legal advice. The bounded importer has implementation safeguards but did not receive a formal
security or legal sign-off. It is intentionally a manual one-shot command, not recurring scraping.

The next step is to create a review/promotion artifact for these 100 rows: compare them with the
existing canonical and human-backed catalogs, classify exact casting-family matches versus new
families, and leave unresolved records unpromoted. Only after reviewing that report should the same
revision-frozen method fetch additional completed years toward 3,000 variants.

## 2026-09-07 — Exact pgvector completes the PostgreSQL canonical retrieval pair

### What was executed and what problem it solves

T09 moved canonical text candidate generation into PostgreSQL, but dense candidates still came from
vectors calculated and searched inside each API process. T10 now gives the same deterministic
catalog vectors a durable lifecycle: a command materializes them into PostgreSQL, startup proves
that the complete expected artifact is present, and each PostgreSQL-backed request performs exact
cosine-distance retrieval through pgvector. Canonical sparse and dense sources therefore share the
database boundary while the independent human-knowledge RAG remains non-canonical.

The change solves more than storage. Previously a database could be catalog-ready while containing
zero vector rows, and the API had no way to distinguish that incomplete state. It now refuses
readiness if dense metadata is missing, the catalog/model/text version differs, the artifact
checksum changes, or even one expected UUID/version/checksum row is absent.

### Code changes and why they were made

`embedding_artifacts.py` defines a stable catalog-text contract, composite embedding version,
pgvector literal encoding, per-product checksum, and whole-index checksum. These values are derived
from sorted canonical UUIDs so the artifact does not change merely because catalog file order
changes. The vector is included in each row checksum so a change to input text or deterministic
encoding output changes the recorded artifact.

`postgres_embeddings.py` adds the `pvr-materialize-embeddings` command. It first verifies the T07
canonical catalog, then writes every `vector(192)` row and the `canonical_dense` metadata row inside
one transaction. `ON CONFLICT` makes an identical rerun safe, while identities outside the loaded
catalog are rejected instead of silently deleted. A post-commit verification ensures the command
does not report success for an incomplete artifact.

`PostgresDenseRetriever` encodes the normalized query with the same versioned model and sends the
vector, version, and limit as SQLAlchemy-bound parameters to the existing exact `<=>` query. The
database returns UUIDs and cosine similarity scores; every UUID must map back to the checksum-matched
catalog. `ResolverService` now injects both PostgreSQL sparse and dense retrievers when that backend
is selected. Debug and health output report the actual dense implementation rather than a generic
configuration label.

Compose gained a separate `materialize` job after migration and ingestion. Keeping this step
separate makes data lifecycle failures visible and lets a future model upgrade rebuild vectors
without pretending it is ordinary catalog ingestion. Unit tests cover repeatability, content-driven
checksum changes, bound query parameters, limits, empty input, and unknown UUID failure. A dedicated
T10 verifier covers the real database and API boundary.

### Technical choices, alternatives, and trade-offs

The accepted Lite implementation deliberately materializes `hashing-v1` before introducing a
sentence-transformer. This model is local, deterministic, CPU-only, and already used by the verified
offline path. It lets the project test versioning, transactional materialization, readiness, and
pgvector querying without mixing those concerns with model downloads, licensing, caches, or a new
quality claim. It remains a lexical hashing baseline and is not described as neural semantic search.

Exact cosine search was retained instead of adding HNSW or IVFFlat. With 120 current rows—and the
planned first scale check near 3,000 rows—exact search provides deterministic complete comparison
and avoids index build/tuning/recall trade-offs that have not been justified by measurements. An
approximate index becomes a valid option only after observed latency or scale requires it.

The alternative of trusting only one metadata checksum was rejected. Startup compares the expected
identity, embedding version, and checksum for every row. This costs one deterministic catalog
encoding pass during startup, but catches incomplete or stale materializations instead of letting
the API operate on a silently partial dense index.

### Decision changes

T09 intentionally left PostgreSQL mode hybrid: database sparse retrieval plus in-memory dense
retrieval. That temporary boundary is now removed for the canonical catalog. In PostgreSQL mode,
both candidate sources execute in PostgreSQL; offline mode remains unchanged and requires no
database.

T10 originally requested a pinned local embedding artifact and was marked partial because only the
in-memory hashing implementation existed. Under the accepted Lite scope, the deterministic model
identifier, dimensions, catalog-text contract, vectors, and checksums now form the pinned artifact.
The task is complete for plumbing and exact retrieval, while the materially different claim of a
neural embedding model remains deferred and explicit.

### Verification evidence

The isolated `pvr-t10` environment used host PostgreSQL port `55435`, PostgreSQL 16.14, and the
rebuilt Python 3.12 project image. Migration and ingestion completed before 120/120 embeddings were
materialized with version `hashing-v1-d192-catalog-searchable-text-v1` and index checksum
`557d7153b077624f64cdc7bd2ada824df90a683216f7c67159e22a68f20d2464`. Repeating the command produced
the same logical rows and result.

Exact dense retrieval recovered a catalog alias and all 12 matched frozen-test targets within
Top-25, for Recall@25 `1.0`. Deleting one embedding row made a newly constructed API fail readiness
with 503; rerunning materialization restored the artifact. A real Uvicorn service on
`127.0.0.1:18010` reported both PostgreSQL sparse and exact dense dependencies ready and resolved
`2022 Chevy Nomad Red #101` to `hot-wheels-chevy-nomad-2022-mainline-red-101`. Its correct candidate
ranked first in sparse, dense, structured, and RRF sources. Separate frozen examples preserved all
three policy outcomes: `matched`, `ambiguous`, and `no_match`. The final host suite passed 77/77,
including rejection of an embedding dimension that does not match the `vector(192)` schema.

### Incomplete work, risks, and next step

No PostgreSQL latency benchmark was taken, so the earlier offline/container p95 numbers must not be
applied to this path. Startup recomputes expected deterministic vectors and checksums, which is
acceptable at 120 rows but should be measured near 3,000. Row checksums prove expected provenance
and version metadata; they do not independently hash PostgreSQL's stored float bytes. Runtime health
remains a startup snapshot, although a later database loss fails the next retrieval request with
503.

The next evidence-driven action is to expand the licensed/reviewed catalog toward approximately
3,000 variants and measure exact pgvector latency and retrieval quality. A neural embedding model
or approximate vector index should be selected only if that held-out evidence shows a real gain or
performance need. The remaining T14 external pointwise reranker is likewise not justified by the
current fixture, where the existing heuristic produced zero Top-1 gain over RRF.

## 2026-09-07 — PostgreSQL sparse retrieval enters the canonical RAG path

### What was executed and what problem it solves

T07 made the canonical catalog durable in PostgreSQL, but every API lookup still searched only the
JSON-backed in-memory index. T09 now lets an explicitly selected PostgreSQL backend retrieve
canonical sparse candidates from the installed `product_search` documents. The default offline
mode remains unchanged, while `PVR_BACKEND=postgres` is now a working, readiness-checked option
instead of an intentionally unavailable placeholder.

The observable result was verified over real HTTP. A PostgreSQL-backed API reported database
version `16.14`, sparse retriever `postgres-fts-simple-v1`, and ready health, then resolved
`2022 Chevy Nomad Red #101` to the expected canonical ID. The same database retriever recovered all
12 frozen matched test targets within Top-25 and returned an exact catalog identifier at Top-1.

### Code changes and why they were made

`retrieval.py` now defines `PostgresSparseRetriever` behind the same retriever protocol used by the
in-memory sparse implementation. It converts already normalized title tokens into a bound
`websearch_to_tsquery` value, executes the existing fixed SQL statement, and maps returned UUIDs to
typed `CatalogProduct` objects. Returning an unknown UUID is an error rather than silently accepting
a database/catalog mismatch.

`postgres_retrieval.py` owns SQLAlchemy engine execution and startup verification. It checks the
installed catalog version, full-content checksum, product count, and search-document count before a
service becomes ready. `service.py` selects only the sparse implementation according to
`PVR_BACKEND`; dense and structured retrieval, RRF, calibration, policy, and the independent human
knowledge source retain their existing contracts. Debug metadata identifies the actual sparse
version. `api.py` reports the database/index versions and maps a runtime retrieval dependency loss
to HTTP 503 rather than an internal-error 500.

Compose now passes the backend switch and database URL into the API service. Docker packages the
T09 verifier, while unit tests record the SQL statement and parameters without needing a database.
The README documents migration, ingestion, and the opt-in PostgreSQL API start order.

### Technical choices, alternatives, and trade-offs

The PostgreSQL path was introduced at one retrieval boundary rather than moving sparse, dense, and
structured logic together. This makes failures attributable and leaves T10's vector model/version
questions independent. It creates a temporary hybrid canonical path—PostgreSQL sparse plus
in-memory dense/structured—but avoids pretending that empty `product_embedding` rows are a working
pgvector system.

Normalized tokens are joined with web-search `OR` for candidate generation. An all-`AND` query
would let one irrelevant seller token remove the correct product entirely; candidate retrieval
instead favors recall, while RRF, calibration, and abstention control precision later. PostgreSQL's
built-in `ts_rank_cd` was retained rather than adding a BM25 extension, matching the Lite scope and
avoiding another deployment dependency before 3,000-row evidence exists.

All title content and limits remain SQLAlchemy-bound parameters. Only a fixed repository-owned SQL
constant is executed; raw titles are never interpolated into SQL or identifier names. This matters
even though `websearch_to_tsquery` is designed for user-style input, because SQL parameterization is
the actual boundary preventing a title from becoming executable database syntax.

### Decision changes

The earlier fail-closed decision rejected every `PVR_BACKEND=postgres` configuration because no
query adapter existed. That decision is narrowed: PostgreSQL mode is now accepted only after T07
metadata and row-count verification succeeds, and only canonical sparse retrieval moves to the
database. Missing/stale data still fails readiness. Exact dense pgvector retrieval remains deferred
and the ordinary default remains `offline`.

The project also previously described PostgreSQL as entirely outside the API runtime evidence.
That is no longer accurate for sparse retrieval: both in-process API and real container HTTP paths
passed. Existing latency numbers remain offline-only, so no PostgreSQL latency or concurrency claim
was added.

### Verification evidence

The final host suite passed 71/71, including two additional API fail-closed tests. The isolated
Compose project `pvr-t09` used port `55434`, migrated PostgreSQL 16.14, and ingested all 120 fixture
products. T09 verification reported identifier Top-1, 12/12 Recall@25 (`1.0`), a forced query plan
using `ix_product_search_document`, injection-shaped bound-input safety, API readiness, and checksum
mismatch health 503. A real Uvicorn container on `127.0.0.1:18009` returned the expected matched
canonical ID and PostgreSQL sparse version.

Unit tests additionally prove that query and limit values are parameters, SQL text never contains
the injection-shaped title, invalid limits are rejected, empty token sets avoid database work, and
unknown database UUIDs fail closed. Fixture validation, Python compilation, both default and
PostgreSQL-profile Compose configuration, and `git diff --check` also passed. All isolated T09
containers, network, and volume were removed.

### Incomplete work, risks, and next step

Startup verifies database consistency, but health does not yet actively re-query PostgreSQL on every
request; a database lost after startup is detected on retrieval and returned as 503. OR-based FTS
was measured only on 120 synthetic/curated products, and its ranking quality or latency may change
with 3,000 real variants. The FTS score is not BM25, dense retrieval remains in memory, and no
external Wiki catalog has been imported.

The single highest-value next action is **T10 — materialize versioned deterministic embeddings and
execute exact pgvector retrieval**. After both PostgreSQL candidate sources work, the project can
benchmark the complete database-backed canonical path before scaling the licensed catalog toward
3,000 records.

## 2026-09-06 — Atomic PostgreSQL canonical-catalog ingestion

### What was executed and what problem it solves

The PostgreSQL schema had already passed its migration lifecycle, but the running project still had
no implementation that could put catalog knowledge into those tables. T07 now installs a complete
validated catalog snapshot through the same ingestion contract used by the in-memory tests. This
closes the gap between “the database tables exist” and “the database contains a coherent catalog.”

On the first fixture import PostgreSQL received 120 product variants, 240 aliases, 120 identifiers,
120 provenance records, 120 sparse-search documents, and one catalog metadata record. Repeating the
same import left every stored row unchanged. A deliberately conflicting import modified an early
record before failing later, and the transaction restored the entire pre-import snapshot. A second
negative case omitted one existing product and was rejected rather than silently deleting its
canonical identity.

### Code changes and why they were made

`src/product_variant_resolver/postgres_ingestion.py` implements the existing `CatalogRepository`
contract with SQLAlchemy 2 parameterized statements. One connection and transaction span every
product plus the final metadata update. Parent product identity is checked by UUID, canonical slug,
and natural-key fingerprint; aliases are reconciled by normalized text; identifiers are checked for
ownership before update; provenance is replaced only when its complete ordered content changes;
and `product_search` receives deterministic source text plus PostgreSQL's `simple` `tsvector`.

`catalog.py` now preserves the structured alias and identifier type/source records that the prior
in-memory resolver flattened into strings. The flattened values remain for retrieval compatibility,
while PostgreSQL can retain `alias_type`, `identifier_type`, and source provenance. Its checksum now
covers the complete normalized catalog representation instead of UUID/slug alone, because a casting,
series, alias, or provenance correction must produce observable version evidence.

The installed `pvr-ingest` command and Compose `ingest` service provide one documented operator
path. Docker includes the isolated verification runner, while `.dockerignore` permits only that
specific additional script. The API backend was deliberately not switched to PostgreSQL: writing
catalog rows is T07, whereas querying FTS and pgvector safely belongs to T09/T10.

### Technical choices, alternatives, and trade-offs

Atomic full-snapshot ingestion was chosen over per-product commits and truncate/reload. Per-product
commits could leave the database half-updated after record 2,500 of a future 3,000-row import.
Truncation would temporarily remove all identities and recreate unchanged surrogate rows. The
selected reconciliation keeps unchanged rows and timestamps stable but still makes all changes
commit together.

The importer also refuses to infer deletion from omission. This is intentionally conservative for
future external sources: a disappeared Wiki row could mean a parsing or export problem rather than
a retired Hot Wheels release. The cost is that genuine retirement will require a later explicit
active/retired field and policy. `product_embedding` remains empty because inserting placeholder
vectors would make T10 look complete without a versioned embedding model or checksum.

### Decision changes

T07 was previously marked partial because only `InMemoryCatalogRepository` implemented the
transaction contract. It is now complete for the 120-product Lite fixture and real PostgreSQL 16
runtime. PostgreSQL is still not the API resolver backend: this milestone promotes database
persistence only, not database retrieval, latency, or 3,000-record external-catalog readiness.

The first checksum implementation tracked only UUID and slug. That was sufficient to recognize an
identity list but would miss corrected searchable fields. The checksum was expanded before accepting
T07 so metadata changes whenever relevant catalog content changes. Structured alias/identifier
records were preserved for the same reason: source and type are database facts, not disposable
loading details.

### Verification evidence

The isolated Compose project `pvr-t07` used host port `55433` and a dedicated named volume. Alembic
upgraded an empty PostgreSQL 16/pgvector database to revision `0001`. The production repository then
passed first import, exact repeated-row comparison, mid-import canonical-ID collision rollback, and
incomplete-snapshot refusal. Counts were 120 products, 240 aliases, 120 identifiers, 120 provenance
rows, 120 search documents, one metadata row, and zero embeddings by design.

The first verification attempt exposed a string-versus-`Path` mismatch in the verification
entrypoint before any write occurred. Explicit environment-boundary conversion fixed it; the rebuilt
image passed the complete scenario and the strengthened missing-row scenario. The host suite passed
66/66 before documentation finalization, fixture checksum validation passed, Python compilation and
Compose configuration passed, and the isolated containers, network, and volume were removed.

### Incomplete work, risks, and next step

The importer expects a migrated PostgreSQL database and a complete validated canonical snapshot. It
does not crawl Fandom, create provisional identities, review licensing, materialize embeddings, or
query PostgreSQL during `/resolve`. It also does not yet model retired products, so intentional
deletion is refused. The local Compose password is development-only and must not be reused outside
the loopback development environment.

The single highest-value next action is **T09 — PostgreSQL sparse retrieval**. That task will query
the populated `product_search` GIN index with bound parameters and prove that identifiers and rare
casting terms recover the correct canonical candidates before pgvector is added.

## 2026-09-06 — Human-backed catalog connected as the second RAG source

### What was executed and what problem it solves

The human-backed catalog previously existed only as a checked-in draft. This iteration connected it
to the running resolver so the project now searches two distinct knowledge corpora for every title.
The original canonical catalog path still owns final identity and abstention. The new human
knowledge path searches reviewed real-world names and exposes provisional suggestions that explain
what the system has seen before, especially when the small fixture catalog cannot return a product.

For the smoke query `Hot Wheels BMW M3 GT2 Neon Speeders`, the human path ranks the reviewed BMW M3
GT2 record first, but the final response remains `no_match` with null UUID because no canonical BMW
exists in the fixture catalog. This is the intended safety boundary: the second RAG source improves
knowledge retrieval without changing a draft label into a production identity.

### Code changes and why they were made

`src/product_variant_resolver/human_knowledge.py` adds a strict loader and an independent hybrid
retriever over the 100 provisional variants. Sparse scoring uses IDF-weighted token overlap so rare
model tokens contribute more than common words. Dense scoring reuses the deterministic `hashing-v1`
embedding already shipped by the Lite runtime, and RRF combines the two ranks without directly
adding incomparable scores. A shared-token gate prevents the non-semantic hashing baseline from
returning candidates for wholly unrelated input.

`ResolverService` loads both catalogs, runs `human_knowledge_retrieval` after shared signal
extraction, records a separate timing/span and candidate count, and includes bounded human results
only in debug payloads. The canonical candidate list alone continues into reranking, calibration,
policy, and final product selection. `schemas.py` therefore gives human candidates explicitly
provisional fields instead of reusing `CandidateDebug`, which would incorrectly imply canonical
identity. `config.py`, `.env.example`, Dockerfile, and `/health` expose the new required catalog and
index versions; a missing human catalog makes readiness fail rather than silently claiming Dual RAG.

The debug UI now renders a separate Reviewed-name candidates table with a visible warning that the
rows are retrieval evidence only. Human names and even markup-like text are assigned through
`textContent`, preserving the existing untrusted-input boundary. Default API responses remain
unchanged and continue to omit all debug data.

### Technical choices, alternatives, and trade-offs

The new source deliberately does not merge its provisional records into the canonical catalog and
does not override `no_match`. Merging would make the existing calibrator and thresholds operate on a
different identity space without training evidence. Allowing a human hit to override policy would
produce apparent coverage immediately, but would erase the distinction between a reviewed name and
a fully specified canonical variant.

Running the second retrieval on every request makes the Dual RAG execution boundary observable and
keeps timing evidence honest. The trade-off is additional CPU work even when debug is false; the
catalog currently has only 100 provisional variants, so Lite mode accepts that cost while deferring
performance optimization until a measured bottleneck exists. The output is shown only in debug to
preserve the minimal consumer contract.

No Top-1 or Recall@K claim is made for the new path. Its indexed aliases come from the same source
cases, so evaluating those aliases against the index would measure memorization. A defensible metric
requires a separate grouped holdout or independently written noisy queries. The next task should
create that evaluation set or define the review-to-canonical promotion workflow before human
evidence influences final decisions.

### Verification evidence

The focused backend, API, observability, and UI selection passed 25/25 tests after adding an explicit
loader test that rejects any provisional variant whose status bypasses canonical review. The full
host suite then passed **64/64**. `scripts/validate_fixture_data.py` reproduced manifest SHA-256
`a4c851228939b3d12db7c879ce9c81e4ae008fd19d1032adb376b833e23c31b8`; Python compilation and
`git diff --check` both passed.

The integration evidence exercises the important product boundary, not only internal functions.
`Hot Wheels BMW M3 GT2 Neon Speeders` retrieves `BMW M3 GT2` / `Neon Speeders` first from the human
source while the API remains `no_match` with a null canonical identity. A known fixture query still
resolves through the canonical source, and default responses omit debug evidence. Health metadata
reports both human catalog and human retrieval-index versions. A missing human catalog prevents app
readiness rather than silently falling back to a single-source system.

These checks use the deterministic 100-document Lite catalog and `hashing-v1`; they do not establish
semantic quality on unseen marketplace titles, production latency under load, or a neural embedding
benchmark. The existing Starlette TestClient deprecation warning remains visible and non-failing in
the host environment. The single highest-value next action is an independently authored, casting-
grouped holdout evaluation so retrieval quality can be measured without testing the index against
its own aliases.

## 2026-09-06 — Human-backed casting catalog and provisional variants

### What was executed and what problem it solves

The conservative alignment proved that the 10-family synthetic fixture catalog cannot represent
the 97 real castings in the reviewed dataset. This iteration therefore built a separate
`human-backed-catalog-v1` instead of weakening alignment rules or overwriting the synthetic fixture.
All 101 confirmed source records are now organized into 97 casting entities and 100 provisional
variant groups that can support retrieval and a future human-review workflow.

The count difference is intentional. Three `83 Chevy Silverado` records remain three variants
because their labels distinguish blue, black, and baby-blue versions. Two `Toyota Supra` records
remain separate because one is Hot Wheels XL/Greddy and the other is Mainline/Fast & Furious. Two
`1970 Chevrolet Chevelle SS` records share the same normalized Premium/Fast and Furious structure,
so they become one provisional variant while retaining both case IDs, names, and pricing keywords.

### Code and data changes, with reasons

`scripts/build_human_backed_catalog.py` creates `data/human_backed_catalog.json` and its checksum
manifest. A casting key uses exact normalized brand and casting. A provisional variant key adds the
reviewed series and variant labels. Both levels receive deterministic UUIDv5 and readable IDs so
regeneration does not change references, while every variant remains explicitly
`needs_canonical_review`.

The catalog keeps all human names, pricing keywords, available initial names, failure categories,
and source case IDs. It does not parse missing year, collector number, scale, color, or edition from
free text. Those values may appear inside a human name, but automatically promoting them into typed
identity fields would mix interpretation with verified evidence and could make later corrections
silently remint an identity.

Focused QA initially exposed inconsistent brand display casing: the reviewed source contains both
`Hot wheels` and `Hot Wheels`, so choosing one complete spelling by frequency produced `Hot wheels`
throughout the draft. The builder now derives a stable display form from the already normalized
brand tokens, producing `Hot Wheels`, `Matchbox`, and `M2` consistently while retaining the original
human strings inside name aliases. This changes presentation only; grouping keys and stable UUIDs
remain based on the same normalized identity.

`scripts/validate_fixture_data.py` now checks the new catalog checksum against the human dataset,
count agreement, unique casting and provisional-variant identifiers, exact one-time coverage of all
101 cases, and mandatory canonical-review status. Seven focused tests cover deterministic output,
the 97/100/101 accounting, exact duplicate preservation, ID uniqueness, evaluation exclusions, and
non-merging of similar-but-distinct names. R19 and T28 record the behavior; README, decision D10,
QA, and AI-eval evidence explain why this catalog is retrieval-ready but not canonical truth.

### Technical choice and next decision

A two-level casting/variant draft was chosen over either extreme of creating 101 unrelated products
or collapsing every record with the same casting into one product. It preserves known structure
and repeated evidence without claiming that incomplete variant labels are production identifiers.
The trade-off is an additional review state and a second catalog artifact, but this boundary makes
future promotion auditable.

The next step is to connect this draft as a second, explicitly non-canonical retrieval source in the
Dual RAG pipeline. Results from that source must be presented as candidate knowledge or review
suggestions until typed attributes are verified and a promotion process mints final canonical IDs.

### Verification evidence

The builder produced 97 castings and 100 provisional variants from all 101 source records, and the
manifest recorded one merged duplicate source record. The central fixture validator passed. Seven
focused catalog tests passed, the complete host suite passed 57/57 with `PYTHONPATH=src`, Python
compilation passed, and `git diff --check` reported no whitespace errors. The already documented
host TestClient deprecation warning remained non-failing and is unrelated to this data-only runtime
boundary.

## 2026-09-06 — Conservative alignment exposes the real catalog-coverage gap

### What was executed and what problem it solves

The newly imported 101-record human-label corpus could not yet participate in canonical resolver
evaluation because the labels had no verified links to this repository's UUIDs. This iteration ran
the requested catalog-alignment step and created a deterministic, reviewable status for every
record. The outcome is 0 canonical mappings, 2 exact casting-family-only matches, and 99 unmapped
records. The two partial matches are `Toyota Supra`; each still has 12 possible synthetic variants,
so neither receives a UUID.

This result identifies the actual constraint rather than hiding it behind a similarity score. The
current fixture catalog contains 10 synthetic casting families, while the human corpus contains 97
real casting names. The next accuracy bottleneck is catalog coverage and variant provenance, not
the mechanics of matching the two JSON files.

### Code and data changes, with reasons

`scripts/align_human_labeled_names.py` builds
`data/human_labeled_catalog_alignment.json` plus a checksum manifest. Each row retains its human
name fields, alignment status, reason, nullable canonical identity, matched family, and possible
canonical IDs. Exact Unicode/punctuation-normalized brand and casting are required for a family
match. A UUID additionally requires exact series and one variant discriminator—color, edition, or
rarity tier—to reduce the family to one unique product.

Fuzzy string matching was intentionally excluded from label creation. It would be useful as a
retrieval signal, but unsafe as ground truth: for example, `Dodge Challenger` versus `Dodge
Charger`, a chassis-specific Skyline versus a generic Skyline family, or a real 2000 Chevy Nomad
versus synthetic 2022/2023 variants can look textually close while representing different product
identities. The conservative policy allows those items to remain visible as unmapped instead of
silently assigning an incorrect UUID.

`scripts/validate_fixture_data.py` now verifies the alignment checksum, source dataset checksum,
catalog checksum, complete case-ID coverage, status values, and UUID/slug integrity. Five focused
tests cover the current 0/2/99 result, the 12-candidate Toyota Supra families, null identities for
unmapped rows, frozen inputs/output, and deterministic regeneration. R18 and completed task T27
were added to the Lite brief; README, QA review, decision D9, and the AI-eval evidence document now
state that this is a catalog-coverage measurement rather than an accuracy result.

### Technical choice and next decision

The method uses standard-library normalization and exact structured fields instead of adding an
embedding model or fuzzy-matching dependency. This keeps the alignment deterministic, auditable,
and appropriate for the Lite workflow. The trade-off is deliberately low automatic coverage: it
prefers a review queue over false canonical labels.

The next data task should not weaken the threshold. It should define how reviewed names become a
separately versioned, human-backed catalog: deduplicate repeated scans, settle whether series and
variant fields describe the product or marketplace listing, add provenance, mint stable IDs, and
then create a casting-family grouped evaluation split. PostgreSQL ingestion T07 remains valuable,
but loading a broader catalog should follow a clear source-of-truth decision.

### Verification evidence

The alignment command processed all 101 records and reproduced the frozen 0 mapped / 2
casting-family-only / 99 unmapped counts. The central fixture validator passed with both input and
output checksums linked. Five focused alignment tests passed, the complete host suite passed 50/50
with `PYTHONPATH=src`, Python compilation passed, and `git diff --check` reported no whitespace
errors. The existing host TestClient deprecation warning remains an environment/dependency warning
already documented by the project; it did not cause a test failure.

## 2026-09-06 — Human-labeled real-noisy names added as an auxiliary dataset

### What was executed and what problem it solves

The project previously relied on a 100-case synthetic/curated benchmark. That fixture is useful for
proving the resolver architecture, but it does not show how recognition output differs from a
person's verified answer on real noisy scans. This iteration imported the user-approved local
labeling queue into `human-labeled-real-noisy-v1`. The new corpus contains 101 confirmed human
labels: 91 records have both the original top recognition name and the human-verified name, and 10
records preserve the fact that recognition returned no candidate while still retaining the human
answer. Four rows explicitly excluded during the earlier human review were not imported.

This solves two immediate problems. First, future work can measure name cleanup and candidate
selection against real reviewed examples instead of relying only on generated titles. Second,
failed recognition attempts are represented as data rather than disappearing from the sample,
which prevents coverage from looking better simply because empty outputs were dropped.

### Code and data changes, with reasons

`scripts/import_human_labeled_names.py` was added as a deterministic CSV-to-JSON boundary. It
requires the source columns used to distinguish `candidate_1` from `human_expected_candidate` and
the normalized human casting/pricing fields. Included rows must have confirmed human labels;
candidate confidence must be numeric and bounded; duplicate case IDs fail the import. The generated
record uses the explicit fields `initial_name` and `human_label_name`, so a beginner reviewing the
data can see the before/after pair without reconstructing meaning from the old labeling workbook.

The importer writes `data/human_labeled_names.json` and a separate frozen manifest. The manifest
records the source checksum and generated dataset checksum rather than a machine-specific absolute
path. Local frame paths and images were not copied because the current Product Variant Resolver is
a text-first Dual RAG project and the requested evidence is the name pair; omitting those paths also
keeps this repository portable when only the `Product Variant Resolver/` folder is pushed.

`scripts/validate_fixture_data.py` now validates the auxiliary corpus alongside the original
catalog and benchmark. `tests/test_human_labeled_names.py` checks the 101 total records, the 91/10
paired-versus-no-candidate split, confirmed human labels, unique IDs, checksum integrity, and the
declared evaluation exclusions. The MVP brief adds R17 and completed task T26, while the QA review,
README, decision record, and AI-eval evidence explain the data boundary and its limitations.

### Technical and method choices

JSON was selected as the checked-in runtime format because the existing project already uses
versioned JSON fixtures and can validate them with Python's standard library. Keeping XLSX as the
runtime source would add spreadsheet parsing dependencies and make automated validation harder;
copying the CSV would retain many source-only workflow columns and local frame paths that this
project does not need. A deterministic importer preserves the option to regenerate the compact
artifact from the original review queue while allowing GitHub users to inspect the resulting data
without the source project.

The real-name corpus was not merged into `benchmark.json`. Those 101 labels describe reviewed
names, but they have not yet been mapped to this repository's immutable canonical UUIDs and slugs.
Using them immediately for canonical accuracy or calibration would turn text similarity into an
unsupported identity claim and risk label leakage. They are therefore limited to candidate-name
evaluation, name-normalization evaluation, and future catalog alignment. Once mappings and a
casting-family grouped split exist, a qualified subset can be promoted into the formal benchmark.

### Verification evidence and remaining limitation

The central fixture validator passed with the new corpus included. Four focused human-label tests
passed, and the complete host test suite passed 45/45 with `PYTHONPATH=src`. Python compilation and
`git diff --check` also passed. A first complete-suite command omitted `PYTHONPATH=src` and therefore
could not import the package; rerunning with the repository's documented module path passed, so
that attempt is recorded as an invocation error rather than a product failure.

Targeted Ruff and mypy were not rerun in this host interpreter because those optional development
modules are not installed. An offline `uv` attempt could not access its external cache under the
workspace sandbox. The added code is covered by compilation and behavioral tests, but static-tool
verification should be repeated in the pinned development or Docker QA environment before a later
release claim expands beyond this Lite data milestone.

## 2026-09-01 — Lite/MVP fixture implementation and handoff

### Context, problem, and observable outcome

This iteration ran in **Lite / MVP Mode**. The starting specification described a production-shaped
resolver—catalog-backed identity, hybrid retrieval, reranking, calibrated abstention, an API, and a
reproducible benchmark—but the useful first delivery had to be demonstrable without claiming that
PostgreSQL, pgvector, external models, or a real marketplace catalog already worked. The engineering
problem was therefore twofold: build a complete resolution loop that could run offline, and make
every resulting claim traceable to a frozen fixture and an explicit runtime boundary.

The delivered offline path now accepts a noisy title, extracts generic syntax and catalog-derived
hints, retrieves candidates through sparse, dense, and structured signals, fuses them with RRF,
calibrates the leading candidate, and returns `matched`, `ambiguous`, or `no_match`. FastAPI exposes
that path through `/resolve` and `/health`; the default response omits internal evidence, while
`debug=true` returns bounded signals, ranks, conflicts, model versions, and stage timings. The
observable result is a versioned `fixture-v1` report over 21 synthetic test cases rather than an
unsupported production claim: Recall@25 and Top-1 are `1.0`, hard-negative accuracy is `1.0` (4/4),
precision is `1.0`, false-match rate is `0.0`, and coverage is `0.8333`.

Focused re-verification exposed three places where the implementation and its claims needed to be
tightened. First, series text needed to be treated as catalog knowledge, not an application-coded
rule, and a wrong series needed to remain a visible soft conflict rather than filter out the correct
candidate. Second, the heuristic reranker had been available in the pipeline without evidence that
it improved the fused ranking. Third, latency needed an HTTP-level measurement and an explicit
statement of what that measurement excluded. After correction, catalog-provided series values
produce `series_hints`; a target with a conflicting series remains in the top 25 and records
`structured_conflicts=["series"]`; RRF and the heuristic reranker both score Top-1 `1.0` on the same
12 matched frozen-test cases; and the report retains warmed in-process ASGI samples while stating
that Docker, TCP, reverse proxy, database, and concurrency were not measured.

### Implementation trace

The implementation was organized by pipeline responsibility so that each claim has a narrow code
and test surface:

- `data/`, `scripts/generate_fixture_data.py`, and `scripts/validate_fixture_data.py` establish the
  frozen catalog, benchmark, grouped split metadata, checksums, provenance, and fixture validators.
  This was necessary to make evaluation reproducible and to prevent synthetic data from being
  presented as scraped marketplace truth.
- `src/product_variant_resolver/{identity,catalog,ingestion}.py` defines immutable UUID/slug
  behavior, normalized catalog records, and idempotent in-memory ingestion.
  `src/product_variant_resolver/{signals,schemas}.py` keeps syntax
  extraction typed and generic. The series correction was implemented through the catalog-derived
  vocabulary assembled in `src/product_variant_resolver/service.py`, passed into
  `extract_signals`, and represented as
  `series_hints`; no Hot Wheels series branch was added to application code.
- `src/product_variant_resolver/retrieval.py` contains the token sparse baseline, deterministic
  `hashing-v1` dense baseline,
  structured match/conflict features, RRF, and fail-closed retrieval orchestration. Series joins
  year, color, collector number, and series position as a soft structured feature so conflicting
  evidence remains inspectable instead of destructively pruning a candidate.
- `src/product_variant_resolver/{rerank,service,config}.py` provides the pointwise interface, optional
  `heuristic-v1` implementation, pipeline assembly, and runtime selection. `reranker_enabled`
  defaults to false; when disabled, debug and health metadata report `disabled` instead of implying
  that a reranker ran.
- `src/product_variant_resolver/{calibration,policy,training}.py` implements logistic calibration,
  train-only model
  fitting, dev-only threshold selection, artifact/version checks, and the three-state decision
  policy. Training and evaluation both use the same catalog-derived color and series vocabulary,
  avoiding a mismatch between runtime and offline scoring.
- `src/product_variant_resolver/{api,observability}.py` and `ui/` supply structured request
  validation, error mapping,
  readiness, request correlation, privacy-safe logging, stage timings, and the minimal debug UI.
  API-provided strings are rendered as text, and raw titles are not placed in resolution logs.
- `src/product_variant_resolver/{evaluation,reporting}.py`,
  `scripts/generate_evaluation_report.py`, and `reports/fixture-v1/` preserve raw ranks, decision
  counts, latency samples, derivations, configuration, disclaimers, and SVG summaries. Reporting
  now records `selected_default="rrf"`, the exact reranker gain,
  whether an external cross-encoder was evaluated, and whether container latency was measured.
- `tests/unit/`, `tests/integration/`, `tests/api/`, `tests/evaluation/`, and `tests/ui/` cover identity,
  parsing, soft conflicts, fusion, calibration/policy guards, three-state resolution, fail-closed
  behavior, report disclosures, and UI rendering. `migrations/`, `Dockerfile`, and
  `docker-compose.yml` preserve future persistence/deployment boundaries, but their presence is not
  counted as runtime verification.

### Technical choices, alternatives, and trade-offs

The default retrieval path uses deterministic token overlap plus `hashing-v1` vectors because both
run offline and make the fixture loop reproducible. The specification's PostgreSQL FTS and exact
pgvector path remains the intended scalable alternative, while a pinned sentence-transformer is the
intended semantic alternative. The trade-off is deliberate: the current baselines have low setup
cost and fail no external dependency, but `hashing-v1` is not a neural embedding and the measured
fixture accuracy cannot establish semantic recall on real marketplace titles.

RRF was chosen over direct addition of sparse and dense scores because the component scores live on
different scales, while RRF needs only ranks and remains deterministic. Weighted score fusion could
eventually learn more domain-specific signal weighting, but it would add tuning risk to a 100-case
synthetic benchmark. Structured attributes therefore contribute explicit matches and conflicts
without becoming hard filters, preserving recall when seller titles contain an incorrect year,
color, or series.

Calibration and abstention were retained instead of an always-pick-Top-1 policy because an entity
resolver must refuse weak or near-tied evidence. The calibration model is fit on grouped train data,
thresholds are selected on grouped dev data, and test labels are held for final evaluation. This
adds artifact and policy-version management, but it makes `ambiguous` and `no_match` first-class
outcomes and exposes the precision/coverage trade-off.

The pointwise reranker underwent an explicit **selection reversal**. Before the frozen comparison,
the architecture allowed the local heuristic after RRF as a normal pipeline stage. Catalog-derived
series handling then strengthened the generic retrieval and structured evidence, and the same 12
matched test queries produced Top-1 `1.0` for both RRF and `heuristic-v1`. The measured absolute gain
was therefore `0.0`, below the R11 `0.05` value gate. After that evidence, the runtime default was
changed to RRF, the heuristic became an opt-in/offline ablation via
`PVR_RERANKER_ENABLED=true`, and calibration/policy versions were aligned with the RRF path. This
avoids paying for and explaining an unproven stage while preserving a replaceable pointwise
interface. No external cross-encoder was evaluated, so this decision does not predict whether a
pinned neural reranker would help on real hard negatives.

### Verification evidence

Final QA recorded **PASS WITH RISKS** for the dependency-light fixture path. The available unit,
integration, API, UI harness, fixture, training, evaluation, and reporting suite passed 38/38;
Python compilation and fixture validation passed; calibration and dev-selected policy artifacts
were regenerated with `test_labels_accessed=false`; and both default and PostgreSQL-profile Compose
configurations passed static validation. Manual API checks observed all three decision states,
default debug omission, bounded debug candidates, structured validation failures, and fail-closed
responses for a missing catalog, PostgreSQL backend selection, unavailable external providers, and
a simulated retriever failure.

The frozen data evidence is `fixture-v1`: 120 products and 100 benchmark cases (`60 matched`,
`20 ambiguous`, `20 no_match`) across 14 casting families and 30 near-duplicate groups. Families
occur in exactly one query split, and the catalog and benchmark SHA-256 values match
`data/manifest.json`. The checked-in report evaluates exactly 21 synthetic test cases, including 12
matched cases, and retains the raw counts used by every headline metric.

Latency evidence is intentionally bounded. The latest checked-in report records internal-pipeline
p95 `1.5525 ms` and warmed in-process HTTP/ASGI p95 `7.9523 ms`, each over 21 sequential samples
after five excluded warm-up requests at candidate K=25. A separate fresh QA regeneration recorded
HTTP/ASGI p95 `2.45 ms`; both remain below the 1500 ms fixture smoke budget. These numbers include
FastAPI middleware, validation, dispatch, serialization, and response headers only for the
in-process boundary. They do not include Docker/container startup or execution, TCP/network,
PostgreSQL, a reverse proxy, concurrency, or load, and must not be reported as production latency.

Traceable sources are the [MVP brief](../specs/product-variant-resolver/mvp-brief.md),
[final QA review](../specs/product-variant-resolver/review.md),
[versioned report](../reports/fixture-v1/evaluation-fixture-v1-test.md), and
[MVP evidence](evidence/product-variant-resolver-mvp.md).

### Incomplete work, risks, and next step

The offline fixture path is demonstrable, but the original technology scope is not complete.
`PostgresRetrieverAdapter.execute_ranked` remains unimplemented; Alembic migration cycles,
PostgreSQL ingestion, FTS, exact pgvector retrieval, and live database failure behavior were not
run. The verified dense provider is `hashing-v1`, and the verified optional reranker is
`heuristic-v1`; no pinned external embedding model or cross-encoder, license/checksum, or local
model-cache flow was exercised. Selecting those unavailable providers correctly fails readiness,
but that is not equivalent to implementing them.

Docker received static configuration checks only because the daemon was unavailable. Image build,
container health, read-only filesystem behavior, Alembic execution, and the project-pinned Python
3.12 runtime remain unverified; host QA used macOS arm64 with Python 3.14.6. The UI was exercised
through a Node DOM harness rather than a live browser, post-start readiness transition is not yet
covered, the Starlette TestClient deprecation warning remains, and no formal architect, security,
or performance-agent review was performed.

The next highest-value step is to run the existing default stack in Docker on Python 3.12 and
capture container/TCP health and latency evidence without weakening the current disclaimer. If the
repository will claim PostgreSQL/pgvector or neural models as executable features, implement and
integration-test those adapters next; otherwise keep them explicitly deferred. Real catalog data
and marketplace-derived hard negatives are required before revisiting semantic retrieval,
reranking, calibration, or production-accuracy claims.

## 2026-09-01 — Docker/Python 3.12 runtime milestone

### Context, problem, and observable outcome

The preceding handoff had only static Docker Compose validation. The daemon was unavailable during
that QA pass, so the documentation correctly treated image construction, Python 3.12 execution,
container readiness, filesystem restrictions, real port forwarding, and the installed reporting
CLI as unverified. That was the largest remaining gap in the default offline MVP: source-level and
in-process evidence existed, but a user still could not point to a successful build-and-run record
for the shipped container.

This milestone closes that gap for the **default offline runtime**. A no-cache image build ran on
Docker Desktop 29.5.3/aarch64, installed the project on Python 3.12.14, started healthy as non-root
user `pvr` (UID 100) with a read-only root filesystem and writable `/tmp` tmpfs, and exposed only
the loopback-bound API port. From the host, health, UI assets, `matched`, `ambiguous`, and
`no_match` flows were observable; default responses omitted debug data and carried request IDs. A
separate missing-catalog container returned health and resolve 503 without asserting an identity.
The installed `pvr-report` command also generated and validated its JSON, Markdown, and four SVG
artifacts inside the rebuilt read-only image.

### Implementation trace

The runtime work added `scripts/measure_http_latency.py` to give host→container timing a dedicated,
repeatable measurement path instead of reusing the in-process TestClient numbers. Its output,
`reports/runtime-validation/docker-python312-http-latency.json`, freezes the boundary, environment,
warm-up/sample counts, percentile method, summary, raw samples, request payload, and explicit
inclusions/exclusions. Keeping this result separate from `reports/fixture-v1/` prevents the fixture
evaluation report's in-process ASGI latency from being mistaken for a container measurement.

`pyproject.toml` added `httpx2>=2,<3` to runtime dependencies. The reason is operational rather than
test-only: the installed `pvr-report` entry point directly uses FastAPI TestClient when it generates
HTTP samples. The runtime image therefore needs the compatible client library even when development
extras are not installed. The Dockerfile and default Compose configuration did not need a new
product architecture; the milestone exercised their existing non-root, read-only, tmpfs,
loopback-port, and healthcheck settings and captured evidence that those settings work together.

### Technical choices, alternatives, and trade-offs

Host→container latency is measured with a small standard-library HTTP script rather than folding a
live socket test into the fixture evaluator. This keeps the artifact dependency-light and makes the
boundary explicit: host `urllib`, Docker Desktop port forwarding, Uvicorn/FastAPI, resolver work,
and JSON serialization/parsing are included. An in-container TestClient benchmark would be faster
and more deterministic but would skip port forwarding; a full load tool behind TLS and a proxy
would be closer to production but would add infrastructure and concurrency questions outside this
Lite milestone. The selected sequential, concurrency-1 loopback smoke is therefore useful for
runtime verification, not capacity planning.

For reporting dependencies, alternatives included putting `pvr-report` behind a separate extra or
image, rewriting its HTTP measurement to avoid TestClient, or leaving the HTTP client in the dev
extra. Keeping `httpx2` in runtime dependencies makes the already-shipped CLI usable in the default
image with the smallest code change. The trade-off is a larger runtime dependency surface and
weaker rebuild reproducibility because versions are bounded but not locked.

### Decision changes

Before this milestone, Docker/Python 3.12 was documented as unverified and T23 remained partial;
only Compose syntax had passed. After the successful build, health/UI/three-state flow,
missing-catalog failure, filesystem/user checks, and host→container measurement, the default
offline Docker runtime is now an evidenced deliverable and T23 is complete for that Lite boundary.
This does not promote the optional PostgreSQL profile into a working resolver path.

QA also found that the reporter's HTTP client could not be treated as merely a development concern:
`pvr-report` is installed in the runtime image and invokes TestClient directly. The prior dependency
boundary therefore did not guarantee a usable shipped CLI. After moving the compatible client to
runtime requirements, a no-cache rebuild resolved FastAPI 0.141.1, Starlette 1.6.0, httpx2 2.12.0,
and httpcore2 2.12.0; `pvr-report` then produced all six expected artifacts under the read-only,
non-root constraints. The repository still has no lockfile or constraints file, and the dev extra
still lists legacy `httpx`, so this is a runtime-boundary correction rather than complete dependency
reproducibility.

### Verification evidence

The verified image was `product-variant-resolver:lite` with image ID
`sha256:f5df8cba0c0abaae77b1e01be9269cdbef2dd874be5b168da47aed5d365cc739`.
Docker reported version 29.5.3/aarch64; the container reported Python 3.12.14, UID/GID
`100(pvr)/101(pvr)`, `ReadonlyRootfs=true`, and a healthy loopback publication at
`127.0.0.1:8000`. `/app` was not writable and `/tmp` was writable. Container compile passed with
bytecode directed to `/tmp`; mounted API tests passed 8/8 and reporting tests passed 2/2. Earlier
runtime runs also passed 10 unit, 7 integration, 4 evaluation-metric, and 5 fixture tests, while
direct container evaluation retained Recall@25 `1.0`, Top-1 `1.0`, hard-negative accuracy `1.0`,
precision `1.0`, coverage `0.8333`, and false-match rate `0.0`.

The checked-in [Docker latency artifact](../reports/runtime-validation/docker-python312-http-latency.json)
contains 50 finite sequential samples after 10 warm-ups. Sorting those samples and applying the
recorded nearest-rank rule, `ceil(0.95 * 50) - 1`, reproduces p95 **`4.721208 ms`**; median is
`2.7867085 ms` and mean is `3.14272922 ms`. The test used one local macOS arm64 machine,
concurrency 1, loopback, and the offline-memory backend. Container startup, warm-ups, TLS, reverse
proxy, remote network, concurrent load, and PostgreSQL are excluded. This is a runtime smoke result,
not production latency.

The no-cache reporter verification generated exactly one JSON, one Markdown, and four SVG files.
The JSON passed `validate_report_payload`, retained 21 in-process HTTP samples and the exact
21-case synthetic disclaimer, and correctly kept `container.measured=false` because that report's
latency is not the host→Docker artifact. The final [QA review](../specs/product-variant-resolver/review.md)
records R13 as PASS for this limited boundary, R15 as PASS WITH RISK, and R16 as PASS; the full host
suite remains 38/38 green.

### Incomplete work, risks, and next step

The verified boundary is intentionally narrow. PostgreSQL ingestion, FTS, exact pgvector search,
migration-cycle E2E, external embeddings/cross-encoders, TLS, reverse proxy, remote network,
concurrency/load, and post-start dependency failure transitions remain unverified. The runtime
artifact comes from one Docker Desktop arm64 machine and cannot support a production latency or
capacity claim. The UI still lacks a live-browser smoke beyond the Node harness, and no formal
architect, security, or performance-agent review was performed.

Dependency resolution is the next hardening priority. The successful image used compatible bounded
ranges, but no committed lockfile or constraints file ensures the same versions on a future build;
the dev extra's legacy `httpx` also continues to produce a host warning. The next highest-value step
is to freeze or constrain the verified runtime set and reconcile the TestClient dependency across
runtime and development. PostgreSQL/pgvector and external-model adapters should remain explicitly
deferred unless they are implemented and integration-tested before being claimed.

## 2026-09-02 — GitHub publication milestone

### Context, problem, and observable outcome

The publication requirement was narrower than “push the workspace.” The user explicitly wanted
only `Product Variant Resolver/` to become the GitHub repository so that the parent workspace's
`AGENTS.md`, `.codex/` agent configuration, and original `Product Variant Resolver.md` requirement
document would not enter public history. Treating the parent directory as the Git root and relying
on an ignore list would have made that boundary easier to misconfigure and harder to prove after
the fact.

Publication therefore used the existing independent Git repository rooted inside
`Product Variant Resolver/`. That repository already contained two project commits:
`5fef769` (`feat: establish offline product resolver MVP`) followed by `ad9b74a`
(`test: validate Docker Python 3.12 runtime`). GitHub publication completed successfully to the
public repository `MatthewC144/product-variant-resolver` on `main`. The local branch now tracks
`origin/main`, and both pointed to `ad9b74a` when this milestone was verified. The project is
publicly reviewable without placing the parent workspace's agent instructions or source brief in
the published history.

### Implementation trace

No product code was changed to make publication work. The important implementation boundary is the
nested repository itself: `Product Variant Resolver/.git`
owns only the project subtree, while the outer workspace remains outside that repository. The
tracked-file inventory begins with project-owned files such as `.dockerignore`, `.env.example`,
`.gitignore`, `Dockerfile`, `README.md`, configuration, fixture data, evidence, migrations, source,
tests, and UI assets. A history-wide name check returned no tracked `AGENTS.md`, `.codex/` path, or
parent-level `Product Variant Resolver.md` requirement document.

The repository remote is the credential-free HTTPS URL
`https://github.com/MatthewC144/product-variant-resolver.git` for both fetch and push. The local
`main` branch was published and configured to track `origin/main`. This project-log entry records
the publication workflow and its safety boundary; it does not copy any outer workspace content into
the repository.

### Technical choices, alternatives, and trade-offs

An independent subdirectory repository was selected over initializing Git at the parent workspace
and maintaining a large exclusion list. A parent repository plus `.gitignore` could also publish a
single project, but one missed pattern or later `git add -f` could expose orchestration files. A
subdirectory Git root makes the intended scope structural: normal Git commands cannot stage parent
files because they are outside the work tree. The trade-off is operational discipline—contributors
must run Git commands from this repository or explicitly pass its path, and parent-workspace tooling
must not be assumed to manage this history.

HTTPS was retained for the remote rather than placing a personal token in the URL or repository
configuration. The GitHub plugin was useful for verifying the authenticated account
`MatthewC144` and the public target repository, but it did not expose a create-repository
capability. The local `gh` token was also no longer valid. Alternatives were to renew CLI
authentication, switch to SSH after configuring a key, or wait for a plugin capability change.
For this one-time bootstrap, the smallest authorized path was for the user to create an empty
public repository in GitHub and then let standard Git publish the already-prepared local history.
This added one manual step but avoided inventing unsupported plugin behavior or placing credentials
in project files.

### Decision changes

The initial automation preference was to create and publish the repository through an available
GitHub integration or the local `gh` CLI. Capability and authentication checks changed that plan:
the plugin could validate the GitHub identity and repository state but could not create a
repository, while the local CLI credential could not authorize creation. Continuing with either
path would have required new authentication authority or an unsupported operation.

After that evidence, repository creation was split from code publication. The user created the
empty public `MatthewC144/product-variant-resolver` repository; the local independent repository
then added the clean HTTPS remote and performed the first push to `main`. This preserved the
subfolder-only history and avoided expanding the agent's credential or repository-creation
authority. Now that `origin` exists and `main` tracks `origin/main`, future releases do not need the
create-repository capability; they use the normal reviewed commit-and-push workflow.

### Verification evidence

The GitHub plugin verified the signed-in account as `MatthewC144` and the destination as the public
repository `MatthewC144/product-variant-resolver`. Local Git independently showed:

- `origin` fetch and push URLs are both
  `https://github.com/MatthewC144/product-variant-resolver.git`;
- the active branch is `main`, configured as `[origin/main]`;
- `HEAD`, `main`, and `origin/main` resolved to `ad9b74a` after the successful first push;
- the two published commits were `5fef769` and `ad9b74a`, in that order; and
- `git ls-files` plus a history-wide path-name search found no `AGENTS.md`, `.codex/`, or parent
  `Product Variant Resolver.md` content in tracked history.

The first push completed successfully, and the local working tree was clean before this
post-publication documentation entry was added. The remote URL contains no embedded token. This
milestone did not rerun application tests because publication did not change product behavior; the
quality and Docker evidence remain attached to the two published commits and the preceding log
entries.

### Incomplete work, risks, and next step

The GitHub plugin still cannot create repositories, and the local `gh` credential remains
unusable until the user deliberately reauthenticates it. Neither limitation blocks routine work on
the existing `origin`, but a future repository bootstrap must again use an explicitly authorized
creation path. The project is public, so future commits must continue to avoid credentials,
machine-local files, external private data, and parent-workspace instructions. Publication does not
change the previously documented product limitations around synthetic fixtures,
PostgreSQL/pgvector, external models, or production readiness.

For future remote updates, begin inside `Product Variant Resolver/`, confirm
`git rev-parse --show-toplevel` resolves to that directory, inspect `git status` and the staged
diff, and repeat the tracked-path check for `AGENTS.md`, `.codex/`, and the parent requirement file
before committing. Push ordinary reviewed commits to `origin main`, then confirm local `main` and
`origin/main` agree. Do not initialize or publish the parent workspace, embed tokens in remote URLs,
or use force-push as a routine update mechanism. Documentation changes made after the initial
two-commit publication, including this milestone record, should follow that same review, commit,
push, and remote-verification sequence.

## 2026-09-06 — Quantity `x` token-boundary correction

### Context, problem, and observable outcome

While reviewing the signal-extraction stage, a concrete false positive was reproduced from the
title `box12 Nomad`: the quantity expression treated the trailing `x12` inside the word `box12` as
an independent quantity marker. `extract_signals()` therefore returned `quantity=12` and
`multipack_hint=true`, even though the title did not contain a quantity token. This could distort
the structured evidence passed into retrieval and make an ordinary single-product title look like
a multipack.

The correction narrows only the `x` quantity syntax. After the change, an `x` must begin outside a
word, so `box12` is no longer interpreted as a quantity while the intentionally supported forms
`x12` and `x 12` continue to produce quantity 12. The observable behavior is therefore more
precise without removing the compact marketplace notation that the resolver already accepted.

### Implementation trace

The regression was captured first in `tests/unit/test_identity_signals.py`. The new coverage
asserts both sides of the contract: the embedded substring in `box12 Nomad` must not produce a
quantity or multipack hint, while standalone `x12` and `x 12` remain valid. Writing the failing
test before the fix preserved the original defect as evidence and prevented a narrow correction
from silently breaking supported input.

The product change is confined to the quantity pattern in
`src/product_variant_resolver/signals.py`. Only the `x` branch of `QUANTITY_RE` changed, gaining the
negative lookbehind `(?<!\w)`. No retrieval, ranking, calibration, policy, API, or catalog behavior
was modified. This limited scope matches the root cause: the extractor lacked a left token
boundary for one syntax branch rather than having a broader quantity-parsing design failure.

### Technical choices, alternatives, and trade-offs

The selected boundary, `(?<!\w)x`, rejects an `x` immediately preceded by a Unicode word
character while still accepting `x12`, `x 12`, and an `x` preceded by punctuation or whitespace.
It was chosen as the smallest rule that describes the intended semantic distinction: `x` is a
quantity marker only when it starts a token-like expression, not when it is part of an existing
word.

A simple whitespace requirement was considered conceptually but would be unnecessarily strict:
marketplace titles can place compact quantity markers after punctuation or at the beginning of a
title. A broader parser or post-match tokenization layer could offer more control over multilingual
and unusual listing formats, but it would enlarge the change surface without evidence that those
formats are currently required. The accepted trade-off is that this remains a regex-based,
English-oriented heuristic rather than a general quantity grammar.

### Decision changes

The earlier quantity rule implicitly allowed the `x` marker at any character position. Review
evidence from `box12 Nomad` showed that this permissive behavior was not merely theoretical: it
produced a false structured signal and a false multipack hint. The decision was therefore narrowed
from “any `x` followed by digits may indicate quantity” to “only an `x` without a word character on
its left may indicate quantity.”

The supported configuration and public signal schema did not change. Existing `lot of`, `qty`,
`quantity`, and pack-style branches were deliberately left untouched because the reproduced fault
and regression coverage concern only the standalone `x` notation.

### Verification evidence

The responsible implementation run reported that the new unit test failed before the regex change
and passed afterward. Following the correction, the signal-focused unit set passed **6/6**, the
complete `unittest` suite passed **39/39**, and `git diff --check` reported **PASS**. These results
verify the local Python test boundary and patch formatting; they do not add Docker, browser,
PostgreSQL, external-model, or production accuracy evidence.

The test run continued to emit the repository's existing Starlette/httpx deprecation warning. No
new warning was attributed to this change, but the warning remains part of the active dependency
maintenance risk and should not be represented as resolved by the passing suite.

### Incomplete work, risks, and next step

Quantity extraction still recognizes a deliberately small set of English-oriented patterns. This
milestone did not expand coverage for other languages, locale-specific notation, Unicode
multiplication symbols, or additional marketplace-specific quantity formats, and it did not
replace regex extraction with a parser. Those cases remain deferred until real catalog or listing
evidence justifies their complexity.

The highest-value next action is to continue the planned Lite-mode product work while keeping new
quantity formats evidence-driven: when a real false positive or false negative is found, add the
smallest paired regression test before changing the grammar. Separately, the existing
Starlette/httpx deprecation warning should be resolved through the already documented dependency
reconciliation work rather than mixed into signal-extraction changes.

## 2026-09-06 — Python 3.12 dependency contract hardening

### Context, problem, and observable outcome

The Lite runtime had already been exercised with Python 3.12 and Docker, but dependency resolution
was still allowed to drift inside broad version ranges. The immediate symptom was a deprecation
warning during TestClient use. Investigation traced the first cause to the development extra
explicitly installing legacy `httpx`: with Starlette 1.3+/1.6 this allowed TestClient to take its
legacy fallback path even though the project already depended on the current `httpx2` transport.
Removing that duplicate transport exposed a second, independent compatibility warning in a fresh
Python 3.12 environment: AnyIO 4.15.1 deprecated an alias still imported by Starlette 1.6.

The dependency contract is now explicit for the compatibility-sensitive Python 3.12 web stack.
Fresh constrained installation selects one TestClient transport and keeps its import warning-free;
ordinary Docker builds consume the same constraints instead of silently choosing new FastAPI,
Starlette, transport, AnyIO, Pydantic, or Uvicorn versions. This is dependency hardening for the
existing Lite application, not a product-feature or retrieval-behavior change.

### Implementation trace

`pyproject.toml` removed legacy `httpx` from the `dev` extra. Runtime `httpx2` remains because the
installed `pvr-report` command uses FastAPI TestClient, so this was not merely a test-only concern.
The direct dependency declarations continue to express supported ranges; they were not replaced
with exact pins in project metadata.

`constraints/python312.txt` was added as the selective exact-version layer for the validated web
stack: FastAPI 0.141.1, Starlette 1.6.0, `httpx2` 2.12.0, `httpcore2` 2.12.0, AnyIO 4.14.0,
Pydantic 2.13.5, and Uvicorn 0.52.4. `constraints/README.md` explains the scope, local install
command, coupled update procedure, and evidence required before promoting future versions.
`Dockerfile` now uses `python:3.12.14-slim`, copies the constraints directory, and applies
`constraints/python312.txt` through pip's `-c` option while installing the existing PostgreSQL
extra.

`tests/unit/test_dependency_constraints.py` adds executable contract checks rather than relying on
documentation alone. It verifies that every direct runtime dependency is represented in the
Python 3.12 constraints, that Docker applies the constraint file, and that development no longer
installs legacy `httpx` while the selected TestClient transport and AnyIO compatibility pin remain
present.

### Technical choices, alternatives, and trade-offs

A selective constraints file was chosen instead of converting `pyproject.toml` to exact versions.
This preserves normal Python package semantics—direct dependencies still publish bounded supported
ranges—while Docker and reproducible local verification can constrain the small stack whose
versions demonstrably interact. The alternative of leaving only broad ranges was simpler, but a
future install could reproduce either warning or introduce an unreviewed compatibility change.
A complete transitive lock would provide stronger reproducibility, but it would also expand this
Lite milestone into packaging, platform-marker, PostgreSQL, and build-tool resolution work that has
not yet been runtime-validated.

AnyIO 4.14.0 was pinned instead of suppressing the warning or accepting AnyIO 4.15.1. Warning
suppression would hide compatibility drift without removing it, while changing Starlette or the
TestClient transport again would disturb the already validated FastAPI stack. Keeping the known
Starlette 1.6/`httpx2` 2.12 combination and constraining the smallest newly identified edge made
the dependency decision evidence-driven. The fixed Docker patch tag similarly reduces unexpected
Python drift, while deliberately avoiding an architecture-specific digest so the same Dockerfile
continues to support ARM64 and AMD64.

### Decision changes

The first decision was to resolve the TestClient warning solely by removing legacy `httpx` from
development dependencies and relying on the project's existing `httpx2` runtime dependency. A
fresh Python 3.12 install showed that this was necessary but insufficient: once the legacy fallback
was gone, AnyIO 4.15.1 produced a separate alias-deprecation warning through Starlette 1.6. The
decision therefore changed from transport cleanup alone to a coupled, selectively constrained web
stack with AnyIO fixed at 4.14.0.

The runtime-image policy also narrowed from the moving `python:3.12-slim` family to the verified
`python:3.12.14-slim` patch tag, and from unconstrained pip resolution to `pip -c`. These changes do
not claim that every transitive package is locked: PostgreSQL extras and packaging dependencies
remain range-resolved. Future updates must treat Starlette, AnyIO, `httpx2`, and `httpcore2` as a
compatibility set and regenerate evidence rather than changing one pin in isolation.

### Verification evidence

The responsible implementation run created a fresh environment under `/private/tmp` with Python
3.12.13 and installed the project successfully using the new constraints. Importing and using
FastAPI TestClient was warning-free. The full suite passed **41/41** with warnings promoted to
errors via `pytest -W error`; `pip check`, targeted Ruff, targeted strict mypy, Docker Compose
configuration validation, and `git diff --check` all reported **PASS**. Docker Hub manifest
inspection confirmed that the selected `python:3.12.14-slim` base is published for both ARM64 and
AMD64.

This initially proved constrained host installation and the static dependency/Docker contract. At
that point the Docker daemon was not running, so the first record correctly stopped short of
container validation. A subsequent closure run on Docker Desktop 29.5.3 completed
`docker compose build --no-cache api` and produced image
`sha256:e67d64e95abab329c901bdb5946f86962a09dc7217e2048a3b1c0568ec8b9d75`.
The image reported Python 3.12.14, UID/GID `100(pvr)/101(pvr)`, FastAPI 0.141.1, Starlette 1.6.0,
`httpx2`/`httpcore2` 2.12.0, AnyIO 4.14.0, Pydantic 2.13.5, and Uvicorn 0.52.4. A
`python -W error` TestClient import completed without warnings, and legacy `httpx` was absent.

With the repository mounted into a read-only container and writable paths supplied through tmpfs,
the 39 backend/API/evaluation/reporting/integration/unit/fixture tests that do not require Node all
passed. The attempted full 41-test container selection was not a 41/41 pass: the UI controller
test errored because this runtime image intentionally has no Node executable. That is a validation-
environment boundary, not evidence of a UI regression; the fresh constrained host Python 3.12
environment remains the evidence for the complete 41/41 suite. In the same read-only container,
`pvr-report` generated one JSON, one Markdown, and four SVG artifacts successfully. Compose reached
healthy state; inspection confirmed `User=pvr` and `ReadonlyRootfs=true`; live HTTP checks returned
ready health plus the expected `matched`, `ambiguous`, and `no_match` outcomes, with no identity in
the latter two states.

The container closure promotes the exact selected pins from host-only to container-verified for
this Lite offline boundary. It does not change the earlier scope caveats: full-repository Ruff still
reports 36 pre-existing findings, and whole-repository mypy debt also remains outside this focused
dependency check.

### Incomplete work, risks, and next step

`constraints/python312.txt` is intentionally not a complete transitive lock. PostgreSQL extras,
setuptools/build tooling, platform markers, and indirect packages outside the compatibility-
sensitive web stack may still resolve differently, so this milestone does not establish fully
reproducible builds. It also does not resolve the 36 existing whole-repository Ruff findings or
change the previously deferred PostgreSQL runtime adapter.

The no-cache container closure is now complete for the Lite offline path. The next dependency
decision is deferred until the PostgreSQL runtime path is implemented: at that stage, evaluate a
complete transitive lock that includes its extras and repeat the same constrained build/runtime
evidence. Until then, the selective constraints must not be described as a complete lock, the
runtime image must not be expected to execute Node-based UI tests, and the existing whole-repository
Ruff/mypy findings remain explicit maintenance debt.

## 2026-09-06 — T04 PostgreSQL/pgvector migration-cycle verification

### Context, problem, and observable outcome

T04 already had an Alembic `0001` migration describing the PostgreSQL/pgvector catalog schema,
but the repository did not yet contain runtime evidence that a new database could apply it,
reverse it, and apply it again without schema drift. The task therefore closed the verification
gap rather than redesigning the database: the existing migration schema required no changes.

An isolated PostgreSQL 16/pgvector database now completed the full
empty → upgrade `0001` → downgrade `base` → upgrade `0001` cycle. Both upgraded states were
inspected and found equivalent. The observable result is a reproducible T04 check that verifies
the seven application tables, their identity and integrity constraints, the required indexes and
specialized PostgreSQL types, the `vector` extension, and final Alembic revision `0001`.

### Implementation trace

`scripts/verify_postgres_migration.py` was added as the executable verification boundary. Before
making any migration change it requires an empty application schema, then drives Alembic through
the complete cycle and inspects PostgreSQL metadata after each upgrade. The runner asserts all
seven application tables; their primary keys; the required product, alias, and identifier unique
constraints; the complete normalized release-year expression; and each cascade foreign key from
its source column to `product_variant.canonical_uuid`. Index checks bind table, index name, access
method, ordered columns, and column order rather than accepting a name/method match alone. The
runner also verifies `product_search.search_document` as `tsvector`,
`product_embedding.embedding` as `vector(192)`, removal of the application tables after
downgrade, and final database revision `0001`. Alembic's `script_location` is resolved to an
absolute repository path so execution does not depend on the caller's working directory.

`Dockerfile` now includes this runner so the verification can execute from the same constrained
project image used by the repository. `.dockerignore` was narrowed only enough to allow
`scripts/verify_postgres_migration.py` into that build context; other scripts remain excluded.
The existing `migrations/versions/0001_initial_catalog.py` schema was left unchanged because the
runtime assertions matched its intended contract. No API, resolver, fixture, retrieval, or
calibration code changed as part of T04.

### Technical choices, alternatives, and trade-offs

A committed, fail-fast runner was selected instead of documenting only a sequence of manual
Alembic and `psql` commands. Manual commands could demonstrate one successful attempt, but they
would leave important checks dependent on operator memory and make the downgrade/second-upgrade
comparison difficult to repeat consistently. The runner turns the intended migration contract
into executable assertions and produces a structured result that a future developer or CI job can
re-run against a disposable database.

The accepted trade-off is deliberate strictness: this runner is for isolated, empty databases and
refuses to operate when application tables already exist. It is not a general database diagnostic
or an upgrade tool for developer or production data. The empty-schema guard deliberately inspects
application tables, not every possible schema object, so it must still be paired with a disposable
database rather than treated as a universal safety detector. Schema assertions use PostgreSQL
catalog and SQLAlchemy inspection rather than adding a second migration framework. No
approximate-nearest-neighbor index was added because T04 only establishes the schema and the
planned T10 path requires exact pgvector retrieval at MVP scale; an ANN structure would add
maintenance and tuning without a current acceptance requirement.

### Decision changes

The prior project record treated PostgreSQL migration cycling as deferred because only migration
files and static Compose configuration had been reviewed. Runtime evidence from the isolated
cycle now promotes T04 itself to complete: the database can be created, downgraded, and recreated,
and the resulting constraints, indexes, types, extension, and revision are explicitly checked.
This does not promote the broader PostgreSQL resolver path, because ingestion and retrieval remain
separate tasks.

The downgrade policy intentionally removes the application schema while leaving the `vector`
extension installed. Extensions can be shared by other schemas or applications in the same
database, so automatically dropping it would create a wider destructive boundary than T04 needs.
Consequently, the runner checks that application tables are gone after downgrade but does not
misrepresent retention of the shared extension as a failed rollback.

QA follow-up initially identified three ways a schema check could pass too loosely: indexes could
match without proving their ordered columns, foreign keys could match without proving their target,
and the release-year check could be accepted from partial numeric fragments. The runner was
narrowed to compare complete index tuples, complete source/target/delete-action foreign-key tuples,
and the normalized full check expression. The absolute Alembic script path additionally removes a
working-directory assumption. Re-execution closed these verification risks without changing the
`0001` migration itself.

### Verification evidence

The responsible implementation run used the isolated Compose project name `pvr-t04` and host port
`55432`, keeping the verification separate from ordinary project services and local PostgreSQL
ports. It reported a successful empty → upgrade `0001` → downgrade `base` → upgrade `0001` cycle
and passed every schema assertion: seven tables, primary and unique constraints, the release-year
check, fully targeted cascade foreign keys, btree/GIN index definitions including ordered columns,
`tsvector`, `vector(192)`, the `vector` extension, and final revision `0001`. A separate sentinel
safety check created an application table before invocation and confirmed that the runner refused
to migrate or downgrade the non-empty schema. After verification, the temporary container,
network, and volume were removed.

The same implementation run reported **41/41 host tests PASS**, Python compilation of the added
runner and migration sources **PASS**, and `git diff --check` **PASS**. These results support the
migration runner, existing host behavior, and patch integrity. They do not constitute PostgreSQL
fixture-ingestion, sparse-FTS, exact-vector-retrieval, resolver-E2E, production-data, or
concurrent-load evidence.

### Incomplete work, risks, and next step

Creating the `vector` extension depends on database permissions; environments where the migration
role cannot install extensions still need administrator provisioning or a documented preinstall
step. The runner must remain restricted to disposable empty databases because its deliberate
downgrade would remove all application tables. The guard detects existing application tables but
does not inventory views, functions, types, or every other possible object in `public`, and CI does
not yet provision PostgreSQL and run this cycle automatically. Its decision to preserve the shared
`vector` extension also means the cycle does not prove complete database-level teardown. ANN
indexing remains unnecessary for the exact-search MVP and has not been implemented or evaluated.

T07, T09, and T10 remain incomplete: PostgreSQL fixture ingestion, PostgreSQL full-text search,
and exact pgvector retrieval have not been exercised by this milestone. The single highest-value
next action is **T07 — implement idempotent PostgreSQL fixture ingestion**, preserving immutable
canonical IDs and catalog/index version metadata while proving that repeated loads are identical
and invalid or colliding fixtures fail transactionally. Completing T07 will turn the verified
empty schema into a populated, repeatable database foundation for the later retrieval tasks.

## 2026-09-12 — T48.4 frozen Human Knowledge RAG v2 evaluation

### Context, problem, and observable outcome

T47 had proved that all 42 accepted family documents were wired into the second, non-canonical RAG
source, but its exact-name smoke queries could not answer the important question: can the retriever
recover a family from independently worded marketplace-like text? T48.1–T48.3 therefore froze a
separate 105-case, project-owner-approved benchmark before any candidate output was inspected.
T48.4 has now run that first scored evaluation without changing the frozen query text, labels,
retriever, catalog, RRF settings, or thresholds.

The observable result is an honest **FAIL**: eight of nine precommitted gates passed, while
lexical-variation Recall@5 reached `31/42 = 73.81%`, one retrieved case short of the required 75%.
Overall positive Recall@5 was `73/84 = 86.90%`, Recall@1 was `58/84 = 69.05%`, MRR@5 was
`65.0/84 = 77.38%`, and family coverage was `42/42 = 100%`. Marketplace-noise cases, all four
merge controls, all forbidden-family checks, and all ten unrelated controls passed. This means the
system handles seller/year/condition wrappers well, but its harder typo, abbreviation, punctuation,
and spacing behavior is not yet consistent enough to clear the frozen family-quality gate.

### Implementation trace

`src/product_variant_resolver/human_knowledge_evaluation.py` is the new read-only scoring boundary.
It verifies the benchmark and manifest hashes, every referenced input checksum, exact 105-case
composition, and the frozen source/model/index settings before constructing the existing 142-
document Human Knowledge retriever. Within each case it retrieves and serializes the Top-5
candidates before reading the `expected` label branch. It then records typed IDs, UUIDs, sparse,
dense, and RRF ranks/scores, matched tokens, expected rank, forbidden-hit ranks, and an explicit
error category. Aggregate numerators and denominators are derived only from this ordered case array;
the validator independently recomputes them before accepting the report.

`scripts/generate_family_retrieval_report.py` converts the validated JSON into the compact human-
readable report at `reports/family-retrieval-v1/evaluation.md`. It deliberately refuses to render
metrics that differ from the raw-case recomputation, shows every failed case, links the AI-eval
record, and offers a non-mutating `--check` mode. JSON and Markdown writes use temporary files plus
atomic replacement so an invalid or interrupted evaluation cannot overwrite known-good evidence.

`tests/evaluation/test_human_knowledge_evaluation.py` covers metric formulas, preserved FAIL
behavior, all evaluator failure categories, a guarded mapping that raises if `expected` is touched
before retrieval, stale-input no-overwrite behavior, the actual frozen result, and byte-identical
JSON/Markdown reproduction. `docs/evidence/ai-evals/family-retrieval-holdout-v1.md` applies the
project AI-output rubric to the measured result and narrows the allowed claim. No API, canonical
ranking, confidence policy, PostgreSQL schema/data, benchmark source, or existing retriever code was
modified.

### Technical choices, alternatives, and trade-offs

The evaluator stores full raw candidates rather than only final percentages because a number such
as 86.90% cannot show whether errors come from empty retrieval, ranking beyond K, a wrong identity
type, or a safety-control violation. The larger JSON artifact is an accepted trade-off: it enables
every result and metric to be audited and regenerated without rerunning or trusting prose. The
Markdown report contains only a compact failure table while the JSON retains all 105 cases.

The existing sparse plus deterministic feature-hashing and RRF stack was evaluated unchanged.
Adding fuzzy matching, query expansion, a neural embedding, or a wider candidate limit could likely
improve the 11 lexical misses, but doing so after seeing this test set would convert an independent
holdout into a tuning set. The selected method therefore preserves the failed gate and requires a
new v2 holdout for final evidence after any redesign. The evaluation also records the
`signals.extract_signals-v1` source checksum in its output: token cleanup participates in the actual
runtime query path, even though the earlier frozen manifest separately named the normalizer and
retriever sources.

### Decision changes

Before T48.4, independent family retrieval quality was explicitly “not evaluated”; only exact-name
wiring, type safety, and canonical isolation had passed. That status now changes to a measured
**FAIL** for the current independent family-quality gate. The earlier T47 wiring/safety result
remains valid, but it cannot be used as a retrieval-quality claim.

Because the acceptance boundary says every gate must pass, the strong overall Recall@5 and perfect
control results do not cancel the lexical-style failure. T49 PostgreSQL/pgvector scale design and
the approximately 3,000-row expansion are therefore not authorized by this result. The next product
decision must be a retrieval redesign with separate development data, followed by a newly authored
unseen holdout; it must not lower the v1 gate or rewrite the failed queries.

### Verification evidence

The formal artifacts are `reports/family-retrieval-v1/evaluation.json` and `evaluation.md`, tied to
benchmark SHA-256 `440246fb6a3b38f56fc25c1ec939d53d6cfc4457fed738aad561899325808afd`.
Their raw counts are 73/84 Top-5 hits, 58/84 Top-1 hits, reciprocal-rank sum 65.0, 42/42 family
coverage, 31/42 lexical hits, 42/42 marketplace-noise hits, 4/4 merge hits, zero forbidden family
candidates, and 0/10 unrelated non-empty results. Error accounting contains ten
`expected_identity_not_retrieved`, one `no_candidates`, and 94 `none`, totaling all 105 cases.

The focused T48.4 suite reported **7/7 PASS**. Targeted Ruff reported no findings, and isolated
strict mypy (`--follow-imports=skip`) reported no issues in the three new source/test files. The
JSON and Markdown `--check` paths reproduced the checked-in bytes. Complete repository regression,
data-chain checks, canonical fixture metrics, Compose validation, and final scope review remain the
explicit work of T48.5 and are not claimed by this entry.

### Incomplete work, risks, and next step

The 105 queries are synthetic rather than live marketplace traffic, and 42 family groups produce
wide percentage steps: one additional lexical hit would have met the minimum. They test casting-
family retrieval, not release-variant identity, canonical resolution, confidence calibration,
database scale, concurrency, or production latency. After this publication v1 is development-known
and cannot serve as an unseen final test for a modified retriever.

The immediate next step is **T48.5 — close the Lite evaluation gate**: run the full suite and frozen
data chain, verify canonical/T47 regressions, compilation, Compose configuration, repository scope,
and report reproducibility, then write the final review/evidence mapping. If those engineering checks
pass, T48 will close with a truthful quality FAIL and a documented redesign requirement—not with
permission to begin T49.

## 2026-09-12 — T48.5 Lite evaluation-gate closure

### Context, problem, and observable outcome

T48.4 produced a valid model-quality FAIL, but that result alone did not prove that the evaluator
was reproducible in the complete repository, that canonical behavior stayed unchanged, or that the
earlier human/Fandom evidence chain still validated. T48.5 therefore performed the final Lite QA
closure. It did not attempt to improve retrieval or reinterpret the failed threshold.

The outcome has two deliberately separate verdicts. Engineering verification is **PASS**: 201/201
tests, the full deterministic data chain, fresh canonical evaluation, T47 regressions, compilation,
JavaScript syntax, both Compose configurations, and repository-scope checks succeed. Retrieval
quality remains **FAIL** because lexical-variation Recall@5 is still `31/42 = 0.7381` against the
precommitted `>=0.75` gate. As a consequence, T48 is complete but T49 and the approximately
3,000-row PostgreSQL expansion are not authorized.

### Implementation trace

No product code, retriever, runtime configuration, catalog, benchmark, policy, migration, or
PostgreSQL file changed in T48.5. `specs/family-retrieval-evaluation/review.md` now maps all sixteen
requirements to executable or immutable evidence and makes the two-verdict distinction explicit.
`docs/evidence/family-retrieval-evaluation-t48.md` records the artifact hashes, raw metric counts,
full verification chain, protected-file comparison, limitations, and carry-forward decision.

The T48 requirements/design/tasks headers were advanced from build/in-progress to verified and
complete, with both T48.5 tasks checked. README and the evaluation-directory README no longer say
that scoring has not happened; they now link the reports, state the failed lexical result, and warn
that T49 is blocked. The AI-eval gained final regression evidence, while decision D36 records why
the result must not be rounded, weakened, edited, or immediately retested with a changed model.
The shared AI-output rubric index now links this scored record instead of saying independent family
quality is still unevaluated.

### Technical choices, alternatives, and trade-offs

The closure treats “did we implement and verify the evaluation correctly?” separately from “did
the retriever meet the quality bar?” This avoids two misleading outcomes: marking sound evaluation
software as broken because it discovered a model weakness, or calling the model acceptable because
the software tests passed. The accepted trade-off is a completed milestone whose headline model
verdict is FAIL; that is more useful and defensible than a cosmetically green but altered gate.

The full source chain was replayed through non-mutating check modes rather than rebuilding committed
files in place. That choice protects frozen byte identities while still proving reproducibility.
Canonical regression used a new report under an isolated temporary directory so variable local
latency samples could not overwrite checked-in evidence. Compose was parsed in both offline and
PostgreSQL profiles, but containers were not rebuilt or load-tested because T48 changes no runtime
image or database path and makes no Docker/database performance claim.

Whole-repository Ruff and MyPy were run for transparency after the project dev tools became
available. Ruff 0.16.7 reports 143 existing style findings and strict MyPy reports 817 existing
findings, including unavailable optional dependencies and legacy test annotations. Automatically
rewriting the entire repository during an evaluation closure was rejected: it would create a large,
unrelated refactor and could alter frozen source checksums. The three T48.4 evaluator/report/test
files pass targeted Ruff and isolated strict MyPy, and the full executable suite remains green.

### Decision changes

Before T48, PostgreSQL scale design was conditionally next if the independent family-retrieval gate
passed. The condition is now resolved negatively. T49 changes from “available after evaluation” to
**blocked pending a redesigned retriever and a new unseen holdout**. The current family source may
remain as debug/review evidence because all safety and canonical-isolation checks pass, but it may
not become canonical, persistent, or production-claimed.

The proposed improvement direction is intentionally not selected here. Fuzzy/character candidate
generation, field-aware ranking, query expansion, or a neural representation may address different
parts of the eleven lexical misses, but choosing among them using the final v1 outcomes would blur
development and test evidence. A new feature spec must define development data and architecture;
final evaluation then needs a separately authored and owner-approved v2 holdout.

### Verification evidence

The complete Python suite reported **201/201 PASS**. Its sole warning is the known Starlette
TestClient use of an AnyIO alias deprecated by the locally resolved dependency version; no T48 code
emits it. The deterministic checks passed from fixture and 100-row pilot through review, base queue,
priority-one evidence/decisions, all five priority-two research/decision batches, the 42/4/7 registry,
the 42-document projection, the T48 query pack, owner decisions, benchmark, JSON evaluation, and
Markdown report.

A fresh 21-case canonical fixture report retained Recall@10/25/50, Top-1, MRR@10, hard-negative
accuracy, and precision at `1.0`, false-match rate `0.0`, and coverage `0.8333`. Its local macOS
arm64/Python 3.12.13 warmed p95 values were `2.3194 ms` for the direct pipeline and `2.6189 ms` for
in-process ASGI; these exclude containers, TCP, database, concurrency, and production. T47 tests
retain the 142-document typed index, exact-name family wiring, BMW variant behavior, and Proton Saga
canonical isolation.

Python `compileall`, `node --check ui/app.js`, default and PostgreSQL-profile `docker compose config
--quiet`, and `git diff --check` passed. Diff inspection from pre-implementation T48 baseline
`b7f6ac1` found no changes to protected canonical/runtime/policy/PostgreSQL files. The first attempt
to inspect the fresh canonical JSON assumed an obsolete flat output path; generation had succeeded,
and reading the emitted versioned path immediately confirmed the expected metrics. No committed
file or result was affected by that command-path mistake.

### Incomplete work, risks, and next step

The v1 test is synthetic, family-level, and only 42 groups wide; it does not represent marketplace
frequency, release variants, canonical accuracy beyond the unchanged fixture, PostgreSQL scale,
concurrency, or production latency. It is now development-known. Full-repository Ruff/MyPy debt and
the dependency warning remain separate maintenance items, not resolved within this evaluation
milestone.

The single highest-value next action is to **write a new retriever-redesign specification** that
defines independent development data and chooses how to address token-disruption failures without
tuning against v1. After implementation, a newly authored `family-retrieval-holdout-v2` must pass
before T49 persistence or the approximately 3,000-row expansion can resume.

## 2026-09-12 — Human Knowledge retriever-redesign Lite specification

### Context, problem, and observable outcome

T48 closed correctly but did not permit the planned PostgreSQL scale step: Human Knowledge RAG v2
missed the lexical-variation gate at 31/42. The failures share an architectural cause. V2 requires
at least one exact normalized token before a document is eligible, then computes the existing
feature-hashing dense score only inside that eligible set. A misspelled single-token identity cannot
reach the dense stage, while queries retaining only generic words can rank broad provisional-
variant documents instead of the intended family.

This planning step creates the complete Lite specification for a redesign, not a patch selected
from the failed test cases. `specs/human-knowledge-retriever-redesign/` now defines twenty testable
requirements, a concrete architecture and data lifecycle, and six ordered tasks. The observable
repository state remains unchanged at runtime: v2 is still active, T49 remains blocked, and no new
development query, v3 candidate, model artifact, or holdout result exists until the owner confirms
the spec.

### Implementation trace

`requirements.md` turns the redesign boundary into EARS-style behavior. It prohibits v1 use for
selection, requires an exactly 199-case development-only pack, restricts character fields by
document type, defines deterministic character indexing/union/fusion, freezes a 21-configuration
grid and safety-first selection rule, preserves API/canonical/failure safety, adds bounded local and
synthetic-3,000-document cost checks, and requires v3 to be committed before a new 105-case holdout
v2 is authored and owner-approved.

`design.md` specifies how character bigram/trigram TF-IDF postings operate on spaced and compact
identity forms and query windows. Token-sparse candidates and threshold-qualified character
candidates form a union; `hashing-v1` dense ranking is calculated only on that bounded union; sparse,
dense, and character ranks then enter weighted RRF without fabricated ranks for missing sources.
It also defines the development report, immutable selection artifact, optional debug fields,
readiness failure, v2 evaluation lifecycle, privacy boundary, test strategy, alternatives, 10x
behavior, and likely threshold conflict.

`tasks.md` divides delivery into six auditable handoffs: freeze development data, implement the
experimental v3/API/UI path, select and freeze one config or stop, freeze a new output-blind final
query pack, obtain owner labels and evaluate once, then close QA and decide T49. The tasks contain an
owner confirmation now and another mandatory owner gate before final labels/retrieval. Decision D37,
the specification evidence, and README record the same boundary for future reviewers.

### Technical choices, alternatives, and trade-offs

Character n-gram TF-IDF was selected as the proposed first redesign because the diagnosed problem
is identity spelling/spacing rather than general semantic question answering. It is dependency-free,
offline, deterministic, explainable by scored grams, and can use inverted postings for the later
roughly 3,000-document scale. The cost is a third retrieval score, an immutable selection artifact,
and additional API/debug evidence. It is still search/IR, not a neural embedding, and the
documentation says so explicitly.

Running current hash vectors across every document would require less code, but collisions and
generic fragments would enter without an interpretable floor. Edit-distance query rewriting can
silently force an unknown word toward a known identity. Fixed family quotas could improve the
reported metric without improving relevance and could hide valid variant merges. A sentence-
transformer could add semantic power but also model downloads, cache/version/license management,
startup memory, offline packaging, and a larger evaluation surface. Lite mode therefore tests the
deterministic candidate generator first and requires a new design if it cannot qualify.

### Decision changes

The prior closure named several possible techniques but intentionally chose none. D37 now proposes
one implementation path and, just as importantly, a selection method that cannot read the v1
benchmark. The new development set is allowed to be label-derived and therefore explicitly cannot
support final accuracy. It selects only a score floor and character RRF weight from a fixed grid;
all other retrieval parameters remain constant.

T49 remains blocked rather than renumbered or bypassed. A development winner merely freezes an
experimental v3. Final permission still requires new queries authored after that freeze, explicit
owner label approval, unchanged final gates, one scored v2 report, canonical/T47/T48 regression,
and full QA.

### Verification evidence

This is a documentation-only specification milestone. File inspection tied each proposed runtime
change to the current `HumanKnowledgeRetriever`, typed schemas, service serialization, debug UI,
evaluation lifecycle, and T48 failure evidence. The 11 v1 misses were inspected by expected family,
query, returned type/ID, and matched tokens to verify the shared-token/generic-token diagnosis; no
v1 metric, query, rank, or threshold was changed or used to select a configuration.

The spec contains HRR-R1–HRR-R20, six tasks with requirement back-references and acceptance
criteria, Overview/Architecture/Interfaces/Data Models/Error Handling/Security/Testing/Alternatives,
an explicit 10x assessment, most-likely-failure analysis, and two owner gates. `git diff --check` and
repository-scope inspection are the appropriate executable checks for this planning-only change;
no product test result is newly claimed.

### Incomplete work, risks, and next step

No evidence yet shows that character TF-IDF can satisfy recall and safety simultaneously. The exact
development queries do not exist, no configuration has been executed, no v3 artifact is frozen,
and the synthetic 3,000-document budget is only a proposed gate. Neural retrieval remains deferred,
and PostgreSQL persistence remains out of scope.

The immediate next action requires project-owner confirmation of the three spec files. After that,
HRR-T1 may create and freeze the 199-case development-only pack before any v3 configuration output
is generated. If the owner changes the architecture, counts, grid, or gate policy, the specification
must be revised before implementation rather than inferred during build.

## 2026-09-12 — HRR-T1 development-only challenge-pack freeze

### Context, problem, and observable outcome

The retriever-redesign specification could not safely proceed directly to character-search code.
Doing so would allow queries and configuration boundaries to be changed after seeing which settings
looked best—the same kind of test-set tuning that the project prohibited after the v1 holdout became
known. HRR-T1 therefore creates and freezes the development evidence before any v3 candidate is
executed.

The observable result is a new 199-case `family-retrieval-development-v1` pack: 168 positive cases
cover all 42 accepted families four times, 4 controls preserve existing-family merges, 7 controls
preserve held identities, and 20 unrelated controls divide evenly between opaque zero-overlap and
generic marketplace text. The pack and manifest both state that the questions are development-only,
derived from indexed/governance identities, and ineligible for final accuracy. No retriever output,
configuration result, selected winner, or v3 runtime artifact exists at this point.

### Implementation trace

`scripts/build_family_retrieval_development.py` adds a deterministic author/validator instead of a
manually editable JSON fixture. It validates the frozen review-family registry and projection, the
human-backed catalog used by merge targets, all source manifests, and exact 42/4/7/97 source counts.
The historical v1 query pack is opened only to reject exact or normalization-equivalent text; its
labels, candidates, ranks, metrics, and failures never become builder inputs.

The positive-case generator changes the identity in four distinct ways: one deleted character,
spacing/token-boundary disruption, abbreviation or numeric variation, and an exact identity inside
seller context. Merge and hold identities receive new development-only wrappers. Ten meaningless
opaque strings must share no searchable token with either Human Knowledge corpus, while ten generic
listings may use marketplace vocabulary but must contain no known casting phrase. Derived expected
targets come from the already approved registry relationships rather than new variant judgments.

The generated `development-pack.json` freezes cases and the 21-option grid before experimentation.
Its companion manifest hashes the pack, builder, six primary source/integrity files, and the v1
query pack plus manifest used for non-reuse checks. The script validates the complete prospective
result before opening output files and writes with temporary-file replacement, so invalid input
cannot erase the last valid freeze. `tests/test_family_retrieval_development.py` turns the dataset
boundary into ten executable contract tests. The feature requirements/design status now reflects
owner confirmation, HRR-T1 is checked in the task list, README links the evidence, and
`docs/evidence/family-retrieval-development-v1.md` gives the complete human-readable audit.

### Technical choices, alternatives, and trade-offs

Deterministic transformations were chosen over asking an LLM to generate 168 questions because the
exact operation on each identity remains inspectable and byte-reproducible, does not require an
external model/version, and cannot drift between runs. The trade-off is deliberate artificiality:
this pack measures whether implementation and a small fixed configuration family can handle known
spelling/token disruptions; it does not estimate real-user accuracy. That is why final evaluation
still needs a later output-blind, owner-reviewed holdout v2.

The grid is frozen as the specification requires: seven character floors from `0.25` through
`0.55` crossed with weights `0.5`, `1.0`, and `1.5`. Keeping sparse/dense weights, dimensions,
RRF `k`, and K fixed constrains degrees of freedom and makes a 21-result report understandable.
Safety gates are evaluated before quality and tie-breaking. This may legitimately yield no winner;
the accepted cost of fail-closed selection is preferable to widening the search after viewing
results.

Labels are stored in the development cases because selection needs them, but the artifact carries
an explicit leakage disclosure and prohibited-use list. A fully independent development corpus
would give stronger generalization evidence, but no separate owner-labeled corpus of sufficient
coverage exists. The future holdout—not this derived pack—will provide the independent claim.

### Decision changes

The earlier specification state said no development data existed and implementation awaited owner
confirmation. The owner's instruction to proceed satisfied that first gate. The project is now in
Build with HRR-T1 complete, but only the data contract has advanced: v2 remains the active Human
Knowledge retriever, the canonical RAG remains the sole final-identity authority, and T49 remains
blocked.

During implementation, the initially entered grid constants were checked against HRR-R8 and found
not to match the confirmed spec. They were corrected before the artifact was frozen to the exact
`0.25–0.55 × 0.5/1.0/1.5` grid, and the regression test now locks those values. No candidate output
existed during that correction, so the choice remained genuinely precommitted rather than
result-driven.

### Verification evidence

The deterministic `--freeze` and `--check` paths both report exactly 199 dev cases and
`retrieval_executed=false`. The focused suite passes 10/10 tests covering counts, four-style family
coverage, unique/non-v1 text, unrelated-control boundaries, the exact grid, source/script/output
hashes, deterministic bytes, a non-mutating check, and preservation of existing outputs when an
invalid 41-family source is supplied. Targeted Ruff passes, and strict MyPy reports no issues in the
builder. The pack SHA-256 is
`23589b23567220dbba0de959ec5223cf60365b1222320f3a372f1b156244dbe9`; the manifest binds builder
SHA-256 `3da7becca7b0cb27568e887140d6f07a1e41c0ceb56d0badce38134bca1a776c`.

The complete repository suite passes **211/211 tests** with the known Starlette/AnyIO deprecation
warning. The first whole-suite command did not export `PYTHONPATH=src`: pytest itself found source
modules through project configuration, but a subprocess spawned by an older reproducibility test
did not inherit that in-process path and reported `ModuleNotFoundError`. Re-running the same suite
with the repository's documented subprocess environment passed all tests. Strict MyPy over the new
unittest file also reported the repository's familiar dynamic test-class typing pattern; the
production builder alone passes strict MyPy, while the executable tests verify that dynamic test
behavior. Neither diagnostic changed a frozen output artifact.

### Incomplete work, risks, and next step

Generated controls may not cover the distribution of real marketplace language, and the frozen
grid may expose a recall/safety conflict with no qualifying setting. Those are expected empirical
risks for HRR-T3, not reasons to edit this pack after results. No PostgreSQL data, 3,000-document
load, production/concurrent latency, canonical behavior, or neural embedding is represented here.

The next step is **HRR-T2**: add the experimental character n-gram TF-IDF candidate path, three-
source weighted RRF, typed debug evidence, and fail-closed version metadata without changing
canonical output. HRR-T2 may prove mechanics against fixtures, but it must leave configuration
selection and winner/artifact publication to HRR-T3 using this already frozen pack.

## 2026-09-12 — HRR-T2 experimental character-hybrid implementation

### Context, problem, and observable outcome

HRR-T1 froze the development questions before any new retriever result existed. HRR-T2 could now
solve the underlying mechanics problem without yet optimizing against those questions: v2 requires
an exact shared token before a document becomes eligible, so a query such as `Protn Sagx` cannot
reach the `Proton Saga` family even though their character structure is close.

The new implementation adds an experimental `human-knowledge-hybrid-v3` path that admits candidates
through character evidence as well as tokens. In a controlled implementation fixture, `Protn Sagx`
returns `Proton Saga` first with no sparse rank, character rank 1, and character similarity above
0.7. That family remains debug evidence: the canonical result is still `no_match` with null UUID and
ID. The normal application still runs v2 because there is no selected v3 artifact. No 199-case
development selection, winner, performance report, final holdout, PostgreSQL write, or canonical
change occurred in this task.

### Implementation trace

`src/product_variant_resolver/human_knowledge.py` gains two deliberately separate concepts. Each
typed document now publishes `character_identity_texts`, whose content is narrower than the existing
token-search `searchable_text`: review families allow only casting/aliases, while provisional
variants allow only casting/human-verified labels. `CharacterIdentityIndex` turns normalized spaced
and compact identity forms into Unicode character bigram/trigram TF-IDF vectors and an inverted
posting map. It builds query windows near known identity lengths, gets candidate UUIDs from shared
gram postings, calculates cosine only for those candidates, applies the configured floor, and breaks
ties by UUID.

The v3 retrieval branch ranks at most 25 token and 25 character candidates, unions the IDs, and runs
the existing 192-dimensional `hashing-v1` dense score only on that bounded set. Sparse, dense, and
character ranks then contribute weighted reciprocal rank terms at `k=60`; a missing rank stays null
and contributes exactly zero. The old body was retained as a separate `_retrieve_v2` branch so the
default code path does not accidentally inherit v3 candidate or fusion behavior.

The same module also defines a strict v3 artifact loader. `config.py` exposes only paths to a
selected artifact and the frozen development files—there are no environment variables that accept
arbitrary thresholds. The loader permits only HRR-T1's seven floors and three weights, verifies
every fixed parameter and field allowlist, and checks catalog, projection, development, manifest,
and implementation SHA-256 references. `service.py` constructs v3 only after that validation; index
or retrieval failures cross the dependency boundary as 503 rather than becoming a fabricated result
or a silent v2 fallback.

`schemas.py` adds typed optional character rank/score fields to the common base of both Human
Knowledge candidate variants and a typed character-index metadata object. `service.py` serializes
artifact/version/index evidence only in debug. `api.py` exposes the active Human Knowledge version
and artifact in readiness detail. `ui/index.html`/`ui/app.js` add the Character column and artifact
evidence using the existing safe `textContent` rendering path. The canonical response model is
unchanged.

The tests now cover character-only, sparse-only, compact-spacing, equal-score UUID ties, invalid
floor/short identity, allowlisted fields, posting metadata, strict/stale artifact rejection,
settings paths, debug/OpenAPI/health fields, UI rendering, runtime 503, and exact non-debug canonical
compatibility. The historical v1 builder/evaluator were adjusted only where they had assumed that
the whole mixed v2/v3 source file must retain its old SHA forever.

### Technical choices, alternatives, and trade-offs

The implementation stores character vectors and postings in memory because the corpus has 142
documents and T49 persistence is explicitly blocked. This provides deterministic offline behavior
and keeps HRR-T2 independent of PostgreSQL. The measured structure contains 4,508 posting keys and
19,001 posting entries. That is implementation accounting, not a latency or scale claim; HRR-T3
must still measure both 142 and synthetic 3,000-document scopes.

Both spaced and compact forms were retained. Spaced grams preserve word-boundary information, while
compact grams let `TwinMillGenE` match `Twin Mill Gen-E` without query rewriting. Query windows keep
seller wrappers from diluting every comparison. The cost is more postings and multiple cosine
comparisons per posting-derived candidate. A single compact form would be smaller but would erase
useful boundaries; scoring the full query only would punish noisy marketplace strings.

Candidate-source caps are 25 rather than the final K=5. Five is the fixed selection/report output
depth, whereas each source needs enough recall before fusion. Capping both sources still bounds the
dense union to at most 50 documents and prevents a generic gram from turning dense scoring into an
unconditional 142-document scan. This remains a local deterministic IR design, not a neural
embedding or approximate index.

Artifact-gated activation was selected over a boolean `PVR_V3=true` plus free environment floats.
The artifact path makes version, corpus, implementation, development evidence, and allowed parameter
set one fail-closed unit. The trade-off is that v3 cannot run as the normal application until HRR-T3
writes a valid artifact. That temporary inconvenience is the desired protection against activating
an unselected configuration.

### Decision changes

D37 previously described the character path as proposed and said it had no implementation impact.
It now records that HRR-T1 and HRR-T2 are complete but that v2 remains active. The architecture
choice is implemented; the configuration decision is still intentionally unresolved. Only HRR-T3
may turn one of the 21 precommitted pairs into a selected artifact, and it must publish FAIL if none
meets every gate.

The v1 benchmark stored SHA
`5bf582b921b62945b7e4405beb98822abd876b870bdb5267854764c2e1ab2982` for the original complete
`human_knowledge.py`. Once v3 code was added to that same module, comparing the historical hash to
the live mixed-version file made four regression tests fail even though `_retrieve_v2` output was
unchanged. Rewriting the old benchmark/report with the new file hash would falsely claim that T48
tested code that did not exist. The builder/evaluator now validate the old SHA as the frozen v2
identity and separately require current default v2 execution to reproduce the old output bytes.
That preserves historical truth without using the holdout to tune v3.

### Verification evidence

The HRR-T2-focused unit/integration/API/UI/historical set passes 56 tests. The complete repository
passes **223/223 tests** with the same known Starlette/AnyIO deprecation warning. The development
pack remains byte-valid with 199 cases and `retrieval_executed=false`; the old v1 query pack,
benchmark, JSON, and Markdown remain reproducible. Node syntax checking passes for the UI. Focused
Ruff F/I checking passes for all changed source/tests, and strict MyPy with imported modules skipped
reports no issues in `human_knowledge.py`, `config.py`, and `service.py`.

Two focused tests initially failed for test-assertion reasons: exact floating equality saw
`0.9999999999999999`, so the assertion was correctly changed to approximate numeric equality; the
DOM harness initially inspected the character cell's wrapper rather than its nested rank text, so
the path was corrected. Later, the first full suite exposed the four historical source-hash failures
described above. After separating historical v2 identity from the live mixed file, all 223 tests
passed. A final OpenAPI assertion initially looked for a standalone parent-schema component, but
Pydantic correctly flattens inherited rank fields into both concrete discriminated candidate
schemas; the assertion now verifies `character_rank`/`character_score` on each concrete type. No
development-selection or final-holdout output was inspected during these corrections.

### Incomplete work, risks, and next step

Fixture success does not establish aggregate quality. A floor low enough to recover typos may also
admit generic listings, and a high floor may recreate v2's miss. Human-verified label strings can be
long marketplace titles even though the field itself is allowlisted; query windows reduce but do
not eliminate that noise. The source cap and in-memory posting count still require measured evidence.

The next step is **HRR-T3**: execute exactly the already frozen 21 floor/weight combinations on the
199 development cases, publish raw metrics and every rejection reason, measure the disclosed 142-
document and synthetic 3,000-document cost, and either freeze one checksum-bound artifact or stop
with selection FAIL. Until then, v2 stays active and T49 remains blocked.

## 2026-09-12 — HRR-T3 fixed-grid development selection completes with FAIL

### Context, problem, and observable outcome

HRR-T2 supplied an experimental character-hybrid implementation but had not established whether
any configuration was safe or affordable. This step executed exactly the HRR-T1-frozen 21 floor/
weight combinations against 199 development cases, retaining all 4,179 case/configuration outputs.
The observable result is `verdict=FAIL`, `winner=null`. The active service remains v2; no v3 runtime
artifact, new final v2 query pack, PostgreSQL write or real-catalog expansion was produced.

Positive development retrieval is strong: every setting recovers 164–168 of 168 positives, every
style recovers at least 38/42, every merge control reaches an existing provisional casting (4/4),
and no forbidden family is returned. However, every setting also returns candidates for all ten
generic-no-identity negatives. The ten opaque negatives remain empty. These results cannot be
described as overall success: the precommitted all-gates rule rejects every setting before the
MRR/Recall@1 tie-break can choose anything. This data was transformed from indexed identities,
so even its positive success is development evidence, not final independent accuracy.

### Implementation trace and why these parts changed

`human_knowledge_selection.py` is a separate local evaluator, not a service/ranking change. It
locks both development checksums, verifies non-v1 source references, executes the exact grid with
runtime signal extraction, serializes ordered typed candidates, and only then scores expected
identities. Its checker recomputes raw/style/merge/safety metrics, cost percentiles, rejection
reasons and deterministic selection; it also rejects invented corpus IDs, nonfinite scores,
invalid source ranks and inconsistent weighted RRF. Separating this module prevents development
labels or tuning code from entering canonical resolution. Explicit source-key validation prevents
an incomplete checksum list from silently bypassing integrity checks.

`generate_human_knowledge_selection_report.py` renders the validated JSON rather than recomputing
a different summary. `freeze_human_knowledge_v3.py` implements both conditional paths: FAIL returns
without touching the output; a hypothetical qualified result binds all 21 metric summaries and
the full raw-report checksum, and refuses to overwrite an existing artifact. Unit tests distinguish
this mocked construction behavior from an actual quality PASS. `human_knowledge.py` adds validation
for the freezer's optional `selection_evidence` field, requiring an in-project development-report
path, matching checksum and a matching genuinely qualified winner. T2 ephemeral fixture artifacts
remain compatible without the optional field; T3 freezer outputs always include it. The retriever's
candidate generation, thresholds and ranking algorithm were not changed after results were viewed.

`tests/evaluation/test_human_knowledge_selection.py` covers the fixed grid, guarded no-v1 reads,
every safety/quality/cost rejection gate, all tie-break levels, source/raw/cost tampering, synthetic
scope and conditional freeze/overwrite protection. The existing artifact unit test gains a path-
escape rejection assertion. Reports, QA checkpoint, AI-eval, README and spec statuses now reflect
the actual FAIL and blocked downstream tasks instead of suggesting selection has not started.

### Method choices, trade-offs, and decision changes

The method remains deterministic offline IR: 192-dimensional hashing, character TF-IDF and weighted
RRF. No neural package, new model, scrape, family-slot quota or query rewrite was introduced. Cost
measurement uses a fixed protocol—three warm-ups/configuration, all 199 real queries, and the first
20 case-ID-ordered dev queries on a deterministic 3,000-family synthetic index. Nearest-rank
percentiles and raw samples are saved. Checking arithmetic from saved samples is reproducible;
requiring a new wall-clock measurement to match old bytes would not be honest.

The key decision moves from “select a v3 winner if the frozen grid qualifies” to “retain v2 and
return to design.” For `frd-unrelated-generic-00` (`sealed blue collector model from storage box`),
the 0.55-floor/1.5-weight result still returns five provisional documents through `box`, `collector`
and `blue`, with character rank/score null. This directly exposes an exact-token admission path
independent of the character floor. Expanding that floor grid would not resolve the illustrated
path. Future work must design identity-bearing eligibility rather than select the nearest failing
setting. Likewise, posting indexes alone do not establish cheap scoring: the synthetic corpus has
419,820 posting entries and its shared forms still make comparison expensive. Any optimization
must receive a new decision and measured before/after evidence, not be slipped into this evaluation.

### Verification evidence and execution corrections

The complete suite passes **236/236 tests**, no skips, with one existing Starlette/AnyIO warning.
The complete report passes source/raw arithmetic checks and Markdown byte reproduction; the actual
freeze invocation reports `selection FAIL: runtime artifact untouched, v2 stays active`. Focused
Ruff F/I and isolated strict MyPy on the two retrieval/selection modules pass. Development, family
projection/registry, v1 query/benchmark/JSON/Markdown checks, fixture validation, compilation, Node
syntax and default/PostgreSQL-profile Compose static configuration checks pass. A fresh canonical
fixture report in a temporary directory preserves Recall@25/Top-1/MRR/precision 1.0, false-match
rate 0 and coverage 0.8333. Whole-repository lint/type maintenance debt is not claimed resolved;
SQL/container runtime and concurrency were not repeated.

Two incomplete harness runs were interrupted before report output: the first to finish report/
artifact evidence binding, the second after an isolated type check exposed invariant synthetic-
document list typing. The latter was fixed with the union document type annotation; two earlier
typing findings were resolved by annotating raw counts and casting the selected configuration.
These were implementation/provenance corrections, not threshold, data or metric-driven tuning.
One full unmodified 21-setting execution then produced the committed raw report. Verification also
initially invoked the canonical wrapper without `PYTHONPATH=src` and referenced a nonexistent
separate PostgreSQL Compose file; correct module loading and `--profile postgres` invocations pass.
Neither command mistake required a product change.

On this macOS arm64 desktop with 10 logical CPUs and Python 3.12.13, real 142-document p50 is
8.51–9.70 ms and p95 is **29.37–36.60 ms**, above 25 ms. Synthetic 3,000-document p95 is
**337.15–377.28 ms**, above 150 ms. The real index has 4,508 keys/19,001 entries; synthetic has
2,431 keys/419,820 entries. Measurements are warmed single-process K=5 retrieval on a non-isolated
desktop, excluding index construction, serialization, HTTP, networking, databases and concurrency.
They do not demonstrate 3,000 real records or production scale.

### Incomplete work, risks, and next step

HRR-T3 is complete through its designed no-winner branch, but the feature's final-quality gate is
not complete or approved. HRR-T4–T6 and T49 stay blocked. The next highest-value action is a new
Lite design decision addressing identity-only admission and bounded character comparisons, retaining
this development FAIL and the old final v1 FAIL. A later qualifying code/artifact freeze must still
precede a newly authored, owner-approved unseen final holdout. No such redesign is implemented in
this step. See [raw/report evidence](../reports/family-retrieval-development-v1/selection.md),
[AI-eval](evidence/ai-evals/human-knowledge-retrieval-development-v1.md) and
[checkpoint review](../specs/human-knowledge-retriever-redesign/review.md).

## 2026-09-13 — Propose a new Lite identity-bounded retrieval design after v3 FAIL

### Context, execution and observable outcome

The owner asked for the next step after HRR-T3 preserved a no-winner FAIL. D38 requires a new design
decision rather than another threshold sweep, so this step returned to Phase 1. I reread the frozen
requirements, development evidence and actual sparse/character retrieval code, then authored the
new `human-knowledge-identity-bounded-retrieval` requirements/design/tasks and proposed D39. The
observable output is a reviewable plan for an isolated experimental v4 path. There is no v4 product
code, frozen execution protocol, candidate output, new quality result, runtime artifact or ingestion.

The design addresses the two observed structural weaknesses. Any broad token in human listing text
can admit a document independently of character threshold; generic-00 proves that path with `box`,
`collector` and `blue`. Character posting lookup still feeds a query-window/document-form Cartesian
comparison and per-query sparse frequency scans. I did not rerun a profiler or infer that either
code section accounts for an exact share of latency. The published p95 failures motivate a new
oracle-verifiable algorithm and measured budget, not an unearned speedup claim.

### Files changed and why no product code changed

The three new spec files define casting-only admission fields, a shared frozen whole-token identity
noise policy, complete-core token admission, exact weighted form-posting cosine accumulation with
unknown query grams in the norm, all-or-nothing limits, query-local debug counters and separate v4
artifact readiness. Tasks specify files, evidence and blocked downstream order. README now points
to this proposal while retaining default v2 and the old failures. D39 records alternatives, 10x/
likely failures and six anticipated benefit/risk dimensions; none is reported as a measured PASS.

No code was modified because spec-dev-loop's Lite G1* requires owner confirmation of requirements,
design and tasks before build. Avoiding source-bound v3 modules in the proposed implementation also
preserves the old report's live checksum checks. The new v4 path must integrate through separate
service/config/schema/UI opt-in, not edit historical scoring or silently change its reported version.
This planning pause is a requirement of the skill, not an implementation or quality blocker verdict.

### Technical choices, narrowed decisions and trade-offs

The proposal retains deterministic TF-IDF/hashing/RRF rather than introduce a neural dependency.
It narrows provisional admission from full human-verified listing labels to casting identity; labels
remain stored and broad text may rank already admitted documents. Whole-token filtering avoids
substring rewrites, but can collapse color/common-word names. Complete exact cores are safer than
single-token overlap, but depend on character rescue for partial/typo identities. Unknown-gram norm
handling avoids inflated evidence but can reduce recall. Those risks must pass development and a
later independently authored/owner-approved final test, not be patched by per-case exemptions.

Direct posting accumulation preserves the new formula exactly on small oracle tests, with declared
query/form/posting limits that discard all partial results on budget exhaustion. Such limits do not
guarantee timing and can produce misses. A new scale workload therefore retains the old 20 dev-query
cost probes and adds 100 deterministic target-bearing exact/typo/contextual probes; correctness gates
prevent empty-only fast results from being called scale success. Index/SQL/network/concurrency remain
outside warmed local retrieval measurements.

The old 21-setting grid and all safety/quality/timing thresholds remain unchanged in the proposal.
This is a new architecture/protocol version, not widening the old search. The 199 dev cases are
explicitly already viewed/identity-derived and may be reused as development diagnostics, never as
new blind or final evidence. Original v1 final data remain prohibited for selection. Old v3 reports
and source checksums must remain unchanged. No default deployment or T49 expansion follows planning.

### Verification and incomplete work

Verification results are recorded in `docs/evidence/human-knowledge-identity-planning.md`. They check
the current baseline and documentation scope, not v4 behavior or a speedup. G1* is pending owner
confirmation and all IBR build/evaluation tasks remain unchecked. The highest-value next action is
owner review of the three spec files; once confirmed, IBR-T1 validates actual core/collision/form
limits and freezes/commits a new protocol before any v4 retrieval. If validation fails, return to
design before output rather than quietly drop approved names. T49 and new final holdout authoring
remain blocked. No subagent was spawned and all delivery files stay in the project folder.

## 2026-09-13 — IBR-T1 validates identity cores and freezes the approved v4 protocol

### Context, execution and observable outcome

The owner's `執行下一步` instruction immediately followed the three-spec confirmation handoff, so
this step records approval of the exact requirements/design/tasks at commit `880e4f5` and executes
IBR-T1 only. The goal is to make the new experiment reproducible before its outputs exist, not to
retry the failed v3 grid. The execution protocol now freezes the policy, formula, work ceilings,
unchanged 21 settings, safety/quality/cost gates, all 199 dev query IDs and 120 scale queries/targets.
No v4 retrieval, new rank/metric/latency result, selected runtime artifact or database operation occurs.

The static check finds 142 valid documents and 284 spaced/compact forms, at most 2/document against
the ceiling 32. Two core collision groups contain the already distinct `83 Chevy Silverado` and
`Toyota Supra` variants. These are same-casting version distinctions, not different casting names
collapsing under the policy; all 142 IDs remain separate. No core is empty/too short and no cross-
casting collision occurs. The 199 real queries peak at 90 forms and the scale workload at 60, below
256. These are construction counts, not a scored or timed runtime index.

### Implementation trace and reasons for each file group

`scripts/build_human_knowledge_identity_protocol.py` is an offline deterministic artifact builder.
It reuses the unchanged catalog/normalizer and synthetic document construction, but reads only
provisional casting and family casting/aliases for the core audit. It does not call a retriever.
Strict approved-spec hashes and noise-block validation prevent the code's policy drifting from the
approved design. Stable form IDs, deduplication, gram-reference counts and full collision groups
make future implementation and review inspectable instead of reporting only a total count.

The new `data/evaluation/human-knowledge-identity-development-v1/` contains protocol/manifest, full
real core audit, owner approval and original approved spec snapshots. Snapshots are extracted from
the approved Git commit when freezing, then checks use delivered snapshots without requiring old
Git history. This both preserves attribution and avoids stale integrity checks when live task
checkboxes/statuses change. The snapshots retain historical proposed headers; approval is recorded
as a separate event with actual UTC time, not a retroactive rewrite. Source hashes bind old corpus/
governance/development/v3 evidence and the builder; every delivered artifact is checksum-bound.

`tests/test_human_knowledge_identity_protocol.py` adds 12 checks for portable byte reproduction,
guarded no-v1 reads/no ranking calls, approval/leakage disclosure, exact real/scale counts/targets,
ignored broad human fields, Unicode/whole-token/numeric cores, invalid/empty/duplicate/excessive
forms and query ceilings, all source/file bindings and preservation/idempotence. Evidence, AI-artifact
assessment and scoped QA review separate a valid contract from unmeasured v4 retrieval. README/live
spec statuses and D40 now reflect approval and T1 completion; runtime source files are unchanged.

### Method choices, corrections and trade-offs

The stack remains standard-library JSON/hash/file/Git reading plus existing project models; no
model dependency, external API or PostgreSQL is necessary for protocol construction. Frozen output
checks compare deterministic bytes, and freeze validates all inputs/existing outputs before writes.
Different existing frozen files are rejected rather than overwritten; repeating identical freeze
does not even replace their timestamps. These semantics preserve meaningful pre-output provenance.

An initial freeze attempt stopped before writing because the approved Markdown noise block's fence
language `text` was parsed as an extra token. Stripping that language line fixes the parser without
changing the approved noise set. Initial MyPy checks also needed `MYPYPATH=src` and explicit set
annotations. These were builder/parser/type corrections before v4 output, not data, gate or ranking
tuning. The resulting script and artifacts now reproduce unchanged.

One limitation became concrete during static validation: synthetic `Scale vehicle model NNNN`
casting cores retain only numbers because `scale`, `vehicle`, `model` are approved noise tokens.
The `Scale` → `Scxle` probe edits a removed wrapper, not retained numeric identity. I preserved the
approved workload and explicitly recorded this limitation, rather than change it silently. The
100 target probes still prevent an entirely empty fast implementation from passing, but cannot
prove genuine core-name typo robustness. Real four-style dev quality and independent final tests
remain required. Form-level gram references also cannot be compared to old document postings as
an observed speed/memory improvement; no such measurement was run.

### Verification evidence and next step

Focused tests: **12 passed**. Full repository: **248 passed**, no skips, one existing Starlette/
AnyIO warning. Protocol `--check`, focused Ruff F/I, isolated strict MyPy builder check, compilation
and whitespace checks pass. The old 199-case freeze, v3 JSON/Markdown and v1 final-report checks all
pass without historical source/data/report edits. Protocol SHA-256 is
`31802be99f02698423c4526bbd8752e6f517fcbef8ca8080926d019f55083fde`; its manifest is
`b7634f7f3d52277c4ee4d92489b656fcf1a6c446d56085c5affb7cb7a12c6ea7`.
See [freeze evidence](evidence/human-knowledge-identity-protocol-v1.md) and
[QA checkpoint](../specs/human-knowledge-identity-bounded-retrieval/review.md).

IBR-T1's freeze must be committed before v4 output; IBR-T2 is the next highest-value task: implement
the isolated identity/posting retriever, verify exact scores against a brute-force oracle, and test
query-local budget/debug/canonical readiness isolation. Posting cost, budget-abstention quality and
runtime package evidence are still unmeasured. Default v2, old development/final FAIL verdicts,
blocked final-authoring/T49 and no real-catalog growth remain unchanged. No subagent was spawned;
all delivery files remain inside the project folder.

## 2026-09-14 — IBR-T2: exact identity-posting implementation and isolated runtime evidence

### Context, executed work and observable outcome

The approved v4 protocol existed, but no code could yet enforce casting-only admission or calculate
the new form-posting scores. V3's broad any-token path could admit generic listing words independently
of its character floor, and its full form/window comparisons had failed cost gates. This step completes
IBR-T2's isolated implementation and mathematical/runtime safety checks. It does not rerun selection
or assert that the proposed architecture fixes measured quality or latency.

Callers still get default v2 behavior unless they request a new v4 evidence artifact. A valid v4
retriever now produces casting-core sparse/character evidence, a bounded dense/RRF result and its
own work counters. Generic-only or over-budget queries return no human candidates while canonical
resolution continues. Missing/corrupt requested evidence instead produces readiness/resolve 503.
There is no qualified artifact yet, so normal runtime remains v2 and canonical final authority is intact.

### Implementation trace and why these modules changed

`human_knowledge_identity.py` implements the approved whole-token policy, identity forms, document-level
DF/IDF and normalized weighted gram postings. Direct query posting accumulation avoids reconstructing
every candidate's form/window cosine in the query path. Unknown grams stay in query norms, so unfamiliar
text cannot gain an artificially high score simply by discarding its unmatched features. Exact sparse
admission requires all tokens of one approved identity core; human labels/initial names/series/pricing
never create forms. Dense scores apply only after bounded identity admission, then RRF preserves absent
source ranks and deterministic UUID ties. Budget aborts discard the entire result, including otherwise
exact candidates, rather than publishing a misleading partial shortlist.

`human_knowledge_identity_artifact.py` is an implementation decomposition, not a changed product spec.
It checks the frozen contract/corpora/source hashes and demands a complete, recomputable raw selection
report with a matching qualified winner. Keeping readiness evidence separate from query math makes
both responsibilities testable and leaves source-bound v3 modules unchanged. It defines future report
validation without running the grid or creating a winner. Its positive parsing fixtures deliberately
mock selection validation; they are not development quality evidence.

`config.py` adds a separate v4 artifact setting and rejects v3/v4 conflict. `service.py` selects the
new retriever only from an explicit validated config and retains work inside each resolve invocation.
`schemas.py`, `api.py` and `ui/app.js` expose typed index/form/policy/work/abort evidence while safe-text
rendering preserves inert user/source markup and old payload behavior. Canonical retrievers, policy,
calibration and output selection were not changed. Dockerfile/ignore changes include the protocol-bound
builder and report dependencies in the image context; these are static packaging corrections only.

### Method choices, alternatives and corrections

The stack remains existing Python catalog types, standard-library arithmetic/postings, hashing-v1 and
FastAPI/Pydantic with safe vanilla-JS UI. No neural model, new dependency, network source or database
write is necessary for this eligibility/comparison change. Exact form scores are independently checked
against an all-form/window TF-IDF cosine oracle. An approximate shortlist or type quota could obscure
missed targets; shared last-query debug state could mix requests. The implementation therefore keeps
exact accumulation and immutable returned work values. Four-thread in-process tests check isolation,
not production concurrent throughput.

The initial full test command lacked `PYTHONPATH=src`, causing an existing report subprocess import
failure; the corrected source-path run passes without regenerating reports. A Compose override command
initially named nonexistent files and was corrected to the actual file's PostgreSQL profile. Type checks
needed explicit casts around reused legacy helper contracts, and window-abort debug bounds account for
the two forms added by the detection step. These are implementation/environment corrections, not
after-output tuning of policy, grid, gates or data. No architectural selection was reversed.

### Verification, remaining risks and next step

Core/artifact/API/UI focused tests: **65 passed**; full repository: **311 passed**, no skips, one
existing Starlette/AnyIO warning. Focused Ruff F/I, isolated strict MyPy on new modules/config/service,
Python compilation, Node syntax and whitespace checks pass. The identity freeze, old 199-case freeze,
v3 JSON/Markdown and v1 final JSON/Markdown reproduce with historical hashes/FAILs unchanged. Default
and PostgreSQL-profile Compose/context checks pass; no Docker rebuild/run, PostgreSQL ingestion, full
project lint/type-debt cleanup, latency sampling or 21-grid execution occurred. Detailed limits and
commands are in [T2 evidence](evidence/human-knowledge-identity-implementation-v1.md) and scoped QA/AI
records; live task/README checklists now distinguish engineering completion from quality approval.

Common grams may still exceed the posting ceiling; stricter cores/unknown norms/noise removal can
lose legitimate names. Numeric synthetic identity and wrapper-only typo probes remain limited evidence.
IBR-T3 is next: implement/run the frozen 21-config development and 120-query scale evaluation, publish
all raw outputs/work/timing and apply every gate unchanged. Only a committed qualified winner can
unblock new output-blind final questions and owner approval. Final FAIL must remain FAIL; T49, real
3,000-row catalog expansion, deployment and end-of-project beginner code review remain downstream.
All delivery files stay inside the independent project folder and no subagent was spawned.

## 2026-09-14 — IBR-T3: frozen development selection passes; qualified v4 artifact published

### Context, new execution and observable outcome

IBR-T2 proved the new arithmetic and runtime isolation, but it did not establish real development
quality or cost. This step implements and executes IBR-T3's one frozen architecture experiment:
exactly 21 existing floor/weight settings, every unchanged 199-case development query and the exact
120-query synthetic workload per setting. All 21 pass every predeclared development gate. The fixed
ranking tie-break selects floor 0.50 / character weight 1.0, and its fully evidenced experimental artifact
can now be loaded explicitly. Default v2 and canonical authority remain unchanged; this is not final
quality, a default deployment, database promotion or proof of 3,000 real products.

The selected run finds 168/168 positives, 165/168 at rank 1, MRR 0.9911, 42/42 in all four styles,
merge 4/4, forbidden 0 and unrelated nonempty 0/20. Real/aggregate-scale p95 is 2.07/45.14 ms against
25/150 ms budgets. Known synthetic exact/edit/context hits are 60/60, 20/20, 20/20. Complete raw outputs
and all misses/abstentions are retained, including the two floor 0.55 positive misses; no setting or
sample was dropped, resampled or tuned. A higher floor is not automatically a better configuration.

### Code changes and why these responsibilities are separated

`human_knowledge_identity_selection.py` loads the checksum-valid protocol/corpora, creates the exact
two retrievers for each setting, warms each with three queries and measures only retrieve_with_work.
It serializes all 4,179 real and 2,520 scale results with candidate identities/ranks/work and attaches
expected labels after retrieval is complete. Raw latency, scale subgroup hits/cost and work totals
are retained so summaries can be audited instead of trusted. Source checks before/after prevent mixed
code versions from being frozen. The check command replays arithmetic without any retrieval.

`human_knowledge_identity_artifact.py` adds mandatory runtime-boundary, original-20 subgroup and work-
summary recomputation to its future report contract. These checks were finalized and tested before
real outputs; they change evidence validation, not eligibility, ranking, noise policy, limits or
grid. No checksum-bound predecessor module or v4 query core was edited. Separate readable-report
and freezer scripts keep rendering/publication distinct from selection. Exclusive temporary-file
publication validates artifact bytes with the genuine runtime loader before creating the final path;
existing files are never overwritten, and FAIL does not even create an artifact directory.

`reports/human-knowledge-identity-development-v1/` holds complete JSON and readable tables, while
`config/human-knowledge-retrieval-v4.json` holds the winner and full evidence/source/policy bindings.
Config is intentionally committable, unlike ignored model artifacts/cache. Evaluation tests use an
explicit empty fake retriever for orchestration and no-winner preservation, then separately replay
the genuine report and genuine API artifact. Mock fixtures are not called quality winners. README,
live specs/QA, AI evidence and D42 now distinguish development PASS from the still-unrun final gate.

### Technology choices, corrections and trade-offs

The method remains standard-library Python, existing document models and hashing-v1; no neural
model/API/dependency or SQL write is necessary. One fixed-grid raw evaluation is chosen over an
open-ended threshold search. The original-20 scale subgroup has selected p95 of 61.22 ms, separately
shown against unchanged old-v3 original-20 p95 337.15–377.28 ms. The full 120 aggregate includes easier
exact probes; comparing only aggregate 45.14 ms to old 20 would misstate the workload. Index scoring
representation and non-isolated execution differ, so the observed difference is diagnostic, not a
controlled causal speedup or production SLA. Document/form-gram counts also do not prove memory gain.

An operational issue became visible after publication: temporary-file-based artifacts have host
0600 modes. Docker's non-root pvr could not necessarily read locally copied public evidence. Dockerfile
therefore grants read/traversal on copied public data/config/reports/scripts inside the image, without
changing bound bytes, write permission or the host's private cache. Static context/Compose tests check
this; no new container runtime was claimed. MyPy required an explicit callback annotation for safe
temporary publication. These are packaging/type corrections, not measured-score changes.

The pre-run full test process briefly overlapped first-setting startup/early measurement. I preserved
the run and disclosed this instead of removing/resampling an inconvenient configuration. Runtime
therefore explicitly remains non-isolated: Darwin 24.6.0 / Python 3.12.13 / arm64 / 10 logical CPUs; CPU brand
lookup did not return more than arm. Index/startup, extraction, serialization, HTTP/SQL/network and
concurrent request load are excluded. Synthetic cores remain numbers and Scale→Scxle edits a removed
wrapper, so successful probes do not prove retained-name spelling robustness or real-catalog growth.

### Verification evidence, remaining work and next action

18 new tests, 48 focused T3/artifact tests and 329 full tests pass, no skips, one prior Starlette/AnyIO
warning. Focused Ruff F/I, isolated strict MyPy evaluator/validator, Python compilation, Node syntax,
whitespace and both Compose profiles/context checks pass. Frozen protocol/old dev/v3 JSON+Markdown/
v1 JSON+Markdown remain valid and unchanged. Genuine selected-artifact/API readiness, health/debug
SHA and non-debug canonical equality pass; report checks do not retrieve. No fresh Docker rebuild/run,
real ingestion, final questions/labels/score, whole-feature PASS or default activation was performed.
See [T3 evidence](evidence/human-knowledge-identity-development-v1.md), raw report, QA and AI records.

The selected report SHA is `f52f85f775806d43a57c11e5fa9f7f965da980f54cc58a814d727fdfe7876f42`;
artifact `82c94a2629da6936bec3e4a2983e67c70d69e94cb94a9817375f891d59b1ae6b`. Commit code/protocol/
report/artifact before IBR-T4 authoring. Next is 105 new output-blind final questions, reuse rejection
and owner approval before labels/retrieval, then one final score and runtime/regression closure.
Viewed development can overstate generalization; unseen identity/noise/alias ambiguity remains the
primary risk. T49/3,000-real-row planning remains gated until final/closure PASS. No subagent was
spawned; all delivery stays inside Product Variant Resolver, ready for its independent GitHub repo.

## 2026-09-14 — IBR-T4 preparation: new final query pairs frozen for owner review

### Context, executed work and observable outcome

The development experiment passed and its v4 winner/report/artifact were committed, but final
generalization had not been tested. The approved lifecycle requires new questions **after** that
commit and owner approval **before** labels/retrieval. This step completes only question preparation,
not the whole IBR-T4 task or a final PASS. There are now 105 immutable query/reference pairs and a
complete owner-review table. No owner decisions, expected labels, benchmark, new-final candidates
or score exists. Default v2, canonical authority and the real-expansion/T49 gate stay unchanged.

The pack includes 84 positives, each of 42 approved families with marketplace and lexical questions,
four existing-casting merge controls, seven held-family exclusions and ten ordinary nonvehicle words.
The intended references help the owner judge fairness; they are not model outputs or preapproved
ground-truth labels. Hold means the unapproved family must not be materialized, not that every
provisional candidate must disappear. All questions remain synthetic and same-family, not a live
marketplace or unseen-casting sample.

### Implementation trace and reasons for the changed files

`scripts/author_family_retrieval_query_pack_v2.py` holds explicitly composed question strings, rather
than extracting searchable text or applying a global typo template. It does not import/call a query
retriever or generate expected answers. `family_retrieval_final_v2.py` verifies winner ancestry and
input bytes against commit `a9a3730`, confirms the new pack did not exist there, validates coverage
and static reuse, and builds the query pack/manifest/owner table. A staged directory publishes all
three files together; invalid inputs, existing artifacts and simulated write failure cannot expose
a partial new final folder. Rechecking compares exact case/source/review checksums and timestamps.

Static comparisons cover the old 105 final and 199 dev queries plus 561 indexed/governance/human-label
strings. They reject normalized/compact duplicates and nonempty old query identity-core equality,
without changing the normalizer/noise policy or trying new candidates. All 42 paired families and
4/7 controls are present; ten unrelated words have zero corpus-token overlap. This does not guarantee
zero character matches or semantic independence. The new tests guard no-new-retrieval/no-old-final-
label/result reads, cover invalid references/styles/counts/labels/metadata/stale sources, repeat-freeze
preservation, atomic publication failure and genuine frozen pair hashes. Temporary Git fixtures are
mocked only after a separate real committed-winner proof.

Live specs, README/QA, D43 and AI evidence now say T4 **preparation** complete but owner approval
pending. All delivery remains in the independent project folder. Source-bound v4/v3/runtime files,
selected report/artifact, existing final benchmark/FAIL reports and data corpus were not edited.

### Method selection, correction and accepted limitations

The stack is existing Python plus standard-library Git subprocess/JSON/normalization/hash/staging;
no new dependency, database/network operation or subagent is needed. Explicit strings preserve varied
marketplace context, spelling, spacing and numeric wording. Machine-score screening would bias final
questions toward success, so the new questions were not queried or filtered by retrieval performance.
The author does know previous development results and model rules: output blindness is limited to
these new candidates, not an independent author/population claim. Human review cannot remove every
construction bias but provides attributable relevance approval before formal truth.

A pre-approval metadata mistake was caught while checking the old final formula: coverage was named
`positive_coverage`, while the inherited 0.90 gate is **family_coverage_at_5 over 42 groups**. I preserved
that unapproved initial pack/manifest/review and exact author-source snapshots in a superseded folder,
then corrected the field name and re-froze the identical 105 cases. No question, threshold, model,
approval, label or candidate output was changed or used for this correction. The old draft SHA is
explicitly ineligible for approval/scoring; the authoritative current SHA is presented to the owner.
This is a contract-fidelity correction before scoring, not relaxed acceptance or a new fitted metric.

### Actual verification, pending approval and next permitted work

22 new focused tests and 351 full repository tests pass, no skips, one prior Starlette/AnyIO warning.
Focused Ruff F/I, isolated strict MyPy live authoring module, Python compilation, Node syntax, whitespace
and static default/PostgreSQL-profile Compose checks pass. The authoritative query check and old
identity protocol/dev/v3 JSON+Markdown/v1 JSON+Markdown reproduction pass. These engineering checks
do not establish final ranking quality; full-suite retrieval tests use existing fixtures, not this
new 105-question final set. No fresh container runtime, SQL promotion or real 3,000-row ingestion ran.

Authoritative query SHA is `b23b69912c678c027461c96eb23f113484c5a8ed6218c06d90026704abe5102b`;
freeze time 14:15:13Z follows winner commit 14:04:23Z. See
[all 105 owner-review pairs](../data/evaluation/family-retrieval-v2/owner-review.md) and
[freeze evidence](evidence/family-retrieval-final-v2-query-freeze.md). Per-case checksums and input
fingerprints are in the manifest. The next action is **explicit owner confirmation of those exact
pairs/checksum**, or Case IDs for a versioned pre-score revision. Stop here under Lite/spec-dev-loop;
approval/label/scoring implementation is intentionally deferred. After approval, freeze attributable
labels and commit benchmark before one final score, then runtime/regression closure. Unseen typo/
numeric/alias ambiguity and negative character overlap remain risks; T49 is still not authorized.

## 2026-09-14 — IBR-T4 owner-approved family labels and benchmark

### Context, problem and observable outcome

The105 output-blind questions were frozen but deliberately had no formal answers because owner
consent was missing. A generic next-step message did not close that gate. The owner then explicitly
confirmed the validation targets and raised an important scope question: colors and distinguishing
features matter as much as casting for the final product. I inspected the actual signal/identity/
structured-ranking/policy code and explained that existing color/year/series/number mechanisms
do not amount to complete wheel/tampo or real variant validation. This105-question pack validates
casting/family retrieval only. After that explanation, the owner replied `沒有問題，請繼續下一步`.
The approved targets now have105 attributable, reproducible family-level answers and a frozen
benchmark, without running any of their retrieval queries or inferring release/canonical truth.

### Code changes and why they are separate

The new `src/product_variant_resolver/family_retrieval_final_v2_labels.py` validates committed
question/review bytes at8f28918 and the existing winner/input chain, derives labels from the frozen
registry/projection/human casting data, records actual conversation excerpts, and provides strict
label/source/metadata and commit-before-score checks. The new
`scripts/build_family_retrieval_benchmark_v2.py` offers exclusive freeze, pure validation and
committed validation commands. Keeping these separate is necessary: the previous question author
and v4 runtime/evaluator sources are checksum-bound and must not be retroactively changed. Their
pending-review flags describe a historical freeze, not the new approval status.

The three approved documents are published together under `data/evaluation/family-retrieval-v2/
approved/`, preserving the original questions. Positive answers name review-family IDs/UUIDs;
merge answers name provisional casting IDs/UUIDs, not release UUIDs. Held controls exclude only
the held identity and may return other legitimate evidence; unrelated controls require no hits.
The manifest binds every case and all input/builder bytes. The new28-test label suite checks
exact mappings, missing/partial/duplicate/rejected approvals, generic-only proceed instructions,
changed queries/targets/gates/scope, stale builders, bool/int substitutions, recording times,
repeat-preservation, partial-publication failure and commit gates. The old query test was narrowed
to immutable top-level files so a legitimate separate approved child does not invalidate history.
Live design/tasks/QA/README, evidence/AI rubric and D44 now describe this completed label stage.

### Method choice, trade-offs and decision boundaries

Existing Python standard-library JSON/SHA/Git/private staging is sufficient; no new dependencies,
agents, database writes or external model are needed. Reusing confirmed registry targets avoids
inventing colors or converting provisional labels to canonical truth. Publishing one complete
child directory was selected over writing three independent final files, which could leave a
partially approved benchmark after an interrupted write. Exact type-sensitive reconstruction
guards against metadata and scope drift; the scorer must also prove committed, unchanged bytes.

Consent is recorded as a whole-pack target approval, not105 independent hand-labeling events or
cryptographically signed identity evidence. Recording time16:36:32Z is available; actual message
timestamps are not, so the record stores null rather than inventing them. The version's context
validator requires the actual target/scope/proceed excerpts, not a generic consent NLP classifier.
At10×, data validation and SHA reads grow with artifact size but do not run retrieval or train a
model. The most damaging failure would be promoting family answers to release truth; explicit
scope and tests prevent that claim. No threshold, query, identity policy or winner decision changed.
The earlier broader variant goal remains required work, not implicitly satisfied by family tests.

### Verification actually run

28 new label tests and50 combined query/label tests PASS; the correct
`PYTHONPATH=src .venv/bin/python -m pytest` invocation passes379 tests, no skips, one existing
Starlette/AnyIO deprecation warning. The initial full invocation omitted PYTHONPATH and had
378 pass/1 subprocess module-resolution failure; fixing the launch environment, without product
edits, resolves it. The first Node check named a nonexistent nested UI path; the correct
`node --check ui/app.js` passes. Focused Ruff F/I and isolated strict MyPy, compilation, current
label and original question validators, v4 JSON/Markdown replay, protocol, v1 benchmark/Markdown
reproduction PASS. These are actual engineering checks, not final-v2 ranking or runtime benchmarks.
The actual precommit benchmark CLI refuses scoring eligibility until the label artifacts are committed.
No fresh container/HTTP/SQL/load check or real3000-product ingestion ran.

### Remaining risks and next step

See [approval/label evidence](evidence/family-retrieval-final-v2-label-freeze.md) for all artifact
hashes and consent details. Query SHA remainsb23b6991; the benchmark is now frozen independently.
The final-v2 retrieval/ranks/score are still absent. Next commit/push this benchmark and verify
its commit gate, then T5 performs one final evaluation followed by runtime/full regression closure.
Synthetic same-family author bias, alias/typo ambiguity and true variant-data gaps remain disclosed.
Defaultv2 stays unchanged; old FAILs, real SQL promotion and T49/real expansion remain gated.

## 2026-09-14 — IBR-T5 pre-execution evaluator freeze

The committed105-question family benchmark at87bbd19 permits one final score, not final-set tuning.
I added a separate `family_retrieval_final_v2_evaluation.py`, report entry script and28 fake-output
tests rather than changing source-bound v4/label modules. Separate preflight integrity validation
checks committed inputs; the collector does not open approved labels, retrieves each question
exactly once with zero final warmups, and durably saves all ranks/work/errors before scoring.
An exclusive run reservation survives interruptions, deliberately preventing a convenient rerun.
JSON/Markdown check reconstructs fixed gates,84/42/4/10 denominators, all misses/safety/errors and
nearest-rank diagnostic samples without retrieval. The new code is committed before any final run.

Standard-library subprocess/JSON/hash/exclusive publication reuses the existing stack. Tests use
fake rows, not live final retrieval. They exposed insertion-order differences in dict-rendered
Markdown; stable sorted JSON rendering fixes byte reproduction before any real score. A temporary
preflight fixture lacked copied source files; adding the private fixture files fixes the intended
ValueError assertion rather than altering production behavior. Initial full run406 pass/1 fixture
failure is preserved as development evidence; corrected results are recorded at closure.

The independent `verify_human_knowledge_v4_runtime.py` runs real loopback Uvicorn HTTP within a
non-root/read-only Docker container using only old fixture queries, with isolated tmpfs and no host
port or PostgreSQL service. It checks default/v4 canonical equality, health/debug/UI and missing/
malformed/stale mandatory evidence503, then binds the report to image/runtime source hashes. Docker
socket access requires sandbox escalation; the authorized read confirmed Docker Desktop available.
An initial dedicated image built successfully; current-code rebuild and runtime checks follow.

No model rule, artifact, query, label, threshold or canonical authority changed. Before execution,
all existing report FAILs and source-bound bytes remain untouched. Final quality is still unviewed;
next is the single real run, followed by full/runtime/historical verification and honest PASS/FAIL
closure. Synthetic family accuracy cannot prove release/color/wheel/tampo or production accuracy.

## 2026-09-14 — IBR-T5 single final score and Lite/runtime closure

### What ran and what problem it closes

The approved benchmark87bbd19 and new evaluatorb86578c were committed before any real final
output. I ran exactly105 final queries once with the selected0.50/1.0 v4 settings, zero final
warmups/retries. A separate preflight process validates committed labels/source integrity; the
collector itself does not open approved labels. All raw results are saved before the runner parses
answers and scores. The frozen9 gates all PASS: positive80/84@5,77/84@1,MRR.93254; marketplace
42/42,lexical38/42; family42/42; merge4/4; forbidden/unrelated/errors0. Four lexical misses remain
empty and fully published, rather than being repaired against viewed final queries. This closes
the scoped family-retrieval quality checkpoint, not complete release/color/wheel/tampo accuracy.

### Code and evidence changes, with reasons

`reports/family-retrieval-v2/` now contains immutable run-start/raw/evaluation JSON and readable
Markdown. The evaluator's pure checker reconstructs raw candidate IDs/UUIDs/source ranks/RRF/
work/budgets, event order, fixed denominators, every gate and text from stored evidence without
retrieval. No pinned retriever/normalizer/loader/artifact/question/label bytes changed after output.
The additional `test_human_knowledge_v4_closure.py` checks genuine stored final data, Docker-root/
non-root packaging requirements, runtime source/image/503/canonical evidence, and preserved
failure records. Unlike orchestration fixtures, it does not execute a real final query.

Fresh Docker testing exposed a real deployment-path bug: defaultv2 started, but v4 returned503
because an installed module derived ROOT as/usr/local/lib/python3.12, while evidence lives/app.
`Dockerfile` now sets `PYTHONPATH=/app/src`, reusing exact bundled source bytes and existing
project-relative evidence layout. This is a packaging correction, not a new retrieval architecture.
It avoids editing checksum-bound loader/runtime code or weakening evidence checks, and keeps
dependency installation in the image while executing the validated source tree. The dedicated
old failing image and observed traceback/health failure are retained, not overwritten as PASS.

The independent runtime verifier first incorrectly used relocation of identical artifact bytes
as its stale sample. With a fixed/app root, valid bytes still correctly validated against the full
evidence chain. I corrected only that test fixture to corrupt mandatory selection evidenceSHA;
the original missing/malformed/stale health/resolve503 requirements still apply. Its initial
assertion failure is also retained. The verifier now additionally records its own and Docker/
Compose packaging hashes, binding the actual HTTP smoke to the exact successful image and files.

### Technical choices and accepted trade-offs

The evaluation remains standard-library/existing deterministic v4 retrieval; no model, threshold,
query policy, database or agent was added. A durable exclusive reservation is intentionally less
convenient than overwrite/rerun, but makes one-shot output and interruptions auditable. Separate
integrity validation necessarily sees labels only for preflight; collection/scoring does not parse
them until all105 raw outputs exist. Fixed42-family coverage measures either paired hit, not an
inflated84-row denominator. The fourmisses and known construction bias are explicit limitations.

Real HTTP within a non-root/read-only container was selected over claiming host TestClient/static
checks prove packaging. It exposed the site-packages/data layout mismatch that prior static checks
missed. Loopback Uvicorn uses no published host port and only existing fixture questions, not a
second final run. Temporary child servers and the test container are cleaned up; previous service,
volumes and PostgreSQL are untouched. Old images remain for diagnosis. The verifier is mounted
read-only rather than added as a runtime dependency. At10×, source-valid T3 posting-cost results
remain the synthetic budget evidence, not a claim of3000 real released variants or production load.

### Actual verification and measurement scope

32 new evaluator/closure tests and411 full repository tests PASS, no skips, one pre-existing
Starlette/AnyIO BlockingPortal deprecation warning. Before real execution, a dict-rendering-order
bug in fake report Markdown was fixed with sorted JSON and a private missing-source fixture was
corrected; its406pass/1fail full run preceded the407-pass pre-final run and evaluator commit.
The final full run411 and32focused cover stored evidence or fake retrieval, not a rerun of final.
RuffF/I, isolated strict MyPy evaluator, compilation, Node UI and static default/postgres Compose
checks pass. Originalv1 benchmark/report/Markdown,199dev,v3FAIL JSON/Markdown,identity protocol
and v4PASS JSON/Markdown reproduce unchanged. Historical full-repo lint/type debt is not claimed
fixed. Source-bound T3 real/scale p95=2.065375/45.138542ms and known-target budget gates validate.

The final105 diagnostic samples use Python3.12.13/Darwinarm64, one non-isolated process, zero
warmups and nearest-rank p50=2.591583/p95=6.945209ms. Extraction is excluded; retrieval plus
serialization included. No new latency gate or causal/HTTP/SQL/production claim is made. Successful
Docker smoke uses Python3.12.14/Linuxaarch64/uid100/read-only and actual loopback HTTP, validates
defaultv2/v4 health/resolve/UI200, identical canonical outputs, typed debug/work/index metadata,
and missing/malformed/stale503. Source and packaging hashes match the host; image identity and
all outputs are in the runtime report. No new SQL or3000-real-row insertion occurred.

### Remaining work and exact next authority

See [final/closure evidence](evidence/family-retrieval-final-v2.md), all105raw results and both
preserved runtime failures. New final quality, source-valid cost, regressions, runtime packaging,
QA/AI rubric and documentation all pass for this feature. T49 DESIGN ONLY may now proceed;
actual promotion/ingestion/defaultv4 deployment is not authorized. The next valuable design work
is a reviewed real release-variant catalog and same-casting color/year/wheel/tampo test cases,
including ambiguous/insufficient-evidence behavior, before expanding toward3000 real rows or
claiming the user's full variant-resolution goal. OldFAILs/defaultv2 and canonical-only final
authority remain unchanged. Commit/push all real progress to the project-only GitHub repo.

## 2026-09-14 — T49 persistence and real-variant roadmap draft (Lite)

### Context, problem and observable outcome

IBR-T5 ataf27dfe permits T49 design only. The user's next-step request follows a scoped family
PASS, not complete variant correctness. I inspected actual canonical schema/identity/signal/catalog
code and source counts before proposing expansion. Human RAG has100provisional+42family docs;
Wiki100release rows all have null color and no dedicated wheel/tampo fields. Existing canonical
identity has seven fields, not wheel/tampo or series-position identity. Consequently, persistence
alone cannot solve the requested color/feature distinctions, and a3,000-row quota cannot replace
evidence/review. The result is a reviewable draft roadmap, not new products or a completed database.

### Changed files and why no product code changed

New `specs/human-knowledge-persistence-and-variant-roadmap/{requirements,design,tasks,review}.md`
defines observableR1–R14 boundaries, proposed snapshot/observation/evidence/review tables,
interfaces/errors/verification and atomic bounded tasks. T49 first plans preservation/measurement
of142typed knowledge documents; a separate release lane starts from100heldsource observations.
The first proposed implementation task is a local-only142doc import-plan validator. It performs
no SQL/network operation. Subsequent isolatedDB/profile/source/release decisions are explicitly
gated. This avoids repurposing canonical `product_variant` for unreviewed evidence or retroactively
editing scored v4/config/identity files whose hashes are already frozen.

`docs/REAL-CATALOG-ROADMAP.md` gives a Chinese beginner-readable explanation of the difference
between saving data and confirming release truth. Source-scope/AI evidence and README progress
now distinguish planning delivery from owner approval/implementation. D46 records the proposed
method and accepted uncertainty. No product Python/API/SQL/migration/runtime/config/data file was
edited, and no family/variant decision was recorded. Requirements/design/tasks are all DRAFT.

### Method choice and trade-offs

PostgreSQL/SQLAlchemy/Alembic is proposed because the project already uses that stack and needs
transactional snapshot/provenance persistence; files-only remains the unchanged default until an
optional profile is independently validated. Versioned JSONB human payloads preserve exact142doc
types/UUIDs; structured field observations and append-only reviews make release conflicts visible.
Reusing canonical tables or a single free-text blob would erase the crucial authority/evidence
distinction. Persistence adapter changes require new source/config/report versions, not silent
edits to scored code. ANN/neural/photo/OCR changes are not bundled into this storage decision.

The release method preserves nulls and field evidence; it does not guess colors from year lists,
toy IDs or filenames. Same-casting/different wheels/tampo can stay separate, while missing fields
cannot prove equivalence. Future identity-v2 must be explicitly designed from real discriminator
evidence, preserving legacy UUIDs. At10×, real source requests, review work and SQL/network/posting
cost are the constraints to measure; no cheap scale conclusion is drawn from storing more rows.
Most likely failure is treating a family approval or database row as confirmed release truth.

Approximate3,000count is narrowed to unique real staged source releases, reported separately
from observations/castings/held/reviewed/canonical rows. Proposed100→500→1,500→about3,000batch
milestones are plans, not execution or permission. There is no policy/threshold/source revision
change based on the viewed final105cases; those results remain immutable and are not queried again.

### Verification and source-access limits actually observed

Read-only `jq` counts/keys and SHA reads confirm97human castings/100provisional groups,
42acceptedknowledge families,42new/4merge/7hold registry,100source rows/all100color-null and
absent dedicated wheel/tampo keys. Committed benchmark and stored finalJSON/Markdown checks
PASS without retrieval. New document links/whitespace and unchanged source hashes are checked
at handoff. Upstream411tests/runtimePASS remain existing evidence, not newly implemented T49 tests.
No DB startup, writes, remote row collection, images, canonical minting or source data edits ran.

Read-only web checks found the official MediaWiki API etiquette page accessible; Fandom licensing
and the Hot_Wheels page returned402 through the browsing service. That tool response does not
prove all API access forbidden or permitted; current source-specific rights/access/robots remains
unverified and gates later collection. General serial/request identity/cache advice is linked in
design; it does not grant Fandom permission. No bypass was attempted. HistoricalCC-BY-SA source
metadata is retained as historical attribution, not upgraded to present legal clearance.

### Remaining work and next owner decision

See [plain-language roadmap](REAL-CATALOG-ROADMAP.md) and
[source-scope evidence](evidence/t49-planning-scope.md). Under spec-dev-loopLiteG1*, pause for
requirements confirmation first, then design and task confirmations. This draft's acceptance
does not itself start a database or authorize3,000-row crawling/canonical promotion. The next
bounded approved implementation would produce the142doc import PLAN, preserving all current
runtime/data/UUIDs. Actual variant grouping/evaluation and canonical rollout remain future work.
All draft progress is committed/pushed only within the independent project GitHub repo.

## T49.1 — 本機 142 筆人工知識匯入計畫與完整性檢查

Date:2026-09-14. Lite mode. This entry records local implementation, not PostgreSQL ingestion.

### 執行內容、問題與可觀察成果

你在詳細草案說明後要求「請幫我執行」，本次將授權限縮為第一個本機任務 T49.1。
沒有將這句話記錄成三次獨立規格確認，也没有假定整份資料庫／蒐集／版本上線方案已獲同意。
先前已有 100 筆 provisional variant 與 42 筆 review family，但缺少一份能在未來匯入前
證明「來源同版、內容完整、ID 沒變、待審限制仍在」的可重現計畫。現在產出的
[plan 與中文報告](../reports/human-knowledge-snapshot-v1/report.md)補上這一層，讓下一步不是
直接把不明版本的資料寫入資料庫。這次新增的是工具和報告，資料集筆數沒有增加。

### 修改位置與原因

新增 `src/product_variant_resolver/human_knowledge_snapshot.py` 管理來源指紋、typed document
序列化／還原、完整計畫重建比對、中文報告與 exclusive publication；新增
`scripts/plan_human_knowledge_snapshot.py` 提供 `--run`／唯讀 `--check`。採用新檔案而非修改
現有 human RAG／config／API／identity，是因為後者已被評估來源指紋封存，不應為儲存準備
偷偷改變其執行行為。既有 typed loader 僅被讀取重用，不重新建立 UUID 或改 ranking。

每筆計畫保留原有 ID、UUID、knowledge type、全部 typed payload，以及原始 casting／variant
或 family／registry entry。只保存 typed payload 會漏掉 failure categories、casting-family-only
層級與人工決策／held release references，所以原始 metadata 也一起保留。來源合約原樣保留，
特別是 `postgresql_ingestion` exclusion；本計畫不是解除限制或正式匯入許可。4 個 merge-source
family 與 7 個 held family 不另建文件，42 個已接受 family 的 79 個 source rows 保持原樣。

### 方法選擇、取捨與決策界線

本次只需要本機 JSON 和 SHA256，因此使用 Python 標準函式庫，沒有增加 SQL／HTTP／ML
依賴。對 12 個直接來源檔案固定已確認版本的指紋，比僅相信 manifest 安全：若資料與
manifest 一起被改，兩者雖然相符，仍可能不是原來的資料。本工具會拒絕。整份 plan 從
固定來源重建再比對，因此即使竄改內容後重新計算 checksum，也不能通過驗證。比對以
JSON bytes 進行，避免 Python 把 `False` 與 `0` 視為相同。snapshot ID 是內容指紋字串，
不是新增商品 UUID。12 檔的 immediate source envelope 不等於重新驗證全部歷史 evidence tree。

另一個取捨是為稽核保留部分重複原始內容；142 筆規模可以接受，但未來 10 倍資料量下
檔案大小與版本審查成本會增加，不能據此宣稱查詢或 SQL 效能足夠。來源變更必須建立
重新審核的新 snapshot 版本，不能修改 v1 指紋假裝舊報告仍有效。D46 的資料表方案仍是
提案，D47 僅接受這個本機方法，沒有重新選擇或啟動 PostgreSQL 技術棧。

報告只發布至專案 reports 下新資料夾；同名再次執行直接拒絕，不覆蓋既有成果。
正常失敗只移除本次建立的檔案，未知／他人檔案保留。若程序被強制中止可能留下不完整
資料夾，checker 會拒絕、重跑也不會覆蓋；這不是 crash-atomic DB transaction 的保證。

### 實際驗證結果

實際讀取並產生 142 筆計畫，`--check` PASS；全部 ID／UUID／typed fields 完整 roundtrip。
新增 37 個測試 PASS，涵蓋每一個來源指紋、缺檔、重複／缺漏／held／錯誤 type 或 UUID、
重算 checksum 後的竄改、原始來源與 exclusion 變動、重複發布、symlink、未完成報告、
失敗清理與保留未知檔案。守衛測試確認新計畫只讀取宣告的 12 個本機輸入，不讀 final queries。
完整回歸 448 tests PASS；唯一 warning 是既有 Starlette／AnyIO BlockingPortal deprecation。
Ruff F/I 與隔離 strict MyPy PASS，compile/static compose/stored final integrity checks PASS。
這些是本機／靜態驗證，不是新的 SQL、容器部署、檢索延遲或版本辨識準確率結果。

plan content SHA256 為 `f7830e460650e99ab5107ec0f049c96d2dcf322daa5c140c5847a53f969e144f`。
格式化 JSON 的檔案 byte hash 與內容 hash 不同；詳見
[執行界線與證據](evidence/t49-1-execution-scope.md)及 [AI artifact rubric](evidence/ai-evals/t49-1-snapshot-plan.md)。
原始資料、已封存模組、final 評估輸出維持不變，沒有啟動新的 final collector。
網站新請求 0、PostgreSQL 寫入 0、新 canonical UUID 0、新真實資料列 0。

### 未完成項目、風險與下一步

T49.2 尚未執行。下一步先指定並確認可丟棄的隔離測試資料庫環境與限定 schema/import
方案，才建立 human snapshot tables 與交易／rollback／idempotence 測試；不能沿用不明
既有資料庫或重設 volume。Human RAG 仍是 debug-only；142 筆儲存不等於 142 筆正式商品。
顏色／輪圈／tampo 等版本證據與約 3,000 筆真實來源蒐集仍是後續獨立工作，本次未確認
網站權限、未推定未知特徵、未改預設 API／v4 rollout。依 Lite 閉環更新任務、QA、decisions
與這份敘事日誌；所有成果限定在独立 Product Variant Resolver repo。

## T49.2 前置檢查 — 隔離測試環境待確認

Date:2026-09-14. Lite mode. No database implementation or write is claimed in this entry.

你要求進行下一步後，本次先確認規格、canonical migration、原有 PostgreSQL importer／
verifier 與 Docker 配置。T49.2 的前提是明確選定隔離測試資料庫，不能將「下一步」視為
操作不明既有 volume 的授權。原有 compose 使用 `pvr-postgres-data` 持久化 volume，
因此沒有直接執行 compose up、migration 或 importer。這解决了測試可能誤碰既有資料的
環境選型問題，但尚未完成 human snapshot 持久化。

唯讀 Docker inventory 起初因 sandbox 無權存取 docker.sock 而拒絕；取得唯讀檢查權限後
查詢成功，沒有執行中的容器，本機已有 PostgreSQL16／pgvector 映像。未檢查或推定所有
stopped containers／volumes 都是空的，也沒有清理任何既有資源。T49.1 的本機 plan
checker 再次 PASS，142文件與來源指紋保持不變；没有重跑 final collector。

新增 [隔離測試方案](T49-2-ISOLATED-TEST-PLAN.md)，說明 internal network、新專屬容器、
tmpfs、無 host port、無既有 volume／使用者資料庫 URL，以及只清理本次 ownership 資源
的提議。選擇臨時新庫而非沿用持久化庫，是為了將可丟棄的交易驗證與工作資料分開；
沿用本機既有 image 避免不必要的下載與版本漂移。tmpfs 不驗證斷電耐久性，不能把結果
升級成正式部署或 crash recovery 證據。將來10倍資料量的 SQL／查詢效能仍需獨立 protocol。

方案也明确說明，120canonical synthetic fixture 僅供新測試庫建立前後不變基準；
142human docs 儲存在独立 human namespace，不是新增正式商品，也不解除原始來源的
canonical／ingestion 排除。確認後才新增 additive migration、repository 與 SQL verifier，
驗證 roundtrip、transaction rollback、相同 snapshot no-op、collision rejection 和全部
canonical rows／IDs／timestamps 不變。本次只修改方案與日誌，未寫產品碼、資料或 SQL；
沒有新增測試結果或完成標記。依 spec-dev-loop Lite 的環境界線暫停，請 owner 確認新
隔離測試庫及限定寫入／清理範圍後，再執行 T49.2。

## T49.2 — 人工知識 PostgreSQL 隔離匯入與真實交易驗證

Date:2026-09-14. Lite mode. Scoped SQL correctness PASS; not production integration.

### 新執行內容與解決的問題

在隔離方案說明後，你指示「執行測試」，因此本次實作並執行 T49.2 限定的新測試庫，
不再停留在 T49.1 的本機匯入 plan。原先缺少的是「142 筆寫入資料庫後仍可完整還原，
而且中途失敗不會留下半份資料」的真實 SQL 證據。現在在 PostgreSQL16.14 實際完成
100provisional variant +42review family 的匯入／讀回／比對，保留原始 ID、UUID、
typed fields、null、raw provenance 與來源排除界線。這142筆仍是人工知識，不是142筆
已確認商品；沒有新增真實 dataset rows、推定顏色／輪圈／tampo 或建立 canonical UUID。

### 修改位置與設計原因

新增 `migrations/versions/0002_human_knowledge_snapshot.py`，只建立獨立 `hk_snapshot`
與 `hk_document`，不改 canonical0001/history。Snapshot 保存 storage version、獨立 test
namespace、固定 plan header/source/contracts/counts/checksum 與 imported_at；子文件保存
原有 ID／UUID／type、順序、完整 typed payload／checksum 與原始來源。把人工知識放進
`product_variant` 會模糊審核權威，所以保持兩条儲存路徑；embedding／release tables 尚未建立。
加入0002會讓 migrationhead 前進，但不改 canonical schema 或 API/default/v4 行為。

新增 `human_knowledge_persistence.py`，在連線前複製並驗證整份固定來源 plan，只允許
明確 disposable authorization 與 matching `pvr_t49_2_<12hex>` DB 名稱，連線後再次驗證
actual database。沒有 `.env` 或正式 database URL fallback。這是另外授權的
`human-knowledge-isolated-storage-test-v1` 保存／測試命名空間，不修改或解除來源本身的
`postgresql_ingestion` exclusion，也不授權 canonical ingestion。Repository 沒有 overwrite
upsert／update／delete 修復路徑；來源或既有 stored snapshot 不完整、竄改就拒絕。

新增 `scripts/verify_human_knowledge_postgres.py` 執行真實 SQL 測試；新增
`scripts/run_human_knowledge_postgres_test.py` 管理只屬於本次的 network／containers、
staging、immutable report 與精確 ownership cleanup。新增兩組測試共25項，分開驗證
repository orchestration 和 supervisor safety；本機 fake 不拿來宣稱 PostgreSQL rollback。

### 方法選型、取捨與調整原因

沿用專案已有 PostgreSQL16／SQLAlchemy2／Alembic，而非換資料庫或新裝 ML stack。
單一 `engine.begin` transaction 配合兩張 human tables 的 SHARE ROW EXCLUSIVE locks，
使完整142筆一起 commit／rollback，也讓同時第一次匯入只能有一個寫入，另一個核對後
no-op。鎖只作用於 human tables，不改 canonical rows。讀回使用 explicit ID+hash、
repeatable-read read-only transaction，避免讀取 latest snapshot 或跨兩次 SELECT 出現不同版本。
這是142筆的小規模簡化；10倍規模下鎖競爭、JSONB／raw provenance 大小與查詢成本仍需量測。

實際前置檢查發現 host venv 沒有 SQLAlchemy，部分原始 family files 權限為600。
選擇既有 SQL-enabled Docker image 搭配 byte-exact staged source 副本，不安裝 host 依賴、
不改原始權限、不重新下載／build image。副本只有必要 Python／migration／config／data／
plan 共54檔，没有使用者 `.env` 或 final questions；report 記錄每個檔案指紋與完整 image IDs。
Optional SQLAlchemy 使用 lazy import，避免未選用資料庫的 offline 路徑強制安裝依賴；
首次 static checks 的 import ordering／缺少 optional stub／Any-return 問題在 SQL 執行前
修正，focused Ruff 與 isolated strict MyPy 再次 PASS，沒有以放寬來源驗證處理問題。

臨時庫使用 tmpfs、新 internal network、無 host published port、不掛既有 volume，runner
UID100/read-only root/read-only staged bind。SQL 測完只依本次完整資源 ID 與 ownership label
移除兩個容器和 network，未接管既有 stopped containers。tmpfs 不是持久性／斷電復原證據，
程序強制中止仍可能留下 owned resources；不宣稱 cleanup crash-atomic。Application importer
維持完整性與 immutable snapshot，但 superuser 手動 SQL 仍可竄改；讀取／重匯入偵測後拒絕，
不是透過 trigger 阻止所有 privileged writes。

另一個相容性界線：歷史 T04 verifier 使用 `upgrade head` 卻固定斷言0001，它是舊 revision
測試，不宣稱可直接用於新0002。保留其歷史來源，改由新的 T49.2 verifier 驗證
0001→0002→0001→0002 的限定循環；沒有改舊斷言或把未執行的 legacy CLI 說成 PASS。

### 實際 SQL 與回歸結果

第一次真實 SQL invocation PASS，未重試。PostgreSQL16.14/Linuxaarch64、Python3.12.14、
SQLAlchemy2.0.52／Alembic1.20.0／psycopg3.3.5。真實 unique violation 在 header 與71筆
子文件已可見後觸發，transaction 完整回滾至0snapshot／0documents；這不是只在寫入前
擋掉壞輸入。之後兩個同時 first imports 得到一個inserted、一個verified unchanged；
最終只有1snapshot／142documents。重複匯入全部 rows／UUIDs／rawJSON／imported_at 不變，
讀回typed documents 與原plan精確一致。缺漏／重複／changed payload／held input 都拒絕；
新測試庫內刻意製造stored header corruption與缺少child，reader/importer均拒絕而不修復。

在全新測試庫先匯入原有120synthetic canonical fixture 作比較基準；7張canonical tables
的每一列、ID／UUID／timestamp 前後完全一致，before/after row-snapshot SHA256 同為
`ed4be9dc736c8ac476ca5fd2a66b4f5e4e104ed25583c98e6fd8c355f60b2daf`。此 hash 包含本次動態
fixture timestamp，不是跨run固定dataset checksum。Actual fixture counts：product_variant120、
product_alias240、identifier120、provenance_record120、index_metadata1、product_search120、
product_embedding0。這些fixture僅写入新測試庫，不是寫入使用者工作資料庫。

25新增測試 PASS；full473tests PASS，唯一 warning仍是既有Starlette／AnyIOBlockingPortal
deprecation。RuffF/I、isolated strictMyPy on repository/supervisor、compile 與 frozenplan/
storedfinal integrity checks PASS。舊 source/data/config/API/identity/Dockerfile/compose/
canonical0001/final artifacts 未改，沒有新的 final collector run、模型重訓或 latency claim。
Raw [SQL report](../reports/human-knowledge-postgres-t49-2.json) SHA256 為
`3450185e2f8b6d97b5b39c3e563265080e8f11d5b8db988bfd28fd448c22c39d`；唯讀 `--check` PASS。
詳見[SQL證據](evidence/t49-2-human-knowledge-postgres.md)與[AI rubric](evidence/ai-evals/t49-2-postgres-storage.md)。

### 清理成果、未完成工作與下一步

本次建立的兩個容器與 internal network 已刪除，cleanup errors0、remaining owned resources0，
tmpfs測試資料已隨容器清除；舊 containers／volumes／images 保留。因此現在沒有一個已填入
142筆、可供日常查詢的永久DB，保留下來的是程式與可追溯報告。正式儲存／role permissions／
durability／optional runtime hydration／perquery SQL cost 尚未驗證，不能把 isolatedSQL PASS
解讀成正式RAG上線。依 Lite 更新任務、QA、decisions 與日誌，所有deliverables都在獨立repo。
下一步 T49.3 先 freeze 新storage profile／source／artifact／development-cost protocol，
不在已scored v4模組原地改寫，不重用final105questions做live selection/replay。
網站權限、約3,000真實資料與exactvariant evidence仍是獨立後續工作；本次授權沒有擴張。

## T49.3 規劃 — 人工知識 storage profile 與 development 驗證協議草案

Date:2026-09-14. Lite mode. Planningdelivery only; approvalfreeze/build/SQL/cost NOT RUN.

### 新執行內容與問題

前一步證明142筆人工知識可以在新隔離PostgreSQL完整保存，並且不改canonical rows；
測試庫已清除，還沒有讓查詢API使用這種來源。你在「下一步規劃profile／測試協議」的
交接後要求執行，因此本次交付限定的T49.3規劃草案，不推定新的DB操作／正式部署授權。
要解決的問題是：換人工知識儲存來源後，如何保證候選與正式答案不變、運作中資料庫
失效時如何拒絕回覆，以及哪些新增成本需要誠實量測。沒有捏造三份規格獨立確認或新輸出。

### 改動位置與理由

新增 `specs/human-storage-profile-development/` 的 requirements/design/tasks/review 與
`protocol-draft.json`，把profile、完整性／錯誤行為、版本綁定、199dev比較與成本步驟寫成
可驗收契約。新增[新手guide](HUMAN-STORAGE-PROFILE-GUIDE.md)解釋儲存來源和RAG計算的差別；
planning evidence／AIrubric、D49、README與上層task同步區分planning／freeze／implementation。
這次沒有修改產品Python、API、config、migration、原始資料或封存report；原因是新adapter
策略與協議需要先確認，不能把草案當成已批准實作。FullT49.3仍未勾選，僅T49.3-PLAN完成。

### 技術選型與從真實介面得到的設計限制

唯讀inspection確認現有API提供 `service_factory` hook，ResolverService constructor 可接
明確HumanKnowledgeCatalog與v4config。因此提議新增compositional factory，而不是修改
已scored service/config/api或monkeypatch舊global app。PostgreSQL只作人工snapshot儲存與
完整性來源，human候選仍用未修改castingidentity gate／hash192／RRF60／floor0.5／weight1.0。
不能因此稱為perquery SQLvector retrieval；canonical RAG仍唯一控制正式UUID、product、
status、confidence、policy／calibration，human RAG僅debug。顏色／輪圈／tampo仍需後續
release evidence，不能由casting family結果推定。

另一個實際限制是HumanKnowledgeV4Config固定oldmathprotocol SHA，不能把新storageprotocol
hash塞進同一欄位。草案將兩個protocol／newartifact references分開，保留原math參數與
oldsource/artifact的排除界線。T49.2repository固定142與disposableDBnameguard也不放寬；
新的readprofile只在另外確認的新隔離環境使用，沒有任意workingDB URL／latestfallback。
HTTPtitlemax500和直接human core512char／64pretokens等限制分開，不偷偷改公開API上限。

### 儲存／健康檢查方法的取捨

草案選擇啟動时建立cached142docindex，但在每次health／有效resolve前唯讀核對完整
selectedsnapshot。Startup-only hydration較省，但DB在啟動後斷線／被改／少文件仍可能
顯示healthy，不符合本次failclosed語意；header-only probe又無法發現childpayload被改。
因此提議SELECT-only application role、完整snapshot/source比對，失敗503且latch至restart，
不autoretry／repair／filefallback。代價是每請求SQL與network完整性工作、較嚴格availability；
HTTP成本要包含這些，不能只量memory核心。此方法仍待確認，沒有把它寫成已測功能。

10倍規模下fullsnapshot JSON／sourcevalidation／network成本會增長，應先依新協議量測
再改validation策略，不能提早宣稱3,000真實商品或高吞吐能力。Current142-only snapshot
合約也不能直接塞synthetic3000拿來當SQLscale結果。PerquerySQLvector／ANN／neuralindex
會影響admission／fusion與artifact，另案處理，不綑綁在保存資料這一步。

### 驗證協議草案與本次實際檢查

固定199devcases：168positive／4merge／7hold／20unrelated，新file／DB兩路各199一次性
correctness calls（無prewarmup／retry），原default另199nondebugreferencecalls。候選排序、
全部score／rank／type／ID／UUID／typedpayload／workcounters要一致，正式nondebug body
與default完全相同。這是已見過輸出的development資料，不是新holdout；草案誠實記錄
legacydev/final outputs viewed=true，newstorage outputs=false，不重跑final105或做參數搜索。
Raw先發布再score，失敗run保留。Cost另5startup/profile與199pairedHTTP/core samples，
3warmups/profile，nearest-rankp95；提出5000msstartup／150msintegrity／250msHTTP／25mscore
工程上限，需先批准封存，不是已測SLA或從新輸出倒推的門檻。

本次實際只有JSONparse／draftfalse-null狀態／199與142counts／11baseline sourcehash checks、
文件whitespace以及唯讀upstreamplan／T49.2／storedfinal integrity checks PASS。原有473tests
和SQLPASS是上一步證據，沒有重新包裝成新增profiletest；沒有profileadapter、role、DB、
retrieval或新latency／accuracy输出。Approvedspec／actualadapter manifest／runtimeimage欄位
維持null，protocol狀態 `draft_unapproved_not_executable`，不宣稱已freeze或可執行。
詳見[planning evidence](evidence/t49-3-planning.md)與[AI rubric](evidence/ai-evals/t49-3-profile-planning.md)。

### 下一步與未完成範圍

依spec-dev-loopLite先請owner確認新需求，再確認設計、任務與budgets，才建立approvedspec/
protocol與sourcefreeze；之後新file／DBadapter、完整性gate與新的隔離測試依HSP1–4分步做。
本次只送交草案，不做正式rollout或新DB寫入。T49.3fullimplementation／T49.4runtimepackaging/
closure、約3,000真實來源與exactvariant review都未完成。所有deliverables限於獨立Product
Variant Resolver repo，project log繼續保留原因、選型、scope與真實驗證，而不是只列已做事項。

## 2026-09-14 — T49.3 需求確認與設計交接（Lite）

Owner在需求說明後回覆「確認完成，請繼續執行」。本次執行將這個確認沉澱成可追溯的
[approval ledger](../specs/human-storage-profile-development/approval.md)，解決草案已送交、
但文件尚未區分需求已接受與整體實作尚未批准的問題。確認限定於 c197d0f 的需求文件
與其完整SHA-256；保留原文件bytes，不修改後再假裝仍是同一份已批准內容。

修改集中於新確認紀錄、protocol草案的requirements flag、tasks/review、README與教學指南。
沒有修改產品模組、migration、資料或舊測試證據。設計及任務／成本預算仍待分別確認，
protocol仍為不可執行草案，approved-spec、actual-source與runtime bindings保持null。
採用外部ledger而非覆寫需求版本，是為了讓後續freeze可以準確指回使用者實際確認的內容。

本次設計交接說明新file／PostgreSQL來源如何在啟動時建立同一份142筆記憶體索引，
以及每次有效請求前完整唯讀核對snapshot的取捨。完整核對比只看連線或header昂貴，
但能發現運作中斷線、缺文件或payload改動；HTTP成本必須包含它。原API不切換預設，
canonical仍控制正式答案，human仍只提供debug證據，舊檢索數學參數不因storage變更而改動。
這些是待確認的設計，不是已實作功能；尚未增加DB角色、SQL run、199筆新輸出或效能數字。

驗證僅核對已批准需求SHA、JSON的單一確認flag及false/null未執行界線，以及git whitespace
檢查；結果PASS。不重跑產品測試、SQL或final105，既有473 tests不當成本次新增功能證據。
下一步先取得設計確認，再送交任務／預算確認，之後才可執行HSP-1的封存工作。
Full T49.3/HSP1–4/T49.4仍未完成，所有本次文件都保留在獨立專案資料夾。

## 2026-09-14 — T49.3 設計確認與任務／成本交接（Lite）

Owner在設計說明後回覆「確認 繼續下一步」。本次把確認綁定到7a90be0的design文件
SHA-256，補入[確認ledger](../specs/human-storage-profile-development/approval.md)，
保留已確認的需求及設計bytes。這解決需求已批准但設計狀態仍停留WAIT的追蹤落差，
並且沒有把「下一步」擴大成全部任務、成本預算或新SQL環境已獲批准。

修改僅涉及protocol的design flag、ledger、tasks/review、README、教學指南與AI rubric。
教學指南補充四個任務順序及成本計時界線，讓不熟程式的owner知道先封存再實作、
模擬API測試與真實SQL證據不同，以及為何完整HTTP耗時不能用純記憶體檢索耗時代替。
沒有新增產品模組或migration。整體G1仍等待第三份任務／預算確認，execution bindings
仍null，新輸出與執行flags仍false；HSP1–4及Full T49.3仍未勾選。

方法與技術棧維持已確認設計，不重新挑選檢索模型。成本協議保留每一路5個獨立程序
初始化樣本、HTTP／core各3次預熱及199樣本、單worker循序測量，及5000／150／250／25ms
四個p95門檻。門檻是待批准的本機工程上限，不是已測SLA；特別說明5個啟動樣本的
nearest-rank p95就是最慢樣本，避免讓小樣本看起來像可靠的長期延遲統計。成本預熱
不混入199題零預熱的正確性比較，也不重跑挑選成功結果。HSP-3新隔離SQL run仍需
另外明確授權，既有測試庫或volume不在scope內。

實際驗證只有JSON確認界線、原需求／設計SHA未變與git diff whitespace檢查PASS。
本次没有新測試套件、SQL、檢索或效能輸出，既有473 tests仍只屬上游證據。下一個
最高價值步驟是確認任務／耗時預算，然後執行HSP-1封存，不是立刻建立工作資料庫。
所有文件仍限於Product Variant Resolver資料夾，project log保留原因、取捨與未完成項。

## 2026-09-14 — HSP-1 開始實作：封存已批准的輸入，而非宣稱API整合完成

Owner在任務／耗時上限說明後指示「開始執行」。本次完成第三份確認，通過限定於新
storage profile的G1，並實際執行第一個任務。原本只有草案與口頭確認，尚不能確定日後
測試用的是哪份規格；現在新增8檔案封存，保存原需求、設計、任務、協議草案bytes，
以及批准紀錄、新protocol、宣告profile與manifest。它綁定26個既有輸入指紋，不新增
142筆副本或商品UUID，也沒有開始199題實驗／SQL run。參見[實際驗收證據](evidence/t49-3-input-freeze.md)。

新增`scripts/freeze_human_storage_development.py`負責明確Git版本的規格讀取、SHA核對、
衍生批准協議、exclusive publication與check；新增test文件以暫存資料測資料改動、
缺檔／多檔／symlink、改規格或producer、拒絕覆寫及pending狀態。程式選用Python標準庫，
沒有安裝SQL或模型依賴：這一步只需Git與檔案驗證，用資料庫工具反而增加範圍與憑證風險。
先提交producer為448f9c0，再產生封存，讓manifest能指回真正已提交的產生程式。

設計沒有重新選型。保留舊math protocol，另建storage protocol；approved_spec hash是
四份commit/path/SHA bindings的canonical JSON指紋，原文件各自也有byte SHA。
選Git snapshot而非改寫所有draft標頭，是為了留下owner實際確認內容。選exclusive
publication而非覆寫既有結果，是為了留下失敗或變動痕跡；代價是程序被殺可能留partial
directory，必須由check拒絕，不能宣稱crash-atomic或OS強制不可寫。
新profile仍只是合約，actual adapter/import manifest及image IDs都null，ready=false；
後续HSP-2需補完並封存全imported sources/runtime，不能沿用此次不完整runtime binding。

實際新增16項測試PASS；Ruff F/I與isolated strict MyPy PASS，freeze／check均PASS。
第一次完整pytest未帶PYTHONPATH，488PASS／1FAIL：既有report測試的子程序找不到套件。
沒有改產品碼或測試assertion，補上既有執行方式`PYTHONPATH=src`後489PASS，保留一項
Starlette／AnyIO既有deprecation warning。這是修正測試呼叫環境，不是重跑真實實驗挑結果；
兩次結果都寫入evidence。14.22秒是測試套件耗時，不當成profile latency。
既有src、migration、config、核心資料與舊supervisor差異為空；沒有新增DB或憑證。

決策D50只接受input freeze，D49 runtime安全／成本尚未驗證。HSP-1勾選完成，但Full
T49.3、HSP2–4與T49.4不勾選。下一步新增profile loader、唯讀完整性gate與組合式API入口，
先以單元／模擬測試驗證；HSP-3真實SQL隔離環境仍須另外明確批准。所有產物與日誌
都位於Product Variant Resolver獨立repo，沒有把root agent設定納入推送。

## 2026-09-14 — HSP-2：接上可選儲存安全門，但不把fake DB說成PostgreSQL證據

Owner在HSP-1完成、下一步明確標為HSP-2後要求「執行下一步」。此前只有固定的協議，
API還不能選擇file／PostgreSQL snapshot，也不能在啟動後偵測來源失效。本次新增獨立
storage profile與app入口：啟動驗證完整142筆並建立既有v4記憶體索引，每個health／
有效resolve再完整唯讀核對來源；一旦失敗便清空app service，直到process restart都503。
原`api:app`仍正常ready，新entrypoint沒profile則not ready，沒有默認切換或舊路fallback。

`human_knowledge_storage_profile.py`修改的是儲存合約邊界：strict/no-duplicate JSON、相對
contained paths、storage/math protocol分離、plan與source SHA、兩種mode、外部URL env及
runtime/mock狀態；Postgres只接受既有`pvr_t49_2_<12hex>`guard。它透過既有repository
的whole-snapshot reader，不新增寫入／修復方法。`human_knowledge_storage_app.py`修改的是
組合邊界：subclass先probe再`super.resolve`，debug在既有timing/model maps增加storage
版本，nondebug canonical body不增加欄位。Health wrapper增加獨立storage dependency，
不把human SQL冒充原`database`（canonical backend）。舊API/service/config/v4/data未修改。

選subclass+factory是因為既有API已提供service_factory、ResolverService已接受明確human
catalog/v4 config；直接改凍結模組較短，卻會破壞先前source-bound證據。選每次完整142
核對而非啟動一次／只看header，才能發現斷線與child payload變動；代價是SQL/network
成本與較嚴格availability，留給HSP-4按已批准門檻實測。沒有用SQL做TopK或改0.5／1.0／
hash192／RRF60，Dual RAG仍由canonical決定正式答案，human只在debug提供casting證據。

測試選private fake repository，使HSP-2能驗證呼叫與故障語意而不偷啟動DB。42項adapter/API
測試後，來源封存測試共55PASS；完整套件544PASS，Ruff/MyPy/compileall與只讀上游checks
PASS。過程保留三類問題：pytest保留參數造成collection error；短`Chevy Nomad`不保證
matched的錯誤測試假設（換成既有明確catalog case，產品碼未改）；第一次source generator
只hash工作檔，50PASS/4FAIL揭露未綁同commit，後改為42檔逐一比對Git bytes。
Starlette/AnyIO既有deprecation仍1項。這些是開發測試，不是199題新結果或latency。

最初commit5d9e2f3的candidate1在review時又發現health缺獨立versioned dependency；依不覆寫
原則保留並加SUPERSEDED說明。補強後commit bd2a838產生accepted candidate2，adapter
manifest`93a8b631…`、42inputs、ready=false、runtime images=null。此決策改變的是「來源
候選版本」，不改需求、數學或輸出權限。HSP-2因此完成，但HSP-3真實SQL仍未授權：
SELECT-only role拒寫、199file/DB逐筆parity、完整fault matrix與runtime image還沒驗證；
HSP-4成本也未量。下一步先向owner說明新的隔離環境與動作，再取得明確SQL run指示。

所有程式、tests、兩個candidate與敘述證據只在Product Variant Resolver repo；沒有加入
root agent設定、憑證、資料庫URL或現有volume。3,000真實資料及顏色／輪圈／tampo精確
variant仍屬後續來源審查，不從本次casting-level storage結果推論。

## Required format for future entries

Every future project-log entry must preserve the following traceability structure:

1. **Context, problem, and observable outcome:** explain what triggered the work, what was wrong or
   missing, what was executed, and what a caller or evaluator can observe afterward.
2. **Implementation trace:** name the changed modules or file groups and explain why each group
   changed; do not provide only a list of completed tasks.
3. **Technical choices, alternatives, and trade-offs:** record the selected method, viable
   alternatives considered, and the cost or limitation accepted.
4. **Decision changes:** when a choice is reversed or narrowed, record the before/after decision,
   the exact evidence that triggered it, and any version/configuration impact.
5. **Verification evidence:** cite commands/results already produced by the responsible agent,
   frozen data/report versions, raw-count-derived metrics, runtime/hardware, and measurement scope.
   Never upgrade a static check into runtime evidence or a synthetic result into a production claim.
6. **Incomplete work, risks, and next step:** state deferred adapters, unrun environments/reviews,
   known warnings, and the single highest-value next action.

Entries may use a small table or compact list for navigation, but the main record must remain an
explanatory engineering narrative linked to existing specifications, code, QA evidence, or reports.

## 2026-09-15 — HSP-3：證明 file 與 PostgreSQL 儲存等價，保留三次測試基礎設施失敗

使用者在上一階段已被明確告知下一步是另建隔離SQL環境後，要求「繼續執行下一步」，因此
本次只執行HSP-3，不擴張到HSP-4成本測試或正式部署。問題不是再改善檢索準確率，而是此前
只有private fake repository，尚未證明同一份142筆human knowledge放在JSON file或真實
PostgreSQL時會得到相同結果。現在可觀察的成果是：固定199題的兩路human候選與work
counters逐筆完全一致，正式canonical body也與原default API一致；真實reader只能SELECT，
斷線／內容破壞會503並鎖住到restart。Dual RAG權限未改，human仍不能填入正式UUID答案。

程式修改集中在四個新HSP-3 scripts與一個test。`freeze_human_storage_hsp3_run.py`先固定每次
執行的source commit、兩個runtime profile、development pack、protocol、image ID及一次性
resource名稱，避免先看到結果再改條件。`run_human_storage_profile_sql.py`只建立帶本次label的
internal network、tmpfs PostgreSQL和read-only runner，不使用compose／host port／volume；
密碼每次隨機產生，只進短期container environment，錯誤報告只保存stderr hash。
`verify_human_storage_profile_sql.py`先migration及匯入canonical120+human142，再建SELECT-only
role，交錯執行199組file／DB health+resolve與199個default reference，最後注入10個啟動故障、
4個啟動後故障、5個無效HTTP和4種寫入。`score_human_storage_profile_sql.py`只讀已發布raw，
不呼叫SQL或retrieval。這個分離是為了滿足raw-before-score，而不是單一script邊跑邊挑結果。

方法選擇延續PostgreSQL16、SQLAlchemy2、Alembic與既有whole-snapshot reader，因為HSP-3
要隔離「storage」變因；沒有改成SQL TopK／pgvector ANN，否則同時改了candidate admission與
數學，無法知道差異來自儲存還是模型。每個有效health／resolve完整讀142筆，能看見child
corruption，但成本較高；HSP-4才會按已固定的5次startup、3次warmup與199 HTTP/core樣本評估，
本次25.6秒總執行時間不能當作latency。相同request ID及奇偶交錯順序降低固定順序偏差；
21個空候選保留，沒有只報好看的178筆。3,000筆、顏色、輪圈、tampo與release identity仍未驗證。

執行過程的決策有三次窄化，全部保留而沒有覆寫成一次成功。Run-v1在建立role時發現
PostgreSQL DDL不能用`$1`綁password；改成只接受48位hex後安全嵌入DDL。該失敗trace曾回顯
已隨DB刪除而失效的短期密碼，基於密鑰零落地刪除敏感raw，留下明示redaction的sanitized
失敗紀錄，後續supervisor只存stderr SHA。Run-v2的missing-snapshot fixture先刪header，
被FK23503正確拒絕；改為children先刪。Run-v3直接寫錯namespace，被CHECK23514拒絕；
改成bootstrap暫時drop該human-table constraint、寫錯值讓app驗503，再恢復值與constraint。
每次修改先commit，再另建run-v2/v3/v4 freeze；每組container/network都確認cleanup errors=0、
remaining owned resources=[]。這些是故障注入方法修正，沒有改產品碼、資料或正確性門檻。

最終run-v4 raw SHA`19301513…0454`先發布，之後evaluation SHA`a6fdcb34…0895`才產生，
exact parity199/199；case組成168positive/4merge/7hold/20unrelated，兩路各21空候選、262個
候選總數，所有per-case health=200及request ID一致。Reader attributes為LOGIN true，
super/inherit/create-role/create-db false，兩張human tables只有SELECT；四種寫入均SQLSTATE42501。
10startup及4post-start故障皆503，修復來源後同process仍503；無效HTTP為400/415/422且probe0。
七張canonical table前後SHA同為`1d7b7f8a…bc172`。Linux aarch64、Python3.12.14、
PostgreSQL16.14、SQLAlchemy2.0.52、Alembic1.20.0、psycopg3.3.5、runner UID100。
Focused59、完整548測試PASS，Ruff F/I/format、strict isolated MyPy與compileall PASS；只剩既有
Starlette／AnyIO deprecation warning。詳細證據在`docs/evidence/t49-3-storage-profile-sql.md`。

HSP-3因此完成，但Full T49.3仍不能勾選：HSP-4尚未量啟動、每次完整snapshot revalidation、
真實loopback HTTP及core成本，也沒有3k/concurrency/durability/production證據。下一個最高價值
動作是先依凍結cost protocol檢查HSP-4執行條件與資源界線，再決定是否啟動新的測量環境。

## 2026-09-15 — HSP-4：量出完整snapshot安全門的成本，完成限定T49.3

### 背景、問題與可觀察結果

使用者在HSP-3完成且下一步已明確說明為HSP-4後要求「繼續執行」。先前已證明file與真實
PostgreSQL保存同一142筆human knowledge時，固定199題的檢索結果完全相同，但「每個有效
request都重讀完整snapshot」的時間成本仍未知。因此這次不是再調Dual RAG準確率，而是依
已批准且預先封存的工程上限，量profile初始化、完整性核對、真實HTTP與純human retrieval。
最後八個file／PostgreSQL p95 gate全數PASS；bounded T49.3因此完成，原default API仍未切換，
T49.4封裝／rollout、3,000筆與顏色／輪圈／tampo release identity仍保持未完成。

### 程式修改與原因

新增的四個HSP-4 scripts把「固定考卷」「建立一次性環境」「收集raw」「離線評分」分開。
`freeze_human_storage_hsp4_run.py`先綁implementation commit、兩個profile、199題pack、cost
protocol、image IDs及owner resource名稱，避免看到速度後改條件。`run_human_storage_profile_cost.py`
只建立帶`pvr.t49-4.owner`label的internal network、tmpfs PostgreSQL與read-only runner，密碼只在
執行時隨機產生；完成後只按精確label與ID清理。`verify_human_storage_profile_cost.py`建立
SELECT-only reader，取兩路各5次新process初始化、3次HTTP／core預熱與199次交錯正式樣本，
並保留每筆duration、status、error、abstention。`score_human_storage_profile_cost.py`不再碰DB
或HTTP，只驗合約／數量後用nearest-rank套固定門檻。新test覆蓋percentile、PASS／FAIL門檻、
樣本數、隔離參數與不得依賴缺失`httpx`。產品retrieval、API、資料、migration及門檻未修改。

### 技術選型、替代方案與代價

測量使用真實Uvicorn loopback而非TestClient，因為HTTP預算需包含ASGI server、序列化與client
解析；core則用已初始化service及預先抽取signals，刻意排除SQL／integrity／canonical／HTTP，
讓兩個數字回答不同問題。file與PostgreSQL按奇偶交錯，避免固定「永遠先file」的順序偏差。
nearest-rank不用插值；5個startup的p95等於最慢值，計算保守但樣本小，不能冒充長期SLA。
資料庫沿用PostgreSQL16、SQLAlchemy2、Alembic與whole-snapshot adapter；沒有改成SQL TopK或
ANN，因為那會同時改候選數學而破壞storage-only比較。代價是每個有效request完整讀142筆，
PostgreSQL HTTP p95比file多約7.52ms，但42.77ms integrity與46.16ms整體HTTP仍低於原門檻。

### 決策改變與觸發證據

Run-v1在任何計時樣本產生前停止。原因不是速度不合格，而是固定runner映像有Uvicorn卻沒有
`httpx`，module import時即失敗，原supervisor只得到空stdout的JSONDecodeError。v1 raw仍保留，
兩container與network全數清除，且沒有密碼／DB URL。沒有臨時下載套件或換一個較有利的映像；
改用Python內建`urllib`維持相同real-HTTP計時邊界，並讓supervisor對空／非法stdout產生結構化
runtime_error及stdout/stderr SHA。修正先commit`31a97e4`，再建立獨立run-v2 freeze`ff5b7d4`。
兩版image、資料、protocol與門檻不變；v2不是看到慢結果後的重跑，也沒有timed retry。

### 驗證證據

Run-v2 raw SHA`78e9eb938ff3615ebc3cf51418e9c06c463cf397a4f6138526863a0ced6c87ed`
先以unscored發布，包含10個startup、12個warmup、398個HTTP與398個core正式結果；HTTP／core
error均為0。之後evaluation SHA`af5ff062fb1f269f3b07ab27c9059a9d9ad31a4487f5ac131aadf724805dcccc`
才評分。file／PostgreSQL p95依序為：startup271.142／300.175ms（上限5000）、HTTP38.645／
46.163ms（250）、integrity34.204／42.773ms（150）、core2.311／2.306ms（25），八項PASS。
環境為Linux arm64、Python3.12.14、PostgreSQL16.14、Uvicorn0.52.4、SQLAlchemy2.0.52、
Alembic1.20.0、psycopg3.3.5、UID100。reader只有LOGIN+兩表SELECT，無super/inherit/create
role/database。兩containers與internal network已刪除，cleanup errors與remaining均空。

聚焦79項測試PASS。第一次完整pytest未帶`PYTHONPATH=src`，既有evaluation子程序因找不到
package而1FAIL；沒有改碼或assertion，依專案既有方式補`PYTHONPATH=src`後552/552 PASS。
changed-file Ruff F/I、strict isolated MyPy與compileall PASS，仍有一項既有Starlette/AnyIO
warning。全repo Ruff另列54個本次以前的import-order債務，沒有趁此任務大量改無關檔案。

### 未完成、風險與下一步

這份PASS只涵蓋本機ARM64、142份文件、單worker、concurrency1；沒有測throughput、多worker、
durability、production SLA或10倍／3,000筆完整snapshot成本，也沒有驗證來源權利與release-level
顏色／輪圈／tampo。下一個最高價值動作是T49.4：把已通過的可選profile整理成可操作的
runtime packaging/runbook，明確決定仍維持opt-in或另行批准rollout；不能因T49.3通過就自動
更改default API或建立長期本機資料庫。

## 2026-09-15 — T49.4：把可選file profile做成可重現的Docker服務

### 背景、問題與可觀察結果

使用者在HSP-4完成、下一步已明確指出為T49.4後要求繼續執行。當時程式已證明file與
PostgreSQL保存相同142筆human knowledge會產生相同候選，也量過本機成本，但一般使用者仍
沒有一條被驗證過的方式把storage-gated app啟動起來。這次新增的是可選runtime package，
不是新的Dual RAG演算法或資料。現在操作員可透過獨立Compose profile啟動file-backed服務；
缺profile會停止，正常服務health會顯示固定storage version，四組非debug正式回應與default
reference完全相同。原本API的Docker路徑、canonical權限與預設行為沒有被切換。

### 程式修改與原因

`Dockerfile.human-storage`與專用`.dockerignore`建立一個能執行strict profile loader的最小映像，
只帶`src/data/config/ui`、必要scripts和被遞迴驗證的selection/plan證據；這樣後來新增一般QA
report不會無意改變映像。`docker-compose.human-storage.yml`同時提供default reference與只有
明確`--profile human-storage`才選到的storage service，將profile以read-only bind掛入，並保留
nonroot、read-only root、tmpfs、loopback和single worker界線。

`freeze_human_storage_runtime_package.py`在看runtime輸出前，將implementation commit、確切
image ID、profile SHA、來源與封裝檔hash寫入不可覆寫的versioned package；`verify_...py`則建立
唯一Compose project，先測缺profile，再測health/debug／四筆正式回應／Docker inspect，最後
只清理由owner label辨識的資源。新增七項static tests檢查opt-in、allowlist、freeze與cleanup
合約。規格、review、runbook、QA evidence及AI rubric同步建立，避免只有程式沒有接手說明。

### 技術選型、替代方案與代價

採用獨立Dockerfile/Compose而不是修改歷史封裝，因為IBR-T5已把原三個檔案的SHA當作驗收
證據。外部profile不能直接烘進自己所綁定的image，否則會形成「要先知道image ID才能build
該image」的循環，所以先build再exclusive freeze，runtime只讀掛載。選擇file mode是因為它
不需要放寬目前只允許一次性DB名稱的guard，也不需要發明正式secret、migration/import、backup
與volume生命週期。代價是這一步沒有帶來長期PostgreSQL服務，而且顯式allowlist在協議新增
間接證據時必須維護；這是可稽核性換來的維護成本。

### 決策改變與觸發證據

最初曾直接修改`.dockerignore`、`Dockerfile`與`docker-compose.yml`加入storage service；聚焦
回歸測試立刻以IBR-T5封裝SHA漂移失敗，因此三檔完整還原，改成三個專用新檔。這不是單純
換檔名，而是保留歷史runtime證據與不改default路徑的必要決策。

第一個專用映像`923da9b4…8617`及v1 freeze也沒有被包裝成成功。缺profile測試正常拒絕，
但真正startup因v4 math protocol遞迴要求`family-retrieval-development-v1/selection.json`而失敗；
profile直接列出的檔案完整，間接證據卻沒進image。沒有關掉遞迴SHA檢查或粗暴複製所有reports，
而是加入確切selection/plan與兩個producer，再以新commit重build成`d8ccf54d…0e718`並另建v2
freeze。v1 sanitized failure仍在repo，能回答「為何現在image需要那些看似不像產品碼的檔案」。

### 驗證證據

v2 manifest/profile SHA為`b89dfbc4…624`/`a51d3112…980a`。隔離Docker report先於本次收尾文件
產生，SHA`bac44242…761c`、verdict PASS：missing profile exit1且path未被建立；兩service health
200；四個canonical comparison均200/200且內容hash一致；debug有固定storage version/SHA及
integrity timing。Docker inspect確認兩container都是確切image、user`pvr`、read-only root，
storage profile mount為RO，host僅`127.0.0.1:18080/18081`。cleanup errors與remaining皆空。

完整`PYTHONPATH=src .venv/bin/pytest -q`為559/559 PASS，聚焦package/storage/API/v4 closure為
71/71 PASS；兩個scripts的strict isolated MyPy、compileall、changed-Python Ruff F/I和Compose
config均PASS，仍只有既有Starlette／AnyIO deprecation warning。一次QA命令誤把Dockerfile交給
Ruff當Python而得到78個syntax findings；適用的Python-only Ruff隨後PASS，Dockerfile也已成功
build及實際啟動，因此該次結果是命令選檔錯誤，不是隱藏的產品失敗。

### 未完成、風險與下一步

T49.4只涵蓋本機ARM64、142 documents、file mode、one worker及循序smoke。沒有PostgreSQL
deployment、正式TLS/proxy、concurrency/durability/SLA或3,000筆成本，也沒有證明外部來源權利
或顏色／輪圈／tampo的release-level identity。下一個最高價值功能工作是VAR-PLAN1：先建立
100筆來源列的欄位證據審查計畫，保留unknown/conflict，再提出小批人工review；不能把目前
casting storage PASS直接升級為variant資料已完成。

## 2026-09-15 — VAR-PLAN1：把100筆來源列拆成可逐欄審查的證據，而不是直接叫作版本

### 背景、問題與可觀察結果

使用者在T49.4完成並被告知下一步是VAR-PLAN1後要求繼續。專案此前已能辨識casting family，
也能保存142份human knowledge，但同一casting的顏色、輪圈、tampo和包裝差異仍沒有release
truth。這次讀取現有100筆2025來源，確認100筆color全是null、wheel/tampo欄位不存在；45筆
只有`2nd Color`、`3rd Color`或`Zamac`文字提示。因此可觀察成果是完整100筆欄位證據plan，
不是100個已驗證variant：每筆仍held、沒有canonical UUID或variant equivalence，並提出一個
4families/11rows的第一批人工review工作量。

### 程式修改與原因

新增`plan_release_field_evidence_review.py`，在本機將normalized100、cross-catalog review100與
最終53-family queue以`source_record_id`做嚴格一對一join。每列得到另一個deterministic
observation ID，避免把來源列ID誤當產品identity。十三個欄位各自保存raw value、
`observed_unverified/unknown`狀態、來源JSON pointer及未來允許的人類狀態；variant note只照錄，
不解析成顏色。`--run`只能發布到不存在的資料夾，`--check`從三個來源重新產生並逐byte比較。

新spec定義EARS需求、資料權限、批次選擇及錯誤界線；JSON計畫保留100筆機器可驗證資料，
Markdown讓初學者能先看差距與批次。九項test覆蓋100筆membership、null、all-held、ID分離、
完整family批次、不可覆寫／漂移、來源刪列及無network/DB client。review、evidence、AI rubric、
架構決策、README與本日誌同步更新，因為「如何知道這個值能不能相信」是此功能的主要產物。

### 技術選型、替代方案與代價

採逐欄evidence envelope而非只有一個row-level confidence，因為series可能有來源而color未知，
不能讓整列看起來同樣可信。選用observation ID而不產生variant ID，因為觀察一列只證明來源
存在；兩列都缺wheel也不能推出同一版本。第一批使用complete-family greedy pattern coverage，
最多5 families/15 rows，讓reviewer同時看到same-casting siblings並涵蓋create/merge/hold、
series差異、Zamac與無note情境。代價是這批刻意多樣，不是隨機抽樣，不能估計variant accuracy。

沒有用spreadsheet手填固定清單，因為那難以重現來源hash與遺漏；沒有先爬casting pages，因為
目前source-specific rights/access仍未重新確認。JSON在100筆規模最簡單，10倍時可能需要分頁或
資料庫，但現在先驗證review工作流，避免替尚未證明可用的流程過早做基礎建設。

### 決策改變與觸發證據

第一次未提交的plan顯示第五個family重複Lamborghini Huracán Sterrato。根因是selector將加入
`new_coverage_at_selection`後的字典，拿去和原candidate做整個字典相等比較；shape不同便被當成
尚未選過。錯誤兩個產物被精確刪除，selector改以immutable`family_review_id`集合追蹤，test要求
family ID unique。進一步發現第五組沒有增加任何風險覆蓋，因此不再為了湊到5組而選；當三種
decision與所有資料pattern已覆蓋就停止，最終得到較小的4families/11rows，來源與欄位規則不變。

### 驗證證據

最終JSON/Markdown SHA為`f470d731…675a`/`ae3ffe3a…c43f`，綁定三個輸入SHA
`e5e0384a…b9a6`,`72029287…c4e`,`989bc914…e4d8`。計數為100 source/100 observation/53 families；
color/wheel/tampo/edition/packaging unknown各100，literal variant note45；held100，canonical UUID、
variant equivalence、owner field decision皆0。第一批包含Lamborghini Huracán Sterrato3、Subaru
BRZ3、Nissan Skyline 2000GT-R LBWK3及'87 Audi quattro2。

聚焦9項與完整568項測試PASS。changed-file Ruff F/I、strict MyPy、compileall與artifact`--check`
PASS；只有既有Starlette／AnyIO deprecation warning。測試還以刪成99筆的暫存來源確認planner會
fail closed，並確認script沒有requests/httpx/urllib/SQLAlchemy/psycopg/Docker client import。

### 未完成、風險與下一步

沒有任何欄位被owner確認，也沒有檢查目前Fandom授權／robots／API可用性、讀新頁面、處理圖片、
寫SQL或改runtime。這不是100 verified variants，更不是3,000產品進度。下一個最高價值動作是
owner逐欄審查batch01的11筆：每個非null值要綁文字證據，無法證明保持unknown，有歧義標
conflicted，並分別決定same release/different release/unresolved。完成這個人類authority事件後，
才能決定是否建立append-only decision artifact；VAR-PLAN2遠端收集仍須另行確認rights與budget。

## 2026-09-15 — VAR-REVIEW1-PREP：把11筆資料變成owner真正能逐項回答的審查表

### 背景、問題與可觀察結果

使用者在VAR-PLAN1完成並被告知下一步是審查11筆後要求繼續。上一階段只決定「先看哪四個
families」，但plan.json有100筆×13欄，並未將過去research中的文字證據、每列差異與需要回答
的same/different/unresolved問題放在同一畫面。本次可觀察成果是batch01 packet：4families、
11rows、10個within-family pairs、143個欄位決定slot，以及一份全部空白的owner decision
template。它仍標示owner decisions0、canonical changes0、all rows held，沒有替使用者簽核。

### 程式修改與原因

新增`prepare_release_field_review_batch.py`，先驗VAR-PLAN1固定SHA與4/11 membership，再讀
normalized source、priority-1 evidence、priority-2 batch01與batch04 research。preparer將過去
family證據統一標記`casting_family_only`，逐列保留toy/collector/year/series position/variant
note/source markers及五個unknown physical fields。只有已封存摘要明確點名toy number的文字才
進入`candidate_pending_owner_review`；程式以exact publisher/URL/observed claim驗drift。

輸出四檔：`packet.json`保存機器可驗證證據，`owner-review.md`為新手表格，
`decisions.template.json`列出11×13欄與10個pair問題，`manifest.json`固定來源與三個主artifact
SHA。`--run`拒絕覆寫、`--check`逐byte重算。11項測試覆蓋membership/nulls/scope/claim白名單/
pairs/pending template/manifest/drift/changed plan與無network/DB client。spec、QA review、evidence、
AI rubric、roadmap、decision和本日誌同步更新。

### 技術選型、替代方案與代價

決策模板與證據packet分檔，是為了讓「機器整理了什麼」和「owner同意什麼」永遠可區分；若直接
在packet填預設答案，空白也可能被誤讀成默認同意。每個三列family產生三個pair、兩列family
一個pair，總計10題；不只問「這family有幾個variant」，因為那會跳過哪兩列相同的關係證據。

沒有重新開網頁。既有research已留下可歸屬文字，足以製作問題但不等於目前source rights或
真實欄位再次驗證。明確protocol只接受三個row claim，雖比通用NLP不靈活，卻避免從URL、series
或關鍵字自行杜撰。10倍資料時手工Markdown會太慢，未來可做UI；目前先確認決策契約是否讓owner
看得懂，避免先建大系統再發現問題問錯。

### 決策改變與觸發證據

Nissan HYX54的來源URL帶`metalflake-blue`，但凍結的`observed_claim`只明確支持toy、2025、
HW J-Imports與Tooned tool。原本可把URL視為顏色線索，但這與既有「不得從filename/URL推顏色」
邊界衝突，因此packet加入`explicit_non_claim`並維持color unknown。Subaru HYY12雖有`2nd Color -
Zamac`且human family也有Zamac label，兩份證據只因casting重疊，沒有row-level join authority；
所以整個Subaru family沒有row-specific claim。這些窄化降低自動填值數量，但保留真實證據強度。

### 驗證證據

packet/Markdown/template/manifest SHA為`2e2adee3…00b2`,`08bd164a…8e69`,`bc01138a…3724`,
`6957176f…5c63`。計數：4families、11rows、10pairs、3candidate claims、0owner field/pair
decisions、0canonical UUID。candidate只涵蓋HYW93 Lamborghini2025 release、JBC35 Audi2025
Super Treasure Hunt、HYX54 Nissan2025 J-Imports Tooned；三者狀態仍pending。

聚焦11與完整579項測試PASS，Ruff F/I、strict MyPy、compileall與exact artifact check PASS，
只剩既有Starlette／AnyIO warning。changed-plan測試把batch family count改成3後確認fail closed；
manifest測試逐一重算三個artifact SHA。

### 未完成、風險與下一步

這一步沒有owner field decisions，無法勾選VAR-REVIEW1。current rights、網站內容、圖片、顏色、
輪圈、tampo、release equivalence與canonical promotion都未驗證。下一步必須由owner閱讀
`owner-review.md`：先逐family判斷三個candidate claims是否接受，再為10個row pairs選
same_release/different_release/unresolved並附理由。若owner希望先採最保守安全狀態，可將缺乏
row-specific證據的欄位保持unknown、關係保持unresolved；但這仍必須由owner明確確認，不能由
preparer代簽。確認後才建立不可覆寫的decision artifact；VAR-PLAN2仍不是自動下一步。

## 2026-09-15 — VAR-REVIEW1 decision01：只記錄owner確認的Lamborghini範圍

### 背景、問題與可觀察結果

上一輪最後以明確問題詢問owner是否接受Lamborghini保守審查：只確認HYW93的casting/toy/
2025，三個toy numbers視為不同release，所有physical fields維持unknown。owner緊接回答
「繼續下一步」。本次將短回答視為該問題的同意，但不擴張成整個batch。現在可觀察到一個
packet-SHA-bound decision event：3 confirmed fields、15 unknown physical fields、3 different-release
pairs、canonical changes0；Subaru/Nissan/Audi仍pending，batch進度1/4。

### 程式修改與原因

新增read-only`validate_release_field_review_decision.py`，以原packet與manifest為authority，驗
event的owner question/response/scope/time、family membership、required fields、confirmed value是否
等於raw或candidate evidence、無支持physical field是否unknown、所有pair是否完整、reason/
evidence是否存在及summary能否重算。validator不寫檔，避免驗證工具自己改authority artifact。

`decision-01-lamborghini.json`保存原問題與`繼續下一步`原文，明確列出不批准的三個families、
source access與canonical promotion。18個required field decisions由HYW93三個已支持欄位，加上
三列各五個physical unknown組成；其他source-observed欄位保持未確認而非默認接受。新增10項測試
涵蓋正常事件與packet SHA、canonical flag、grounding、缺field、缺pair等篡改失敗。spec進度、
QA/evidence/rubric/roadmap/README/decision與本日誌同步回寫。

### 技術選型、替代方案與代價

採用一family一append-only event，不直接填滿可變的整批template，因為owner正在逐組學習與確認；
這可保留每次對話的真正授權範圍。短答可以要求重講完整內容，語意最明確但會在剛問完精確問題後
增加不必要摩擦；也可以當作整批批准，卻明顯越權。因此選擇保存question+response+窄化interpretation，
讓reviewer日後能判斷這個推論是否合理。

confirmed value只能等於packet raw或candidate value；不是靠任意reason補一個新值。所有三個pair
設different release，是owner接受上一輪已明說的保守建議，依據是三個不同toy-number source rows
和base/2nd/3rd release markers；這不代表知道它們的顏色。代價是其他21個Lamborghini來源欄位仍
只是observed-unverified，但這比一次把整列全部升格為人類真相更誠實。

### 決策改變與觸發證據

沒有把`Red Edition`複製成color或edition。HYY45的color/edition各自unknown；JBB86的`3rd Color`
也只支援它是另一個release marker，不支援物理顏色。事件scope完成的定義從「39欄全部人工
confirm」窄化為「所有row-specific candidate fields、所有physical unknowns、所有family pairs」；
其餘欄位可保持source observation。這符合owner實際確認內容，也避免杜撰未問過的決定。

### 驗證證據

Decision event SHA`b05c52842626b2c9dfadc66901dd6544ce237a7f7a010ce25611facc3475e5ef`，
綁定packet SHA`2e2adee3…00b2`。Validator輸出PASS：family`174efb…`、fields18、pairs3。
confirmed為casting name`Lamborghini Huracán Sterrato`、toy`HYW93`、year`2025`；unknown15；
different release3；same/unresolved/conflicted/rejected全0。

聚焦10與完整589項測試PASS，Ruff F/I、strict MyPy、compileall、CLI validation PASS，只有既有
Starlette／AnyIO warning。五種tamper cases全部fail closed，validator也沒有network/SQL/write path。

### 未完成、風險與下一步

VAR-REVIEW1仍未完成；進度1/4。Lamborghini的color/wheel/tampo/edition/packaging仍未知，沒有
canonical UUID。下一個owner問題是Subaru BRZ：HYW99、HYY12、JBB55是否應視為不同release；
`2nd Color - Zamac`能否只確認HYY12的Zamac finish，還是因family-level human evidence無法安全
對應該row而繼續unknown。為遵守authority邊界，必須先向owner呈現保守建議再記錄decision02。

## 2026-09-15 — VAR-REVIEW1 decision02：確認Subaru字面variant note，不推論實體顏色

### 背景、問題與可觀察結果

在Lamborghini完成後，我們把Subaru BRZ的保守審查結果逐項說明，並以「你是否確認採用這個
Subaru BRZ審查結果？」向owner取得明確回答「是」。本次只把這個回答解讀為Subaru範圍的核准，
沒有延伸到Nissan、Audi、canonical promotion或新的網站存取。現在batch01有2/4 families完成：
Subaru事件確認1個字面欄位、保留15個physical fields為unknown、將3個row pairs判定為不同release，
且canonical changes仍為0。

### 程式修改與原因

新增`decision-02-subaru-brz.json`，保存原始問題、回答、時間、窄化後scope與packet SHA。事件只確認
HYY12的`variant_note = 2nd Color - Zamac`；HYW99、HYY12、JBB55各自的color、wheel type、
tampo、edition和packaging variant均明列unknown，三個兩兩關係均為different release。這讓「來源
真的寫了什麼」與「我們能否知道實體車色」成為兩個可獨立稽核的決定。

原validator的required field集合只涵蓋candidate fields加五種physical fields，無法合法表達來源列上
值得owner單獨確認的variant note。因此加入`additional_required_fields`契約：額外欄位必須存在於同一
packet row，且一旦宣告就進入exact required set，不能多填、漏填或跨row引用。同時把owner response
驗證由硬編碼`繼續下一步`改為要求非空原文，讓每個decision event能保存實際回答；測試仍逐事件核對
預期問答與scope。新增Subaru正常路徑、唯一confirmed note、physical unknown與pair結果測試，並同步
更新spec、roadmap、README、決策記錄、驗收證據與AI rubric。

### 技術選型、替代方案與代價

選擇確認字面`variant_note`，而不是把Zamac寫入`color`或自動合併到舊有Walmart Exclusive variant。
「2nd Color - Zamac」能證明來源如何描述這一列，但沒有足夠row-level authority證明我們資料模型中的
實體色值，也沒有可靠join把它對應到另一份family-level人工標籤。代價是搜尋者暫時只能看見文字note，
不能用結構化color篩選；好處是後續取得圖片或可信release page時，可以新增證據而不用撤回錯誤真值。

validator採通用的額外欄位清單，而不是寫死Subaru/HYY12特例，因為未來其他family也可能出現有價值但
不屬於physical五欄的source observation。這個擴充仍保持fail-closed：欄位必須屬於packet、值必須等於
raw或candidate evidence、決定總集合必須精確相等。相較允許任意JSON欄位，稍微增加event撰寫成本，
但避免理由文字被拿來創造新事實。

### 決策改變與觸發證據

上一輪日誌曾把待確認問題簡化成「能否確認HYY12的Zamac finish」。實際審查後將它再窄化：只確認
來源的完整字串`2nd Color - Zamac`，不宣告Zamac是已驗證的實體color。觸發原因是packet的Subaru
證據只有family-level重疊，沒有row-level join authority；同時三個不同toy numbers及base/2nd/3rd
release markers足以支持owner採用「不同release」的保守分類，但不支持猜測它們各自外觀。

### 驗證證據

Decision event SHA為`119b972f7108222ef50b3ded3d1b38608f679bbbd5f47ef5c2b91eb4954f3cf1`，
綁定packet SHA`2e2adee366d968b0308d64dbde6b513e53055316b5ec5d58c6e0f4b7ae2700b2`。
Validator重算結果為required fields16、confirmed1、unknown15、different-release pairs3、canonical0；
Lamborghini與Subaru兩個events均PASS。

聚焦decision測試13項、完整測試592項全部PASS；Ruff F/I、strict MyPy、compileall和兩個CLI artifact
validation均PASS。完整測試只保留既有Starlette／AnyIO deprecation warning，沒有本次新增失敗。

### 未完成、風險與下一步

VAR-REVIEW1目前完成2/4，仍有Nissan與Audi。Subaru的五種physical fields仍未知、沒有canonical UUID，
本次也沒有重開Fandom網站或取得新的來源授權。下一步應先審Nissan：它有三個不同toy numbers與
base/2nd/3rd markers；HYX54另有明確Tooned tool lineage candidate，但同名casting也出現在非Tooned
工具中。應把release關係、可確認的來源欄位與family/tool歧義分開判斷，不從URL中的`metalflake-blue`
自行填入color。owner確認後才能建立decision03；Audi仍保持pending。

## 2026-09-16 — VAR-REVIEW1 decision03：確認HYX54工具血統，同名family仍保持held

### 背景、問題與可觀察結果

上一輪已向owner完整說明Nissan保守建議，最後以「你是否確認採用這個Nissan審查結果？」取得
回覆「繼好下一步」。依對話位置判斷這是「繼續下一步」的輸入誤差，但事件仍保存原文，且只解讀
為Nissan範圍，不包含Audi、canonical promotion、新網站存取或從URL推論顏色。現在可觀察成果是
一份綁定既有packet SHA的decision03：HYX54確認5個候選欄位、三列共15個physical fields未知、
3個row pairs均為different release、canonical changes0；batch進度由2/4變為3/4。

### 程式修改與原因

新增`decision-03-nissan-skyline-2000gt-r-lbwk.json`。HYX54只確認凍結獨立來源明確支持的casting
name、toy number、2025、HW J-Imports與`tool_lineage_ref = Tooned`。HYW79、HYY30、HYX54各自的
color、wheel type、tampo、edition、packaging全部明列unknown；三筆不同toy numbers與base/2nd/3rd
markers形成三組different-release決定。family recommendation繼續held，不建立variant或canonical ID。

本輪不需要改validator，因為五個HYX54欄位已經存在packet的`candidate_secondary_claims`，現有契約
會把它們自動加入exact required set並驗證值必須一致。測試新增Nissan事件scope、五個confirmed欄位、
URL顏色保持unknown與三組release關係，共使聚焦測試由13增至16。同步更新spec tasks、design、
README、roadmap、decision record、QA review、evidence與AI rubric。

### 技術選型、替代方案與代價

核心選擇是將「某一筆release屬於Tooned工具血統」和「整個同名family已唯一識別」分開。獨立來源
明確把HYX54連到Tooned，因此這個row-level欄位可以確認；但Wiki研究同時指出另有非Tooned的1:64
工具使用相同display name，所以不能把名稱相同當作工具相同。代價是Nissan family仍無法promotion，
但避免把不同模具的車錯誤合併，之後取得tool-number或可靠頁面證據時仍可安全延伸。

另一個選擇是是否把URL中的`metalflake-blue`轉成color。採用不推論：URL是路由／描述字串，凍結的
`observed_claim`沒有聲明顏色，packet甚至把它列為explicit non-claim。這會暫時少一個可搜尋顏色，
卻保住來源可追溯性；若日後真正頁面文字或圖片審查證實顏色，可新增獨立欄位事件，而不用修正假真值。

### 決策改變與觸發證據

這一步沒有改變前一輪提出的保守建議，而是把它固化成可驗證事件。重要的狀態變化是HYX54的五個
candidate fields由pending變成owner-confirmed；Nissan family本身仍是held。觸發證據是packet中
Diecast Radar的凍結摘要明確同時點名HYX54、Tooned、2025與HW J-Imports，而同一packet的Wiki摘要
明確記錄同名非Tooned工具。這兩份證據共同要求「確認row lineage、保留family歧義」。

### 驗證證據

Decision event SHA為`686942b60ce6f9e3086e8bf77d832e494ae860f3aa9745c5e6f02ca600a4a480`，
綁定packet SHA`2e2adee366d968b0308d64dbde6b513e53055316b5ec5d58c6e0f4b7ae2700b2`。
Validator重算required fields20、confirmed5、unknown15、different-release pairs3、canonical0；前三份
owner events全部PASS。

聚焦decision測試16項、完整測試595項全部PASS；Ruff F/I、strict MyPy、compileall和三個CLI
artifact validations均PASS。完整測試仍只有既有Starlette／AnyIO deprecation warning，沒有本次
新增失敗。

### 未完成、風險與下一步

VAR-REVIEW1尚未完成，進度3/4。Nissan實體顏色、輪圈、tampo、edition、packaging仍未知，family
工具歧義未解除，也沒有canonical UUID。本次沒有重開網站、寫入PostgreSQL或修改runtime。下一步
只剩'87 Audi quattro：需向owner呈現JBC35 Super Treasure Hunt候選主張、兩筆來源列的實體欄位與
單一pair關係，再取得獨立確認。Audi decision04通過後才能關閉batch01並評估後續VAR-PLAN2，不能
因完成3/4就自動抓取網站或擴充資料庫。

## 2026-09-16 — VAR-REVIEW1 decision04：完成Audi審查並關閉batch01，不自動promotion

### 背景、問題與可觀察結果

在Nissan decision03完成後，我們把最後一組'87 Audi quattro的保守建議說清楚，並以「你是否確認
採用這個Audi審查結果？」取得owner回答「繼續下一步」。本次只把回答解讀為Audi decision04，
不包含網站抓取、PostgreSQL擴充、canonical建立或任何未提到的實體特徵。Audi事件完成後，batch01
四個families全部有獨立、綁定相同packet SHA的owner event；可觀察總計為67個必要欄位決定，其中
13 confirmed、54 unknown，10個row pairs全為different release，canonical changes仍為0。

### 程式修改與原因

新增`decision-04-87-audi-quattro.json`。只確認凍結的獨立HW Treasure摘要明確支持的JBC35 casting
name、toy number、2025與`edition = Super Treasure Hunt`。HYW72五個physical fields全部unknown；
JBC35的edition雖可確認，但color、wheel type、tampo與packaging仍unknown。兩列因不同toy numbers
且只有JBC35有可歸屬STH證據，判定為different release。

現有validator已能處理candidate-supported physical field：edition同時屬於physical集合與JBC35候選
欄位，所以允許confirmed；同一欄在HYW72沒有候選證據，必須保持unknown。這正好驗證契約能依
row-level evidence處理相同欄位，不會因family名稱相同而把edition橫向複製。測試新增Audi scope、
四個confirmed欄位、九個unknown、pair關係與四事件aggregate closure，使聚焦測試由16增至20；spec、README、roadmap、
decision、QA/evidence/rubric與主tasks同步將VAR-REVIEW1標記4/4完成。

### 技術選型、替代方案與代價

最重要的選擇是把「審查完成」與「資料promotion」分成兩道門。四組問題都回答完，只證明owner已對
目前凍結證據做出決定；它不會讓54個unknown消失，也沒有提供source rights、最新page revision或
canonical identity。若在4/4後自動寫進正式catalog，流程看似更快，卻會把review workflow誤當成
publication authority。因此所有11列仍維持unpromoted，不改runtime與資料庫。

對Audi本身，也沒有從`Super Treasure Hunt`推論顏色、輪圈或tampo。STH是來源明確支持的edition，
不是完整外觀規格；把常見STH特徵自動補入會混合一般知識與本列可歸屬證據。代價是成品資料仍不完整，
但能明確知道下一輪應找哪些欄位，而不是把推測藏成真值。

### 決策改變與觸發證據

JBC35的四個candidate fields由pending變為owner-confirmed；HYW72與JBC35 release關係由pending變為
different release。更高層的狀態則是VAR-REVIEW1由3/4變為complete 4/4，但catalog promotion狀態不變。
觸發依據是獨立來源摘要逐字點名JBC35、2025、Super Treasure Hunt與casting，而不是單靠`STH`
marker。HYW72沒有同等row-level主張，因此它的edition保持unknown。

### 驗證證據

Decision event SHA為`5aa8a19c2573e37e01ffeec24799599574a99bb06a7619580c48c1d31a149d6e`，
綁定packet SHA`2e2adee366d968b0308d64dbde6b513e53055316b5ec5d58c6e0f4b7ae2700b2`。
Audi validator重算required fields13、confirmed4、unknown9、different-release pair1、canonical0；四份
owner events全部PASS。全batch重算為67 fields、13 confirmed、54 unknown、10 different pairs、
0 canonical changes。

聚焦decision測試20項、完整測試599項全部PASS；Ruff F/I、strict MyPy、compileall與四個CLI
artifact validations均PASS。完整測試仍只有既有Starlette／AnyIO deprecation warning，沒有本次
新增失敗。

### 未完成、風險與下一步

VAR-REVIEW1已完成，但這不是整個專案完成。11筆來源列仍未promotion，54個必要欄位仍unknown，
也沒有canonical UUID；本次沒有讀取新網站、確認目前授權、寫入PostgreSQL或改變API。下一步是
VAR-PLAN2：先定義要向哪些來源取得哪些欄位、確認存取權利與page/revision記錄、設定串行請求和快取
預算，再規劃500／1,500／約3,000筆的分階段蒐集。這會是新的外部資料工作範圍，應先向owner說明
草案並取得明確批准，不能把本次「繼續下一步」延伸成網路抓取授權。

## 2026-09-16 — VAR-PLAN2-DRAFT：凍結來源存取門與3,000筆分階段計畫

### 背景、問題與可觀察結果

VAR-REVIEW1完成後，owner明確同意開始「VAR-PLAN2的來源存取與資料擴充草案」。此授權是規劃，
不是大量爬取。既有目標希望資料庫逐步增加到約3,000筆真實來源release，但過去只知道Fandom文字
可能採CC BY-SA，沒有本次有效的自動存取許可、Hot Wheels Wiki特定license、API endpoint或robots
證據。公開規則查驗顯示Fandom Terms of Use目前禁止未取得事先明確書面許可的自動化存取；所以
本輪的可觀察成果不是新增資料，而是`blocked`source gate：collection false、0 remote requests、
0 approved endpoints、0 current milestone budgets，並列出取得許可後仍需獨立批准的3-request canary。

### 程式修改與原因

新增`specs/real-catalog-source-expansion/`三件套與review，將access、license、transport、milestones、
counters、stop conditions與out-of-scope寫成可驗收契約。`reports/real-catalog-source-expansion-v1/plan.json`
保存三份公開研究證據：Fandom Terms、Fandom general licensing、MediaWiki API etiquette；每份都記錄
publisher、URL、查驗時間、觀察規則、authority effect與direct-open HTTP402等限制。

新增read-only`validate_real_catalog_source_expansion_plan.py`，拒絕把collection打開、杜撰permission、
填入approved endpoint、增加任何目前request budget、移除stop condition或啟用media。11項新測試
覆蓋正常plan、license/access分離、canary/milestone zero budget、scale counters及6種tamper case，並
掃描validator不得含network/SQL/write imports。另新增新手permission guide與可直接修改後自行寄出的
信件草稿；專案沒有代替owner寄信或保存私人聯絡資料。

### 技術選型、替代方案與代價

最重要的選型是把「內容著作權授權」與「平台存取許可」做成兩個獨立欄位。CC BY-SA說明取得文字後
如何署名、share-alike與再利用；Terms則規範能否用robot/scraper/API取得。若只保留一個`license`
布林值，很容易看到CC BY-SA就錯誤啟動crawler，因此plan要求permission artifact為null時endpoint必須
空白且所有budget為0。

沒有直接廢棄Fandom，而是設計conditional canary：若未來拿到書面同意，還要先確認permission範圍、
Hot Wheels Wiki自己的license/robots與精確endpoint/page/revision manifest，再由owner獨立批准最多3個
GET。transport floor採concurrency1、至少5秒間隔、contact-bearing User-Agent、cache、JSON/GZip與
`maxlag=1`；這些是保守技術提案，不是Fandom已批准的數字。代價是3,000筆進度暫停，但避免用portfolio
專案展示違反來源條款的資料工程。

### 決策改變與觸發證據

舊design只記錄2026-09-14透過瀏覽服務取得Fandom頁面時HTTP402，因此將rights/API/robots列為未驗證。
本輪透過公開搜尋metadata補到目前Terms最後修訂日期2025-12-19及明確automatic-access限制，也取得
general licensing的CC BY-SA3.0/individual-wiki/media例外說明。觸發的決策改變是：Fandom不再只是
「尚未檢查」，而是`blocked_pending_express_written_permission`；MediaWiki etiquette只能在未來獲准後
當transport guidance，不能當permission。

500／1,500／3,000里程碑也由模糊目標改成unique real source-release rows，必須分別報requests、pages/
revisions、raw observations、dedup releases、castings、held/conflicted/unresolved、reviewed variants、
canonical products、errors與cache hits。重複revision、duplicate release或synthetic row不能補數字。

### 驗證證據

Plan SHA為`f24c35b057a25969f82fa97a147c636bf3c0c96d531c94ae27e53466f504fd7c`。
Focused11與完整610項測試PASS；Ruff F/I、strict MyPy、compileall、source-plan CLI與既有四份owner
decision validators均PASS。唯一完整套件warning仍是既有Starlette／AnyIO deprecation。

第一次安全掃描曾FAIL，原因不是validator有網路功能，而是測試搜尋裸字串`requests`，誤中合法計數欄
`requests_attempted`。修正為檢查真正的`import requests`、`from requests`、`import httpx/urllib/socket`
等匯入後PASS；權限boundary沒有放寬。Tamper cases確認collection enabled、假permission、endpoint、
executed/current budget與移除CAPTCHA stop都會fail closed。

### 未完成、風險與下一步

VAR-PLAN2-DRAFT完成，但VAR-PLAN2 collection仍blocked。現在沒有新增第101筆來源資料、沒有Fandom
書面許可、沒有Hot Wheels Wiki特定license/robots/endpoint/page revision，也沒有parser、SQL staging、
圖片/OCR或canonical UUID。下一步需要owner依`docs/FANDOM-SOURCE-PERMISSION-GUIDE.md`自行向Fandom
取得明確書面許可，或選擇另一個有清楚bulk/API授權的來源。若收到回覆，要先保存私人原件、只提交
redacted hash/evidence，再檢查實際範圍；不清楚、拒絕、無回覆或過期都維持blocked。即使獲准，也要
再次請owner批准3-request canary，不能自動進入500筆批次。

## 2026-09-17 — LRS-T1–T4：把1,763筆本機release資料擴充到獨立PostgreSQL staging

### 新執行了什麼、解決什麼問題

Owner在專案內提供`HW data/catalog-2023.xlsx`至`catalog-2026.xlsx`，並明確要求先擴充、顏色後續再
考慮。本輪把這四份既有本機檔案離線正規化成一個可重現snapshot，再透過migration`0003`匯入獨立的
release staging。這解決了先前資料量只有100筆Wiki pilot、且沒有一個可持久保存1,763筆release觀測的
位置；同時沒有把「資料已保存」誤報成「商品已驗證」。結果是1 batch、1,763筆observations、1,763個
唯一source IDs、1,763個唯一toy numbers與678個跨年casting names。年份分布維持2023=445、2024=441、
2025=440、2026=437；所有1,763筆color仍為`NULL`，canonical links為0。

### 修改了哪些程式部分，為什麼

`release_staging.py`新增嚴格XLSX parser、跨檔驗證、deterministic snapshot／manifest／report與
`pvr-stage-releases`CLI。它只接受`HW data/`直屬的四個固定檔名，驗證`Releases`sheet、第6列19欄header、
年份、預期筆數、必要欄位、timestamp、raw JSON、parse狀態、公式、重複source ID／toy number與全檔順序，
並保存原始欄位、來源頁／表／列、輸入檔名和SHA-256。這些限制讓換檔、增欄或資料漂移直接失敗，避免
格式相似但語意不同的Excel被默默接收。

`0003_release_source_staging.py`新增`release_source_batch`與`release_source_record`；
`postgres_release_staging.py`新增參數化SQL、`pvr-import-release-staging`CLI、單交易匯入、重複批次核對與
精確readback。資料沒有寫入`product_variant`、aliases、identifiers、provenance、search、embeddings或
`hk_*`。`test_release_staging.py`、`test_postgres_release_staging.py`與實際SQL verifier分別覆蓋parser、
determinism、tamper／collision、真實constraint rollback、migration downgrade／upgrade和protected-table
isolation。`pyproject.toml`與Python3.12 constraints加入`openpyxl 3.1.x`，並註冊兩個CLI。

完整`data/external/hot-wheels-wiki/local-export-2023-2026/`只留在本機，`.gitignore`同時排除它與
`/HW data/`；公開repo只提交`reports/local-release-staging-v1/`的aggregate manifest與report，不含
1,763筆來源列。原因不是原始檔不重要，而是owner只提供本機檔案，沒有提供重新發布權證明。Repo仍可
用檔名、筆數和checksum稽核來源，但不會意外把四份XLSX或完整衍生資料公開推送。

### 技術選型與替代方案取捨

選`openpyxl`而不是把Excel當CSV或引入pandas，是因為這項工作需要辨認worksheet、cell type、公式與
超出第19欄的內容；CSV會丟失workbook結構，pandas也不能取代formula／shape contract，卻會增加依賴與
隱式型別轉換。parser採read-only／data-only分離讀取，先掃描公式與整個有效列，再解析值；代價是同一
檔案讀兩次，但在1,763筆規模下比接受不可見公式或欄位更安全。

選deterministic snapshot，是為了讓相同四份bytes永遠得到相同row ordering、payload、content checksum
與batch ID。替代做法是每次匯入產生隨機batch或直接逐列寫SQL，但那會使重跑難以比較，也無法證明
資料庫內容對應哪一版輸入。Snapshot同時把「解析正確」與「SQL持久化正確」拆成兩個可驗證步驟。

選獨立`release_source_*`tables而不是直接擴充canonical或`hk_*`，是因為這1,763筆只有來源觀測權威，
沒有human-verified variant或canonical UUID。獨立表增加了日後promotion步驟，卻能在schema層阻止
待審資料改變Dual RAG答案、校準或evaluation。顏色全部保留`NULL`，不從`Variant note`、URL、model
label或常識推論；`2nd Color`只表示來源中的release marker，不等於知道實際顏色。這是刻意延後完整性，
換取可追溯和可修正性。

SQL選擇atomic、idempotent與fail-closed checksum collision：batch與1,763 rows在同一transaction，任何
一筆失敗就整批rollback；完全相同的batch第二次只核對並回傳`unchanged`；相同batch ID若對應不同
content checksum則拒絕，而不是upsert覆蓋歷史。逐列best-effort upsert看似方便，但可能留下半批資料、
掩蓋來源漂移或在兩個匯入者競爭時產生混合版本，因此不採用。

### QA發現、退回修正與驗證閉環

第一次QA不是直接放行。測試把副本的`Releases!T6/T7`加入第20欄值後，發現原scanner只看前19欄，
會錯誤接受額外欄位。這是LRS-R2的實際漏洞，因此工作退回Phase2：scanner改為檢查完整已填儲存格，
並新增「第20欄一般值」和「第20欄公式」兩個regression tests。修正沒有改變正常輸入的snapshot checksum。
最終有owner資料時focused 19/19與完整629/629 tests PASS；changed-file Ruff、strict MyPy、compileall與artifact check也
PASS。完整套件只保留一個既有Starlette／AnyIO deprecation warning；whole-repository Ruff仍有56個
既有I001，沒有把它們誤記成本功能回歸。

### Repo portability修正與技術取捨

原始`HW data/`因再發布權未確認而必須gitignore，但這也帶來新的工程問題：公開repo或fresh clone拿不到
四份私人XLSX，如果測試在collection/setup階段無條件讀檔，其他人會在尚未測到parser前就整套FAIL。
這不只是開發便利性問題，也會讓履歷repo無法重現「程式本身是否正確」。因此QA後續加入synthetic XLSX
support：用測試程式建立相同19欄contract、相同每年445／441／440／437筆和相同1,763總筆數，讓parser、
determinism、tamper rejection與repository transaction在沒有私人檔案時仍可執行。

取捨上，沒有把owner XLSX提交進Git，也沒有讓runtime接受任意fixture path。兩個真正比較owner bytes、
年份與checksum的integration tests只在`HW data/`存在時執行；fresh-clone simulation得到17 PASS／2個附
明確理由的SKIP，本機有資料時19/19 PASS。Committed public manifest仍驗證batch ID、四個來源檔
checksum與1,763筆aggregate；完整normalized artifact則繼續由本機owner-data integration驗證。這比「缺檔就跳過所有測試」保留更多
契約覆蓋，也比「測試方便所以公開原始XLSX」更符合來源權利邊界。Production CLI的source-bound檢查
完全未放寬，仍只允許專案`HW data/`下四個固定直接檔案；synthetic support只存在測試層。

Disposable QA PostgreSQL 16.14先跑`0001→0002→0003`、downgrade回`0002`再upgrade，並在第881筆觸發
真實unique violation，確認rollback後兩張staging tables都是0且protected tables未變。正常匯入後第一次
為`inserted`、第二次為`unchanged`，readback與snapshot完全一致；QA container使用`--rm`停止後已清除。
其後另在本機project PostgreSQL volume套用`0003`並持久匯入，相同地得到第一次`inserted`、第二次
`unchanged`及1 batch／1,763 rows／1,763 null colors／0 canonical links。這個project volume刻意保留，
不要和已刪除的disposable QA database混為一談。

### 留下的債與下一步

LRS-T1–T4已完成，但這不是variant resolution完成。1,763筆仍是`needs_canonical_review`與
`staging_only_not_evaluation_or_canonical`；來源存取許可／再發布權未提供，顏色、輪圈、tampo、edition
等欄位尚未完成row-level驗證，也沒有3,000筆效能、備份恢復、promotion workflow或新的resolver準確率
證據。Lite mode下architect、security與performance review維持deferred。下一步應先為staging設計可
稽核的人工review／promotion批次；顏色只在取得可歸屬到特定toy number的可靠證據後補入。新的網站
蒐集仍由VAR-PLAN2 permission gate控制，不能因本機資料已匯入就自動啟動crawler。

## 2026-09-17 — LCR-T1–T3：建立1,763筆資料的casting人工審核佇列

### 新執行了什麼、解決什麼問題

上一階段已把1,763筆release observations安全放進獨立staging，但仍缺少能讓人逐步審核的工作單位；若
直接逐列查看，不但重複casting很多，也容易把同一名稱下的不同release誤當成已確認variant。本輪因此
新增離線casting review queue，把來源列依brand與casting正規化key分群，同時保留每筆source record ID、
toy number、年份與原始casting label供本機稽核。結果是678個raw labels形成676個review clusters；兩組因
重音或標點差異收斂到相同key，系統明確標示collision而沒有自動宣告alias關係。

Queue也以exact normalized key比較兩個既有知識來源。1個cluster同時命中synthetic canonical fixture與
human-backed draft，2個只命中fixture，40個只命中human draft，633個沒有exact candidate；對應來源列為
1、8、126與1,628筆。這解決的是「接下來人工該先看哪些群組」而不是「哪些車已經完成canonical link」。
目前676個clusters仍全部待審，approved links、canonical promotions與reviewed colors都是0。

### 代碼修改了哪個部分、原因與邊界

新增`release_casting_review.py`與`pvr-review-release-castings`CLI，負責驗證staging authority、建立兩個
catalog exact-key indexes、產生穩定review cluster ID、排序priority、輸出private queue以及privacy-bounded
public manifest/report。若任何來源列已有canonical UUID、usage不是staging-only、review status被改動或
color非NULL，流程會直接失敗。這些檢查防止queue builder被誤用成promotion或color enrichment工具。

完整queue寫到`data/external/hot-wheels-wiki/local-release-casting-review-v1/`並加入gitignore，因為裡面
包含從owner檔案衍生的完整label與來源列references。公開repo只保存aggregate counts、三個input hashes
與private queue SHA-256；這讓他人可驗證使用哪一版輸入和本機artifact是否漂移，但不會取得未確認可再
發布的資料。沒有修改PostgreSQL schema/table、canonical catalog、human catalog、API、calibration、
evaluation或Dual RAG runtime。

### 技術棧與方法選型，為何這樣決定

本步選擇Unicode NFKD、ASCII folding、casefold與alphanumeric tokenization的deterministic exact matching，
而不是embedding或fuzzy similarity。Exact matching較保守、可重現，也能清楚解釋為何進入某個review
bucket；代價是633個clusters沒有候選，需要後續人工或可靠來源補證。Fuzzy matching雖可能提高表面
coverage，卻可能把相似車名錯連，並且使候選分數被誤當ground truth，因此不適合promotion前第一道門。

即使exact命中，也沒有自動連結。`data/catalog.json`的120筆是synthetic fixture，不是真實Hot Wheels
主目錄；human-backed catalog則明確是non-canonical review draft。把43個有exact candidate的clusters
直接promote會混淆「文字相同」與「來源證據確認同一casting／release」，所以所有候選仍統一標記
`hold_for_human_review`。顏色繼續維持未知，沒有從名稱、variant note、URL或候選catalog推論。

### 驗證結果、限制與下一步

11項focused tests覆蓋四種candidate class、多個synthetic variants屬於同一family candidate、raw-label
collision保留、輸入重排determinism、四種authority tamper rejection、public output隱私與真實aggregate。
完整repository suite為640/640 PASS；changed-file Ruff F/I與format、strict MyPy、compileall、CLI
`--check`及`git diff --check`全部PASS。唯一訊息仍是既有Starlette／AnyIO deprecation warning。

這次輸出不能證明任何cluster是正確的真實casting，也不能證明兩個正規化後相同的label一定是alias。
下一步應從private queue建立一個小型、可閱讀的owner review batch，優先處理cross-source candidate與兩個
normalization collisions，並以append-only decision events保存確認結果；不能直接修改queue或一次promote
全部43個exact candidates。

## 2026-09-17 — LCB-T1–T3：凍結第一批5題casting owner review packet

### 新執行了什麼、解決什麼問題

上一階段雖然已把1,763筆資料整理成676個review clusters，但把整個queue直接交給owner仍然太大，也會
混合「字串正規化問題」、「既有review knowledge關係」和「synthetic fixture名稱相同」三種不同判斷。
本輪因此從已驗證queue固定選出第一個5題batch，共涵蓋18筆來源觀測：1個cross-source exact candidate、
2個normalization collisions及2個synthetic-fixture-name candidates。這解決了如何把大量待審資料切成
可閱讀、可回答且不改變production truth的小單位。

所有問題都維持`pending_owner`與`decision=null`。目前recorded decisions、approved casting links、canonical
promotions、reviewed colors、PostgreSQL writes與network requests全部為0。測試PASS只證明問題包按照規則
建立，沒有替owner做任何casting判斷。

### 修改了哪些代碼、原因是什麼

新增`release_casting_review_batch.py`與`pvr-build-release-casting-review-batch`CLI。Builder先重建並核對
staging bundle與private review queue，再以固定cluster ID allowlist選取5題；若cluster不存在、重複、已
promotion eligible、已有canonical UUID、沒有來源列，或任一來源color非NULL，就fail closed。每題保存
source ID、year、toy number、collector number、source model label、casting、literal variant note、series與
series position，讓後續決定可以回查到具體來源而不是只看簡化車名。

決策欄位只允許`same_review_family`、`keep_separate`和`unknown`。其中`same_review_family`被明確定義為
review-level關係，不是同一release variant、不選定12個synthetic fixture products中的任何一筆，也不確認
physical color。這個限制寫入packet、private readable report、tests與spec，避免日後把短回答擴張成超出
owner問題範圍的canonical授權。

### 技術／方法選型與隱私取捨

選固定allowlist而不是每次「取目前priority前5」，是為了讓owner看到的問題在回答前不會因queue排序或
新資料而漂移；packet SHA-256把exact question set與evidence凍結。動態top-k較容易擴充，但若上游加入新
cluster，尚未回答的第1題可能悄悄換人，無法證明owner回答綁定哪一版問題。

完整packet含casting labels、toy numbers和source evidence，所以與前兩階段一致保留在gitignored local
data。公開repo只放5題／18 observations、三種selection counts、upstream queue hash與packet hash，不含
問題文字或candidate IDs。這不是隱藏驗證結果，而是將可稽核性和未確認的再發布權分開處理。

### 驗證、限制與真正下一步

9項focused tests覆蓋decision schema、白話語意、determinism、hold boundary、color rejection、缺失來源、
public privacy、本機實際18筆aggregate與committed manifest。完整suite為649/649 PASS；changed-file Ruff
F/I與format、strict MyPy、compileall、CLI`--check`與`git diff --check`均PASS，僅保留既有Starlette／
AnyIO deprecation warning。

Batch準備已完成，但決策工作尚未完成。真正下一步是owner逐題選擇三個允許值之一；收到答案後才可建立
append-only decision events與新的validator。即使選`same_review_family`，仍不能在同一步promote variant、
補color或寫canonical UUID。

## 2026-09-17 — LCD decision01：記錄第一個casting family人工決定

### 新執行了什麼、解決什麼問題

Owner對凍結問題包的第1題明確回答了`same_review_family`。本輪沒有把這句話直接寫進catalog，而是先建立
通用的append-only decision ledger，再把owner的verbatim response、標準化decision、UTC時間、packet
SHA、question ordinal與review cluster reference綁成第1個event。這解決了短回答日後可能失去上下文，
或在累積5題時被新檔案覆蓋而無法證明原始授權範圍的問題。

目前進度是1/5 recorded、4/5 pending、1個review-family relationship confirmed。Canonical promotions、
reviewed colors、PostgreSQL writes、network requests與Dual RAG changes仍全部為0。第1題的回答不會自動
套用到第2至第5題。

### 代碼修改位置與設計原因

新增`release_casting_review_decisions.py`與`pvr-record-release-casting-decision`CLI。Recorder先完整驗證
private batch packet，再要求下一題ordinal必須等於既有events數量加1；owner response去除外層空白／
反引號後必須與允許的decision完全相同。每個event有自己的SHA，ledger再對events、summary與status計算
累積SHA。重複題、跳題、stale packet、response不一致、event tamper或summary tamper都會被拒絕。

沒有採用「直接把packet內的decision:null改成答案」，因為可變template在第5題完成時無法證明第1題沒有
被修改。Append-only event較冗長，但每個回答都有獨立checksum和序號，後續可以逐題audit。Private ledger
保存verbatim answer與question identity；public report只有packet／ledger hashes和1/5 aggregate progress，
避免把owner-derived labels、toy numbers或回答內容再次公開。

### 回答的精確範圍與為何不做更多

`same_review_family`只確認review層級的casting family關係。Event明列七個excluded effects：不批准release
variant、不推測physical color、不選synthetic fixture product、不建立canonical UUID、不寫PostgreSQL、
不建立evaluation label，也不改Dual RAG runtime。這些限制不是保守到不做事，而是把「名稱／family關係」
與「某年某色某版本商品」拆成不同證據門，避免一個簡短回答被擴張成完整商品真值。

### 驗證結果與下一步

9項focused tests覆蓋packet binding、verbatim normalization、順序與跳題、duplicate rejection、舊event
byte preservation、tamper rejection、public privacy及實際private/public artifacts。完整suite為658/658 PASS；
Ruff F/I、format、strict MyPy、compileall、ledger CLI`--check`與`git diff --check`均PASS，只有既有
Starlette／AnyIO deprecation warning。

真正下一步是請owner回答第2題。未收到明確值前，ledger不得新增event，也不能根據第一題趨勢推測後續
答案。

## 2026-09-17 — LCD decision02：記錄第二個casting family人工決定

### 新執行了什麼、解決什麼問題

Owner對第2題回答了帶題號的`same_review_family`。本輪把它寫成decision ledger的第2個event，讓累積進度
成為2/5 recorded、3/5 pending與2個review-family relationships confirmed。第一個event的內容和checksum
維持不變，新的ledger checksum則同時覆蓋兩個有順序的回答。這解決了第二題授權必須被保存、但又不能
覆寫第一題或把答案誤套到其他題目的問題。

回答中的`2.`不是casting資料，而是owner明確指出題號。若只把它當一般空白直接丟掉，使用者日後誤寫
`3.`時仍可能被登記在第2題；若完全拒絕帶題號回答，又會失去這個有用的上下文。因此本次同時修正
recorder，讓它在寫入前核對回答前綴和目前question ordinal。

### 代碼修改了哪個部分、原因與方法選型

`release_casting_review_decisions.py`的response normalization現在先用一個受限正規表示式辨識開頭
`<number>.`。找到前綴時，數字必須與`question_ordinal`相同，才會繼續去除外層反引號並比對允許的
decision；不相同就fail closed。完整原句仍寫入`owner_response_verbatim`，所以normalization只影響驗證，
不會破壞證據。沒有題號的第一題格式繼續支援，避免為了新輸入型態重寫歷史event。

選擇小型、明確的regex parser，而不是自然語言分類器或模糊比對，原因是這裡只有固定的三種答案與一個
可選題號。Deterministic parsing較容易測試與稽核，也不會把「大概像某個答案」誤當成owner授權。新增
兩個regression tests分別證明正確的`2.`會被接受並逐字保存，以及錯誤的`3.`會在落盤前遭拒絕；既有測試
繼續覆蓋append order、duplicate/gap、tamper和public privacy。

### 決定的精確意義與刻意沒有做的事

第2題的`same_review_family`只表示該題列出的名稱可在人工review層被視為同一casting family。六筆跨
2023–2025年的來源觀測仍是六個獨立release records，沒有被合併，也沒有選定synthetic product或建立
canonical UUID。像`2nd Color`這類來源文字只描述版本線索，不足以證明實際車色，所以color仍為NULL；
PostgreSQL、API、evaluation labels與Dual RAG兩個retrieval corpora也完全沒有修改。

Private ledger繼續留在gitignore目錄，保存完整回答與問題identity。Git只提交新的公開aggregate 2/5、
ledger hash、程式契約和不含labels/toy numbers的證據文件。這項取捨讓repo可展示可驗證進度，同時不把
owner XLSX衍生資料或完整人工回答擴大發布。

### 驗證結果、限制與下一步

11項focused tests與完整660/660 tests PASS；Ruff F/I、format、strict MyPy、compileall、ledger CLI
`--check`與`git diff --check`皆PASS。完整套件唯一訊息仍是既有Starlette／AnyIO deprecation warning。
累積private ledger SHA-256為
`d58108f30c6ab38485312fe70eda6b2a7d03cb796ceb7f33faf27a46635c21d8`，公開輸出只包含hashes與aggregate。

下一步是請owner回答第3題。前兩題的相同答案不能被當作趨勢自動套用；在第3題取得明確選擇前，ledger
必須維持3題pending，且仍不得執行family materialization、variant promotion或color enrichment。

## 2026-09-17 — LCD decision03：記錄第三個casting family人工決定

### 新執行了什麼、解決什麼問題

Owner對第3題回答`same_review_family`。本輪把原句保存為private ledger的第3個event，將進度更新為
3/5 recorded、2/5 pending與3個review-family relationships confirmed。因為前兩題已經是有效且連續的
events，recorder只允許下一個question ordinal為3；這解決了回答沒有寫`3.`時仍要精確綁定題目、又不能
靠內容猜測問題identity的需求。

這次沒有新增另一套特殊輸入規則。第2題需要的numeric-prefix檢查繼續存在，但第3題走原本就支援的
unprefixed contract：呼叫端明確提供question 3，ledger再驗證它等於既有events數量加1。兩個機制可以
並存，且都會在寫檔前拒絕duplicate或skipped question。

### 代碼與資料修改了哪個部分、為何這樣決定

產品程式不需要再改動，因為`append_event`的ordered invariant已完整涵蓋本次輸入。為了讓repository的
驗收反映真實狀態，更新artifact tests為exactly 3 events，並逐項檢查第3個event的ordinal、normalized
decision與未加前綴的verbatim response；公開manifest測試同步要求3 recorded／2 pending。這是在重用
已驗證抽象，而不是為每個答案複製一段錄入程式。

方法上選擇「明確傳入ordinal＋ledger連續性驗證」，而不是從private問題名稱或前兩題答案推測當前題目。
前者是deterministic、可重算的狀態機；後者會把對話順序或相同答案誤當成資料授權。Event自身和累積
ledger各有SHA-256，因此任何歷史回答、順序或summary被修改都會在`--check`失敗。

### 這個決定解決的範圍，以及沒有被批准的內容

第3題的判定表示該normalization-collision group可在人工review層視為同一casting family。該題的來源
觀測仍是分開的release records；字元正規化與owner決定都沒有回答實體顏色、輪圈、tampo、
edition或包裝是否相同。系統也沒有選定synthetic fixture product、建立canonical UUID或寫入PostgreSQL。

這一層與Dual RAG的關係仍只有未來可能使用的人工review證據；目前兩個retrieval corpora、融合政策、
API與evaluation labels都沒有修改。完整問題與回答留在gitignored private ledger，GitHub只保存aggregate
3/5進度、hashes、spec與不含owner-derived row identity的驗證文件。

### 驗證結果、已知限制與下一步

11項focused tests與完整660/660 tests PASS；Ruff F/I、format、strict MyPy、compileall、ledger CLI
`--check`與`git diff --check`皆PASS。唯一警告仍是既有Starlette／AnyIO deprecation。第3個event SHA-256
為`256bd8d3ca1768ba20de8e12193463d0e871f6ca78aa14cdc1799d11d36c3d36`，累積ledger SHA-256為
`92be88b06461e5bac0e8086edae8795e8a151829402f0cdd5f0cdbad8eedf419`。

下一步是第4題。前三題碰巧都選`same_review_family`不構成第四題的答案；在owner明確選擇前，剩餘兩題
必須維持pending，也不能啟動review-family materialization或release/color promotion。

## 2026-09-18 — LCD decision04：記錄第四個casting family人工決定

### 新執行了什麼、解決什麼問題

Owner對第4題回答`same_review_family`。本輪將原句保存為private ledger第4個event，累積進度因此成為
4/5 recorded、1/5 pending與4個review-family relationships confirmed。Recorder在落盤前先驗證前三個
events及其checksums，再限定唯一可新增的ordinal為4；因此第四題的授權不會覆寫歷史，也不會提前回答
最後一題。

這一步解決的是「把新的人工作答安全累積到既有決策歷史」。它沒有解決family relationship如何轉成
canonical catalog，因為那是另一個需要spec與驗證證據的promotion gate。把兩件事拆開，可避免一個簡短
回答同時改動review、release、database和runtime等多層真值。

### 代碼與測試修改、以及為何沿用既有方法

產品程式碼沒有新增question-specific分支。既有generic recorder已將packet binding、allowed decision、
verbatim evidence、contiguous ordinal、event hash與cumulative ledger hash分開驗證，第四題只需使用相同
contract。若為每一題新增專用function，會產生五份近似程式，日後容易出現其中一題少做privacy或tamper
check的漂移，因此選擇重用已測試的狀態機。

Artifact tests更新為exactly 4 events，新增第4個event的ordinal、decision與verbatim assertions，公開
manifest則必須呈現4 recorded／1 pending。這些測試不只檢查數字，也會透過完整ledger validator重算前
三個event，確保本次append沒有改寫歷史。

### 決定的範圍、技術邊界與資料選型

第4題屬於private fixture-name candidate；`same_review_family`只確認來源觀測在人工review層的casting
family關係。即使名稱與synthetic catalog fixture相同，也不能據此選定fixture product，因為fixture是測試
資料而非真實Hot Wheels canonical authority。各release observations繼續獨立，顏色、輪圈、tampo、edition
與包裝保持未知。

沒有修改PostgreSQL、API、evaluation label或Dual RAG兩個corpora。Private ledger保存問題identity與完整
回答；公開repo只保存ledger/packet hashes、4/5 aggregate、規格與方法證據。這延續先前的權利邊界，不將
owner XLSX衍生明細或人工回答內容擴大發布。

### 驗證結果、限制與下一步

11項focused tests與完整660/660 tests PASS；Ruff F/I、format、strict MyPy、compileall、ledger CLI
`--check`與`git diff --check`皆PASS。唯一警告仍是既有Starlette／AnyIO deprecation。第4個event SHA-256
為`dec834a797ed7d18f630f99195f1ae775f83e97b2684221f93d24d39ac1e6c36`，累積ledger SHA-256為
`68065d88366150f8efe2027daee98f50f69ad7047907f0746e73ccb1244f280d`。

下一步是第5題，也是本批最後一題。前四題相同的答案不能作為第五題授權；完成第五題後，也只代表owner
review packet完成，不能直接等同canonical promotion或variant/color驗證完成。

## 2026-09-18 — LCD decision05：完成5題owner review batch，但不自動materialize

### 新執行了什麼、解決什麼問題

Owner對第5題回答`same_review_family`。本輪將回答加入private ledger的第5個event，讓凍結的batch 01從
`in_progress_awaiting_owner`轉為`complete`：5/5 recorded、0 pending、5個review-family relationships
confirmed。這解決了第一批人工問題全部取得可追溯答案的工作，並形成一個可以被checksum重算的完整
decision history。

「complete」在這裡只描述問題包，不描述整個資料專案。為避免履歷文件或後續程式把狀態讀得太寬，本輪
特別把batch closure與family materialization分開：前者已完成，後者尚未設計或授權。Canonical promotions、
reviewed colors、PostgreSQL writes、evaluation labels、network requests與Dual RAG changes仍全部是0。

### 代碼與資料修改、設計決定及原因

產品 recorder沒有新增第5題專用分支；同一個generic append contract先重新驗證packet與events 1–4，再
只允許ordinal 5。`build_ledger`根據event數量等於question數量自動導出`complete`，而不是由呼叫端任意
傳入狀態。Derived status避免「只有4題卻手動寫complete」或「5題齊全仍忘記關閉」這類雙重真值。

Artifact tests更新為exactly 5 events，逐項驗證第5題ordinal、decision和verbatim response，並要求private
ledger與public manifest皆為`complete`、5 recorded／0 pending。前四個events的hash仍要通過完整重算；
這確保closure不是用覆寫檔案的方式偽造，而是合法的最後一次append。

沒有直接產生family-link database rows。雖然五題都得到相同答案，但現有回答只定義review family，沒有
指定canonical UUID、release-to-family mapping的持久格式、conflict handling、idempotency、rollback或
provenance readback。先設計materialization contract再寫資料，比「看到5/5就直接更新catalog」更容易稽核
與復原，也不會把synthetic fixture誤當真實authority。

### 技術／方法選型與隱私界線

繼續採用append-only JSON ledger與SHA-256，而不是直接修改原始packet的五個`decision:null`欄位。完整
ledger可以證明每個回答的順序、時間、問題綁定和歷史event未變；代價是private artifact較冗長，但只有
五個events，且audit價值高於少量儲存成本。

完整ledger仍在gitignored local directory。公開manifest/report只顯示complete、5/5 aggregate與packet／
ledger hashes，不包含private問題名稱、toy numbers、cluster IDs或verbatim responses。這讓GitHub能展示
流程確實結案，又不擴大發布owner XLSX衍生明細。

### 驗證結果、剩餘限制與真正下一步

11項focused tests與完整660/660 tests PASS；Ruff F/I、format、strict MyPy、compileall、ledger CLI
`--check`與`git diff --check`皆PASS。唯一警告仍是既有Starlette／AnyIO deprecation。第5個event SHA-256
為`5d4949550c43733dff2994408d73795e1dce960a8b80dca0ef9f5b7e00ee6872`，complete ledger SHA-256為
`9da688295717588d553922f448e43b6a27255922bdd8513f3245247e39eaad4a`。

下一步不再是回答第6題，因為batch 01只有5題。真正下一步是先規劃一個小型、可回滾、可重跑且不碰
release/color的review-family materialization功能，決定如何把這五個owner-confirmed relationships轉成
獨立review-layer artifact；在新spec通過前不能寫canonical catalog或PostgreSQL resolver truth。

## 2026-09-18 — LRFM-T1–T4：將5個owner decisions物化為獨立review-layer registry

### 新執行了什麼、解決什麼問題

上一階段完成5/5 owner questions，但答案只存在append-only ledger，後續程式若要使用仍需重新理解packet
與event語意。本輪新增local release casting review-family materialization，把五個肯定決定轉成5個機器可讀
的review relationships，並附帶18筆獨立source references。這解決了「決策已完成但沒有穩定下游交接
artifact」的問題，同時保持所有release為`held_for_variant_review`。

這不是把資料升級為canonical。Materialization在此代表把已授權的review-layer關係整理成有schema、版本、
hash與validator的registry，不代表建立真實商品ID。公開summary因此同時顯示5 relationships、18 held
references、0 exclusions，以及canonical promotions、reviewed colors、PostgreSQL writes、evaluation labels、
runtime indexing和network requests全部為0。

### 代碼修改位置、資料模型與技術選型原因

新增`release_casting_review_materialization.py`與CLI
`pvr-materialize-release-casting-review-families`。Builder先呼叫既有`check_batch`與`check_decisions`，只有
完整且checksum一致的ledger能進入。每個肯定event綁定packet、question ordinal、private review cluster、
event hash、observed labels、normalized key與source references，並產生SHA-256-derived relationship ID和
item checksum。

沒有使用UUIDv5或canonical UUID。這個ID只在本次review registry中定位關係，使用SHA prefix可以明確避免
被API或資料庫誤認為canonical product identity。另一個既有`data/review_family_registry.json`屬於不同的
2025 Wiki adjudication來源，因此也沒有把兩個registry合併；共用名稱不代表共用lineage或decision contract。

Candidate evidence只保存checksum與`context_only_not_selected`。原因是前三階段的owner回答確認family關係，
沒有精確選擇synthetic fixture或human draft target。若把candidate ID直接寫成target，就會把問題上下文
誤當成owner授權。Generic builder仍支援未來的`keep_separate`與`unknown`，兩者會進入non-materialized
exclusions而不是被丟棄。

### 重跑、衝突、回滾與隱私為何這樣設計

第一次執行同時建立private `registry.json`與public manifest/report；完全相同的第二次執行回傳`unchanged`。
若只有一邊存在、檔案集合不同或任何byte衝突，流程fail closed且不覆寫。若首次建立private成功但public
寫入失敗，只刪除本次建立的private directory，留下原有外部資料不動。這提供小型但明確的transaction
boundary，不需要為一個JSON registry引入資料庫交易。

完整registry含labels、source IDs與toy numbers，因此加入gitignore。公開manifest只含packet／ledger／
registry hashes和aggregate counts。這個private/public split讓GitHub可驗證產物版本與結果範圍，但不發布
owner XLSX衍生的row-level內容。

### 驗證結果、目前能力與下一個限制

13項focused tests覆蓋肯定／否定／未知決定、determinism、held release boundary、incomplete/tampered
ledger、duplicate source/cluster、public privacy、created/unchanged、conflict、partial state與simulated
second-write rollback。完整repository suite為673/673 PASS；Ruff F/I與format、strict MyPy、compileall、
installed CLI三種狀態、artifact `--check`與`git diff --check`全部PASS，唯一訊息是既有Starlette／AnyIO
deprecation warning。Private registry SHA-256為
`1b8c18618390c4f224634da7a0fe3ee403c2c49f7e1614b941e4332196fc1a83`。

目前registry仍不是Dual RAG knowledge。下一步應先規劃privacy-bounded knowledge projection與離線retrieval
evaluation，決定只公開／索引哪些family-level文字，以及如何避免與既有2025 review-family corpus產生ID或
語意碰撞；在新gate完成前，不應寫PostgreSQL或改production retrieval。

## 2026-09-19 — LRFK-T1–T4：建立5-document private human-knowledge evaluation projection

### 新執行了什麼、解決什麼問題

上一階段已把五個owner decisions物化成review relationships，但registry仍是audit artifact，不適合直接當
retrieval documents。本輪新增獨立knowledge projection，把每個relationship轉成typed `review_family`
document，總計5 documents與18筆private source references。這解決了下一階段離線retrieval evaluation需要
一致文件格式、穩定knowledge key和明確search fields的問題。

Projection狀態是`offline_evaluation_candidate_not_runtime`。這表示資料已準備好接受評估，但API、現有
Human Knowledge RAG、canonical resolver與Dual RAG runtime完全沒有載入它。把資料準備和runtime integration
拆成不同gate，可避免「能建立文件」被誤寫成「已證明搜尋品質」。

### 代碼修改了哪一部分、文件模型如何選擇

新增`release_casting_review_knowledge.py`與CLI
`pvr-project-local-release-review-family-knowledge`。Builder先重跑完整materialization validator，再將每個
relationship轉為只含`knowledge_type`、review family ID／UUID、identity level/status、brand、casting、
aliases與source record IDs的document。`review_family_uuid`使用local namespace UUIDv5，提供日後retriever
需要的穩定typed key，但不會填入canonical UUID欄位。

Searchable allowlist固定為brand、casting與aliases。Owner確認過的observed labels才可成為aliases；source IDs
只作provenance，不參與搜尋。Toy number、年份、series、variant note、candidate evidence、顏色與release
attributes都不複製到search surface。這樣可以讓未來benchmark測試名稱辨識，又不讓release-level線索被
錯當family ground truth。

### 為何需要與既有42-document corpus做collision guard

Repo原本已有一個來自不同2025 Wiki adjudication的42-family projection。如果直接把新5 documents串接進
runtime，即使UUID不同，也可能因品牌與casting／alias正規化後相同而建立兩份語意重複identity。本輪因此
同時比較review ID、UUID和normalized brand-plus-name/alias；任一碰撞都fail closed。真實資料的三種結果
皆為0，所以新projection可以成為未來47-document evaluation candidate，但尚未被授權合併或上線。

這個決定也避免重寫既有`data/review_family_knowledge.json`。舊42 documents和新5 documents各自保留版本、
hash與authority lineage，之後的evaluation spec必須明確決定如何組合，不能靠檔案append隱性改變document
frequency和ranking。

### 重跑、隱私、錯誤處理與測試理由

第一次執行建立gitignored private projection與public aggregate；完全相同的第二次回傳`unchanged`，
`--check`則重建並逐byte比較。Partial pair、existing checksum mismatch、registry/projection tamper、ID／UUID／
normalized identity collision、duplicate source、conflicting bytes都會拒絕。模擬public write失敗時，本次剛
建立的private directory會被回滾。

Public manifest只公布source/projection hashes、document/search field names、5/18/42 counts與zero-effect
boundaries，不含document值、labels、aliases、IDs或source rows。完整projection繼續留在owner-data的
gitignored路徑，符合先前未取得再發布權的邊界。

### 驗證結果與下一步

13項focused tests與完整686/686 tests PASS；Ruff F/I與format、strict MyPy、compileall、installed CLI
`--check`、artifact validation、privacy scan與`git diff --check`全部PASS。唯一警告仍是既有Starlette／
AnyIO deprecation。Private projection SHA-256為
`32644f9c5b91039fde7b7a9586f8a6bf9479ea7c6878661d329ea53bed4207d8`。

下一步是建立獨立的offline retrieval benchmark。它必須包含非逐字query、alias變體與hard negatives，且
expected family labels要與retrieval執行分離；不能用這5個文件中的exact casting文字當唯一queries，也不能
在沒有評估證據前修改Dual RAG runtime。

## 2026-10-05 — PPHR-T1–T5：確認Pointwise v2缺少獨立no-match holdout

### 新執行了什麼、解決什麼問題

前一步已在development selection上得到三態policy，但20筆no-match selection同時參與了threshold選擇，不能
再被當成未看過的test。本輪沒有急著執行resolver，而是先盤點本機剩餘的真實查詢來源，回答一個更基本的
問題：是否已存在可以誠實測試v2的獨立no-match資料。

檢查結果為不存在。105-row人工queue包含已追蹤的101筆，以及4筆`excluded/ambiguous`且沒有任何human
expected identity的資料；230-row comparison與1,640-row evidence檔分別只有91與79個unique case IDs，全部
重疊既有101筆。換句話說，檔案列數看起來很多，但它們是相同query的模型比較或candidate evidence，不是
新增人工答案。既有52筆catalog-relative no-match已全數用於v2 fit／selection，untouched eligibility為0。

RHB公開進度另有1筆owner-approved `no_match`，但其labels尚未materialize，且split、scoring、resolver
evaluation均明確為false。本輪把它記為potential-but-ineligible，而不是跨越原批准範圍拿來湊數。最終
readiness因此是0/20，shortfall為20，Pointwise v2繼續保持development-only。

### 代碼修改了哪一部分、為何這樣設計

新增`pointwise_policy_holdout_readiness.py`與CLI `pvr-audit-pointwise-policy-holdout`。第一次audit需要顯式
提供外部evidence root；builder只讀CSV的`case_id`與人工答案是否存在，輸出source hash、row／unique／overlap
counts與分類。外部CSV、query、label與case ID均未複製進repo。之後的`--check`只驗證tracked aggregate與
parent hashes，因此GitHub checkout不依賴使用者另一個private專案仍存在。

Artifact同時綁定v2 calibration、policy、selection與RHB aggregate progress，並固定最低20筆新organic
catalog-relative no-match契約：必須有人工作答、綁定同一catalog、在resolver access前freeze、不得重用52筆
development資料、不得用synthetic/counterfactual negatives，也不得藉新holdout重調model/features/thresholds。
這比直接保存外部rows更小、更容易公開審查，也符合使用者要求repo只保留必要最終資料。

### 方法選型、替代方案與限制

以case-ID overlap而不是檔案列數判斷independence，是因為comparison與evidence pipeline會為同一query產生多列；
若用1,640作為樣本數會嚴重高估資料量。人工答案完整性則阻止4筆excluded row被無證據轉成negative。沒有採用
counterfactual移除catalog family的方法，因為那只測人造absence，不能代表真實image-search文字中的no-match。

最低20筆沿用目前negative threshold-selection的規模，目的是建立最小可審核gate，不宣稱20筆足以代表global
traffic或manufacturer truth。較強方案是另外收集數百筆，但這會成為新的資料蒐集／人工標註工作，應由owner
另行批准，不能由readiness audit自行擴權。

### 驗證結果、既有baseline與下一步

7個focused tests全部PASS；scoped Ruff check/format、strict MyPy、compileall、CLI `--check`與
`git diff --check`均PASS。完整repo測試揭露13個既有`human_knowledge_storage_api` failures：舊v4 storage
protocol仍綁定過期的`retrieval.py` hash，因此按設計fail closed為503。全repo Ruff／MyPy也有歷史問題；它們
與本次新module無關，本輪依lite mode不擴張去重封存另一套protocol或重寫舊scripts，並在QA中如實保留。

下一步不是runtime activation或繼續審RHB held rows，而是由owner決定是否批准新的最小資料任務：收集並獨立
審核至少20筆、確定其expected family不在同一1,763-record frozen catalog中的真實查詢；membership與答案需在
任何resolver/model access之前封存。完成該gate後，才可用固定v2 artifacts做一次不可retune的policy test。

## 2026-10-05 — PNMH-T1–T6：封存20筆owner-reviewed no-match holdout

### 新執行了什麼、解決什麼問題

前一步誠實揭露Pointwise v2沒有獨立negative holdout，readiness為0/20。本輪完成新的資料蒐集與owner gate：
從2022 community catalog source解析447筆release rows，找出相對既有2023–2026 frozen catalog確切缺少的
88個casting families，再以固定salt建立40筆候選池。蒐集流程依序嘗試28筆候選，透過image search與
reverse-image文字結果建立query，最後得到20筆可由原始release fields回答的資料；owner已一次審閱並批准
這20筆query和expected identity由`staged`轉為`owner_reviewed`。

本輪解決的不是resolver準確率，而是測試治理問題：現在先把20筆測試輸入與答案封存，之後才可能在另一個
gate查看resolver輸出。這樣可以證明未來的test不是看到結果後才換題、改答案或選threshold。資料層面的
shortfall因此由0/20關閉為20/20，但尚未產生任何model score。

### 代碼與資料修改了哪一部分、原因是什麼

新增`data/evaluation/image-search-pointwise-no-match-holdout-v1/dataset.json`，其SHA-256為
`b46367efb54c9ab2a74c23d0824d1da5f939ecdf74a63c612da37c0688c50a7e`。每筆只保留`id`、自然語言
`query`、`expected_casting`與七個必要release identity fields：brand、casting、release year、series、
collector number、series position及toy number。20筆query與20個casting皆唯一，且20/20 normalized exact
brand/casting families都不存在於綁定SHA-256
`b4e0747450a5447c2bf66b0838c91f3f723a19ac97c90c7ac3636cf3a9a709d4`的1,763筆catalog。

資料集沒有color與edition，因為原始source未提供足以支持這兩欄的可靠答案；也沒有保存圖片、來源URL、圖片
hash、搜尋時間或raw API response，因為它們不是未來resolver測試所需輸入。新增四項focused tests鎖定dataset
與catalog hashes、20筆順序與唯一性、exact schema、full identity一致性、catalog-relative absence以及privacy
forbidden fields。這些測試使日後catalog或test truth被改動時直接fail closed。

### 方法與技術選型理由

候選來源選擇2022，是因為resolver目前的frozen corpus是2023–2026：同一品牌、相同community資料結構可以
提供真實產品文字，同時自然形成catalog-relative no-match，不需要捏造不存在的車名。先用固定salt凍結候選
順序，再進行image／reverse-image查詢，避免依結果好壞挑選題目。正確答案直接沿用候選release row的casting
與完整release fields，符合owner明示不需額外花時間重新驗證的範圍。

最終選擇單一minimal JSON，而不是把蒐集程式、55個raw API JSON、圖片或review packet一起提交。後者只服務
一次性資料建立，不是產品runtime或可重用benchmark input；保留它們會增加repo噪音、外部內容與隱私面積。
Dataset只用candidate-pool與staged-review hashes保留必要lineage，既能重現批准邊界，也不公開無關collection
metadata。依事先約定，`.local-image-search-collection-no-match-holdout-v1/`在最終驗證後完整刪除。

### 驗證結果、限制與下一步

Focused tests在暫存資料夾刪除前後都通過，證明正式dataset不依賴collection workspace。Scoped Ruff check／
format與`git diff --check`也通過。整個步驟沒有載入resolver或neural model，沒有執行scoring，沒有修改model、
features、match/no-match thresholds、catalog或runtime default。

這20筆的no-match只代表expected family不在該1,763筆third-party frozen snapshot中，不是Mattel認證或global
truth。下一個必要gate是owner另行批准一次output-blind frozen-policy evaluation；即使未來分數不理想，也不能
使用這20筆重新選model／threshold或直接啟用runtime。

## 2026-10-05 — PNMHE-T1–T5：完成一次output-blind no-match holdout evaluation

### 新執行了什麼、解決什麼問題

Owner以PNMH-G2明確批准使用SHA-256
`b46367efb54c9ab2a74c23d0824d1da5f939ecdf74a63c612da37c0688c50a7e`的20筆holdout與
SHA-256 `68969b386a05002fca8f48826f37f5a00c24128672fbfbf3befb748b881ab418`的Pointwise v2
policy進行一次output-blind evaluation。本輪在任何輸出可見前先固定protocol與成功條件，再載入一次local
Pointwise scorer逐筆運算，最後只保存aggregate result。

結果為11筆`no_match`、9筆`ambiguous`、0筆`matched`。No-match recall為55%，ambiguous rate為45%，
false-match rate為0%。預先登記的gate要求至少5筆明確no-match且最多2筆錯誤matched，兩項都通過。這解決了
前面只知道development threshold表現、卻不知道它在全新catalog-relative negatives上能否泛化的問題。

### 代碼修改了哪一部分、原因是什麼

新增`pointwise_no_match_holdout_evaluation.py`與CLI
`pvr-evaluate-pointwise-no-match-holdout`。Evaluator在讀query前先驗證dataset、catalog、calibration、policy、
development selection、model config與model manifest七項content hashes，再重用既有五feature calibrator及
雙threshold decision policy。全部20筆decision只存在記憶體，方法立即把它們reduce成counts/rates、aggregate
reason counts及confidence min/mean/max，沒有建立可被寫出的row-level result物件。

正式結果位於`data/evaluation/image-search-pointwise-no-match-holdout-evaluation-v1/results.json`，SHA-256為
`937eabc88164532ce686d5c1d4521d0ffef58efc2691d8836cba723fd68b05c6`。Validator用exact schema拒絕query、ID、
expected identity、candidate或prediction等row-level keys，並重新計算count/rate/gate一致性。結果檔存在時
`--run`會在載入model前拒絕第二次執行，`--check`則只檢查既有aggregate，不重新score。

### 技術與方法選型理由

Minimum no-match count選5，是沿用development gate原本的minimum accepted count；maximum matched count選2，
等於20筆negative上10%的false-match上限。這兩個數字在執行前寫入spec與程式，避免看到結果後移動門檻。
Ambiguous沒有合併到no-match，因為它代表系統知道自己不確定，和明確拒絕具有不同產品意義；但相較錯誤匹配，
保守abstention仍是較安全的結果。

沒有保存逐筆錯誤分析，雖然那會方便debug，原因是這20筆現在是final holdout；一旦用單筆結果改model或
threshold，它就不再是untouched test。只保存aggregate使專案能展示generalization evidence，又能實際執行
owner要求的output-blind與no-retuning契約。

### 驗證、限制與下一步

Focused tests鎖定結果hash、所有parent bindings、aggregate算術、pre-registered gates、recursive privacy guard、
one-run refusal及no-runtime/no-adaptation flags。Scoped Ruff、strict MyPy、compile與`git diff --check`亦納入驗證。
唯一runtime訊息是transformer dependency既有的`torch_dtype` deprecation warning，不影響結果。

這是20筆negative-only、third-party-catalog-relative測試，因此0% false-match不能被描述成整體resolver accuracy；
它無法測catalog-present query的exact-match或false-no-match率，也不是manufacturer/global truth。結果PASS只支持
目前policy在此範圍內的保守拒絕行為。Model、features、兩個threshold、dataset answers與runtime defaults皆未
變更，runtime activation仍未獲批准。

## 2026-10-05 — PBHE-T1–T6：完成53+20 aggregate balanced policy evaluation

### 新執行了什麼、解決什麼問題

前一輪只驗證20筆catalog-relative negatives，無法回答系統遇到catalog-present query時會正確匹配、錯誤拒絕
或大量abstain。本輪依PBHE-G1使用固定153-row positive dataset中從未參與v2 calibration／threshold selection的
53-case test split，執行唯一一次policy-layer positive evaluation；20筆negative沒有重新score，而是只讀取
先前SHA-256固定的aggregate result。

Positive結果為5筆`matched`、45筆`ambiguous`、3筆錯誤`no_match`。五筆matched在casting與exact release兩層
全部正確，因此accepted precision皆為100%，但positive exact recall只有9.43%，false-no-match rate為5.66%。
搭配既有negative的11 no-match／9 ambiguous／0 matched後，73筆共有54筆ambiguous，combined abstention為
73.97%；19筆decisive中16筆end-to-end正確，decisive exact precision為84.21%，end-to-end exact accuracy為
21.92%，balanced identity recall為32.22%。

### 代碼修改了哪一部分、原因是什麼

新增`pointwise_balanced_holdout_evaluation.py`與CLI
`pvr-evaluate-pointwise-balanced-holdout`。Evaluator驗證positive dataset/split、catalog、calibration、policy、
selection、model config/manifest、既有ranking final comparison、negative result和owner authorization bindings，
只挑出53個frozen test IDs載入相同Pointwise scoring context。每筆結果只在記憶體存在，最後轉成positive、
negative-reused與combined三組aggregate metrics。

Casting與exact release分開計算，是因為這個專案的第一層任務是辨識車型，但最終目標是完整release identity。
若只報casting正確會掩蓋同車型不同年份／series／toy number的錯誤。本次恰好兩層都是5筆正確，但schema與測試
仍強制exact count不得大於casting count，並讓兩層precision／recall保持獨立。

結果檔`data/evaluation/image-search-pointwise-balanced-holdout-v1/results.json`的SHA-256為
`8764f2642208b7cfddf63402fb18f487514af1b38a2d183afbc4da41b72a9566`。結果存在後任何`--run`會在model load前
拒絕，`--check`只驗證artifact、算術和guardrails。沒有逐筆query、ID、expected identity、candidate、confidence
或prediction進入tracked output。

### 技術棧與方法選型理由

Gate在輸出可見前固定為至少5筆exact-correct matched、matched exact precision至少90%、positive false-no-match
不超過10%，並要求negative aggregate gate繼續PASS。Minimum 5沿用development selection的accepted-count下限；
10%沿用既有false-no-match safety ceiling。結果剛好只有5筆accepted，雖然形式上PASS，文件仍明確標示沒有裕度。

沒有把53筆稱為全新的end-to-end untouched benchmark：它們過去已用於底層ranker final comparison，但沒有參與
v2 calibration／threshold selection，也沒有看過v2 policy status，因此只宣稱為固定的policy-layer positive test。
這種說明比重新包裝成“全新資料”更適合可被面試官追問的履歷專案。

### 驗證結果、技術判斷與下一步

Focused tests鎖定result hash、所有transitive bindings、one-run refusal、negative non-rerun、casting/exact層級、
combined arithmetic、recursive privacy與no-adaptation/no-runtime guardrails。Scoped Ruff、strict MyPy、compile、
artifact `--check`和diff checks亦完成；唯一訊息是既有transformer `torch_dtype` deprecation warning。

本輪的技術判斷是「evidence gate PASS，runtime HOLD」。100% accepted precision不能脫離9.43% positive recall與
73.97% combined abstention單獨展示。若後續要提升coverage，不得用這53或20筆重新選threshold；應使用新的
development資料改善model／calibration，再建立新的fresh final test。就目前履歷展示而言，這份結果已能呈現
Dual RAG之外的neural reranking、calibration、三態decision policy、data governance與output-blind evaluation，
同時誠實揭露prototype尚未production-ready。

## 2026-10-05 — PER-T1–T5：把履歷首頁更新到最新ranking與policy證據

### 新執行了什麼、解決什麼問題

原README的架構與entity-resolution定位正確，但首頁仍把120-product／100-case synthetic fixture與早期
`winner: null`當作headline evidence。那是2026-09-26時的真實狀態，卻沒有包含後來完成的1,763-release
third-party snapshot、153筆image-search-derived positive queries、Pointwise final ranking與73-case balanced
policy evaluation。對第一次打開GitHub的面試官而言，最強證據被埋在Project Log與深層artifact中。

本輪只更新公開敘事：README先展示53-case frozen ranking test，再展示53 positive + 20 negative calibrated policy
結果；Portfolio Guide同步改寫成三個可直接用於履歷的current-evidence bullets與一段60–90秒pitch。舊fixture沒有
刪除，而是被重新定位成「baseline飽和、因此需要更難benchmark」的研究歷史。

### 修改了哪些部分、為何這樣修改

`README.md`的opening scope改為1,763 releases、153 positives與20 negatives，Architecture圖加入optional local
Pointwise與frozen calibration/policy，同時保留RRF為default runtime及Human Knowledge不得產生UUID的Dual-RAG
authority boundary。原本過長且已過期的RHB進度敘事縮成Data and authority boundaries，詳細review歷史仍由
Deep evidence連結保存。

Measured evaluation現在分成release ranking與calibrated policy兩部分。Ranking table並列RRF、release heuristic、
Pointwise與Listwise：Pointwise casting Top-1為52/53、exact release Top-1為36/53，相較RRF exact 29/53提升
13.21 percentage points。Policy table則把5/5 accepted precision和5/53 recall、3/53 false no-match、11/20
negative recall、0/20 negative false match及54/73 abstention放在同一視野，防止單獨引用漂亮數字。

`docs/PORTFOLIO-GUIDE.md`改成三個bullets：核心ranking gain、output-blind calibrated evaluation，以及Dual-RAG／
provenance／PostgreSQL boundary；另新增四步code-review walkthrough、claim guardrails與tech-stack rationale。
`specs/portfolio-evidence-refresh-v2/`保存這次新的要求與QA，而不覆寫2026-09-26已完成的v1 positioning spec。

### 方法與內容選型理由

首頁仍以confidence-aware entity resolution而不是「RAG專案」作headline，因為使用者可觀測成果是把noisy title
解析為canonical release或安全abstain；Dual RAG的重要性在於兩個retrieval corpora的authority不同，而不是由LLM
生成文字。這種定位能讓AI Engineer／SWE面試官先理解問題，再看到RAG、reranking與database技術如何服務它。

沒有建立新的dashboard或live hosted demo，因為目前policy coverage不足且runtime未獲批准。GitHub Markdown
landing page直接連結immutable JSON、QA與AI-eval evidence，可以展示技術深度又不暗示production deployment。
同理，舊null experiment保留：它證明專案不是預設neural一定較好，而是資料變難後才由量測選出Pointwise。

### 驗證結果與下一步

Static QA核對README 66個、Portfolio Guide 14個repository-relative links，缺失為0；Portfolio Guide resume section
正好三個bullets。JSON metric comparison確認29/53、36/53、5/5、5/53、3/53、11/20、0/20與54/73皆和frozen
artifacts一致。Terminology scan確認`hashing-v1`仍標為non-neural、Pointwise未被寫成runtime default、community
source未被寫成Mattel/global truth，`git diff --check`通過且diff只含documentation/spec。

下一個履歷必要工作不是再改模型，而是由owner決定是否把目前65個local commits推送GitHub，並在GitHub頁面
實際檢查README rendering。若未來追求runtime coverage，必須另開使用新development data與fresh final test的
產品迭代，不能回頭使用已封存的53+20 holdouts調整threshold。

## 2026-10-06 — GPM-T1：補齊 GitHub repository 公開展示資訊

### 新執行了什麼、解決什麼問題

在最新 portfolio evidence commit 推送後，GitHub repository 首頁已能正確呈現新版 README，但 repository
description 與 topics 仍完全空白。這會使招聘者在個人首頁或 GitHub 搜尋結果中只能看到 repository 名稱，無法在
打開 README 前辨識這是一個 entity-resolution、retrieval 與 calibrated-abstention 專案。

本輪將公開 description 設為「Confidence-aware product entity resolution with Dual-RAG retrieval, neural
reranking, calibrated abstention, and governed evaluation.」，並新增 `python`、`fastapi`、
`entity-resolution`、`information-retrieval`、`rag`、`postgresql`、`pgvector`、`machine-learning`、
`cross-encoder` 與 `human-in-the-loop` 十個 topics。更新後重新讀取 GitHub metadata，確認 description 與
topics 已保存。

### 代碼修改了哪一部分、原因是什麼

沒有修改產品程式碼、資料集、模型、threshold、API、runtime 或 evaluation artifact。GitHub metadata 是
repository-level 的公開展示設定，不存在於產品 source tree；本地唯一變更是追加這段 Project Log，讓公開展示
決策仍有可追溯紀錄。

Description 沒有使用「production-ready」、「deployed」或「100% accurate」等字眼，因為 frozen policy 仍是
runtime HOLD。它以問題與架構能力為主：confidence-aware entity resolution 是核心產品問題，Dual-RAG、neural
reranking、calibrated abstention 與 governed evaluation 則是可被現有 evidence 支持的技術特色。

### 技術棧或方法選型原因

Topics 同時涵蓋語言／API（Python、FastAPI）、問題領域（entity resolution、information retrieval）、AI 方法
（RAG、machine learning、cross-encoder、human-in-the-loop）與可選 storage backend（PostgreSQL、pgvector）。
沒有加入 LLM、generative-ai、production 或 computer-vision：最終答案不是由 LLM 生成，圖片只用於建立測試
query，且 production readiness 尚未成立。這樣能提高搜尋可見度，同時維持 README 的 claim boundary。

### 驗證結果與下一步

GitHub API 回讀顯示 repository 仍為 public、default branch 為 `main`，description 完整一致，十個 topics 全部
存在。README 的 GitHub rendered page 亦顯示最新 commit `a1e70e6`、1,763-release scope、Pointwise/Listwise
比較、`5/53` positive recall、`54/73` abstention與 runtime HOLD。

下一個必要步驟是從面試官閱讀順序執行一次完整 code review rehearsal：由 API contract 開始，沿 signal
extraction、candidate retrieval、RRF／optional Pointwise、calibration policy走到 authority boundary與 frozen
evaluation，整理每一站應該解釋的問題、程式入口和證據，而不是再新增功能。

## 2026-10-09 — DRSP planning：規劃 domain ranking、hard negatives 與 calibration 閉環

### 新執行了什麼、解決什麼問題

使用者希望專案更能呈現 AI Engineer 能力，因此要求完善 domain cross-encoder fine-tuning、hard-negative
mining 與 calibration。這三項先前並非同一個可執行 milestone：目前 Pointwise 只是 pinned generic MiniLM 的
zero-shot evaluation，Listwise 是較早 fixture 上訓練的 candidate-set head，五特徵 logistic calibration 雖已
完成，但尚未建立 domain ranker 後的 ECE、reliability 與 risk/coverage 閉環。

本輪建立 `specs/domain-ranker-selective-prediction-development-v1/` 的 requirements、design、tasks，將三部分
重新排成一條 development-only ML lifecycle：先過資料權利與 label-authority Gate，再做 family-safe split、
train-only one-shot mining、domain MiniLM fine-tuning、generic/domain selection，最後才對 frozen winner 做
calibration與三態 selective policy。這解決了「先訓練再補評估規則」會導致 holdout reuse、stale calibration與
threshold leakage 的問題。

### 代碼修改了哪一部分、原因是什麼

本輪沒有修改產品程式、資料、模型、threshold或runtime，只新增三份 Lite／Lean 規格文件，並追加 decision與
Project Log。Requirements用可觀測行為鎖定 purpose-specific permission、53/20 permanent denylist、split-before-
mining、hard-negative semantics、safetensors lineage、ranker freeze、calibration isolation、risk/coverage及
aggregate-only公開邊界。Design則定義資料的兩條安全路徑：取得現有 development rows 的明確 training-use／
derived-checkpoint權利，或改用 owner-authored／project-controlled synthetic data並降低外部泛化 claim。

Tasks拆成十個有序 Gate。T1只建立 training-use／authority contract；未通過前，T2以後不能 scoring、mining或
training。53 positive ranking test和20 negative holdout已開封，因此永久排除所有 adaptive phase；未來新的
fresh final要在ranker、calibrator與policy全部凍結後另案建立。

### 技術棧與方法選型理由

沿用同一個 revision-pinned MiniLM CrossEncoder與candidate renderer，能把變因限制在domain training資料，而非
同時更換模型架構。v1只採一個binary relevance objective和two-seed stability check；Pairwise/Listwise objective
search延後，避免小樣本model zoo。Hard negatives以same-casting wrong release、adjacent year、series、identifier
與explicit color conflict為主，但缺少排他證據的siblings標held，不強迫二元負標。

Calibration必須在ranker hash freeze後才開始。主方案仍是現有五特徵logistic correctness model；single-score
Platt與temperature可作ablation，isotonic只有calibration-fit至少200個獨立groups時才允許參選。低
`P(exact-correct)`不等於高`P(no_match)`，因此只有存在rights-cleared no-match rows時才建立獨立absence head；
否則policy只能可靠地選matched／ambiguous，不能假裝已校準catalog absence。

### 驗證與下一步

規格已寫入ranker quality、latency、Brier、NLL、ECE、precision/risk-coverage、AURC、coverage與false-decision
門檻，也明確接受`winner: null`與calibration shortfall作為有效負結果。所有checkpoint預設local-only，Git只保存
manifest、hash與aggregate；FastAPI保持RRF default，任何development policy都是`runtime_eligible=false`。

下一步是Owner Gate DRSP-T1，不是直接fine-tune。Owner需先決定：現有100 positive development rows與1,763
parent source是否具備可證明的ML-training／derived-checkpoint權利；既有52 development no-match是否可擴張到
新calibration用途；若不具備，則採owner-authored／synthetic development route。門檻也必須在看到新結果前確認。

## 2026-10-09 — DRSP-T1：封存 B 路徑的本機 ML 資料使用 Gate

### 新執行了什麼、解決什麼問題

Owner 選擇 B 路徑，允許現有 development data 支援後續 AI Engineer milestone。本輪沒有把這句同意直接當作
所有資料都可任意使用，而是建立 checksum-bound governance Gate：100 筆 positive development rows 可做
family-safe partition、one-shot hard-negative mining、本機 domain cross-encoder fine-tuning 與 ranker selection；
52 筆 no-match development rows 僅保留既有 32 筆 calibration-fit／20 筆 threshold-selection 用途，不可拿來
訓練 ranker。

這解決了先前「資料已存在 repo，所以是否能直接訓練」的不清楚狀態。Gate 同時把已開封的 53 筆 positive test
與 20 筆 negative holdout 寫成永久 denylist，涵蓋 partition adaptation、candidate-pool adaptation、mining、
fine-tuning、model selection、calibration、threshold selection 與 future-final manifest；後續程式不能只靠人工
記得避開它們。

### 代碼修改了哪一部分、原因是什麼

新增 `domain_ranker_governance.py` 與 CLI `pvr-materialize-domain-ranker-governance`。Validator 會重算並核對
positive dataset 的 153／100／53 結構與 split hash、human no-match 的 52／32／20 結構與 overlay、1,763 筆
catalog 的檔案 hash／rights state，以及 20-row negative holdout 的 hash 與禁止調參欄位。任何檔案漂移、權限
擴張或 artifact tampering 都會 fail closed；它不載入 resolver、neural model，不做 scoring、mining 或 training。

新增兩份 aggregate-only artifacts：`owner-authorization.json` 與 `governance.json`。公開 authorization 不保存
Owner 的逐字訊息，只保存 reviewer role、正規化後的核准範圍與訊息 SHA-256；這避免把對話內容不必要地寫入
Git。兩個檔案的 SHA-256 分別為
`cd4d04e12923aec65a9e46d7a46154ed3ce14435979c7eec9248e38619c10097` 與
`dee18eb3725804611827921f90202e7c43a78203758b47b78e02e0ba096378a0`。

`.gitignore` 新增 milestone 專用的 `local-*` 與 checkpoint artifact 路徑；測試則涵蓋 exact materialization、
row-level key／URL privacy、所有 frozen bindings、四種 input drift、authorization tamper 與無本機 catalog 時的
public-checkout validation。Specs 狀態更新為 T1 complete，但沒有把 T2–T10 或 acceptance thresholds 誤標為已批准。

### 技術棧或方法選型原因

採 deterministic Python validator 與 canonical JSON，而不是只寫一段政策文字，是為了讓資料用途成為可測試的
build precondition。內容 hash 與檔案 SHA 分開保存：前者偵測 schema/content tampering，後者讓後續 artifact 能
綁定實際 bytes。Public checkout 可用 tracked manifests 重驗證；嚴格模式則要求 Git-ignored 的 1,763-row local
catalog 實際存在並重算 hash。

權利狀態刻意寫成 `owner_attested_not_independently_verified`。Google 可搜尋／取得描述的是 acquisition route，
不等同於已獨立驗證第三方 license 或 public redistribution rights；因此本輪允許的是本機 bounded development，
不是 rights-cleared/public-model claim。這也是為何 raw training projection、mined pairs、row labels/predictions 與
checkpoints 全部 local-only，而 Git 只保存 hashes、counts、limitations 與 aggregate evidence。

### 驗證結果與下一步

獨立 Lite QA 驗證 9 項新 governance tests 與 22 項 FastAPI regression tests 全部通過；Ruff、strict MyPy、
strict CLI `--check --require-local-catalog` 與 `git diff --check` 亦通過。唯一訊息是既有 Starlette／AnyIO
第三方 deprecation warning，不影響本次 Gate。Gate 的 guardrails 顯示 neural model 未載入、queries scored
為 0、hard negatives mined 為 0、training runs 為 0，FastAPI runtime default 未改動。

下一步是 DRSP-T2：只建立 family/evidence-safe development partitions 與 frozen candidate-pool contract。它需要
獨立 Owner Gate；在那之前不可 mining 或 fine-tune。新 fresh final dataset、公開 checkpoint／weights 與 runtime
activation 仍是另外的未授權事項。

## 2026-10-09 — DRSP-T1A：把公開資格與執行／啟用權拆開，完成 governance v2

### 新執行了什麼、解決什麼問題

Owner 修正 T1 的公開邊界：hard-negative row-level pair package 與實際的 safetensors fine-tuned checkpoint 不需要
永久 Git-ignored；它們可以在各自的 release Gate 通過後進入 Git 或公開發布。Fresh-final 的 aggregate report，
以及 runtime code、config、model manifest 也可在未來公開。這項修正解決了「公開一份經過最小化與掃描的訓練
artifact」被原本 local-only 規則一併禁止的問題，但沒有把「可以公開」錯寫成「已建立、已驗證或已部署」。

本輪新增 `publication-amendment.json` 與 `governance-v2.json`，將四種狀態分開記錄：Owner publication
permission、artifact release-Gate、evaluation execution、runtime activation。現況仍是 hard-negative pairs 與
checkpoint 均未發布；fresh-final 明確為 `evaluation_authorized=false`、`executed=false`；runtime 明確為
`activation_authorized=false`、`activated=false`。Row-level final query／prediction 與 public endpoint 仍未授權，
53 筆 positive test 和 20 筆 negative holdout 的永久 denylist 也沒有改變。

### 代碼修改了哪一部分、原因是什麼

`domain_ranker_governance.py` 增加 T1A amendment、effective governance v2 的 materialize／check 流程，並把原始
T1 JSON 的 file SHA 與 content SHA 納入 amendment binding。選擇新增 amendment/v2，而不是覆寫 T1，是因為原
T1 代表當時真實批准的 local-only 邊界；直接改寫會讓 Git 歷史看似一開始就允許公開，也會破壞已被後續流程
引用的 hash。實作後兩份舊 T1 檔案仍維持
`cd4d04e12923aec65a9e46d7a46154ed3ce14435979c7eec9248e38619c10097` 與
`dee18eb3725804611827921f90202e7c43a78203758b47b78e02e0ba096378a0`，沒有被重寫。

`.gitignore` 的第一次 QA 發現一個 blocker：只忽略 `local-*` 和 checkpoint 目錄並不是 default-deny，未命名的
row-level 檔案仍可能被 Git 追蹤。修正後改為預設忽略整個 milestone data tree 與 artifact tree，再只 allowlist
四份 governance JSON、`public-hard-negative-pairs-v1/` 與 `public-checkpoint-v1/`。這表示路徑本身只提供未來
release 的窄入口，不代表內容自動安全；public pairs 仍須通過 schema／field minimization、PII／secret／local
path、lineage、license 和 denylist intersection 檢查，checkpoint 另須 safetensors-only、model card、NOTICE、
offline-load 與 digest Gate。Optimizer state、pickle、cache、scratch 和任意 run directory 繼續被忽略。

測試同步加入 frozen-T1 byte identity、permission／release／execution／activation 分離、tamper fail-closed、公開
checkout、預設忽略／窄 allowlist 與 forbidden-field 掃描。Specs、decision 與本 log 只描述已驗證狀態；沒有把
尚不存在的 pairs、weights、fresh-final report 或 runtime 當成完成成果。

### 技術棧或方法選型原因

採 canonical JSON + SHA-256 chaining，是為了讓「T1 原始決策 → T1A amendment → v2 effective policy」能被機器
重算，而不是靠文件覆蓋舊語意。Pair package 使用 non-executable、最小欄位的版本化資料格式；模型只允許
safetensors，因為這比 pickle 類 payload 更適合公開供應鏈檢查。大型 checkpoint 不直接塞進一般 Git blob，
而是保留 Git LFS／release asset 路徑，manifest 仍固定實際 weight SHA-256。權利文字繼續保留
`owner_attested_not_independently_verified`，表示 Owner 已授權專案公開，不等於第三方權利已被獨立驗證，也不
得升格為 manufacturer/global truth。

### 驗證、技術債與下一步

修正 default-deny blocker 後，QA 證據為 18 項 governance/focused tests 與 22 項 FastAPI regressions 全綠；
Ruff、strict MyPy、strict CLI、public-checkout CLI 與 `git diff --check` 也通過。舊 T1 file/content hashes 不變，
FastAPI default、模型載入、query scoring、mining、training、final evaluation、runtime activation 和 endpoint 都
沒有發生。

尚未完成的是 artifact-specific release Gate 本身：T3 未產生 public pair package，T4 未產生或發布 checkpoint，
fresh-final dataset／evaluation 與 runtime activation 也都沒有得到批准。下一個必要步驟仍是 DRSP-T2 的
family/evidence-safe partitions 與 frozen candidate pools；它需要獨立 Owner Gate，不能由 T1A 的公開資格推導。

## 2026-10-09 — DRSP-T2：封存 family-safe 70/30 分區與 query-only Top-25 候選池

### 新執行了什麼、解決什麼問題

本輪在獨立 Owner Gate 下完成 DRSP-T2，將已准入的 100 筆 positive development rows 先分區、再建候選池，
避免後續 hard-negative mining 自己挑資料或根據答案改寫 retrieval。Connected-component audit 得到 100 個
singleton components；deterministic salted ordering 將它們固定為 70 筆 `ranker_train` 與 30 筆
`ranker_selection`。Normalized query、alias、evidence event、casting family 與 exact identity 五種
cross-partition overlap 均為 0。

每筆 query 都建立一個 query-only Top-25 pool，因此共有 100 個 pools、每池固定 25 個 candidates。Retrieval miss
為 0，target injection 也為 0。這解決了「expected identity 是否暗中幫助檢索」的核心可信度問題：正確答案只在
retrieval 完成後用來觀察 target 是否出現在 pool，不能作為 retriever input，也不能補入 pool。

53-row positive test 並未用於 adaptive decision 或 scoring；不過實作會先 parse 包含完整 153 rows 的 source JSON，
再篩出 100-row development subset，因此文件不宣稱完全沒有讀取該檔案 bytes。20-row negative holdout 與 52-row
no-match development data 的 ranker scoring 也都是 0。Hard-negative mining、training、model selection、
calibration fit、fresh-final evaluation 與 runtime change 全部仍為 0。

### 代碼修改了哪一部分、原因是什麼

新增 `domain_ranker_partitions.py` 與 CLI `pvr-freeze-domain-ranker-partitions`，負責驗證 T1/T1A chain、建立
connected components、產生 deterministic 70/30 assignment、執行 query-only retrieval、以 pinned generic
MiniLM score frozen pools，以及嚴格重驗 artifact digests、檔案 mode 與禁止動作。`freeze_domain_ranker_partitions.py`
提供薄 script entry；`test_domain_ranker_partitions.py` 覆蓋 deterministic split、五種 leakage、Top-25、holdout
隔離、target-injection boundary、tamper、privacy、檔案權限及 calibration shortfall。

私有 `local-t2/partitions.json` 與 `local-t2/candidate-pools.json` 包含 row-level membership／query／candidate／score，
維持 Git ignored 且 mode `0600`。公開的 `t2-owner-authorization.json`、`split-manifest.json` 與
`candidate-pool-manifest.json` 僅保存 aggregate counts、不可逆 digests 與 lineage，mode 為 `0644`。`.gitignore`
只 allowlist 這三份 public artifacts，避免私有 rows 被誤提交。

Candidate manifest 綁定 catalog SHA-256
`b4e0747450a5447c2bf66b0838c91f3f723a19ac97c90c7ac3636cf3a9a709d4`、generic MiniLM revision
`233902d25c440f23af6f7d6e94d2946bac0bee0a`、config SHA-256
`3a88163cc7abc84468024f5e6410e0ca489a80a710b67b4c2474c4b4f7d7fad6` 與 manifest SHA-256
`32f889bb415ef5a56760a299da0635e8e1704d46fe0b11ded06c563de896feb8`。同一 manifest 也固定 retriever contract、
renderer hash與七個相關 source-code hashes；後續若 catalog、retriever、renderer、model config／manifest 或實作
漂移，就不能把新 pool 當成這次 frozen baseline。

### 技術棧或方法選型原因

分區採 connected components，而非單純 random row split，是因為不同 query 仍可能透過 family、alias、evidence
或 exact release 指向同一知識單位；把 whole component 放進單一 partition 才能避免跨分區洩漏。排序使用固定
salt 與 component digest，兼顧 deterministic reproduction 與不公開 row membership。當前資料剛好形成 100 個
singleton components，但演算法仍能處理未來非 singleton 關係。

Retrieval 採既有 `token-index-v1` sparse、`hashing-v1:192` dense、`structured-v1` 與 `RRF k=60`，再以 revision-
pinned `cross-encoder/ms-marco-MiniLM-L6-v2` 做 generic Pointwise scoring。沿用既有 retriever、candidate renderer
與 generic scorer，能把未來 T4 比較的變因限制在 domain fine-tuning；generic 與 domain 必須使用同一 frozen
pool。禁止 target injection 則讓 Recall@25 保持真正可失敗的 retrieval 指標，而不是設計上保證 100%。

### 驗證方式與 QA 修正

第一次 QA 判定有兩項 Important 必須補強：測試雖驗了最低數量，尚未精確 assert 70/30；同時只看
`target_injection_count=0` 不足以證明 expected target 沒傳入 retriever。修正後加入 exact 70/30 assertion，以及
retrieval spy／mutated-target invariance：捕捉所有 100 次 retriever inputs，確認沒有 target／expected 欄位；再
改變 private expected target，候選 UUID sequence 仍必須完全不變。

修正後 focused T1/T1A/T2 suite 為 `28 passed`，FastAPI regression 為 `22 passed`；Ruff、strict MyPy、使用真實
pinned MiniLM 的 strict CLI check 與 `git diff --check` 亦通過。Starlette／AnyIO deprecation warning 是既有第三方
警告，並非本輪產生。Public artifacts 本身不含 query、label、candidate identity、score、URL 或 local path。

### 留下什麼債、下一步是什麼

T2 明確發現 T6 calibration capacity shortfall：100 筆 catalog-present positives 全部已屬於 family-disjoint
ranker train／selection，因此可供 exact-correctness calibration 的新 family-disjoint catalog-present rows 為 0。
既有 52 筆 no-match 只能提供 catalog-absence calibration；未來 T6 必須另取得 admissible positive calibration rows，
不能回收 ranker rows。這個 shortfall 不阻塞 T3，因為 T3 只會在 70-row train partition 做 one-shot mining。

另一項 deferred assurance gap 是 `--public-only` 可驗 public artifact schema 與 self-checksum，卻無法在缺少 Git-
ignored row-level inputs 時獨立重算 70/30、overlap 或 pool claims；目前完整 strict check 仍須 local artifacts。後續
可考慮 signed attestation 或可驗證 aggregate certificate，但不得為此公開 private membership。

下一步是 DRSP-T3 deterministic train-only hard-negative mining。T2 的 PASS 只表示 split 與 pool 可供下一階段引用；
T3 仍需獨立 execution Gate。未取得該 Gate 前，不得 mining、產生 public pair package、fine-tune、calibrate、執行
fresh final 或改動 runtime。

## 2026-10-09 — DRSP-T3：完成 one-shot hard-negative mining 與固定五檔公開封裝

### 新執行了什麼、解決什麼問題

本輪在獨立 T3 Gate 下，只對 T2 已凍結的 70 筆 `ranker_train` queries 與原封不動的 Top-25 candidate pools 執行
一次 deterministic hard-negative mining。結果產生 345 筆可用於 binary relevance training 的公開 pairs，其中
207 筆是 adjacent-year／wrong-series-or-identifier、67 筆是 same-casting wrong-exact、67 筆是 high generic-score，
另 4 筆是 high RRF。69/70 queries 各有至少兩筆可辯護 negative，超過預先設定的 36-query Gate；每筆 query 最多
五個 negatives，避免少數 query 支配訓練分布。

這一步解決的不是「盡量產生更多負例」，而是「怎樣只留下有證據的困難負例」。65 個 same-family candidates 因
證據不足被標為 ambiguous held，沒有為了湊數強迫標負；45 個 permanent-holdout identities、34 個
ranker-selection identities，以及 20 個 target casting 未明示的候選也依邊界排除或保留。如此能讓後續 domain
fine-tuning 學到年份、series、identifier 與 exact release 差異，而不是把同 family 的合理 sibling 誤學成錯誤。

30 筆 selection、53 筆 positive test、20 筆 negative holdout 與 52 筆 no-match development rows 的 mining／scoring
均為 0；T2 pool 檔案 bytes 未改變。Training run、checkpoint、calibration、fresh-final evaluation 和 runtime
activation 也全為 0，因此 T3 完成不代表模型已微調或系統已啟用。

### 代碼修改了哪一部分、原因是什麼

新增 `domain_ranker_hard_negatives.py` 與對應 CLI／test，負責重新驗證 T1–T2 lineage、只讀取 train membership、
套用 frozen miner 規則、建立 hold／exclude audit，並在發布前驗證 package schema、digests、denylist 與內容安全。
`.gitignore` 與 package release contract 改成 default-deny，公開入口不再允許任意 nested files；唯一可追蹤內容固定
為 `pairs.jsonl`、`manifest.json`、`owner-authorization.json`、`DATA_CARD.md`、`NOTICE.md` 五檔。這項修改是因為
第一輪 security review 將原本的 nested allowlist 判為 High：即使頂層檔案安全，未來任意子目錄仍可能把 scratch、
secrets 或私有 row-level 資料帶入 Git。

公開 pair projection 刻意只保留訓練必要欄位，因此會揭示這些 records 屬於 training membership；它不公開
selection／test membership、原始未最小化 source fields 或 no-match rows。`pairs.jsonl` SHA-256 為
`50f88e73889b31e8f314e93b2cca9e4871934662b5218c6659a72fe06c0ca2ba`，固定五檔 package SHA-256 為
`89bc430289c36e75c6302e7aa4ecca1889f32df95e5199f61aba1f676b18022a`，manifest content SHA-256 為
`da5422568c9b0bae6e3d152d66318e251329ca966dbdff078a78029c77a04392`。Owner authority 仍是
`owner_attested_not_independently_verified`；資料只代表 frozen community catalog-relative labels，不是
manufacturer/global truth。

### 技術棧或方法選型原因

Miner 採 one-shot deterministic 規則，而不是 fine-tuned model 的 iterative remine。原因是小資料下反覆用自己的
錯誤選負例，容易形成 feedback loop，亦會讓 generic/domain 比較失去共同 baseline。沿用 T2 frozen pools 則能把
T4 唯一主要變因限制在 domain fine-tuning，而非同時改變 retriever、候選集合與訓練標籤。

公開 artifact 使用 JSONL pairs 加 canonical JSON manifest，而不是 pickle 或任意訓練 dump，便於逐列掃描、hash
binding 與跨工具重驗。Security scanner 擴充 AWS-style credentials、Bearer tokens、`.env` 名稱、path traversal、
local paths、URL、email/contact 與其他 PII／secret；電話數字判斷同時避開合法 11-digit product barcode 的 false
positive。Final manifest 會再做 secondary scan，sanitized內容仍須過 permanent denylist，避免清理字串後反而
繞過 identity boundary。

### 驗證方式、QA／security 修正

本輪經過兩輪 QA／security 修正。第一輪補上 strict MyPy 問題與 rematerialize validation，確保重新生成與 check
模式都能重現相同 hashes。第二輪關閉 nested allowlist High，改為固定五檔加 recursive unexpected-file rejection，
並擴大 secret／PII／traversal／contact scan、加入 barcode 誤判防護、final-manifest secondary scan 和 sanitized
denylist check。

最終驗證為 50 項 focused tests 加 22 項 FastAPI regressions 全綠；Ruff、strict MyPy 的 materialize／check 兩種
模式、T1／T1A／T2／T3 CLI chain 與 `git diff --check` 都通過。Security review 沒有殘留 High／Critical。
FastAPI default與既有runtime行為未改變。

### 留下什麼債、下一步是什麼

T3 的公開 pairs 已通過本版本 release Gate，但這不授權 T4。下一個必要步驟是 DRSP-T4 的獨立 Owner Gate：用同一個
pinned MiniLM、固定 binary objective 與兩個 seeds 進行 domain fine-tuning，再依 selection gate 判定是否存在
winner。開始前必須把 checkpoint Git allowlist 收緊為固定 package files，而不是可接受任意 nested contents；所有
來自資料、model card 或 metadata 的 untrusted text 只能當資料，禁止進入 `eval`、shell command 或 prompt
interpolation。

後續仍存在 T6 的 positive calibration-row shortfall；T4 不能為了解決它而重用 ranker train／selection 或已開封
53/20 holdouts。Fresh-final evaluation 和 runtime activation 也必須等待各自 Gate，不能由公開 pairs 或未來 checkpoint
的發布資格推導。

## 2026-10-09 — DRSP-T4：完成兩個 seed 的 domain MiniLM fine-tuning 與 checkpoint release

### 新執行了什麼、解決什麼問題

本輪完成第一個真正的 domain fine-tuning 階段。345 筆 T3 hard-negative pairs 被 deterministic 投影成 690 筆平衡
binary examples，涵蓋 69 個 training queries。Pinned MiniLM revision 分別以 seed 17 與 29 訓練；兩次都只用 frozen
30-query ranker-selection MRR@10 做 early stopping，最後選中 epoch 1，並在連續兩個 epoch 未改善後停於 epoch 3。
兩個 checkpoint 的 selected MRR@10 都是 `0.86111111`。這解決了「是否真的產生 domain-adapted cross-encoder」的
問題，同時保留 T5 才能做 generic/domain 公平比較的邊界。

第一次啟動在任何 optimizer step 前失敗，原因是 PyTorch AdamW 的參數名稱是 `lr`，程式卻傳入
`learning_rate`。修正後兩次 training 都完成，但 release Gate 因 validator 把 `safe_open` 當成可直接迭代物件而
拒絕 package。該批暫存 checkpoint 被刪除而未被信任。之後 validator 改用實際 `.keys()` API，新增真實
safetensors regression test，再從 pinned base model 以相同 recipe 重跑。兩次執行的 epoch metrics 完全一致，形成
直接的 reproducibility evidence，而不是沿用未通過 Gate 的 scratch output。

### 代碼修改了哪一部分、原因是什麼、為何這樣選型

新增 `domain_ranker_training.py`，統一負責驗證 T1A/T2/T3 hash chain、建立 checksum-bound Owner Gate、只載入 T3
pairs 與 T2 selection pools、設定 deterministic CPU training、執行 binary BCE-with-logits、逐 epoch 計算 MRR@10、
保留 earliest best epoch、輸出 float16 safetensors，最後用 `trust_remote_code=false` 做 offline reload。CLI 名稱是
`pvr-train-domain-ranker`。測試覆蓋 recipe freeze、pair projection、partition isolation、手算 MRR、tie/early-stop、
真實 safetensors 解析、完整 package validation 以及 unexpected nested file rejection。

固定 recipe 是 seeds 17/29、最多 4 epochs、patience 2、batch 16、learning rate `2e-5`、weight decay `0.01`、10%
warmup、max length 128、gradient clipping `1.0`。選擇單一 binary objective，而不做 Pointwise/Pairwise/Listwise 搜尋，
是因為 69 個 training queries 不足以支撐可信的架構競賽。Checkpoint 由 selection MRR 而不是 training loss 決定：
seed 17 loss 從 `0.52359351` 降至 `0.21914327`，seed 29 從 `0.47575115` 降至 `0.20618327`，但 MRR 都在 epoch 1 後
下降；這就是 early stopping 要阻止的小資料 overfitting。

Release package 同時保存兩個 seed，而沒有提早挑一個。每個 checkpoint 以 float16 safetensors 輸出，大小
45,439,178 bytes，使單一 Git blob 低於 50 MiB，也避免 pickle execution risk 與 optimizer-state disclosure。Package
使用 nested `.gitignore` 建立 exact 14-file allowlist，因此不必修改已被 T3 hash 綁定的 root `.gitignore`。Package
還包含 offline config/tokenizer、authorization、manifest、model card、Apache-2.0 license 與 NOTICE。Text metadata 會
掃描 credentials、secrets、`.env`、traversal、local path 與 email；weights 則必須能被 safetensors parser 解析並
離線載入，才允許發布。

### 結果、驗證邊界與下一步

Seed 17 checkpoint SHA-256 是
`652f1e900bfeefd1536603e2d7e3b9c783df7b93273eb0a83a3bb0dce4360417`；seed 29 是
`315df109e64798108cb06fb249cb43f85f625e8224f34b51559b8d4c74cecb2d`；14-file package SHA-256 是
`1cc26cc8aea072d02cb5fd25909b0adfcdbdfd2a7f642433945cf00211b002e1`。Training code lineage 綁定 commit
`14bcf2866becc4b1215155010157cdf5f4f63ee2`。移除 safetensors header 的 unordered metadata、把 tokenizer
文字正規化成 LF 後，連續兩次 clean rebuild 的兩個 checkpoint 與完整 package hashes 完全相同，正式補足
byte-level reproducibility，而不只是 metrics 相同。

Positive-test reads/scores、negative-holdout reads/scores、no-match development reads/scores、calibration fits、fresh-final
evaluations 與 runtime changes 全部是 0。本輪證明 domain training 與 model supply-chain pipeline 可運作，不代表
checkpoint 已經勝過 generic model。DRSP-T5 必須另外在 identical frozen pools 上比較 generic 與兩個 seeds，測量
exact/casting Top-1、MRR@10、hard-negative accuracy 與 CPU latency；若 frozen gate 未通過，就必須發布
`winner: null`。T5 尚未授權。

## 2026-10-09 — DRSP-T5：完成 generic/domain 公平比較並凍結 `winner: null`

### 新執行了什麼、解決什麼問題

本輪先在任何比較結果可見前，凍結三個模型共用的評估協議，再提交 comparison code commit
`a23b1b27073ea16c93c1eda9d814824638ccee58`。正式執行只讀 T2 的 30 筆 ranker-selection queries，且每筆使用原封
不動的 25 個候選；generic、domain seed 17 與 seed 29 都重新執行相同的 float32 CPU inference。這一步解決的是
「domain fine-tuning 是否真的比原始 generic cross-encoder 好」，而不是再次證明 checkpoint 可以被訓練或載入。

結果沒有通過。Generic 的 exact Top-1 是 `24/30`、MRR@10 `0.87777778`、same-family hard-negative accuracy
`41/52`；兩個 domain seeds 都是 `23/30`、`0.86111111`、`40/52`。三個模型的 casting Top-1 與 Recall@25 都是
`30/30`，顯示候選集合與 casting 層沒有退化，但 domain fine-tuning 在 exact release 區分上反而少一筆正確。Seed 17
與 29 的 CPU p95 分別是 `243.6395 ms` 與 `244.865875 ms`，雖都在 generic 的 1.25 倍以內，仍超過預設 200 ms
上限。因此兩個 seed 都未通過 exact、MRR、same-family、absolute latency 與正向 seed-stability gates，正式結果是
`winner: null`。

### 代碼修改了哪一部分，為何做出這樣的決定

新增 `domain_ranker_comparison.py` 與 `pvr-compare-domain-rankers` CLI，負責重新驗證 T2/T4 hashes、離線載入三個
模型、對同一 candidate pool 計分、計算六組核心指標、套用 all-or-nothing gate，最後輸出 checksum-bound aggregate
result。測試新增 UUID tie-break、casting parser、nearest-rank percentile、嚴格 hard-negative 勝負、完整 gate 與 winner
tie-break。Public config 只有 aggregates、hashes 與 gate decisions；逐 query ranks／latencies 放在 Git-ignored
`local-t5/diagnostics.json`，權限為 `0600`。

Same-family accuracy 採 `target_score > negative_score`，而不是大於等於，原因是相同分數並不能證明模型已學會分辨
exact release。Latency 先做三次 warm-up，再用三輪共 90 個 query batches 的 nearest-rank p95，避免用單次最佳值美化
結果。兩個 seed 若都通過時，才依 exact Top-1、MRR、same-family accuracy、latency、seed 做 deterministic tie-break；
本次沒有 seed 合格，因此沒有進入挑選步驟。

### 驗證、技術判斷與下一步

重新計算的 generic ordering 與 T2 frozen ordering 完全一致，證明評估沒有悄悄換 baseline。Result content SHA-256
為 `d9665b151c4c3263afd8e24345024985904f1a407d93ce6c9173ed37d8444e2b`，public result file SHA-256 為
`219789db3f1e6f7e3e114656d165ca3ebe733225139e294787dc64beaa3e25c3`。53 筆 positive test、20 筆 negative holdout、
52 筆 no-match development rows 的 reads/scores 仍全部是 0；calibration、fresh-final evaluation、runtime activation
也全為 0。

這個 negative result 對履歷項目仍有價值：它展示完整的 hard-negative mining、domain training、artifact lineage、
公平 model selection 與「不因已投入訓練成本就宣稱模型變好」的 ML 判斷。依 DRSP-R9，calibration 必須先有 immutable
selected-ranker hash；本次 winner 是 null，所以 T6 不是下一個可直接執行的步驟。若要繼續 domain fine-tuning，必須
另開新版本，提出新的資料或 objective 假設並取得新 Owner Gate，不能修改本次 thresholds 或拿 holdout 回頭調參。

Lean QA 中，16 項 T4/T5 focused tests、22 項 canonical FastAPI regressions、Ruff、strict MyPy、artifact check mode 與
whitespace gate 均通過。擴大執行整個 `tests/api` 時另發現 13 項既有 Human Knowledge storage app failures；只讀診斷
確認原因是其 v4 protocol 對 `retrieval.py` 的 source hash 已過期，experimental service 因而依設計 fail closed 為 503。
T5 沒有修改該 service、profile 或 runtime code，本輪不越界重建另一條已 gated 的 storage artifact；這項既有 QA 債已
明列在 T5 review，而不是隱藏或誤算成 domain-ranker regression。

## 2026-10-09 — DRV2-T0：建立 domain-ranker v2 remediation readiness

### 新執行了什麼、解決什麼問題

T5 產生 `winner: null` 後，本輪沒有把「繼續下一步」解讀成繞過 Gate 執行 calibration。相反地，先建立獨立的
`domain-ranker-v2-remediation` Lite 規格，把 v1 的負面結果接回新的資料與模型假設。這解決了兩個問題：第一，避免
因為已經完成 fine-tuning 就勉強挑一個失敗 checkpoint；第二，讓下一次實驗能真正測試新假設，而不是回頭利用已
看過的 30 筆 T2 selection errors 調參。

唯讀證據顯示，v1 的 345 筆 pairs 中有 207 筆（60%）是 adjacent-year／wrong-series-or-identifier，same-casting
wrong-exact 只有 67 筆（19.4%），另有 65 個 same-family candidates 因 query 證據不足被 held。兩個 seed 都在 epoch 1
達到最好 MRR，後續 training loss 繼續下降時 MRR 反而下降。這些現象支持「資料太小、exact-release ordering 密度
不足、binary Pointwise objective 與 sibling ranking 不完全對齊」的假設；文件刻意沒有把它寫成已證實根因。

### 規格修改了哪一部分，為何這樣選型

新增 requirements、design、tasks 與 readiness evidence。V2 最低資料門檻設為 180 筆全新的 catalog-present queries，
以 connected components 分成至少 120 train、30 validation、30 untouched selection；validation 只做 early stopping，
selection 只做一次 generic/domain winner qualification。至少 60 個 train queries 必須各有兩個 query-supported、
same-casting wrong-release negatives，防止只增加容易區分的跨 casting 數量。

主要訓練假設改成單一 pairwise ranking objective，而不是再次用獨立 binary relevance 或同時搜尋 Pointwise、Pairwise、
Listwise。原因是本次要回答的問題是「同一 query 下，正確 release 是否高於相似 sibling」，pairwise score difference 與
這個排序目標更直接；同時固定單一 objective 可避免小資料 model zoo。這只是待 Owner 審核的設計，loss、hyperparameters、
data hash 與 gates 尚未授權。

V1 三個模型的 CPU p95 都約 244 ms，代表 200 ms 失敗是共同 benchmark readiness 問題，不能歸因於 fine-tuning
overhead。V2 不因結果難看就調高 SLO，而是在任何 training 前先凍結 hardware/runtime manifest 並要求 generic 通過
200 ms；若 generic 仍失敗，先修正 benchmark 環境或 inference procedure，不消耗新 labels 或訓練 checkpoint。

### 目前邊界與下一個 Gate

本輪只有 DRV2-T0 planning 完成。沒有收集資料、重跑 T5、讀取 53/20 holdouts 或 52 no-match rows、建立 candidate
pools、訓練、calibrate、final evaluate 或改 runtime。下一步是 Owner 審核五項決策：180-query 目標與 120/30/30
split、新資料來源與 rights、單一 pairwise objective、selection gates、以及新 training triples/checkpoint 的 publication
boundary。未取得該 Gate 前，DRV2-T1 及後續任務全部維持未授權。

## 2026-10-09 — DRV2-T1：完成 source 與 owner-authored query governance

### 新執行了什麼、解決什麼問題

本輪把 Owner 的「下一步」限定解讀為 DRV2-T1，建立 v2 source／authoring governance，而沒有直接產生 180 筆資料或
啟動 training。容量 audit 對 frozen 1,763-row catalog、153-positive dataset、20-negative holdout 與 T5 null result 逐一
驗證 SHA-256。全部 153 個既有 positive identities 都先排除，positive 與 negative queries 合計 173 個 hashes 進入
denylist。剩餘 1,610 catalog rows 中，1,041 筆分布於 269 個至少有三個 releases 的 casting families，超過未來 180 筆
authoring 的最低容量。

這一步解決「新資料從哪裡來、會不會偷看 v1 selection／holdout、哪些欄位可以形成 label」三個問題。V2 選擇
owner-authored synthetic route：查詢只由 frozen catalog 的 casting、year、series、series position、collector number 與
toy number 投影；source URL、filename、raw fields、collection metadata 不進入 query dataset。Color 與 edition 沒有
新增 authority，仍不得用來造 label。

### 代碼修改了哪一部分、原因與方法選型

新增 `domain_ranker_v2_governance.py` 與 CLI `pvr-materialize-domain-ranker-v2-governance`，負責 strict JSON、input hash、
T5 null lineage、identity/query denylist、multi-release family capacity、aggregate-only schema 與 permissions 檢查。
`.gitignore` 對 v2 evaluation directory 採 default-deny，只允許 authorization、authoring protocol、governance 三個 JSON；
未來 local row-level query/split 資料預設不能進 Git。

Authoring protocol 使用 salted SHA-256 identity ordering 與三個固定模板，而不是人工挑「看起來容易成功」的車款；
partition unit 固定為 casting／alias／evidence／exact-identity connected component，避免同 family 跨 train、validation、
selection。初次快速 audit 用 casefold 得到 1,040 eligible rows；正式程式改用專案 `normalize_text` 後得到 1,041，並在
materialization 前修正文檔與測試。這個差異被保留在 QA findings，沒有為了貼合先前數字而改 normalizer。

### 結果、驗證與下一步

Governance code lineage 綁定 commit `819666fad6756e06d695af2dadfab833fa7f17fc`。Authorization、protocol、governance
file SHA-256 分別為 `d42ab9415c66c24b986731292ff9a9d02f4dd46a974b57c9cd0a4b3bfa8e3fab`、
`9d56b2d2ad524159b5334b9b1a3aab321954e6153a3ae5afe5ca9935806be4fc`、
`66bbe6f660492a372e2a7dce70ba126b849913efd25c952e389886dbc73ca3d6`；governance content hash 是
`5b981e79df16510210b529a299932dc52c54b3b776808f792433f002eb7d03f8`。10 項 focused tests、Ruff、strict MyPy、CLI
check 與 whitespace gate 全綠。

Source 原始狀態仍是 `staging_only_not_evaluation_or_canonical`，rights 仍是 owner-attested、not independently verified；
governance overlay 沒有把它升格為 manufacturer truth。T1 沒有產生 queries、labels、split membership、candidate scores、
hard negatives 或 checkpoint。下一步 DRV2-T2 才能 materialize 180 筆 local-only queries 並建立 120/30/30 family-safe
partitions，而且仍需獨立 Owner Gate。

## 2026-10-09 — DRV2-T2：封存 180 筆 family-safe v2 queries 與 120/30/30 分區

### 新執行了什麼、解決什麼問題

本輪把 Owner 的「繼續下一步」限定為 DRV2-T2 Gate，從 T1 已批准的 1,041 筆容量中 deterministic 建立 180 筆
新 query。每筆選自不同 casting family，並封存為 120 train、30 validation、30 untouched selection。實際結果是
180 個 unique queries、180 個 unique exact identities、180 個 unique casting families；跨 partition 的 normalized query、
exact identity 與 casting family overlap 都是 0。這解決了 v1 將 early stopping 與 selection 混在同一小集合、以及
相同車系可能跨 split 洩漏的問題。

每個 train family 至少保留兩個符合欄位密度的 sibling releases，因此 120 筆都具備未來 exact-release negative mining
的候選容量，超過最低 60 筆要求。但本輪沒有把「存在 sibling」誤當成「已驗證 negative」：candidate labels 仍是 0，
hard-negative evidence review 保留給後續獨立任務。

### 代碼修改了哪一部分、原因與技術選型

新增 `domain_ranker_v2_authoring.py` 與 CLI `pvr-author-domain-ranker-v2-queries`。程式會重驗 T1 三份 artifact hashes、
catalog 與 153 identity／173 query denylist，再用三個固定 salted SHA-256 步驟依序選 family、family 內 target release
與 query template。選 salted deterministic ordering，而不是 Python random 或人工挑選，是為了讓同一 frozen input 必定
得到相同 pack，又不把字母順序或「看起來容易」變成 selection bias。

分區刻意採 one family per query，而不是實作更複雜的 graph splitter；因為本批資料正好能用更強約束直接保證 family
disjoint。逐筆 pack 存於 `local-t2/query-pack.json`，Git-ignored 且 mode `0600`。`.gitignore` 只額外放行 T2 authorization、
query manifest 與 split manifest；三份 public files 不含 query、expected identity、case ID 或 membership。README、spec、
decision、readiness evidence 與 Lite QA 同步更新，避免把「data readiness」描述成模型已改善。

### 驗證結果、限制與下一步

Query-pack content SHA-256 為 `149d7d867b9e270ffb805906aec64685d6823f11efcd68a59e9e74ba60134e6f`，本機檔案
SHA-256 為 `8f52043d615c1422018e5abe01670ba867c1908a6b268ce85754c71a9528d1fa`；split manifest content
SHA-256 為 `bebcaa059212081fe465d102b5a0ae1626508ea3104471bbd8311703d099b73d`。Focused T1/T2 tests、
Ruff、strict MyPy、deterministic CLI check、ignore/mode check 與 whitespace gate 全部通過。

資料仍是 owner-attested、community-catalog-relative，而不是 manufacturer/global truth；color 與 edition 沒有新增 authority。
本輪沒有產生 candidate pools、scores、negative triples、checkpoint、calibration 或 evaluation，也沒有修改 FastAPI runtime。
下一步只有 DRV2-T3：在獨立 Owner Gate 後凍結 query-only Top-25 pools 與 generic CPU latency readiness；若 generic p95
仍超過 200 ms，必須先停下修正環境／procedure，不得直接訓練。

## 2026-10-09 — DRV2-T3：封存 Top-25 pools，generic latency Gate 以 217.70 ms 擋下 T4

### 新執行了什麼、解決什麼問題

本輪把 Owner 的「幾續下一步」限定為 DRV2-T3 Gate。系統對 T2 的 180 筆 query 全部執行 query-only retrieval，
每筆凍結 25 candidates，共 4,500 candidates；train 120、validation 30、selection 30 的 expected target 都自然存在於
retrieval output，三區 miss count 都是 0，target injection 也是 0。這解決了進入 mining 前最重要的資料問題：候選池
確實能靠 query 本身找回正確 release，而不是因為系統偷看答案後補進去。

同一批 frozen pools 由 revision-pinned generic MiniLM 計分，但沒有計算 selection accuracy 或比較 domain model。
Latency 只用 validation 30 筆，固定 CPU one thread、batch 25、max length 128、3 warm-ups、3 rounds，共 90 samples。
結果 p50 為 `183.735 ms`、p95 為 `217.699834 ms`，高於預先固定的 `200 ms` 上限。因此 T3 的 pool/integrity 部分
PASS，但 latency readiness FAIL，流程依設計停在 T4 之前。

### 代碼修改了哪一部分、原因與技術選型

新增 `domain_ranker_v2_candidate_pools.py` 與 CLI `pvr-freeze-domain-ranker-v2-candidate-pools`。模組重驗 T1/T2 hash
chain、catalog、generic model config／manifest／safetensors，再使用既有 sparse、192 維 hashing dense、structured retrieval
與 RRF `k=60`。Target UUID 是 retrieval 完成後才由 frozen identity 對回 catalog，用來計算 aggregate miss；它從未傳給
retriever。這個介面隔離使「zero misses」可以被驗證，又不會發生 target injection。

Pool scorer 沿用相同 generic model、tokenizer、max length 與 Top-25 batch，不另換較快但語意不同的模型。Latency manifest
同時凍結 OS、CPU architecture、Python、Torch、Transformers、Sentence Transformers 與測量 protocol。之所以不把 200 ms
門檻調高到 220 ms，是因為 v1 已發現相同問題；再次放寬只會讓效能預算失去意義。下一個修復必須針對 inference
implementation 並證明 score/order 等價，不能利用 selection quality 選方案。

### 驗證結果、限制與下一步

Candidate-pool manifest content SHA-256 是
`da419555a6e364063a288a7ece691a330f849d361b7735809e616af4d4310777`，local pool artifact SHA-256 是
`0c889bfc06755a49ba779f2df64a4e4d87d3de676bf47063fcfcdec454022b24`，latency readiness content SHA-256 是
`7b396578d36e8c6a76fd79e447770713014716aa911661f4055898f2f0c76d86`。16 項 T1–T3 focused tests、Ruff、strict
MyPy、CLI integrity check、private mode／Git-ignore 與 whitespace gate 全部通過。逐筆 pools 保持 mode `0600` 且不進 Git；
Git 只保存 authorization、aggregate candidate manifest 與 latency report。

本輪沒有產生 hard-negative labels、沒有 training run、沒有 selection quality evaluation、沒有 calibration/final evaluation，
也沒有修改 FastAPI runtime。下一個必要工作是 DRV2-T3R：先選定一個 CPU inference repair，對相同 4,500 pairs 證明
generic score／ordering 等價，再用完全相同 90-sample protocol 重測。T3R 未經獨立 Owner Gate 前不得執行；T4 維持 blocked。

## 2026-10-10 — DRV2-T3R：以全池等價驗證完成 float32 ONNX latency repair

### 新執行了什麼、解決什麼問題

T3 的 PyTorch generic p95 為 `217.699834 ms`，所以本輪依 Owner 的「繼續下一步」只執行 T3R，沒有跳到 mining。
正式流程先把完全相同的 generic safetensors 權重匯出成 float32 ONNX opset 17，再對 T3 frozen pools 的全部 4,500 pairs
逐一比較 logits 與排序。最大 absolute logit delta 是 `1.4781951904296875e-05`，低於預先固定的 `2e-5`；180/180 個
Top-25 complete ordering 全部一致。只有等價 Gate 通過後，才執行相同 validation 30 queries、3 rounds、90 samples 的
latency 測試。

正式 ONNX Runtime 結果為 p50 `88.765583 ms`、p95 `103.654042 ms`，相較 T3 p95 減少 `114.045792 ms`，改善
`52.39%`，並通過未改動的 200 ms budget。這解決的是「共同 generic inference backend 還沒達到產品預算」，不是
domain model quality；T3R 沒有改變任何 ranker weights，也沒有建立新的學習結果。

### 代碼修改了哪一部分、原因與技術選型

新增 `domain_ranker_v2_latency_repair.py` 與 CLI `pvr-repair-domain-ranker-v2-latency`，負責 strict T3 hash chain、float32
ONNX export、全池 logit/order equivalence、ONNX Runtime CPU session、90-sample benchmark、aggregate-only public result 與
local graph integrity。`pyproject.toml` 與 `constraints/reranking-python312.txt` 加入 exact `onnx==1.23.2`、
`onnxruntime==1.31.0` 及其 transitive pins，避免未來 backend 漂移。

選型不是只看最快數字。Validation-only diagnostics 顯示 direct Transformers 與 SDPA 沒有實質改善；`torch.compile`
則因目前含空白的 workspace 路徑在 PyTorch/clang include path 上解析失敗，不具可移植性。Dynamic INT8 雖將 graph 縮到
約 23 MB 且 latency 通過，但只保留 3/180 個完整 Top-25 orderings、Top-1 也只有 175/180 相同，因此明確拒絕。
Float32 ONNX 約 91 MB，保留 180/180 ordering；graph 保持 Git-ignored/mode `0600`，Git 只保存 deterministic exporter、
exact dependencies、artifact SHA 與 aggregate evidence，避免讓履歷 repo 再增加大型 binary。

### 驗證結果、限制與下一步

T3R authorization、ONNX manifest、repair result content SHA-256 分別為
`cd19616fc9414d200e34ebd485bd43a8e8db1efae36a96371884bdb2154e3f57`、
`245d9bc88182f662f4d2b18135989305fe8d7eb9be2c4197173271329b001146`、
`f95095a1f710fedc5c8d98a2d1e72b7fda25b2d3a3c3edeaa3f5b469850b47f7`。Local ONNX SHA-256 是
`2c668e0e1bb772e0a9ba4b14e08875ec750a58e39b3ca9790e166eb927fbc42f`，重新 export 得到相同 bytes。
21 項 T1–T3R focused tests、Ruff、strict MyPy、CLI check、dependency pins、private mode/ignore 與 whitespace gate 通過。

本輪沒有讀取 selection quality、沒有 hard-negative label、training、calibration、final evaluation 或 FastAPI runtime activation。
T3R PASS 只讓下一步 DRV2-T4 具備被 Owner 獨立授權的資格；它不自動開啟 mining，更不代表 domain fine-tuning 已改善。
