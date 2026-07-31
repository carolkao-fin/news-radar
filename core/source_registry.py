# -*- coding: utf-8 -*-
"""來源註冊表：內建來源（sources.py）+ 使用者自訂來源（data/sources.json）。

程式其他地方一律透過 `all_sources()` 取得來源，不要直接用 `sources.SOURCES`，
否則使用者自己加的 RSS 不會被看到。
"""
import json
import os
import re

from . import store
from .sources import KIND_LABELS, KIND_ORDER, SOURCES

CUSTOM_FILE = os.path.join(store.DATA_DIR, "sources.json")
CUSTOM_REPO_PATH = "data/sources.json"
CUSTOM_PREFIX = "custom_"


# ── 讀寫 ────────────────────────────────────────────────────────
def load_custom():
    if not os.path.exists(CUSTOM_FILE):
        return {}
    try:
        with open(CUSTOM_FILE, "r", encoding="utf-8") as f:
            return json.load(f).get("sources", {})
    except (json.JSONDecodeError, OSError):
        return {}


def custom_json(custom):
    return json.dumps({"updated_at": store.now_iso(), "sources": custom},
                      ensure_ascii=False, indent=2)


def save_custom(custom, sync=True):
    os.makedirs(store.DATA_DIR, exist_ok=True)
    text = custom_json(custom)
    with open(CUSTOM_FILE, "w", encoding="utf-8") as f:
        f.write(text)
    if sync:
        # 同 topics.json，重新部署後容器會還原成 repo 版本，要回寫才留得住
        from . import github_sync
        github_sync.autosync(CUSTOM_REPO_PATH, text, "更新自訂 RSS 來源（來自網站）")


def all_sources():
    """內建 + 自訂，自訂的排在後面。id 相同時以自訂的為準。"""
    merged = dict(SOURCES)
    merged.update(load_custom())
    return merged


def get_source(source_id):
    return all_sources().get(source_id)


def source_name(source_id):
    s = all_sources().get(source_id)
    return s["name"] if s else source_id


def is_custom(source_id):
    return source_id in load_custom()


def sources_by_kind():
    """回傳 [(kind, 顯示名稱, 說明, [(sid, source), ...]), ...]。"""
    buckets = {}
    for sid, s in all_sources().items():
        buckets.setdefault(s.get("kind", "other"), []).append((sid, s))
    out = []
    for k in KIND_ORDER + [k for k in buckets if k not in KIND_ORDER]:
        if k in buckets:
            label, desc = KIND_LABELS.get(k, ("📌 其他", ""))
            out.append((k, label, desc, buckets[k]))
    return out


# ── 新增自訂來源 ────────────────────────────────────────────────
def probe_feed(url):
    """實際抓一次，回傳 (成功?, 訊息, 推測的設定)。新增前先驗證，避免加進壞掉的網址。"""
    from . import collector  # 延後匯入避免循環相依

    entries = collector.fetch_feed(url)
    if not entries:
        return False, "抓不到任何項目，請確認這是有效的 RSS／Atom 網址。", {}

    titles = " ".join(e.get("title", "") for e in entries[:10])
    # 中文字比例超過一成就當作中文來源
    zh_ratio = len(re.findall(r"[一-鿿]", titles)) / max(len(titles), 1)
    sample = [e.get("title", "")[:60] for e in entries[:3]]
    return True, f"成功解析 {len(entries)} 則", {
        "count": len(entries),
        "lang": "zh" if zh_ratio > 0.1 else "en",
        "sample": sample,
    }


def make_id(name, url):
    base = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not base or not base.isascii():
        m = re.search(r"https?://(?:www\.)?([^/]+)", url)
        base = re.sub(r"[^a-z0-9]+", "_", (m.group(1) if m else "feed").lower()).strip("_")
    return CUSTOM_PREFIX + (base or "feed")[:40]


def add_custom_source(name, url, kind="media", official=False, broad=True,
                      lang="zh", note="", is_aggregator=False):
    """新增一個自訂來源。id 重複時自動加序號。"""
    name, url = name.strip(), url.strip()
    if not name or not url:
        raise ValueError("來源名稱與網址都要填。")
    custom = load_custom()
    if any(s["url"] == url for s in custom.values()) or \
       any(s["url"] == url for s in SOURCES.values()):
        raise ValueError("這個網址已經在來源清單裡了。")

    sid = make_id(name, url)
    existing = set(custom) | set(SOURCES)
    if sid in existing:
        i = 2
        while f"{sid}_{i}" in existing:
            i += 1
        sid = f"{sid}_{i}"

    custom[sid] = {
        "name": name,
        "kind": kind,
        "url": url,
        "official": bool(official),
        "broad": bool(broad),
        "lang": lang,
        "note": note.strip() or "使用者自訂來源",
        "custom": True,
        "added_at": store.now_iso(),
    }
    if is_aggregator:
        custom[sid]["is_aggregator"] = True
    save_custom(custom)
    return sid, custom[sid]


def update_custom_source(source_id, **fields):
    custom = load_custom()
    if source_id not in custom:
        raise ValueError("只能修改自訂來源，內建來源請直接改 core/sources.py。")
    custom[source_id].update(fields)
    save_custom(custom)
    return custom[source_id]


def delete_custom_source(source_id):
    """刪除自訂來源，並從所有主題的來源清單中移除。"""
    custom = load_custom()
    if source_id not in custom:
        raise ValueError("找不到這個自訂來源。")
    removed = custom.pop(source_id)
    save_custom(custom)

    topics = store.load_topics()
    touched = False
    for t in topics:
        if source_id in t.get("sources", []):
            t["sources"] = [s for s in t["sources"] if s != source_id]
            touched = True
    if touched:
        store.save_topics(topics)
    return removed
