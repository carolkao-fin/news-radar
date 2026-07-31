# 📡 每日新聞雷達 News Radar

每天自動彙整 **AI**、**台灣國際貿易與關稅**、**國際重大新聞**，
每則新聞都有中文摘要與可點擊的原始出處連結。

- 來源優先採用**政府機關與國際組織的第一手發布**（WTO、USTR、歐盟執委會、關務署、國貿署、財政部、中央銀行、聯合國⋯）
- 財經與產業動態由媒體補足（**鉅亨網**、經濟日報、MoneyDJ、中央社、科技新報、Nikkei Asia、BBC、德國之聲⋯）
- **不採用維基百科**或任何共筆百科
- 每個主題一個獨立頁面，側邊欄**依類別分組**（科技／經貿／國際／自訂⋯）
- **使用者可以自己新增、修改、刪除主題**，系統會自動產生搜尋關鍵字並挑選來源

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

### 主題類別

每個主題都屬於一個類別，側邊欄依類別分組顯示，主題變多也不會擠成一長串。
預設類別是 **科技／經貿／國際／台灣／自訂**，新增或編輯主題時可以選既有類別，
也可以選「＋ 新增類別」自己開一個（例如「環境」「能源」）。

### 刪除與還原

任何主題都可以刪除，包含內建的三個 —— 勾選「我要刪除這個主題」後按刪除鈕。
內建主題刪掉後，主題管理頁上方會出現**還原內建主題**的按鈕；
若只是把某個內建主題的關鍵字改壞了，也可以按該主題的**還原出廠設定**。
內建主題的出廠定義寫在 `core/defaults.py`，`data/topics.json` 只是「目前的狀態」。

> ⚠️ **重要**：Streamlit Cloud 的檔案系統是暫時性的，服務重啟後會還原成 GitHub 上的版本。
> 在網站上新增主題後，請到主題管理頁最下方**下載 `topics.json`**，
> 覆蓋回 repo 的 `data/topics.json` 並 push，設定才會永久保留。
> 在本機執行時則會直接寫入檔案，不受影響。

---

## 專案結構

