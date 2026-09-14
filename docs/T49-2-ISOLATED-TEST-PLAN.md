# T49.2 隔離資料庫方案

2026-09-14，Lite mode。Owner 在此方案說明後指示「執行測試」，授權本次限定隔離測試。
這不是整份後續 T49.3／蒐集／正式部署方案的確認，也未捏造三次獨立 G1 確認。

## 為什麼不直接用原有 PostgreSQL

原有 `docker-compose.yml` 的 postgres service 使用 `pvr-postgres-data` 持久化 volume，
並可開放本機連接埠。T49.2 不應假定這裡沒有使用者資料，也不能透過 reset volume
取得乾淨環境。因此另建可丟棄的隔離環境，而不修改既有 compose 或 canonical0001 migration。

唯讀 Docker inventory 確認目前沒有執行中的容器，本機已有 `pgvector/pgvector:pg16`
映像（short image ID `131dcf7ff6a9`）。這不代表既有 stopped containers／volumes 沒有資料；
方案不使用它們。執行時再次解析並記錄完整 image ID，不預設更新或下載映像。

## 提議的限定範圍

另建具本次專屬名稱與 ownership label 的 internal Docker network、PostgreSQL container
與測試 runner；名稱碰撞即停止，不接管既有資源。不 publish host port，不掛載既有
database volume，不使用使用者的 `.env`／資料庫 URL。資料放在新容器 tmpfs，測試完成
後只清理本次建立且驗證 ownership 的容器／network，保留 repo 裡的驗證報告。
tmpfs 是可丟棄環境，不是資料持久性／斷電復原測試；實際工作資料庫仍未選定。

在新庫內執行原有 canonical migration，加入新的 additive human snapshot migration。
用既有 120 筆 synthetic canonical fixture 建立**僅限測試庫**的前後比對基準，
再將已封存 plan 的 100 provisional + 42 review family 匯入独立 human snapshot tables。
這不是往使用者商品資料庫寫入 120 或 142 筆正式商品，也不重新建立 canonical UUID。

新的 persistence namespace 必須明確限於 human knowledge 保存／測試；原始 projection
與其 `postgresql_ingestion` exclusion 不修改或解除。舊來源限制禁止直接 repurpose 成
canonical ingestion；新 importer 只能接受完整固定來源 snapshot，不能任意匯入 held family
或把 family 審核當成 release truth。API/default/v4 profile 不在本次變更。

## 實作與驗收（確認後才執行）

新增 snapshot/document tables 與 repository，保存來源指紋、完整 typed payload、原始
provenance、counts/checksum/import metadata；embedding/runtime integration 留待 T49.3。
一個 snapshot 的 142 文件在同一 transaction 內寫入，任一失敗全部 rollback。
同 ID／內容完全相同的重複匯入必須驗證後 no-op；同 ID／不同內容或不完整既有資料
必須拒絕，不以 upsert 覆蓋修復。讀回全部文件與固定 plan 做 type-sensitive 精確比對。

實際 SQL 驗證需證明142roundtrip、重複匯入 no-op、collision rejection、真實 transaction
rollback，以及全部 canonical tables 前後 rows／IDs／timestamps 完全不變。單元測試、
完整回歸、QA／AI artifact evidence 與敘事 project log 一併更新。未通過不宣稱 T49.2 完成。

本方案原先等待確認；owner「執行測試」後，僅執行以上測試環境與限定寫入／清理範圍。
實際結果另見 SQL evidence／project log，不以這份方案自身當作 PASS 證据。
網站蒐集、約3,000真實資料、正式DB／既有volume操作、v4 rollout、variant promotion 均不包含。
