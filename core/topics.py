# -*- coding: utf-8 -*-
"""主題管理：新增主題時自動產生搜尋設定。

使用者只要輸入一個主題名稱（例如「半導體出口管制」），系統會自動：
  1. 用 Groq LLM 展開中英文搜尋關鍵字
  2. 從來源目錄挑出相關的官方／媒體 RSS 來源
  3. 產生 Google 新聞 RSS 查詢字串（中文 + 英文各一組）
沒有 LLM 金鑰時，退回規則式展開，功能仍可用，只是關鍵字較少。
"""
import re
import urllib.parse

from . import llm, store
from .sources import SOURCES, SOURCE_GROUPS

# 判斷主題屬性用的線索詞，供無 LLM 時的備援分類
_GROUP_HINTS = {
    "ai": ["ai", "人工智慧", "機器學習", "大型語言模型", "llm", "生成式", "演算法",
           "深度學習", "晶片", "半導體", "科技", "資料", "自動化", "機器人"],
    "trade": ["貿易", "關稅", "出口", "進口", "通關", "供應鏈", "經貿", "tariff",
              "trade", "wto", "fta", "反傾銷", "原產地", "海關", "匯率", "投資"],
    "world": ["國際", "外交", "地緣", "戰爭", "選舉", "聯合國", "氣候", "能源",
              "world", "global", "un", "衝突", "制裁"],
    "taiwan": ["台灣", "臺灣", "兩岸", "taiwan", "國內"],
}


def slugify(name):
    """把主題名稱轉成安全的 id；中文會保留，僅去除路徑不安全字元。"""
    s = re.sub(r"[^\w一-鿿-]+", "-", name.strip()).strip("-").lower()
    return s or "topic"


def unique_id(name, existing_ids):
    base = slugify(name)
    if base not in existing_ids:
        return base
    i = 2
    while f"{base}-{i}" in existing_ids:
        i += 1
    return f"{base}-{i}"


def google_news_url(query, lang="zh", days=None):
    """Google 新聞 RSS 查詢（回傳的是各家新聞媒體的原始連結，非百科內容）。

    Google 的搜尋結果是照相關度排序，不加限制會拿回大量舊聞；
    帶上 `when:Nd` 讓它只回傳最近 N 天的報導。
    """
    if days:
        query = f"{query} when:{int(days)}d"
    q = urllib.parse.quote(query)
    if lang == "zh":
        return f"https://news.google.com/rss/search?q={q}&hl=zh-TW&gl=TW&ceid=TW:zh-Hant"
    return f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"


# ── 自動產生主題設定 ────────────────────────────────────────────
_SYSTEM = """你是新聞監測系統的設定助理。使用者給你一個關注主題，你要產生搜尋設定。
只回傳 JSON，格式如下：
{
  "emoji": "單一 emoji",
  "description": "一句話說明這個主題涵蓋什麼（繁體中文，30 字內）",
  "keywords_zh": ["繁體中文關鍵字，6-10 個，要涵蓋同義詞與相關機構名稱"],
  "keywords_en": ["English keywords, 5-8 items"],
  "queries_zh": ["適合丟進新聞搜尋引擎的中文查詢字串，2-3 組，可用空格組合詞彙"],
  "queries_en": ["English news search queries, 1-2 items"],
  "groups": ["從 ai / trade / world / taiwan 中挑出 1-3 個最相關的分類"]
}
關鍵字要精準，避免過於籠統的字（例如「新聞」「消息」）造成誤抓。"""


