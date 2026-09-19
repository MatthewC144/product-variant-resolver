# 下一階段：從「找到車型」走向「找到具體版本」

2026-09-16，Lite mode。T49.1–T49.4 儲存與可選file runtime已完成；VAR-REVIEW1也已完成第一批
11筆人工欄位審查。另有1,763筆owner提供的2023–2026 release資料已進入獨立PostgreSQL staging；
它們尚未成為已驗證版本、canonical商品或Dual RAG輸入，顏色仍全部未知。

## 現在已經能證明什麼？

目前通過的是指定105題的 casting／family 檢索：辨識哪一款車型。這不能證明同一
車型的紅色、藍色，或不同輪圈、車身圖案，已能被可靠區分成正確商品版本。
正式商品 UUID／答案仍由 canonical catalog 決定；人工知識只提供 debug 檢查證據。

## 接下來分兩條線

| 工作線 | 解決的問題 | 第一階段範圍 |
|---|---|---|
| 保存人工知識 | 資料不只放在JSON檔，未來可在PostgreSQL中持續保存、追溯與檢查 | 先用現有142筆人工知識做「匯入計畫」，不立即寫資料庫 |
| 建立版本證據 | 同casting也可能有不同顏色、年份、輪圈、圖案 | 先以現有100筆Wiki來源建立待審流程，缺少欄位仍保持未知 |

PostgreSQL在這裡是保存資料的工具，不會自動判斷資料真假。把未確認資料寫進資料庫，
也不會讓它變成正式商品答案。人工知識、待審release與canonical商品必須分開保存。

## 顏色等特徵要怎麼補？

每個特徵都要回答：觀察到的值是什麼、哪個來源說的、是否有矛盾、誰確認過。
例如「2025年紅色、輪圈A」與「2025年紅色、輪圈B」不能只因casting同名就合併。
兩筆都沒有輪圈資訊，也不能直接當成同一個版本。

目前100筆Wiki來源的顏色全是空值，輪圈與圖案也沒有專用欄位。下一步不能自行填補。
會先整理待確認項目；後续若網站存取與使用條件確認可行，才考慮以casting頁面中的
文字release資料補證據。圖片辨識／OCR不包含在這個方案裡，須另行規劃。

現有商品UUID的規則也不含輪圈／圖案。未來若需要納入，必須設計新版本規則和對應，
不能直接更改舊規則，讓現有商品UUID全部改變。

## 約3,000筆的意思

建議用100→500→1,500→約3,000筆「去除重複後的真實來源release資料」逐批擴充。
同時分開報告待審、衝突、已確認版本、正式商品等數量。
約3,000筆來源資料不等於約3,000個已驗證商品；不會拿合成資料或重複列補數字。

目前網站頁面與授權條件尚未完成本次確認；一般API建議不等於該網站允許蒐集。
新蒐集前須確認來源使用條件、頁面／revision與請求上限；遇到存取拒絕就停止。

## 目前實作與後續確認

依spec-dev-loop的Lite流程，先確認[需求](../specs/human-knowledge-persistence-and-variant-roadmap/requirements.md)，
再確認[設計](../specs/human-knowledge-persistence-and-variant-roadmap/design.md)與
[任務](../specs/human-knowledge-persistence-and-variant-roadmap/tasks.md)。完整後續方案尚未取得三次獨立確認。
你在詳細草案說明後指示「請幫我執行」，本次僅依此執行第一個本機任務，不推定授權整份後續方案。
第一個任務已讀取本機142筆資料、產生[可檢查的匯入計畫](../reports/human-knowledge-snapshot-v1/report.md)；
不爬網站、不寫PostgreSQL，也沒有增加142筆正式商品。
其後你指示「執行測試」，T49.2 已在另建的臨時 PostgreSQL 匯入並讀回142筆人工知識，
證明失敗整批回滾、重複匯入不變、商品資料前後一致。測試庫已清理，未部署正式資料庫。
詳見[SQL 測試證據](evidence/t49-2-human-knowledge-postgres.md)。新的選用storage profile
與測試協議草案已寫好，見[新手說明](HUMAN-STORAGE-PROFILE-GUIDE.md)。先確認需求、
設計、任務與預算，再freeze／實作，才考慮讓查詢服務接到資料庫；保存資料不等於用它
判斷正式版本。本次沒有接API或新增測試結果。
其後的資料庫測試、額外來源蒐集與正式商品promotion，都有各自的明確邊界。

## VAR-PLAN1已完成：先把不知道的內容誠實列出來

