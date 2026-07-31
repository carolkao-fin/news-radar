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


# RSS 描述裡的機器格式前綴／中繼資料，直接拿來當摘要會很難讀
_BOILERPLATE = [
    # arXiv：「arXiv:2607.28505v1 Announce Type: new Abstract: ...」
    (re.compile(r"^arXiv:\S+\s*Announce Type:\s*\S+\s*(Abstract:)?\s*", re.I), ""),
    # 歐盟新聞室：「European Commission Press release Brussels, 31 Jul 2026 ...」
    (re.compile(r"^European Commission\s+Press release\s+[A-Za-z]+,\s*"
                r"\d{1,2}\s+\w+\s+\d{4}\s*", re.I), ""),
    # Drupal 站台的作者與時間戳：「Anonymous (not verified) Fri, 07/31/2026 - 09:00」
    (re.compile(r"\s*(?:Anonymous \(not verified\)|[a-z]{3,20})\s+"
                r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun),\s*\d{1,2}/\d{1,2}/\d{4}\s*-\s*"
                r"\d{1,2}:\d{2}\s*", re.I), " "),
    # 公文表頭：「財政部 公告 發文日期：... 發文字號：... 附件：...」
    (re.compile(r"^.{0,20}?公告\s*發文日期：.*?(?=主旨：)", re.S), ""),
    (re.compile(r"發文日期：\S+\s*"), ""),
    (re.compile(r"發文字號：\S+\s*"), ""),
    (re.compile(r"附件：[^。]{0,30}?(?=主旨：)"), ""),
    # 央行新聞稿表頭
    (re.compile(r"^中央銀行新聞稿\s*\d+年\d+月\d+日發布\s*(（\d+）新聞發布第\d+號)?\s*"), ""),
]

# 這些字串是「閱讀更多」之類的連結文字，不是摘要
_USELESS = {"內文連結", "詳全文", "詳全文…", "閱讀更多", "繼續閱讀",
            "read more", "more", "continue reading", "(more…)"}

_MIN_LEN = 12


def clean_summary(raw, title="", kind=""):
    """把 RSS 描述整理成可讀的摘要；判定為無用時回傳空字串。"""
    if not raw:
        return ""
    # Google 新聞這類彙整來源的描述是一串「相關報導標題」，不是摘要
    if kind == "aggregator":
        return ""

    text = re.sub(r"\s+", " ", raw).strip()
    for pattern, repl in _BOILERPLATE:
        text = pattern.sub(repl, text)
    text = re.sub(r"\s+", " ", text).strip()

    # 描述開頭常常整句重複標題，去掉才不會讀兩次
    if title:
        t = title.strip()
        if text.startswith(t):
            text = text[len(t):].lstrip(" -–—｜|:：")

    text = re.sub(r"(\[…\]|\[\.\.\.\]|…+|\.{3,})\s*$", "", text).strip()
    text = text.strip(" -–—｜|:：")

    if text.lower() in _USELESS or len(text) < _MIN_LEN:
        return ""
    if title and text.strip() == title.strip():
        return ""
    return text


def extractive_summary(article, max_len=160):
    """不使用 LLM 的備援摘要：清理後的 RSS 描述前段。無可用內容時回傳空字串。"""
    text = clean_summary(article.get("raw_summary", ""),
                         article.get("title", ""), article.get("kind", ""))
    if not text:
        return ""
    if len(text) <= max_len:
        return text
    cut = text[:max_len]
    for p in ("。", "！", "？", ". "):
        idx = cut.rfind(p)
        if idx > max_len * 0.5:
            return cut[: idx + 1]
    return cut.rstrip() + "…"


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
            f'原始描述：{clean_summary(a.get("raw_summary", ""), a["title"], a.get("kind", ""))[:800] or "（無，請直接依標題撰寫）"}'
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
