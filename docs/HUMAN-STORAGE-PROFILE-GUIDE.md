# 下一步：讓服務選用人工知識儲存來源

2026-09-15，Lite mode。T49.3需求、實作與限定驗證均已完成：HSP-1封存輸入，HSP-2新增
可選storage app，HSP-3證明file／PostgreSQL結果一致與失敗安全，HSP-4完成本機成本測量。
原本API仍未自動切換，PostgreSQL測試庫已清除；T49.4封裝／rollout與3,000筆擴充尚未開始。

## 我們現在要解決什麼

T49.2 證明142筆人工知識可以安全存進資料庫；測試庫已清理，所以現在不是一直運作的
資料庫服務。T49.3 接著確認：若服務選用資料庫中的知識，結果是否與讀檔案一致，
資料壞掉時是否正確拒絕回答，以及新增資料庫驗證要花多少時間。

| 路徑 | 人工知識來源 | 目前狀態 |
|---|---|---|
| 原有 API | 原有本機檔案／原有設定 | 不修改、不自動切換 |
| 新 file-reference profile | 已固定版本的142筆 plan | 已通過正確性、失敗與成本驗證 |
| 新 PostgreSQL profile | 隔離庫中的同一份142筆 snapshot | 已通過實驗驗證；測試庫已清除 |

Profile 可以理解成「明確選用的一組設定」，不是另一套商品真相。Snapshot 是指定版本
的整份知識，不能選最新一份就算數，也不能少幾筆而悄悄補成另一個版本。

## 資料庫與 RAG 各做什麼

PostgreSQL負責保存、提供完整知識；服務啟動時驗證後在記憶體建索引，檢索仍使用原有
casting identity gate、hashing embedding、RRF。這一步不是把向量 TopK 搬到 SQL。
Dual RAG 的兩路仍分開：canonical RAG決定正式商品答案，human RAG只提供debug證據。
顏色／輪圈／tampo 的正式版本證據仍是後续release review，不會從casting結果自行推定。

提議每次 `/health` 或有效 `/resolve` 前，再唯讀核對完整snapshot。若只啟動時讀一次，
後來資料庫失效／被改，記憶體還有舊資料，服務就可能仍顯示健康。因此草案選擇完整性
守門：壞掉回503，不切回檔案或最新snapshot；恢復資料後也要重啟，避免靜默恢復到不同版本。
代價是每個請求多一次SQL／network工作，所以HTTP測試必須包含它，不能只報記憶體檢索時間。

## 怎麼測，而不是怎麼調參

使用原有199筆development cases，比較新file／DB兩路每一筆候選的順序、分數、ID／UUID、
typed內容與work counters；正式nondebug商品結果也要與原API完全相同。這不是新holdout，
不重跑封存final105題，不重新選floor／weight，不把相同結果升級成正式版本準確率。

同時測啟動缺資料、運作中DB斷線／被改／少文件是否503；app只用SELECT權限，不能寫入
或修復資料。效能分開量啟動、snapshot驗證、完整HTTP與純human檢索；草案提出時間上限，
須先確認並封存才測，不在看到數字後改門檻。全部錯誤與未命中也保留，不靠重跑換結果。

## 本次與後續界線

本階段交付[需求](../specs/human-storage-profile-development/requirements.md)、
[設計](../specs/human-storage-profile-development/design.md)、
[任務／測試步驟](../specs/human-storage-profile-development/tasks.md)與協議草案。
需求、設計、任務與預算已依序確認，見[確認紀錄](../specs/human-storage-profile-development/approval.md)。
HSP-1至HSP-4均已完成。曾建立真實但一次性的隔離DB與唯讀角色，測試後已精確清除；
沒有新增正式DB、UUID或部署。T49.4封裝驗收與約3,000筆真實資料擴充仍未完成。

## 已確認且完成：任務與測試時間上限

HSP-1先封存已確認的規格、資料版本與測試協議，防止看到結果後更換資料或標準。
HSP-2再新增讀檔案／資料庫的profile與API入口，先用單元及模擬測試驗證正常、失敗與
既有API契約；模擬測試不代表真實PostgreSQL已通過。

HSP-3需要另外明確批准新的隔離測試環境，才建立一次性資料庫與唯讀角色。
用固定199題各跑file／DB一路，另199次原API作正式答案參考；逐筆比對排序、分數、
ID及資料內容，要求199/199一致。零重試、零正確性預熱，未命中與錯誤原樣保留；
另外驗證缺資料、斷線、資料被改、503鎖定及讀取角色不能寫入，清理僅限新建資源。

HSP-4依封存協議量測成本、完成QA與日誌，不能為了過關而修改門檻或重跑挑結果。
每一路啟動取5個獨立程序樣本；HTTP與純檢索各預熱3次，再各取199個樣本，單一worker、
循序請求。原API的199次只是正確性參考，不是新的效能基準。

