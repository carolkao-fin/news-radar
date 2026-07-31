# -*- coding: utf-8 -*-
"""抓取 → 摘要 → 存檔的完整流程。網站端與排程腳本共用這支。"""
from . import collector, store, summarizer


def update_topic(topic, days=2, limit=20, use_llm=True, progress=None):
    """更新單一主題，回傳 (articles, brief)。"""
    if progress:
        progress(f"抓取「{topic['name']}」的來源…")
    articles = collector.collect_topic(topic, days=days, limit=limit)
    if progress:
        progress(f"為「{topic['name']}」產生摘要（{len(articles)} 則）…")
    summarizer.summarize(articles, use_llm=use_llm)
    brief = summarizer.topic_brief(topic["name"], articles, use_llm=use_llm)
    return articles, brief


def run_update(topics, days=2, limit=20, use_llm=True, progress=None, date_str=None):
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
    meta["window_days"] = days
    meta["topic_names"] = {t["id"]: t["name"] for t in topics}

    store.save_news(date_str, topics_data, meta)
    return store.load_news(date_str)
