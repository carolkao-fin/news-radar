# -*- coding: utf-8 -*-
"""摘要產生：優先用 Groq LLM 產生繁體中文摘要，無金鑰時退回擷取式摘要。

刻意不做全文爬取——多數新聞網站禁止自動抓取內文，且 RSS 的 description
已足以產出可靠摘要。摘要一律標註來源，使用者可點原始連結查證。
"""
import re

from . import llm

BATCH = 6  # 一次送幾則給模型，太多會超過輸出長度

_SYSTEM = """你是新聞摘要編輯。使用者會給你數則新聞的標題與原始描述。
針對每一則，產生繁體中文摘要。規則：
1. summary：2-3 句話，說明「發生什麼事」與「為什麼重要」，不要用「本文指出」這類贅語。
2. bullets：2-3 個重點短句，每句 20 字內。
3. 只能根據提供的內容撰寫，不可加入未提及的數字、日期或推論。
4. 若原始描述資訊太少，summary 就直接改寫標題並說明資訊有限，不要編造。
5. 英文來源要翻譯成繁體中文。

只回傳 JSON：{"results": [{"id": "原始 id", "summary": "...", "bullets": ["...", "..."]}]}"""


def extractive_summary(article, max_len=140):
    """不使用 LLM 的備援摘要：清理後的 RSS 描述前段。"""
    raw = re.sub(r"\s+", " ", article.get("raw_summary", "")).strip()
    if not raw:
        return article["title"]
    if len(raw) <= max_len:
        return raw
    cut = raw[:max_len]
    for p in ("。", "．", ". ", "！", "？"):
        idx = cut.rfind(p)
        if idx > max_len * 0.5:
            return cut[: idx + 1]
    return cut + "…"


def summarize(articles, use_llm=True, progress=None):
    """就地填入每則 article 的 summary / bullets，回傳同一個 list。"""
    if not articles:
        return articles

    if not (use_llm and llm.available()):
        for a in articles:
            a["summary"] = extractive_summary(a)
            a["summary_by"] = "extract"
        return articles

    for start in range(0, len(articles), BATCH):
        chunk = articles[start:start + BATCH]
        if progress:
            progress(start, len(articles))
        payload = "\n\n".join(
            f'[{a["id"]}]\n標題：{a["title"]}\n來源：{a["source_name"]}\n'
            f'原始描述：{a.get("raw_summary", "")[:800] or "（無）"}'
            for a in chunk
        )
        data = llm.chat_json(_SYSTEM, payload, max_tokens=3000)
        by_id = {}
        if data and isinstance(data.get("results"), list):
            for r in data["results"]:
                if isinstance(r, dict) and r.get("id"):
                    by_id[str(r["id"])] = r
        for a in chunk:
            r = by_id.get(a["id"])
            if r and r.get("summary"):
                a["summary"] = str(r["summary"]).strip()
                bullets = r.get("bullets") or []
                a["bullets"] = [str(b).strip() for b in bullets if str(b).strip()][:3]
                a["summary_by"] = "llm"
            else:
                a["summary"] = extractive_summary(a)
                a["summary_by"] = "extract"
    return articles


_BRIEF_SYSTEM = """你是新聞簡報主編。使用者會給你某個主題今天的多則新聞摘要。
請寫出這個主題的「今日重點」：3-4 句繁體中文，點出最重要的一到兩件事與整體趨勢。
不可加入提供內容以外的事實。只回傳 JSON：{"brief": "..."}"""


def topic_brief(topic_name, articles, use_llm=True):
    """產生主題層級的每日導讀；失敗或無金鑰時回傳空字串。"""
    if not articles or not (use_llm and llm.available()):
        return ""
    lines = "\n".join(
        f'- {a["title"]}（{a["source_name"]}）：{a.get("summary") or a.get("raw_summary", "")[:120]}'
        for a in articles[:12]
    )
    data = llm.chat_json(_BRIEF_SYSTEM, f"主題：{topic_name}\n\n{lines}", max_tokens=800)
    return (data or {}).get("brief", "").strip()
