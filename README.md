# 📡 每日新聞雷達 News Radar

每天自動彙整 **AI**、**台灣國際貿易與關稅**、**國際重大新聞**，
每則新聞都有中文摘要與可點擊的原始出處連結。

- 來源優先採用**政府機關與國際組織的第一手發布**（WTO、USTR、歐盟執委會、關務署、國貿署、財政部、中央銀行、聯合國⋯）
- 財經與產業動態由媒體補足（**鉅亨網**、經濟日報、MoneyDJ、中央社、科技新報、Nikkei Asia、BBC、德國之聲⋯）
- **不採用維基百科**或任何共筆百科
- 每個主題一個獨立頁面
- **使用者可以自己新增主題**，系統會自動產生搜尋關鍵字並挑選來源

---

## 快速開始（本機）

```bash
pip install -r requirements.txt

# 抓一次新聞（沒有 Groq 金鑰也能跑，摘要會退回擷取式）
python scripts/update_news.py --days 2

# 啟動網站
streamlit run streamlit_app.py
```

想要 AI 生成的摘要，先設定 Groq 免費金鑰（https://console.groq.com）：

```bash
# Windows PowerShell
$env:GROQ_API_KEY = "gsk_xxx"
# macOS / Linux
export GROQ_API_KEY="gsk_xxx"
```

---

## 部署到 GitHub + Streamlit Cloud

### 1. 推上 GitHub

```bash
cd news-radar
git init
git add .
git commit -m "初始版本：每日新聞雷達"
git branch -M main
git remote add origin https://github.com/<你的帳號>/news-radar.git
git push -u origin main
```

### 2. 設定每日自動更新（GitHub Actions）

1. repo → **Settings → Secrets and variables → Actions → New repository secret**
2. 新增 `GROQ_API_KEY`，值填你的 Groq 金鑰
3. repo → **Actions** 分頁 → 啟用 workflows

`.github/workflows/daily-update.yml` 會在**每天台灣時間早上 7:00**執行，
抓取新聞、產生摘要、把結果 commit 回 `data/news/`。
也可以在 Actions 頁面手動按 **Run workflow** 立即執行一次。

> GitHub 排程在尖峰時段可能延遲數十分鐘，屬正常現象。
> 若 repo 連續 60 天沒有任何活動，GitHub 會自動停用排程，屆時進 Actions 頁面按一次啟用即可。

### 3. 部署 Streamlit

1. 到 https://share.streamlit.io → **New app**
2. 選擇這個 repo，Main file path 填 `streamlit_app.py`
3. **Advanced settings → Secrets** 貼上：

```toml
GROQ_API_KEY = "gsk_xxx"
```

每次 GitHub Actions commit 新資料後，Streamlit Cloud 會自動重新部署，網站就會出現當天的新聞。

---

## 使用者新增主題

到網站的 **➕ 主題管理** 頁，輸入主題名稱（例如「半導體出口管制」「碳邊境調整機制 CBAM」），
系統會自動：

1. 用 Groq LLM 展開**中英文搜尋關鍵字**（沒有金鑰時改用規則式展開）
2. 判斷主題屬性，從來源目錄挑出相關的**官方／媒體 RSS 來源**
3. 產生 **Google 新聞 RSS 查詢**（中文 + 英文），讓沒有專屬官方 feed 的主題也抓得到新聞

建立後左側會自動多出一個獨立頁面，並納入每日排程。
關鍵字、查詢字串與來源都可以在同一頁手動微調。

> ⚠️ **重要**：Streamlit Cloud 的檔案系統是暫時性的，服務重啟後會還原成 GitHub 上的版本。
> 在網站上新增主題後，請到主題管理頁最下方**下載 `topics.json`**，
> 覆蓋回 repo 的 `data/topics.json` 並 push，設定才會永久保留。
> 在本機執行時則會直接寫入檔案，不受影響。

---

## 專案結構

```
news-radar/
├── streamlit_app.py            # 網站入口，側欄頁面依主題動態產生
├── core/
│   ├── sources.py              # RSS 來源目錄（每個都經過實測）
│   ├── topics.py               # 主題 CRUD + 自動產生搜尋設定
│   ├── collector.py            # 抓取 → 時間窗過濾 → 關鍵字評分 → 去重 → 來源分散
│   ├── summarizer.py           # Groq 摘要 + 無金鑰時的擷取式備援
│   ├── llm.py                  # Groq 呼叫封裝
│   ├── store.py                # JSON 讀寫
│   ├── pipeline.py             # 抓取＋摘要＋存檔的完整流程
│   └── views.py                # Streamlit 共用畫面元件
├── data/
│   ├── topics.json             # 主題設定
│   └── news/YYYY-MM-DD.json    # 每日新聞快照（保留最近 60 天）
├── scripts/update_news.py      # 每日更新腳本
└── .github/workflows/daily-update.yml
```

## 篩選邏輯

| 情況 | 處理方式 |
|------|----------|
| 聚焦型官方來源（WTO、關務署⋯） | 最近期項目全數收錄 |
| 內容龐雜的來源（arXiv、聯邦公報、財政部⋯） | 需命中主題關鍵字，標題命中 2 分、內文 1 分，**≥ 2 分**才收 |
| Google 新聞搜尋結果 | 查詢自動帶上 `when:Nd` 只取最近 N 天；查詢本身已是過濾，**≥ 1 分**即收 |
| 使用者自訂主題 | 借用的來源一律要命中關鍵字（`require_keywords`），避免抓進不相干內容 |
| 同一來源 | 最多 3 則，避免單一來源洗版；額度沒滿才回補 |
| 排序 | 官方來源優先 → 關鍵字相關度 → 發布時間 |

## 授權與使用注意

- 所有內容皆連回原始發布者，摘要僅供快速瀏覽，引用請以原文為準。
- 本專案只讀取各網站公開提供的 RSS，不做全文爬取。
