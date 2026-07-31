# -*- coding: utf-8 -*-
"""內建主題的預設定義。

放在程式碼裡而不是只存在 data/topics.json，是為了讓使用者刪掉內建主題之後
還能一鍵還原；`data/topics.json` 只是「目前的狀態」，這裡才是出廠設定。
"""

# 預設收錄最近幾天的新聞。官方機關的發布頻率低（關務署、國貿署常常好幾天才一則），
# 窗口太短會導致官方來源幾乎沒有內容，因此預設拉長到一週。
DEFAULT_DAYS = 7
MAX_DAYS = 60

# 主題類別 —— 側邊欄依此分組。使用者可以自由新增類別名稱。
DEFAULT_CATEGORIES = ["科技", "經貿", "國際", "台灣", "自訂"]

# 側邊欄的類別排序；不在清單裡的類別排在後面，依建立順序
CATEGORY_ORDER = ["科技", "經貿", "國際", "台灣", "自訂"]

# 主題分類群組 → 預設類別
GROUP_TO_CATEGORY = {
    "ai": "科技",
    "trade": "經貿",
    "world": "國際",
    "taiwan": "台灣",
}

BUILTIN_TOPICS = [
    {
        "id": "ai",
        "name": "AI 人工智慧",
        "emoji": "🤖",
        "category": "科技",
        "builtin": True,
        "enabled": True,
        "description": "AI 技術突破、產業動態與各國監理政策",
        "keywords_zh": ["人工智慧", "AI", "生成式", "大型語言模型", "機器學習",
                        "晶片", "半導體", "演算法", "自動化", "資料中心"],
        "keywords_en": ["artificial intelligence", "AI", "LLM", "machine learning",
                        "generative", "chip", "semiconductor", "AI Act"],
        "groups": ["ai"],
        "sources": ["arxiv_ai", "arxiv_cl", "ec_digital", "nist", "oecd_ai",
                    "openai", "google_ai", "cna_tech", "technews", "cnyes_tw", "mit_tr_ai"],
        "news_queries": [
            {"q": "人工智慧 政策 監理", "lang": "zh"},
            {"q": "AI regulation policy", "lang": "en"},
        ],
        "auto_by": "builtin",
    },
    {
        "id": "trade",
        "name": "台灣國際貿易與關稅",
        "emoji": "📈",
        "category": "經貿",
        "builtin": True,
        "enabled": True,
        "description": "台灣進出口、關稅措施、貿易談判與國際經貿情勢",
        # 刻意不放「台灣」：台灣媒體幾乎每篇報導都會提到，會把不相干的內容全撈進來
        "keywords_zh": ["關稅", "貿易", "出口", "進口", "通關", "海關", "關務", "進出口",
                        "經貿", "供應鏈", "反傾銷", "平衡稅", "原產地", "出口管制",
                        "自由貿易協定", "貿易談判", "301", "232", "匯率",
                        "貿易順差", "貿易逆差"],
        "keywords_en": ["tariff", "trade", "export", "import", "customs", "supply chain",
                        "anti-dumping", "countervailing", "Section 301", "Section 232",
                        "WTO", "trade deal", "export control"],
        "groups": ["trade"],
        "sources": ["customs_news", "customs_law", "trade_policy", "trade_intl",
                    "mof_news", "cbc", "wto", "ustr", "eu_trade", "fed_register_tariff",
                    "cnyes_headline", "cnyes_tw", "moneydj", "udn_money",
                    "udn_money_world", "nikkei_asia", "cna_finance"],
        "news_queries": [
            {"q": "台灣 關稅 貿易", "lang": "zh"},
            {"q": "Taiwan tariff trade", "lang": "en"},
        ],
        "auto_by": "builtin",
    },
    {
        "id": "world",
        "name": "國際重大新聞",
        "emoji": "🌍",
        "category": "國際",
        "builtin": True,
        "enabled": True,
        "description": "地緣政治、國際組織決議與全球重大事件",
        "keywords_zh": ["外交", "制裁", "衝突", "戰爭", "聯合國", "峰會", "大選",
                        "停火", "能源危機", "氣候", "地緣政治", "難民", "軍事"],
        "keywords_en": ["global", "sanctions", "conflict", "summit",
                        "United Nations", "election", "energy", "climate"],
        "groups": ["world"],
        # 來源本身就是各家國際版，不需要再加空泛的搜尋查詢（只會撈回八卦）
        "sources": ["un_news", "ec_press", "cna_world", "bbc_world",
                    "gnews_world", "dw_chinese", "ltn_world", "cnyes_headline"],
        "news_queries": [],
        "auto_by": "builtin",
    },
]


def builtin_ids():
    return {t["id"] for t in BUILTIN_TOPICS}


def get_builtin(topic_id):
    for t in BUILTIN_TOPICS:
        if t["id"] == topic_id:
            return {k: (list(v) if isinstance(v, list) else v) for k, v in t.items()}
    return None