def auto_configure(name, use_llm=True):
    """回傳主題的搜尋設定 dict（不含 id / name / created_at）。"""
    cfg = None
    if use_llm and llm.available():
        cfg = llm.chat_json(_SYSTEM, f"關注主題：{name}", max_tokens=1200, temperature=0.3)
    if not cfg or not cfg.get("keywords_zh"):
        cfg = _fallback_config(name)
        cfg["auto_by"] = "rule"
    else:
        cfg["auto_by"] = "llm"

    groups = [g for g in cfg.get("groups", []) if g in SOURCE_GROUPS] or _guess_groups(name)
    source_ids = []
    for g in groups:
        for sid in SOURCE_GROUPS[g]:
            if sid not in source_ids:
                source_ids.append(sid)

    queries_zh = [q for q in cfg.get("queries_zh", []) if q] or [name]
    queries_en = [q for q in cfg.get("queries_en", []) if q]

    return {
        "emoji": (cfg.get("emoji") or "📌")[:2],
        "description": cfg.get("description") or f"{name} 相關新聞與官方發布",
        "keywords_zh": _clean_list(cfg.get("keywords_zh"), name),
        "keywords_en": _clean_list(cfg.get("keywords_en")),
        "groups": groups,
        "sources": source_ids,
        "news_queries": (
            [{"q": q, "lang": "zh"} for q in queries_zh[:3]]
            + [{"q": q, "lang": "en"} for q in queries_en[:2]]
        ),
        "auto_by": cfg["auto_by"],
    }


def _clean_list(items, extra=None):
    out = []
    for x in (items or []):
        x = str(x).strip()
        if x and x not in out:
            out.append(x)
    if extra and extra not in out:
        out.insert(0, extra)
    return out[:12]


def _guess_groups(name):
    low = name.lower()
    hits = [g for g, words in _GROUP_HINTS.items() if any(w in low for w in words)]
    return hits[:3] or ["world"]


def _fallback_config(name):
    """無 LLM 時的規則式展開：主題名稱本身 + 分隔符斷詞 + 命中的領域詞。

    中文沒有空白斷詞，所以額外掃描領域詞表，把出現在主題名稱裡的詞抽出來
    （例如「半導體出口管制」會抽出「出口」），讓關鍵字不只有完整字串一個。
    """
    parts = [p for p in re.split(r"[\s、,，/／-]+", name) if len(p) >= 2]
    low = name.lower()
    for words in _GROUP_HINTS.values():
        for w in words:
            if len(w) >= 2 and w in low and w not in parts:
                parts.append(w)
    return {
        "emoji": "📌",
        "description": f"{name} 相關新聞與官方發布",
        "keywords_zh": [name] + parts,
        "keywords_en": [],
        "queries_zh": [name],
        "queries_en": [],
        "groups": _guess_groups(name),
    }


# ── CRUD ────────────────────────────────────────────────────────
def add_topic(name, use_llm=True, extra_sources=None):
    topics = store.load_topics()
    if any(t["name"] == name.strip() for t in topics):
        raise ValueError(f"主題「{name}」已存在")
    cfg = auto_configure(name.strip(), use_llm=use_llm)
    if extra_sources:
        for sid in extra_sources:
            if sid in SOURCES and sid not in cfg["sources"]:
                cfg["sources"].append(sid)
    topic = {
        "id": unique_id(name, {t["id"] for t in topics}),
        "name": name.strip(),
        "builtin": False,
        "enabled": True,
        "require_keywords": True,
        "created_at": store.now_iso(),
        **cfg,
    }
    topics.append(topic)
    store.save_topics(topics)
    return topic


def update_topic(topic_id, **fields):
    topics = store.load_topics()
    for t in topics:
        if t["id"] == topic_id:
            t.update(fields)
            store.save_topics(topics)
            return t
    raise ValueError(f"找不到主題 {topic_id}")


def delete_topic(topic_id):
    topics = store.load_topics()
    target = next((t for t in topics if t["id"] == topic_id), None)
    if not target:
        raise ValueError(f"找不到主題 {topic_id}")
    if target.get("builtin"):
        raise ValueError("內建主題不可刪除，可改為停用")
    store.save_topics([t for t in topics if t["id"] != topic_id])
    return target


def enabled_topics():
    return [t for t in store.load_topics() if t.get("enabled", True)]
