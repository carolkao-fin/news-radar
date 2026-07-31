# -*- coding: utf-8 -*-
"""資料存取層：主題設定與每日新聞快照都存成 repo 內的 JSON 檔。

設計理由：Streamlit Community Cloud 的檔案系統是暫時性的，重啟就會清空。
因此「權威版本」的資料放在 GitHub repo 裡，由 GitHub Actions 每天更新並 commit；
Streamlit 端只負責讀取。使用者在網站上新增的主題會先寫進本機檔案（當次容器有效），
並在設有 GitHub Token 時由 `github_sync` 自動回寫 repo（見主題管理頁「自動保存到
GitHub」），這樣重新部署後設定才留得住；沒有 Token 時可改用手動匯出／匯入 JSON。
"""
import json
import os
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
NEWS_DIR = os.path.join(DATA_DIR, "news")
TOPICS_FILE = os.path.join(DATA_DIR, "topics.json")

TW = timezone(timedelta(hours=8))


def today_str():
    """以台北時間為準的日期字串。"""
    return datetime.now(TW).strftime("%Y-%m-%d")


def now_iso():
    return datetime.now(TW).isoformat(timespec="seconds")


def _ensure_dirs():
    os.makedirs(NEWS_DIR, exist_ok=True)


# ── 主題 ────────────────────────────────────────────────────────
def load_topics():
    if not os.path.exists(TOPICS_FILE):
        return []
    with open(TOPICS_FILE, "r", encoding="utf-8") as f:
        return json.load(f).get("topics", [])


TOPICS_REPO_PATH = "data/topics.json"


def topics_json(topics):
    return json.dumps({"updated_at": now_iso(), "topics": topics},
                      ensure_ascii=False, indent=2)


def save_topics(topics, sync=True):
    """寫入本機檔案，並在有設定 GitHub Token 時回寫 repo。

    Streamlit Cloud 重新部署會把容器還原成 repo 版本，只寫本機檔案的話
    使用者新增的主題與類別會消失，所以這裡順手同步回去。
    """
    _ensure_dirs()
    text = topics_json(topics)
    with open(TOPICS_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    if sync:
        from . import github_sync
        github_sync.autosync(TOPICS_REPO_PATH, text,
                             "更新主題設定（來自網站）")


def get_topic(topic_id):
    for t in load_topics():
        if t["id"] == topic_id:
            return t
    return None


# ── 每日新聞快照 ────────────────────────────────────────────────
def news_path(date_str):
    return os.path.join(NEWS_DIR, f"{date_str}.json")


def save_news(date_str, topics_articles, meta=None):
    """topics_articles: {topic_id: [article, ...]}"""
    _ensure_dirs()
    payload = {
        "date": date_str,
        "generated_at": now_iso(),
        "meta": meta or {},
        "topics": topics_articles,
    }
    with open(news_path(date_str), "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return news_path(date_str)


def load_news(date_str):
    p = news_path(date_str)
    if not os.path.exists(p):
        return None
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


def available_dates():
    """由新到舊回傳所有已有資料的日期。"""
    if not os.path.isdir(NEWS_DIR):
        return []
    dates = [f[:-5] for f in os.listdir(NEWS_DIR) if f.endswith(".json")]
    return sorted(dates, reverse=True)


def latest_news():
    """回傳最新一份快照；沒有資料時回傳 None。"""
    dates = available_dates()
    return load_news(dates[0]) if dates else None


def merge_into_today(topic_id, articles):
    """把單一主題的抓取結果併進今天的快照（供網站上「立即更新這個主題」使用）。"""
    date_str = today_str()
    snap = load_news(date_str) or {"date": date_str, "meta": {}, "topics": {}}
    snap["topics"][topic_id] = articles
    snap["generated_at"] = now_iso()
    save_news(date_str, snap["topics"], snap.get("meta"))
    return snap


def prune_old_snapshots(keep_days=60):
    """只保留最近 N 天的快照，避免 repo 無限膨脹。"""
    dates = available_dates()
    removed = []
    for d in dates[keep_days:]:
        try:
            os.remove(news_path(d))
            removed.append(d)
        except OSError:
            pass
    return removed
