# ZWISCHENFORM Funding Radar

保留原 index.html 深綠設計；私人申請紀錄只存目前瀏覽器 localStorage，不跨裝置同步。請勿上傳私人申請、備註、瀏覽器匯出檔或憑證。清除瀏覽器資料會遺失紀錄。

## GitHub Pages
1. 確認後建立公開 repository `zwischenform-funding-radar`，預設分支 main。
2. 上傳本資料夾內容（包含 .github），不要上傳原 ZIP、work 或私人檔案。
3. Settings → Pages → Source: GitHub Actions。
4. Actions → Funding Radar daily source checks and Pages → Run workflow。
5. 確認 refresh、deploy 成功並打開部署網址。

排程每天 07:15 UTC（柏林夏令 09:15、冬令 08:15），GitHub 可能延遲或暫停不活躍儲存庫的排程。每日更新由同一工作流程直接部署，避免 bot commit 不觸發 Pages 的問題。

## 目前能力
只檢查 sources.json 既有 5 個官方來源是否可連線；**沒有**完成公告擷取、通知、柏林 12 區或完整國際駐村追蹤。追蹤範圍卡片代表目標，不能當成已實作功能。依要求在部署確認後再逐站開發。

opportunities.json 保持空白；不能把來源可連線當成徵件核實。開放資料必須有官方 HTTPS URL、official_source=true、status=open、verification_status=verified、官方公告證據 evidence、附時區 deadline、verified_at。驗證超過七天回到待核實。駐村 support 分為 stipend、artist_fee、accommodation、production、travel。

## 本機驗證
python scripts/validate_data.py
python scripts/build_site.py
python -m http.server 8765 --directory _site

正式發布只打包 index.html 與三個公開 JSON。不使用 API 金鑰、資料庫、自訂網域或付費服務。