| 測量部分 | 已確認p95上限 | 計時範圍 |
|---|---|---|
| profile啟動初始化 | 5,000毫秒 | 驗證知識與建立索引；不含Python匯入、程序／Docker啟動及DB建立 |
| 每次snapshot完整性核對 | 150毫秒 | 新adapter記錄的完整核對工作 |
| 完整HTTP請求 | 250毫秒 | 含核對、SQL／網路、檢索、回應序列化與解析 |
| 純human檢索 | 25毫秒 | 已建好索引與抽取訊號，不含SQL、核對或HTTP |

p95是將耗時排序後約95%樣本不超過的數值，採nearest-rank。啟動只有5個樣本，
其p95等於最慢樣本，不代表可靠的長期統計。這些是142筆知識的本機工程驗收門檻，
不是已達成的結果、正式服務保證或3,000筆規模承諾；「預算」指耗時上限，不是金錢。
任務／預算已確認，HSP-3及HSP-4也在後續明確指示下完成；這仍不等於正式部署授權。

封存可以理解為「測試前先保存考卷版本、規則與資料指紋」，不是已完成測試。
新封存共8個檔案：原需求、設計、任務與協議草案副本，以及確認紀錄、已批准協議、
宣告的profile合約與manifest。Manifest記錄26個輸入指紋；不複製一套新的142筆商品資料。
檢查腳本會拒絕資料改動、缺檔、多檔或覆寫。API程式與執行環境仍待實作／固定，
所以封存明確標示不能產生真實測試輸出，詳見[驗收證據](evidence/t49-3-input-freeze.md)。

## HSP-2現在完成了什麼

新`human_knowledge_storage_profile.py`像「嚴格的入場檢查員」：profile多欄、少欄、重複
JSON key、錯版本／SHA、未固定映像，或PostgreSQL名稱不是隔離測試格式，都直接拒絕。
檔案模式每次核對plan與12個來源；DB模式透過既有repository讀整份142筆，而不是只問
「資料庫還連得上嗎」。啟動時將同一142筆typed資料建立記憶體索引，之後不重建索引。

新`human_knowledge_storage_app.py`像「原API外面的安全門」。有效`/resolve`才先核對來源，
再呼叫原本ResolverService；錯誤JSON、內容類型、空標題、超長標題或禁用debug仍保留
400／415／422，沒有先碰儲存層。核對失敗後將服務鎖為not ready，health及後續有效resolve
都是503，來源恢復也不自動重試。`/health`新增獨立版本狀態，原`database`欄仍只代表
canonical backend。正式nondebug response沒有storage欄，human仍只在debug顯示候選證據。

55項聚焦測試與544項完整測試通過，但DB是fake reader；它證明程式怎麼呼叫、怎麼失敗，
不證明PostgreSQL帳號權限或網路。42個來源在candidate2封存；candidate1因缺health欄被保留
而不覆寫。在HSP-2當時，候選2仍`ready=false`，缺兩個runtime image IDs、實際隔離DB名稱
與SQL run批准；這段是當時的階段界線。後續HSP-3／HSP-4已完成，但仍不是正式部署。
詳見[HSP-2證據](evidence/t49-3-storage-adapter.md)。

## HSP-3與HSP-4最後證明了什麼

HSP-3把固定199題分別交給file與真實PostgreSQL profile。兩路候選順序、分數、型別、
UUID、payload與work counters全數相同，原canonical正式答案也沒有變；reader只能SELECT，
資料缺失、被改或連線中斷會503且同一process不會偷偷恢復。這證明更換「保存位置」沒有
更換Dual RAG的數學或答案權限，詳見[SQL正確性證據](evidence/t49-3-storage-profile-sql.md)。

HSP-4再量「這個安全做法要花多久」。每組5次初始化、3次預熱後199次真實Uvicorn HTTP
與199次純human retrieval，先保存raw再評分。p95如下；斜線前是file，後是PostgreSQL：

| 測量部分 | file／PostgreSQL p95 | 已確認上限 | 結果 |
|---|---:|---:|---|
| profile初始化 | 271.142／300.175 ms | 5,000 ms | PASS |
| 完整snapshot核對 | 34.204／42.773 ms | 150 ms | PASS |
| 完整loopback HTTP | 38.645／46.163 ms | 250 ms | PASS |
| 純human retrieval | 2.311／2.306 ms | 25 ms | PASS |

第一次HSP-4嘗試在任何計時樣本產生前失敗，原因是固定runner映像沒有`httpx`。改用Python
內建`urllib`後建立全新的v2 freeze再測，不下載依賴、不換映像、不改門檻，也沒有重跑
挑較快結果。詳見[成本證據](evidence/t49-3-storage-profile-cost.md)。這些數字只代表本機
ARM64、142份文件、單worker及concurrency1，不是3,000筆、正式流量或SLA。
