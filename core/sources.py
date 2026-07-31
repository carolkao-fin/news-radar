# -*- coding: utf-8 -*-
"""新聞來源目錄。

每個來源都經過實測可正常解析（2026-07 驗證）。
`kind` 是來源類別，用於「資料來源」頁分組與主題頁的來源篩選。
`official=True` 代表政府機關、國際組織或發布方本身的第一手資料。
`broad=True` 代表該 feed 內容龐雜，收錄時必須經過主題關鍵字過濾；
`broad=False` 的來源本身就聚焦在該主題，最近期的項目全數收錄。

刻意排除維基百科與各類百科／共筆網站。
"""

SOURCES = {
    # ── AI / 科技政策 ───────────────────────────────────────────
    "arxiv_ai": {
        "name": "arXiv cs.AI",
        "kind": "research",
        "url": "https://rss.arxiv.org/rss/cs.AI",
        "official": True,
        "broad": True,
        "lang": "en",
        "note": "康乃爾大學 arXiv 人工智慧類最新論文（第一手預印本）",
    },
    "arxiv_cl": {
        "name": "arXiv cs.CL",
        "kind": "research",
        "url": "https://rss.arxiv.org/rss/cs.CL",
        "official": True,
        "broad": True,
        "lang": "en",
        "note": "arXiv 計算語言學／大型語言模型類論文",
    },
    "ec_digital": {
        "name": "歐盟執委會 數位政策",
        "kind": "intl",
        "url": "https://digital-strategy.ec.europa.eu/en/rss.xml",
        "official": True,
        "broad": False,
        "lang": "en",
        "note": "European Commission — Shaping Europe's digital future（AI Act 官方發布）",
    },
    "nist": {
        "name": "美國 NIST",
        "kind": "gov",
        "url": "https://www.nist.gov/news-events/news/rss.xml",
        "official": True,
        "broad": True,
        "lang": "en",
        "note": "美國國家標準暨技術研究院新聞（AI 風險管理框架主管機關）",
    },
    "oecd_ai": {
        "name": "OECD.AI 政策觀測站",
        "kind": "intl",
        "url": "https://wp.oecd.ai/feed/",
        "official": True,
        "broad": False,
        "lang": "en",
        "note": "經濟合作暨發展組織 AI 政策觀測站",
    },
    "openai": {
        "name": "OpenAI 官方公告",
        "kind": "company",
        "url": "https://openai.com/news/rss.xml",
        "official": True,
        "broad": False,
        "lang": "en",
        "note": "OpenAI 官方新聞室",
    },
    "google_ai": {
        "name": "Google AI 官方部落格",
        "kind": "company",
        "url": "https://blog.google/technology/ai/rss/",
        "official": True,
        "broad": False,
        "lang": "en",
        "note": "Google 官方 AI 產品與研究發布",
    },
    "cna_tech": {
        "name": "中央社 科技",
        "kind": "media",
        "url": "https://feeds.feedburner.com/rsscna/technology",
        "official": False,
        "broad": True,
        "lang": "zh",
        "note": "中央通訊社科技新聞（媒體）",
    },
    "technews": {
        "name": "科技新報 TechNews",
        "kind": "media",
        "url": "https://technews.tw/feed/",
        "official": False,
        "broad": True,
        "lang": "zh",
        "note": "台灣科技產業媒體，半導體與 AI 應用報導（媒體）",
    },
    "mit_tr_ai": {
        "name": "MIT Technology Review",
        "kind": "media",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        "official": False,
        "broad": False,
        "lang": "en",
        "note": "麻省理工科技評論 AI 專題（媒體）",
    },

    # ── 台灣國際貿易與關稅 ──────────────────────────────────────
    "customs_news": {
        "name": "財政部關務署 新聞",
        "kind": "gov",
        "url": "https://web.customs.gov.tw/Rss/2222",
        "official": True,
        "broad": False,
        "lang": "zh",
        "note": "關務署即時新聞（通關、邊境查緝、關稅實務）",
    },
    "customs_law": {
        "name": "財政部關務署 法規預告",
        "kind": "gov",
        "url": "https://web.customs.gov.tw/Rss/698",
        "official": True,
        "broad": False,
        "lang": "zh",
        "note": "關務法規草案預告與修正發布",
    },
    "trade_policy": {
        "name": "經濟部國際貿易署 新聞",
        "kind": "gov",
        "url": "https://www.trade.gov.tw/RSS/List.aspx?nodeID=40",
        "official": True,
        "broad": False,
        "lang": "zh",
        "note": "國貿署貿易政策與措施發布",
    },
    "trade_intl": {
        "name": "經濟部國際貿易署 國際經貿動態",
        "kind": "gov",
        "url": "https://www.trade.gov.tw/RSS/List.aspx?nodeID=45",
        "official": True,
        "broad": False,
        "lang": "zh",
        "note": "各國經貿情勢與市場動態彙整",
    },
    "mof_news": {
        "name": "財政部 新聞稿",
        "kind": "gov",
        "url": "https://www.mof.gov.tw/Rss/384fb3077bb349ea973e7fc6f13b6974",
        "official": True,
        "broad": True,
        "lang": "zh",
        "note": "財政部新聞稿（含關稅、稅制、國際租稅）",
    },
    "cbc": {
        "name": "中央銀行",
        "kind": "gov",
        "url": "https://www.cbc.gov.tw/tw/rss-302-1.xml",
        "official": True,
        "broad": True,
        "lang": "zh",
        "note": "中央銀行新聞與統計發布（匯率、貿易收支）",
    },
    "wto": {
        "name": "WTO 世界貿易組織",
        "kind": "intl",
        "url": "https://www.wto.org/library/rss/latest_news_e.xml",
        "official": True,
        "broad": False,
        "lang": "en",
        "note": "WTO 官方最新消息",
    },
    "ustr": {
        "name": "USTR 美國貿易代表署",
        "kind": "gov",
        "url": "https://ustr.gov/rss.xml",
        "official": True,
        "broad": True,
        "lang": "en",
        "note": "美國貿易代表署新聞稿（301 條款、貿易協定）",
    },
    "eu_trade": {
        "name": "歐盟執委會 貿易總署",
        "kind": "intl",
        "url": "https://policy.trade.ec.europa.eu/node/2/rss_en",
        "official": True,
        "broad": False,
        "lang": "en",
        "note": "DG TRADE 貿易與經濟安全新聞",
    },
    "fed_register_tariff": {
        "name": "美國聯邦公報（關稅）",
        "kind": "gov",
        "url": "https://www.federalregister.gov/api/v1/documents.rss?conditions%5Bterm%5D=tariff",
        "official": True,
        "broad": True,
        "lang": "en",
        "note": "Federal Register 關稅相關法令公告（第一手法規原文）",
    },
    "cnyes_headline": {
        "name": "鉅亨網 頭條",
        "kind": "media",
        "url": "https://news.cnyes.com/rss/v1/news/category/headline",
        "official": False,
        "broad": True,
        "lang": "zh",
        "note": "Anue 鉅亨網頭條新聞，國際財經與總體經濟（媒體）",
    },
    "cnyes_tw": {
        "name": "鉅亨網 台股產業",
        "kind": "media",
        "url": "https://news.cnyes.com/rss/v1/news/category/tw_stock",
        "official": False,
        "broad": True,
        "lang": "zh",
        "note": "鉅亨網台股與產業動態（媒體）",
    },
    "moneydj": {
        "name": "MoneyDJ 財經",
        "kind": "media",
        "url": "https://www.moneydj.com/KMDJ/RssCenter.aspx?svc=NR&fno=1&arg=MB010000",
        "official": False,
        "broad": True,
        "lang": "zh",
        "note": "MoneyDJ 理財網國際總經新聞（媒體）",
    },
    "udn_money": {
        "name": "經濟日報 產業",
        "kind": "media",
        "url": "https://money.udn.com/rssfeed/news/1001/5591?ch=money",
        "official": False,
        "broad": True,
        "lang": "zh",
        "note": "經濟日報產業要聞（媒體）",
    },
    "udn_money_world": {
        "name": "經濟日報 國際",
        "kind": "media",
        "url": "https://money.udn.com/rssfeed/news/1001/5588?ch=money",
        "official": False,
        "broad": True,
        "lang": "zh",
        "note": "經濟日報國際財經（媒體）",
    },
    "nikkei_asia": {
        "name": "Nikkei Asia",
        "kind": "media",
        "url": "https://asia.nikkei.com/rss/feed/nar",
        "official": False,
        "broad": True,
        "lang": "en",
        "note": "日經亞洲：亞洲產業與經貿報導（媒體）",
    },
    "cna_finance": {
        "name": "中央社 財經",
        "kind": "media",
        "url": "https://feeds.feedburner.com/rsscna/finance",
        "official": False,
        "broad": True,
        "lang": "zh",
        "note": "中央通訊社財經新聞（媒體）",
    },

    # ── 國際要聞 ────────────────────────────────────────────────
    "un_news": {
        "name": "聯合國新聞",
        "kind": "intl",
        "url": "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
        "official": True,
        "broad": False,
        "lang": "en",
        "note": "United Nations News 官方發布",
    },
    "cna_world": {
        "name": "中央社 國際焦點",
        "kind": "media",
        "url": "https://feeds.feedburner.com/rsscna/intworld",
        "official": False,
        "broad": False,
        "lang": "zh",
        "note": "中央通訊社國際新聞（媒體）",
    },
    "bbc_world": {
        "name": "BBC World News",
        "kind": "media",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "official": False,
        "broad": False,
        "lang": "en",
        "note": "英國廣播公司國際新聞（媒體）",
    },
    "ec_press": {
        "name": "歐盟執委會 新聞室",
        "kind": "intl",
        "url": "https://ec.europa.eu/commission/presscorner/api/rss?language=en&pagesize=20",
        "official": True,
        "broad": True,
        "lang": "en",
        "note": "European Commission 每日新聞稿（第一手政策發布）",
    },
    "gnews_world": {
        "name": "Google 新聞 國際頭條",
        "kind": "aggregator",
        "url": ("https://news.google.com/rss/headlines/section/topic/WORLD"
                "?hl=zh-TW&gl=TW&ceid=TW:zh-Hant"),
        "official": False,
        "broad": False,
        "lang": "zh",
        "note": "Google 新聞國際版頭條彙整，連結指向各家媒體原文",
        "is_aggregator": True,
    },
    "dw_chinese": {
        "name": "德國之聲中文",
        "kind": "media",
        "url": "https://rss.dw.com/rdf/rss-chi-all",
        "official": False,
        "broad": False,
        "lang": "zh",
        "note": "Deutsche Welle 中文版國際新聞（媒體）",
    },
    "ltn_world": {
        "name": "自由時報 國際",
        "kind": "media",
        "url": "https://news.ltn.com.tw/rss/world.xml",
        "official": False,
        "broad": False,
        "lang": "zh",
        "note": "自由時報國際新聞（媒體）",
    },
    "pts_news": {
        "name": "公視新聞",
        "kind": "media",
        "url": "https://news.pts.org.tw/xml/newsfeed.xml",
        "official": False,
        "broad": True,
        "lang": "zh",
        "note": "公共電視新聞網（媒體）",
    },
}

