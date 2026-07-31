# -*- coding: utf-8 -*-
"""新聞抓取：讀 RSS → 過濾（時間窗 + 主題關鍵字）→ 去重 → 排序。"""
import calendar
import hashlib
import re
import time
import warnings
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import feedparser
import requests
from bs4 import BeautifulSoup, MarkupResemblesLocatorWarning

from .sources import SOURCES
from .store import TW
from .topics import google_news_url

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
HEADERS = {"User-Agent": UA, "Accept": "application/rss+xml,application/xml,text/xml,*/*"}
TIMEOUT = 30

requests.packages.urllib3.disable_warnings()
# 部分 RSS 的 description 只有一個網址，bs4 會發出無意義的警告
warnings.filterwarnings("ignore", category=MarkupResemblesLocatorWarning)

# 每個來源最多取幾則，避免 arXiv 這類每日數百篇的 feed 洗版
MAX_PER_SOURCE = 12
MAX_PER_QUERY = 15
# 最終清單中同一個來源最多幾則，確保版面不被單一來源佔滿
MAX_SAME_SOURCE = 3
# 內容龐雜的來源要命中到這個分數才收錄（標題命中 2 分、內文命中 1 分）
MIN_SCORE_BROAD = 2
# 關鍵字搜尋結果本身已經過濾過，門檻放寬
MIN_SCORE_SEARCH = 1


# ── 抓取 ────────────────────────────────────────────────────────
def fetch_feed(url):
    """回傳 feedparser entries；失敗回傳空 list（單一來源掛掉不影響整體）。"""
    try:
        r = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
        r.raise_for_status()
        return feedparser.parse(r.content).entries
    except requests.exceptions.SSLError:
        try:  # 部分政府網站憑證鏈不完整
            r = requests.get(url, headers=HEADERS, timeout=TIMEOUT, verify=False)
            return feedparser.parse(r.content).entries
        except Exception as e:
            print(f"[collector] 取得失敗 {url}: {type(e).__name__}")
            return []
    except Exception as e:
        print(f"[collector] 取得失敗 {url}: {type(e).__name__}")
        return []


def clean_text(html):
    if not html:
        return ""
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return re.sub(r"\s+", " ", text).strip()


def entry_datetime(entry):
    for field in ("published_parsed", "updated_parsed", "created_parsed"):
        st = entry.get(field)
        if st:
            try:
                return datetime.fromtimestamp(calendar.timegm(st), tz=timezone.utc).astimezone(TW)
            except (ValueError, OverflowError):
                continue
    # 少數 feed（如 Nikkei Asia）只給 dc:date 字串
    for field in ("published", "updated", "dc_date", "date"):
        raw = entry.get(field)
        if isinstance(raw, str) and raw.strip():
            st = feedparser._parse_date(raw)
            if st:
                try:
                    return datetime.fromtimestamp(calendar.timegm(st), tz=timezone.utc).astimezone(TW)
                except (ValueError, OverflowError):
                    pass
    return None


def _article_id(url, title):
    return hashlib.sha1(f"{url}|{title}".encode("utf-8")).hexdigest()[:16]


def _norm_title(title):
    t = re.sub(r"\s*[-|｜–]\s*[^-|｜–]{2,30}$", "", title)  # 去掉 Google News 尾巴的來源名
    return re.sub(r"[^\w一-鿿]+", "", t).lower()


def to_article(entry, source_name, official, topic_id, lang="zh", is_search=False):
    url = entry.get("link", "").strip()
    title = clean_text(entry.get("title", ""))
    if not url or not title:
        return None
    dt = entry_datetime(entry)
    raw = clean_text(entry.get("summary", "") or entry.get("description", ""))
    if re.fullmatch(r"https?://\S+", raw):
        raw = ""  # 有些政府 feed 的描述只放一條連結，當成沒有摘要
    # Google 新聞的項目會標示真正的發稿媒體，其餘來源一律用設定檔裡的名稱
    real_source = source_name
    if is_search:
        src = entry.get("source")
        cand = src.get("title") if isinstance(src, dict) else None
        if cand and not cand.startswith("http"):
            real_source = cand
        elif " - " in title:
            real_source = title.rsplit(" - ", 1)[1]
        if title.endswith(" - " + real_source):
            title = title[: -(len(real_source) + 3)]  # 標題不重複顯示媒體名
    return {
        "id": _article_id(url, title),
        "topic": topic_id,
        "title": title,
        "url": url,
        "source_name": real_source,
        "via": source_name,
        "official": bool(official),
        "published": dt.isoformat(timespec="seconds") if dt else None,
        "published_display": dt.strftime("%Y-%m-%d %H:%M") if dt else "時間未提供",
        "raw_summary": raw[:1500],
        "lang": lang,
        "summary": "",
        "bullets": [],
    }