```
news-radar/
├── streamlit_app.py            # 網站入口，側欄頁面依主題類別動態分組產生
├── core/
│   ├── defaults.py             # 內建主題的出廠定義、類別清單與預設收錄天數
│   ├── sources.py              # 內建 RSS 來源目錄（每個都經過實測，含來源類別 kind）
│   ├── source_registry.py      # 內建 + 使用者自訂來源的合併與 CRUD
│   ├── topics.py               # 主題 CRUD + 自動產生搜尋設定
│   ├── collector.py            # 抓取 → 時間窗過濾 → 關鍵字評分 → 去重 → 來源分散
│   ├── summarizer.py           # Groq 摘要 + 無金鑰時的擷取式備援
│   ├── llm.py                  # Groq 呼叫封裝
│   ├── store.py                # JSON 讀寫
│   ├── pipeline.py             # 抓取＋摘要＋存檔的完整流程
│   └── views.py                # Streamlit 共用畫面元件
├── data/
│   ├── topics.json             # 主題設定（目前狀態）
│   ├── sources.json            # 使用者自訂的 RSS 來源
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

## 摘要

摘要分兩層，沒有金鑰也能用：

| 模式 | 條件 | 內容 |
|------|------|------|
| **AI 摘要** | 有 Groq 金鑰 | 2–3 句繁體中文摘要 + 2–3 個重點條列，英文來源會翻成中文；另外產生各主題的「今日重點」導讀 |
| **原文清理** | 沒有金鑰 | 清理過的 RSS 原始描述前段 |

「原文清理」不是直接把 RSS 描述貼上來 —— 各家 feed 的描述常常夾著機器格式，
必須先剝掉才能讀：

- arXiv 的 `arXiv:2607.28505v1 Announce Type: new Abstract:` 前綴
- 歐盟新聞室的 `European Commission Press release Brussels, 31 Jul 2026` 表頭
- Drupal 站台的 `Anonymous (not verified) Fri, 07/31/2026 - 09:00` 中繼資料
- 公文的 `發文日期／發文字號／附件` 表頭（保留「主旨」與「依據」）
- 開頭整句重複標題的部分、結尾的 `[…]` 截斷符號

判定為沒有可用內容時（例如 MoneyDJ 的描述只有「內文連結」、
Google 新聞的描述其實是一串相關報導標題、Nikkei 的描述等於標題），
會直接標示「此來源只提供標題」，而不是塞一段沒有意義的文字。

### 設定 Groq 金鑰

免費申請：https://console.groq.com/keys　三個地方效果不同：

| 設定位置 | 影響範圍 |
|---------|---------|
| 網站「⚙️ 更新與設定 → 🔑 設定 Groq 金鑰」直接貼上 | 立刻可用，但只在當前瀏覽器分頁有效，適合先試用 |
| Streamlit Secrets（Manage app → Settings → Secrets） | 網站上按「立即更新」時使用，重開仍在 |
| GitHub Actions Secret（repo → Settings → Secrets and variables → Actions） | **每日排程要用這個**；只設 Streamlit 的話，每天自動抓的摘要仍是原文清理版 |

設定金鑰後，用「**✍️ 重新產生今天的摘要**」按鈕即可 ——
它只重寫摘要，不會重新連線抓新聞。命令列對應 `python scripts/update_news.py --resummarize`。

## 收錄天數

預設收錄**最近 7 天**的新聞。官方機關的發布頻率低（關務署、國貿署常常好幾天才一則），
窗口太短會讓官方來源幾乎沒有內容。

- 全域預設在「⚙️ 更新與設定」頁調整，範圍 1～60 天
- 每個主題也可以**自己覆寫天數**（主題管理頁的「收錄最近幾天」，填 0 表示用全域預設）
- 主題的設定優先於全域值；GitHub Actions 排程用的預設值寫在 workflow 的 `days` 輸入

## 自訂資料來源

「📚 資料來源」頁可以**貼上任何網站的 RSS／Atom 網址**加入來源清單。
新增前系統會實際連線驗證，抓不到內容就不會加進來，並自動判斷語言、顯示最新幾則標題確認抓對了。

新增時要指定：

| 欄位 | 說明 |
|------|------|
| 來源類別 | 政府機關／國際組織／研究機構／企業官方／新聞媒體／新聞彙整 |
| 官方來源 | 政府機關、國際組織或發布方自己的網站才勾選，會影響排序與標籤 |
| 收錄方式 | 綜合型來源選「需命中主題關鍵字」；聚焦單一主題的來源才選「全數收錄」 |
| 加入哪些主題 | 可直接指定，不指定的話之後到主題管理頁勾選 |

自訂來源存在 `data/sources.json`，與內建來源一起運作。刪除自訂來源時會同時從所有主題移除。

## 指定主題的來源

主題管理頁的「指定 RSS 來源」可以精確控制某個主題要從哪些來源抓取，
內建與自訂來源都在同一份清單裡。

同一頁還有「**併用 Google 新聞搜尋**」開關 —— 取消勾選後，該主題就**只會**從你指定的
RSS 來源抓取，完全不使用搜尋結果。適合需要來源可控、可追溯的主題。

## 資料來源頁

網站的 **📚 資料來源** 頁把所有來源依性質分成
🏛️ 政府機關／🌐 國際組織／🔬 研究機構／🏢 企業官方／📰 新聞媒體／🔎 新聞彙整，
每個來源會標示語言、收錄方式（全數收錄或需命中關鍵字），以及**目前有哪些主題在使用它**。

該頁還有「🩺 檢查所有來源是否正常運作」按鈕，會實際連線抓一次每個 RSS —— 
政府網站改版時 feed 常常會無聲失效，用這個可以直接找出哪些來源該換掉。

主題頁上方也能依來源類別篩選新聞（例如只看政府機關與國際組織的發布）。

## 授權與使用注意

- 所有內容皆連回原始發布者，摘要僅供快速瀏覽，引用請以原文為準。
- 本專案只讀取各網站公開提供的 RSS，不做全文爬取。
