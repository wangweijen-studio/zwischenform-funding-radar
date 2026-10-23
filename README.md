# ZWISCHENFORM Funding Radar

現有網站：https://wangweijen-studio.github.io/zwischenform-funding-radar/
獨立駐村網址：https://wangweijen-studio.github.io/zwischenform-funding-radar/residencies.html

## 介面與私人資料
保留原始 CSS、色彩、字體、卡片及統計排版；五個分頁為總覽、補助、駐村、我的申請、來源。
私人資料只在目前瀏覽器 localStorage；不傳送 GitHub、不自動跨裝置同步。舊的 funding-radar-records 會保留，讀取後遷移到 funding-radar-private-v2。損毀資料不會被空資料覆蓋。
三個個人狀態互斥；已送件改狀態需確認，送件歷史及結果保留。支援本機 JSON 匯出／預覽合併匯入、文件、任務、資格依據、各幣別資金組合與日期衝突檢查。
一次性私人匯入檔必須由使用者在本機選擇；公開程式不包含個人已申請紀錄。
清除瀏覽器資料可能遺失私人紀錄，請先匯出。文件僅存名稱、備註、期限及外部連結。

## 每日擷取
GitHub Actions 每天 Europe/Berlin 09:15 執行，使用 timezone 處理夏令時間；排程可能延遲或被 GitHub 暫停，頁面顯示實際時間，可在 Actions 手動執行。
執行順序：免費 PDF parser → 22 項私人狀態與規劃測試及 11 項官方連結測試 → 39 項 Python 擷取測試 → update_all.py → validate_data.py → 提交公開 JSON → allowlist 打包 → GitHub Pages。
HTTP client 使用明確 User-Agent、官方 HTTPS 網域 allowlist、robots.txt 檢查、至少一秒請求間隔與大小／逾時限制。重新導向逐一核對官方網域與 robots；禁止的入口不繞過。

每個來源的範圍、啟用設定與模組在 data/sources.json。完整／部分成功、被阻擋、失敗、最後嘗試與最後完整成功都在 data/extraction_status.json。HTTP 可連線不代表徵件已核實。
- NCAF：相關補助類別全部收件表、官方 PDF 與最新一頁補助消息。日期、資格及本期金額條件完整時才可開放。
- 文化部：只讀主站最新補助標題；完整辦法入口 grants.moc.gov.tw 的 robots 禁止讀取，保留待人工核實。
- Fonds Soziokultur：解析本期明確日期、金額與團體資格、共同補助限制；個人不可單獨申請。
- Berlin Senatskultur：相關方案索引及有限細節頁；另辨識 IMPACT 官方 2027 結果連結。未辨識到結果不代表官方未公告。
- 柏林十二區、臺北、臺中：有界線的官方文化／補助入口探索；非完整全站爬取。解析失敗或無可辨識公告時顯示問題，不視為沒有機會。
- Solitude、Camargo：分開核對津貼、工作室、住宿與在場要求；未核實本期申請日期不標開放。Camargo 的補件截止不當成申請截止。
- Kunstfonds、Kulturstiftung des Bundes：官方單一方案文字及明確年度截止日期；未完成完整本期驗證時保留人工核實。
- Culture Moves Europe：歐盟本期官方語意日期、分年滾動批次與日額資助獨立解析；下批日期未載時分時不推定午夜。
已加入洪建全基金會藝術支持方案與台新基金會最新消息；提名制不當成公開申請。仍須逐來源完善區級公告格式、臺灣地方及更多私人藝術基金、更多國際來源、個別資格與官方結果名單。

## 公開資料及可信度
opportunities.json 是公開官方候選，不含個人狀態；changes.json 記錄新公告、日期、資格、金額及狀態變動。
未知日期／金額不得補填；週期性日期不得推定為本期開放。過期或超過七日未核實的資料不標開放。失敗保留舊資料並降為待確認，不刷新舊 verified_at。
駐村 type=residency；support.stipend、artist_fee、production、travel 為現金／費用支持，accommodation、studio 為實物支持。月津貼不當成總補助金額。
主題適合程度只是可解釋的文字規則推論，不能當成個人資格核實。金額按幣別分開；待審／未通過不算已取得，通過但核定金額未知也不補零。

## 本機驗證
```sh
python -m pip install -r scripts/requirements.txt
node scripts/test_core.cjs
python -m unittest discover -s scripts -p 'test_*.py' -v
python scripts/update_all.py
python scripts/validate_data.py
python scripts/build_site.py
python -m http.server 8765 --directory _site
```
打包僅包含兩個 HTML、兩個公開 JS 與五個公開 JSON。原始 ZIP、工作備份、私人匯入檔、憑證及文件一律不放進 _site 或公開儲存庫。
不使用付費 API、資料庫、主機或自訂網域；使用現有公開儲存庫及標準免費 runner。

臺北市改讀文化局藝文補助資訊平臺；臺中視覺藝術專區的 robots 重新導向採同官方網域的 HTTPS 對應位置，未發送 HTTP 請求。區級入口已補入區公所正式連結的文化網站；名單與金額、日期仍分別核實。

已擷取的官方頁面會檢查明確取消／重新開放語句，並保存變更紀錄。條件句不當成取消；國藝會同頁多期別若無法從取消語句確認對應期別，只標示待人工核實。取消後缺少公告不代表重新開放。這是有限範圍的公告識別，不能取代人工閱讀所有附件。


## 私人申請與官方資料連結
「我的申請」可手動填主辦、年度、類型、公告 ID 及官方連結；未知留空。新增或匯入不會自動確認連結。系統依官方 URL／公告 ID、具識別力的名稱、主辦與年度提出候選，明確不同年度排除；只有一般「補助／Förderung」標籤不算同一方案。年度未知會清楚警示並要求人工確認。
開啟「編輯／文件」→「官方資料連結」→核對候選→「檢查並確認連結」。確認前不改私人紀錄；兩筆不同 ID 的申請可以連到同一公告。公開資料每次載入及網頁保持可見時每 15 分鐘重讀，重新計算候選；已確認的連結依官方 ID 讀取新公開欄位，不覆蓋私人欄位。找不到公告則顯示歷史快照與待核實警示。
私人備份保留 officialLink、officialSnapshot；現有 version 2 紀錄相容，沒有連結的舊資料不被覆蓋。三筆既有申請由本機私人檔案經預覽、確認匯入，公開 JS／JSON 不含三筆送件內容。
IMPACT 結果必須在官方結果標題同時確認 IMPACT、2027 與結果語句，並取得唯一正式公布日期，才顯示結果已公布；2026 標題加 2027 導覽不算。找不到完整證據只保留待核實，沒有推播或電子郵件通知。官方名單不會改變個人結果。
新增測試：node scripts/test_linking.cjs。官方欄位仍可能只有部分已讀取，連結不代表已符合個人資格。IMPACT 的 2027 方案與 2026 送件期限分開；NCAF 海外藝遊 2026 收件與 2027 執行分開，預定面談不當成最終結果日。
