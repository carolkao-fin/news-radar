# -*- coding: utf-8 -*-
"""新聞來源目錄。

每個來源都經過實測可正常解析（2026-07 驗證）。
`official=True` 代表政府機關、國際組織或發布方本身的第一手資料。
`broad=True` 代表該 feed 內容龐雜，收錄時必須經過主題關鍵字過濾；
`broad=False` 的來源本身就聚焦在該主題，最近期的項目全數收錄。

刻意排除維基百科與各類百科／共筆網站。
"""

SOURCES = {
    # ── AI / 科技政策 ───────────────────────────────────────────
    "arxiv_ai": {
        "name": "arXiv cs.AI",
        "url": "https://rss.arxiv.org/rss/cs.AI",
        "official": True,
        "broad": True,
        "lang": "en",
        "note": "康乃爾大學 arXiv 人工智慧類最新論文（第一手預印本）",
    },
    "arxiv_cl": {
        "name": "arXiv cs.CL",
        "url": "https://rss.arxiv.org/rss/cs.CL",
        "official": True,
        "broad": True,
        "lang": "en",
        "note": "arXiv 計算語言學／大型語言模型類論文",
    },
    "ec_digital": {
        "name": "歐盟執委會 數位政策",
        "url": "https://digital-strategy.ec.europa.eu/en/rss.xml",
        "official": True,
        "broad": False,
        "lang": "en",
        "note": "European Commission — Shaping Europe's digital future（AI Act 官方發布）",
    },
    "nist": {
        "name": "美國 NIST",
        "url": "https://www.nist.gov/news-events/news/rss.xml",
        "official": True,
        "broad": True,
        "lang": "en",
        "note": "美國國家標準暨技術研究院新聞（AI 風險管理框架主管機關）",
    },
    "oecd_ai": {
        "name": "OECD.AI 政策觀測站",
        "url": "https://wp.oecd.ai/feed/",
        "official": True,
        "broad": False,
        "lang": "en",
        "note": "經濟合作暨發展組織 AI 政策觀測站",
    },
    "openai": {
        "name": "OpenAI 官方公告",
        "url": "https://openai.com/news/rss.xml",
        "official": True,
        "broad": False,
        "lang": "en",
        "note": "OpenAI 官方新聞室",
    },
    "google_ai": {
        "name": "Google AI 官方部落格",
        "url": "https://blog.google/technology/ai/rss/",
        "official": True,
        "broad": False,
        "lang": "en",
        "note": "Google 官方 AI 產品與研究發布",
    },
    "cna_tech": {
        "name": "中央社 科技",
        "url": "https://feeds.feedburner.com/rsscna/technology",
        "official": False,
        "broad": True,
        "lang": "zh",
        "note": "中央通訊社科技新聞（媒體）",
    },
    "mit_tr_ai": {
        "name": "MIT Technology Review",
        "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",
        "official": False,
        "broad": False,
        "lang": "en",
        "note": "麻省理工科技評論 AI 專題（媒體）",
    },

    # ── 台灣國際貿易與關稅 ──────────────────────────────────────
    "customs_news": {
        "name": "財政部關務署 新聞",
        "url": "https://web.customs.gov.tw/Rss/2222",
        "official": True,
        "broad": False,
        "lang": "zh",
        "note": "關務署即時新聞（通關、邊境查緝、關稅實務）",
    },
    "customs_law": {
        "name": "財政部關務署 法規預告",
        "url": "https://web.customs.gov.tw/Rss/698",
        "official": True,
        "broad": False,
        "lang": "zh",
        "note": "關務法規草案預告與修正發布",
    },
    "trade_policy": {
        "name": "經濟部國際貿易署 新聞",
        "url": "https://www.trade.gov.tw/RSS/List.aspx?nodeID=40",
        "official": True,
        "broad": False,
        "lang": "zh",
        "note": "國貿署貿易政策與措施發布",
    },
    "trade_intl": {
        "name": "經濟部國際貿易署 國際經貿動態",
        "url": "https://www.trade.gov.tw/RSS/List.aspx?nodeID=45",
        "official": True,
        "broad": False,
        "lang": "zh",
        "note": "各國經貿情勢與市場動態彙整",
    },
    "mof_news": {
        "name": "財政部 新聞稿",
        "url": "https://www.mof.gov.tw/Rss/384fb3077bb349ea973e7fc6f13b6974",
        "official": True,
        "broad": True,
        "lang": "zh",
        "note": "財政部新聞稿（含關稅、稅制、國際租稅）",
    },
    "cbc": {
        "name": "中央銀行",
        "url": "https://www.cbc.gov.tw/tw/rss-302-1.xml",
        "official": True,
        "broad": True,
        "lang": "zh",
        "note": "中央銀行新聞與統計發布（匯率、貿易收支）",
    },
    "wto": {
        "name": "WTO 世界貿易組織",
        "url": "https://www.wto.org/library/rss/latest_news_e.xml",
        "official": True,
        "broad": False,
        "lang": "en",
        "note": "WTO 官方最新消息",
    },
    "ustr": {
        "name": "USTR 美國貿易代表署",
        "url": "https://ustr.gov/rss.xml",
        "official": True,
        "broad": True,
        "lang": "en",
        "note": "美國貿易代表署新聞稿（301 條款、貿易協定）",
    },
    "eu_trade": {
        "name": "歐盟執委會 貿易總署",
        "url": "https://policy.trade.ec.europa.eu/node/2/rss_en",
        "official": True,
        "broad": False,
        "lang": "en",
        "note": "DG TRADE 貿易與經濟安全新聞",
    },
    "fed_register_tariff": {
        "name": "美國聯邦公報（關稅）",
        "url": "https://www.federalregister.gov/api/v1/documents.rss?conditions%5Bterm%5D=tariff",
        "official": True,
        "broad": True,
        "lang": "en",
        "note": "Federal Register 關稅相關法令公告（第一手法規原文）",
    },
    "nikkei_asia": {
        "name": "Nikkei Asia",
        "url": "https://asia.nikkei.com/rss/feed/nar",
        "official": False,
        "broad": True,
        "lang": "en",
        "note": "日經亞洲：亞洲產業與經貿報導（媒體）",
    },
    "cna_finance": {
        "name": "中央社 財經",
        "url": "https://feeds.feedburner.com/rsscna/finance",
        "official": False,
        "broad": True,
        "lang": "zh",
        "note": "中央通訊社財經新聞（媒體）",
    },

    # ── 國際要聞 ────────────────────────────────────────────────
    "un_news": {
        "name": "聯合國新聞",
        "url": "https://news.un.org/feed/subscribe/en/news/all/rss.xml",
        "official": True,
        "broad": False,
        "lang": "en",
        "note": "United Nations News 官方發布",
    },
    "cna_world": {
        "name": "中央社 國際焦點",
        "url": "https://feeds.feedburner.com/rsscna/intworld",
        "official": False,
        "broad": False,
        "lang": "zh",
        "note": "中央通訊社國際新聞（媒體）",
    },
    "bbc_world": {
        "name": "BBC World News",
        "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
        "official": False,
        "broad": False,
        "lang": "en",
        "note": "英國廣播公司國際新聞（媒體）",
    },
    "ec_press": {
        "name": "歐盟執委會 新聞室",
        "url": "https://ec.europa.eu/commission/presscorner/api/rss?language=en&pagesize=20",
        "official": True,
        "broad": True,
        "lang": "en",
        "note": "European Commission 每日新聞稿（第一手政策發布）",
    },
    "gnews_world": {
        "name": "Google 新聞 國際頭條",
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
        "url": "https://rss.dw.com/rdf/rss-chi-all",
        "official": False,
        "broad": False,
        "lang": "zh",
        "note": "Deutsche Welle 中文版國際新聞（媒體）",
    },
    "pts_news": {
        "name": "公視新聞",
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
           "google_ai", "cna_tech", "mit_tr_ai"],
    "trade": ["customs_news", "customs_law", "trade_policy", "trade_intl", "mof_news",
              "cbc", "wto", "ustr", "eu_trade", "fed_register_tariff",
              "nikkei_asia", "cna_finance"],
    "world": ["un_news", "ec_press", "cna_world", "bbc_world", "gnews_world", "dw_chinese"],
    "taiwan": ["cna_world", "cna_finance", "cna_tech", "pts_news",
               "trade_intl", "mof_news", "cbc"],
}


def get_source(source_id):
    return SOURCES.get(source_id)


def source_name(source_id):
    s = SOURCES.get(source_id)
    return s["name"] if s else source_id