目前100筆來源資料都已放入[欄位證據計畫](../reports/release-field-evidence-review-v1/plan.md)。
每筆都有獨立的來源ID與觀察ID；這些ID只表示「看過哪一列資料」，不是商品UUID，也不表示
兩列是同一個版本。顏色、輪圈、tampo、edition與包裝欄位仍全部是unknown。45筆雖然寫有
2nd／3rd Color或Zamac，但那只能證明來源有這段文字，不能得知實際顏色或其他實體特徵。

第一批建議人工看4個完整families、共11列：Lamborghini Huracán Sterrato、Subaru BRZ、
Nissan Skyline 2000GT-R LBWK和'87 Audi quattro。選它們是因為可以一次看到new／merge／hold、
不同series、Zamac提示與完全沒有variant note等問題，不是因為它們比較容易得到正確答案。
目前沒有任何欄位被人工確認，100筆仍全部held。下一步應先由owner看這11筆的逐欄證據；
若要再讀網站，仍須另外完成VAR-PLAN2的存取權利與請求預算確認。

現在[batch01審查表](../reports/release-field-review-batch-01/owner-review.md)也已準備完成。表中逐列
顯示11筆原始值，並把同family內10種兩兩關係列成必答題。只有三個既有文字主張能安全連到
特定toy number；它們仍只是候選證據。尤其Nissan來源網址含顏色文字，但既有觀察摘要沒有
明說顏色，因此不能從網址自動補值。所有決定欄現在都是空白；下一步需要專案owner確認。

Owner已確認第一組Lamborghini的保守結果：HYW93名稱／toy number／2025年份成立；HYW93、
HYY45、JBB86視為三個不同release；三列的顏色、輪圈、tampo、edition與包裝仍未知。這只完成
batch01的1/4，下一組是Subaru BRZ。

Owner也已確認Subaru的保守結果：HYW99、HYY12、JBB55是不同release；HYY12只確認來源文字
`2nd Color - Zamac`，不把Zamac當實際顏色，也不自動對應舊Walmart Exclusive variant。
三列physical fields仍未知。

Owner接著確認Nissan的保守結果：只把獨立來源明確支持的HYX54名稱、toy number、2025、
HW J-Imports與Tooned工具血統升為confirmed；HYW79、HYY30、HYX54是不同release，三列共15個
physical fields仍未知。網址中的`metalflake-blue`不是來源主張，不能當成顏色。相同display name
仍可能指Tooned或非Tooned工具，所以family繼續held，不建立canonical UUID。Batch進度3/4，
下一組是'87 Audi quattro。

Owner最後確認Audi：JBC35的名稱、toy number、2025與`Super Treasure Hunt`edition有獨立來源支持；
HYW72與JBC35是不同release。HYW72的五個physical fields，以及JBC35除edition外的color、wheel、
tampo與packaging仍未知。至此batch01完成4/4：共67個欄位決定（13 confirmed、54 unknown）與10個
different-release pairs，canonical changes為0。這只是完成審查，不等於已把11列promotion為正式商品；
下一階段VAR-PLAN2仍須先確認來源存取權利、revision與請求預算，才能收集更多真實資料。

## VAR-PLAN2草案已完成：目前Fandom自動收集被阻擋

2026-09-16的公開規則查驗發現兩件不能混為一談的事。Fandom一般授權頁表示wiki文字通常採
CC BY-SA3.0，可在遵守署名與相同授權條件下重用；但目前Terms of Use（公開結果標示最後修訂
2025-12-19）同時禁止沒有事先明確書面許可的自動化存取／scraping。文字授權回答「取得內容後
如何重用」，平台條款回答「可不可以用程式取得」，前者不能代替後者。

因此[機器可驗證的source gate](../reports/real-catalog-source-expansion-v1/plan.json)目前設定為blocked：
collection false、permission null、approved endpoints空白、已執行與各milestone request budget均為0，
圖片/OCR也禁止。100筆只代表既有離線baseline；500、1,500與約3,000筆都還沒開始。

下一個外部動作不是啟動crawler，而是由owner依
[許可指南](FANDOM-SOURCE-PERMISSION-GUIDE.md)向Fandom取得針對本專案、endpoint、用途、規模、
保存與再發布條件的書面同意。若取得，再透過獲准方式確認Hot Wheels Wiki當下license、robots與
endpoint，凍結頁面/revision清單，然後再次請owner批准最多3個GET的canary。沒有回覆、拒絕或範圍
不清楚時都必須維持blocked；不能改用proxy、browser impersonation、CAPTCHA繞過或搜尋快取補資料。

## 本機HW data擴充已完成：1,763筆只進入待審staging

