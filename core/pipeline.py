# -*- coding: utf-8 -*-
"""抓取 → 摘要 → 存檔的完整流程。網站端與排程腳本共用這支。"""
from . import collector, store, summarizer
from .defaults import DEFAULT_DAYS


def topic_days(topic, days=None):
    """主題可以自己覆寫收錄天數；沒設定就用傳入值或全域預設。"""
    own = topic.get("days")
    if isinstance(own, int) and own > 0:
        return own
    return days or DEFAULT_DAYS


def update_topic(topic, days=None, limit=20, use_llm=True, progress=None):
    """更新單一主題，回傳 (articles, brief)。"""
    d = topic_days(topic, days)
    if progress:
        progress(f"抓取「{topic['name']}」的來源（最近 {d} 天）…")
    articles = collector.collect_topic(topic, days=d, limit=limit)
    if progress:
        progress(f"為「{topic['name']}」產生摘要（{len(articles)} 則）…")
    summarizer.summarize(articles, use_llm=use_llm)
    brief = summarizer.topic_brief(topic["name"], articles, use_llm=use_llm)
    return articles, brief


def resummarize(topics, use_llm=True, date_str=None, progress=None):
    """只針對已抓下來的新聞重新產生摘要，不重新連線抓取。

    設定金鑰之後最常用的操作 —— 不需要再跑一次抓取就能把摘要換成 LLM 版本。
    """
    date_str = date_str or store.today_str()
    snap = store.load_news(date_str)
    if not snap:
        return None, 0

    meta = snap.get("meta", {})
    briefs = meta.get("briefs", {})
    total = 0
    by_id = {t["id"]: t for t in topics}

    for tid, articles in snap.get("topics", {}).items():
        if tid not in by_id or not articles:
            continue
        name = by_id[tid]["name"]
        if progress:
            progress(f"重新產生「{name}」的摘要（{len(articles)} 則）…")
        summarizer.summarize(articles, use_llm=use_llm)
        brief = summarizer.topic_brief(name, articles, use_llm=use_llm)
        if brief:
            briefs[tid] = brief
        total += len(articles)

    meta["briefs"] = briefs
    meta["use_llm"] = use_llm
    store.save_news(date_str, snap["topics"], meta)
    return store.load_news(date_str), total


def run_update(topics, days=None, limit=20, use_llm=True, progress=None, date_str=None):
    """更新多個主題並寫入當日快照，回傳快照 dict。"""
    date_str = date_str or store.today_str()
    snapshot = store.load_news(date_str) or {"topics": {}, "meta": {}}
    topics_data = snapshot.get("topics", {})
    meta = snapshot.get("meta", {})
    briefs = meta.get("briefs", {})
    counts = {}

    for t in topics:
        articles, brief = update_topic(t, days=days, limit=limit,
                                       use_llm=use_llm, progress=progress)
        topics_data[t["id"]] = articles
        counts[t["id"]] = len(articles)
        if brief:
            briefs[t["id"]] = brief

    meta["briefs"] = briefs
    meta["counts"] = {**meta.get("counts", {}), **counts}
    meta["use_llm"] = use_llm
    meta["window_days"] = {t["id"]: topic_days(t, days) for t in topics}
    meta["topic_names"] = {t["id"]: t["name"] for t in topics}

    store.save_news(date_str, topics_data, meta)
    return store.load_news(date_str)