# ── 過濾 ────────────────────────────────────────────────────────
def match_keywords(article, keywords):
    """回傳命中的關鍵字數量。標題命中權重加倍。"""
    if not keywords:
        return 1
    title = article["title"].lower()
    body = (article["title"] + " " + article["raw_summary"]).lower()
    score = 0
    for kw in keywords:
        k = kw.lower().strip()
        if not k:
            continue
        if k in title:
            score += 2
        elif k in body:
            score += 1
    return score


def within_window(article, days):
    if not article["published"]:
        return True  # 沒有時間資訊的先保留，交由關鍵字與去重把關
    dt = datetime.fromisoformat(article["published"])
    return dt >= datetime.now(TW) - timedelta(days=days)


def dedupe(articles):
    seen_url, seen_title, out = set(), set(), []
    for a in articles:
        key_u = a["url"].split("?")[0].rstrip("/")
        key_t = _norm_title(a["title"])
        if key_u in seen_url or (key_t and key_t in seen_title):
            continue
        seen_url.add(key_u)
        if key_t:
            seen_title.add(key_t)
        out.append(a)
    return out


# ── 主流程 ──────────────────────────────────────────────────────
def collect_topic(topic, days=2, limit=25, include_search=True):
    """抓取單一主題的新聞。

    days   : 只收最近幾天的內容
    limit  : 最終保留幾則
    include_search: 是否併入 Google 新聞查詢（使用者自訂主題主要靠這個）
    """
    keywords = (topic.get("keywords_zh") or []) + (topic.get("keywords_en") or [])
    # 自訂主題借用既有來源，這些來源聚焦的是它們自己的領域，
    # 因此一律要命中主題關鍵字才收，避免抓進不相干的內容
    strict = topic.get("require_keywords", False)
    jobs = []

    for sid in topic.get("sources", []):
        src = SOURCES.get(sid)
        if src:
            jobs.append(("source", sid, src["url"], src))

    if include_search:
        for q in topic.get("news_queries", []):
            query, lang = q.get("q"), q.get("lang", "zh")
            if query:
                jobs.append(("search", query, google_news_url(query, lang, days=days),
                             {"name": "Google 新聞彙整", "official": False, "lang": lang}))

    def run(job):
        kind, key, url, meta = job
        is_search = kind == "search"
        # 彙整型來源（Google 新聞）的項目要另外解析出真正的發稿媒體
        aggregator = is_search or meta.get("is_aggregator", False)
        entries = fetch_feed(url)
        cap = MAX_PER_QUERY if is_search else MAX_PER_SOURCE
        broad = True if (is_search or strict) else meta.get("broad", True)
        min_score = MIN_SCORE_SEARCH if is_search else MIN_SCORE_BROAD
        items = []
        for e in entries[:120]:
            a = to_article(e, meta["name"], meta.get("official", False),
                           topic["id"], meta.get("lang", "zh"), is_search=aggregator)
            if not a:
                continue
            if not within_window(a, days):
                continue
            a["score"] = match_keywords(a, keywords)
            # 內容龐雜的來源要夠相關才收；聚焦型官方來源本身就在主題範圍內，一律保留
            if broad and a["score"] < min_score:
                continue
            if not broad:
                a["score"] = max(a["score"], 1)
            items.append(a)
        items.sort(key=lambda x: (-x["score"], _sort_time(x)))
        return items[:cap]

    collected = []
    with ThreadPoolExecutor(max_workers=8) as ex:
        for items in ex.map(run, jobs):
            collected.extend(items)

    collected = dedupe(collected)
    # 官方來源優先，其次關鍵字相關度，最後時間
    collected.sort(key=lambda a: (not a["official"], -a["score"], _sort_time(a)))
    return diversify(collected, limit)


def diversify(articles, limit, max_same=MAX_SAME_SOURCE):
    """限制單一來源的則數，讓版面不被 arXiv、聯邦公報這類高產來源佔滿。

    先照排序取每個來源的前 max_same 則，額度沒填滿時再用剩下的補齊。
    """
    picked, overflow, used = [], [], {}
    for a in articles:
        key = a.get("via") or a["source_name"]
        if used.get(key, 0) < max_same:
            used[key] = used.get(key, 0) + 1
            picked.append(a)
        else:
            overflow.append(a)
    if len(picked) < limit:
        picked.extend(overflow[: limit - len(picked)])
    return picked[:limit]


def _sort_time(a):
    """新的排前面（回傳負的 epoch 供升冪排序使用）。"""
    if not a["published"]:
        return 0
    try:
        return -datetime.fromisoformat(a["published"]).timestamp()
    except ValueError:
        return 0


def collect_all(topics, days=2, limit=25, progress=None):
    """依序抓取多個主題，回傳 {topic_id: [article]}。"""
    result = {}
    for i, t in enumerate(topics):
        if progress:
            progress(i, len(topics), t["name"])
        result[t["id"]] = collect_topic(t, days=days, limit=limit)
        time.sleep(0.5)  # 對來源網站友善一點
    return result
