# 下一階段：從「找到車型」走向「找到具體版本」

2026-09-15，Lite mode。T49.1–T49.4 儲存與可選file runtime已完成；正式PostgreSQL rollout與
release版本辨識尚未完成。VAR-PLAN1現已建立100筆離線欄位證據計畫，尚無人工欄位決策。

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
三列physical fields仍未知。Batch進度2/4，下一組是Nissan Skyline 2000GT-R LBWK。