# 新增主題時，讓系統自動挑選來源用的分類索引
SOURCE_GROUPS = {
    "ai": ["arxiv_ai", "arxiv_cl", "ec_digital", "nist", "oecd_ai", "openai",
           "google_ai", "cna_tech", "technews", "cnyes_tw", "mit_tr_ai"],
    "trade": ["customs_news", "customs_law", "trade_policy", "trade_intl", "mof_news",
              "cbc", "wto", "ustr", "eu_trade", "fed_register_tariff",
              "cnyes_headline", "cnyes_tw", "moneydj", "udn_money", "udn_money_world",
              "nikkei_asia", "cna_finance"],
    "world": ["un_news", "ec_press", "cna_world", "bbc_world", "gnews_world",
              "dw_chinese", "ltn_world", "cnyes_headline"],
    "taiwan": ["cna_world", "cna_finance", "cna_tech", "pts_news", "ltn_world",
               "cnyes_tw", "udn_money", "trade_intl", "mof_news", "cbc"],
}


# 來源類別 → (顯示名稱, 說明)，順序即為「資料來源」頁的呈現順序
KIND_LABELS = {
    "gov": ("🏛️ 政府機關", "各國政府部會的官方發布與法規公告"),
    "intl": ("🌐 國際組織", "WTO、聯合國、OECD、歐盟執委會等跨國組織"),
    "research": ("🔬 研究機構", "學術預印本與研究單位發布"),
    "company": ("🏢 企業官方", "科技公司自己的官方公告"),
    "media": ("📰 新聞媒體", "財經、科技與國際新聞媒體"),
    "aggregator": ("🔎 新聞彙整", "搜尋引擎彙整，連結指向各家媒體原文"),
}
KIND_ORDER = list(KIND_LABELS)


def kind_label(kind):
    return KIND_LABELS.get(kind, ("📌 其他", ""))[0]


def sources_by_kind():
    """回傳 [(kind, 顯示名稱, 說明, [(sid, source), ...]), ...]。"""
    buckets = {}
    for sid, s in SOURCES.items():
        buckets.setdefault(s.get("kind", "other"), []).append((sid, s))
    out = []
    for k in KIND_ORDER + [k for k in buckets if k not in KIND_ORDER]:
        if k in buckets:
            label, desc = KIND_LABELS.get(k, ("📌 其他", ""))
            out.append((k, label, desc, buckets[k]))
    return out


def get_source(source_id):
    return SOURCES.get(source_id)


def source_name(source_id):
    s = SOURCES.get(source_id)
    return s["name"] if s else source_id
