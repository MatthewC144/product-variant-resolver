# 下一步：讓服務選用人工知識儲存來源

2026-09-14，Lite mode。以下是 T49.3 草案，還沒有改 API、部署資料庫或執行新測試。

## 我們現在要解決什麼

T49.2 證明142筆人工知識可以安全存進資料庫；測試庫已清理，所以現在不是一直運作的
資料庫服務。T49.3 接著確認：若服務選用資料庫中的知識，結果是否與讀檔案一致，
資料壞掉時是否正確拒絕回答，以及新增資料庫驗證要花多少時間。

| 路徑 | 人工知識來源 | 目前狀態 |
|---|---|---|
| 原有 API | 原有本機檔案／原有設定 | 不修改、不自動切換 |
| 新 file-reference profile | 已固定版本的142筆 plan | 提案，作為比較基準 |
| 新 PostgreSQL profile | 新隔離庫中的同一份142筆 snapshot | 提案，尚未接上 API |

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

這次交付[需求](../specs/human-storage-profile-development/requirements.md)、
[設計](../specs/human-storage-profile-development/design.md)、
[任務／測試步驟](../specs/human-storage-profile-development/tasks.md)與協議草案。
需求已確認，見[確認紀錄](../specs/human-storage-profile-development/approval.md)。接著確認設計，
再確認任務與預算，才freeze並開始實作。沒有新增DB、角色、資料、
UUID或正式部署；T49.3完整實作、T49.4封裝驗收與約3,000筆真實資料擴充都尚未完成。
