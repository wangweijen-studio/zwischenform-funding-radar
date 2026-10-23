# ZWISCHENFORM Funding Radar

網站：https://wangweijen-studio.github.io/zwischenform-funding-radar/
駐村：https://wangweijen-studio.github.io/zwischenform-funding-radar/residencies.html

## NCAF 自動擷取

每日 07:15 UTC（柏林夏令 09:15、冬令 08:15）由 GitHub Actions 執行：安裝免費 PDF 解析器 → 13 項回歸測試 → 擷取官方 HTML／PDF → 驗證 JSON → 檢查來源連線 → 提交公開 JSON → 部署 Pages。排程可能延遲；不活躍的公開儲存庫可能被 GitHub 暫停排程，可手動恢復。

- 從 NCAF 補助廣場動態發現相關類別，不寫死補助日期或金額。
- 擷取各類別官方收件表、最新一頁補助消息及官方 PDF 申請辦法。新聞頁範圍是最新一頁；沒有宣稱涵蓋全部歷年公告。
- 僅追蹤視覺藝術、多元／跨域藝術、文化資產、視聽媒體、藝文環境、海外藝遊、共融、策展、藝評及國際文化交流。這是主題篩選，不表示已判斷你的國籍、居留或組織資格。
- 將申請開始、截止時間、辦法年度、金額／經費條件及資格分別保留。金額不固定時保留官方經費條件，不杜撰統一數字。
- 名單／結果公布、採購與無關報名不當成新徵件。
- 同一計畫的同一收件期使用穩定 ID；公告與期程相符時合併其連結。重跑不增加相同紀錄。
- 未知日期、過期辦法、金額或資格缺漏一律待人工核實。未開放及已截止明確分開。
- 日期只有年月日時，儲存 date 精確度，不發明時分；截止當天若缺少精確時間，保守停止標示開放。只有官方當期 PDF 明確載明線上截止時分才加入時分，時區 Asia/Taipei。
- 來源失敗會保留舊資料並改為待核實，不更新舊驗證時間；超過七天的驗證即使 JSON 未更新，前端也不標示開放。
- 視覺設計 CSS 不變。數據透過既有卡片顯示；駐村與一般補助保持分開。

## 公開資料

`data/opportunities.json`：公開補助與駐村候選。
`data/extraction_status.json`：真正公告擷取狀態、失敗原因、來源 URL 與回應 SHA-256。
`data/scan_status.json`：連線狀態；不作為徵件核實依據。

`verification_status=verified` 且 `status=open` 需要本期官方收件證據、開始日期、未過期截止、七日內驗證及已核對的資格和金額條件。缺漏欄位顯示待人工核實；申請費不推定免費。官方開放狀態不表示個人資格已符合。

駐村使用 `type=residency`，資助欄位 `support.stipend`、`artist_fee`、`accommodation`、`production`、`travel` 分開儲存；開放駐村至少需要可核實的生活津貼、藝術家費或製作經費。尚未接入國際駐村擷取器。

## 隱私與費用

私人申請進度只存目前瀏覽器 localStorage，不會上傳 GitHub，也不跨裝置同步。請勿提交私人資料、備份、金鑰或憑證。Pages 打包只允許兩個 HTML 與四個公開 JSON。原 ZIP 備份留在本機，不上傳。

不使用付費 API、資料庫、主機或自訂網域。GitHub Actions 使用公開儲存庫的標準 ubuntu runner。

## 本機測試

```sh
python -m pip install -r scripts/requirements.txt
python -m unittest discover -s scripts -p 'test_*.py' -v
python scripts/collect_ncaf.py
python scripts/validate_data.py
python scripts/build_site.py
python -m http.server 8765 --directory _site
```

## 後續來源

文化部、柏林 Senatsverwaltung für Kultur、Fonds Soziokultur 與有現金資助的國際駐村，依序獨立核對格式、實作及實測後接入。現有首頁連線監測不等於這些公告擷取器已完成。