Owner後續提供了四份本機Excel，不需要重新連線或爬取網站。系統以固定檔名與SHA-256讀取2023–2026
資料，嚴格驗證19欄結構和每年445／441／440／437筆，再建立可重現的normalized snapshot。原始
`HW data/`與完整normalized bundle都加入gitignore，避免把沒有再發布權證明的XLSX或1,763筆衍生列
推到公開repo；可提交的只有不含來源列的aggregate manifest與report。

為避免gitignore造成公開clone「沒有私人XLSX就整套測試失敗」，測試層另建相同19欄與1,763筆分布的
synthetic workbooks。Fresh clone可通過17項portable tests，僅2項需要owner原始bytes的integration明確
skip；本機有資料時19/19全過，完整套件629/629全過。Committed public manifest的batch ID、來源檔
checksum與aggregate筆數仍被驗證，實際CLI也仍只接受`HW data/`四個直接檔案，因此portable test不會放寬runtime來源邊界。

Alembic migration `0003`新增獨立的`release_source_batch`與`release_source_record`，沒有把資料混進
canonical商品、搜尋／embedding或`hk_*`表。本機project PostgreSQL volume現保留1 batch／1,763筆，
包含1,763個唯一source IDs、1,763個唯一toy numbers、678個casting names、1,763個`NULL` colors和
0 canonical links。第一次匯入為`inserted`，相同資料第二次為`unchanged`；可安全重跑而不重複新增。

這次擴充解決的是「把owner已提供的大批release觀測資料安全保存並可追溯」，不是「已能辨識每台車的
顏色與具體版本」。下一步仍是建立人工／來源證據充分的promotion流程；顏色可在取得可靠row-level
證據後再補，不能從`2nd Color`、網址或常識推測。新的網路蒐集仍受上方VAR-PLAN2 source gate阻擋。

## 本機casting review queue已完成：676個群組全部維持待審

下一個離線步驟已把1,763筆staging observations依正規化brand/casting建立676個review clusters。來源中有
678個raw casting labels；其中兩組因重音或標點折疊到相同key，系統保留所有原字串並標成
normalization collision，而不是靜默宣告同一identity。

與現有兩個catalog來源做exact-key比較後，1個cluster同時有synthetic fixture與human draft候選，2個只有
synthetic fixture候選，40個只有human draft候選，633個沒有exact候選；對應observations為1／8／126／
1,628。這些都是review routing，不是canonical truth。676個clusters仍全部unresolved，approved links、
canonical promotions、reviewed colors、SQL writes、network requests與Dual RAG changes都為0。

完整queue包含來源IDs、toy numbers、raw labels與candidate IDs，因此只存在gitignored local data；公開repo
只保存`reports/local-release-casting-review-v1/`的aggregate counts與input/private-queue hashes。下一步應從
queue建立小型owner decision batch，逐項記錄可歸屬證據與決定。不能把43個exact candidate clusters一次
全部promote，也不能在這個階段補顏色。

## Casting owner review batch 01已凍結：5題等待owner回答

第一個owner review packet從private queue固定選出5個高優先群組，共涵蓋18筆source observations。組成為
1個cross-source exact candidate、2個normalization collisions與2個synthetic-fixture-name candidates。
Packet只整理來源年份、toy number、collector number、source label、series與literal variant note；所有
decision都是`null`／`pending_owner`，color decision、approved links與canonical promotions都是0。

每題只接受`same_review_family`、`keep_separate`或`unknown`。第一個值只表示review層級可視為同一casting
family，不代表同一release variant、不選定synthetic fixture中的任何product，也不確認color。完整問題與
labels留在gitignored local packet；公開repo只有selection counts與packet/upstream hashes。下一步必須等待
owner逐題回答，再另外建立append-only decision events；不能從本次測試PASS推導答案。

第一題已由owner明確回答`same_review_family`，並以packet-bound append-only event保存在private ledger。
它只確認一個review-level family relationship；沒有選定release variant、synthetic product、color或canonical
UUID。第二題也由owner以題號前綴明確回答`same_review_family`；系統先驗證`2.`與目前題號一致，再保留
完整verbatim response。第三題的normalization-collision group也獲owner確認為同一review family，並由
既有append-only順序綁定到question 3。公開進度為3/5 recorded、2/5 pending與3個same-review-family decisions，
完整問題與verbatim responses仍留在gitignored local artifact。第四題的fixture-name candidate也獲owner
確認為同一review family，且由append-only順序綁定到question 4。公開進度為4/5 recorded、1/5 pending與
4個same-review-family decisions。第五題的fixture-name candidate也獲owner確認為同一review family，讓
batch 01達到5/5 recorded、0 pending與5個same-review-family decisions。這只關閉owner-answer gate；下一個
階段必須另外設計可稽核的family materialization，不能直接建立canonical UUID、補color或改寫release rows。
