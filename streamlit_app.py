# -*- coding: utf-8 -*-
"""每日新聞雷達 — Streamlit 入口。

側邊欄的主題頁面是依 data/topics.json 動態產生的，
使用者新增主題後就會多出一個獨立頁面。
"""
import functools
import json
import re

import streamlit as st

from core import llm, pipeline, store, topics as topics_mod, views
from core.sources import SOURCES

st.set_page_config(page_title="每日新聞雷達", page_icon="📡", layout="centered")


def _url_path(topic):
    """st.Page 的 url_path 需要 ASCII，中文 id 改用穩定的雜湊字尾。"""
    ascii_id = re.sub(r"[^a-z0-9-]+", "", topic["id"].lower())
    if ascii_id:
        return ascii_id
    return "topic-" + str(abs(hash(topic["id"])) % 100000)


# ── 首頁：今日總覽 ──────────────────────────────────────────────
def home():
    views.inject_css()
    st.title("📡 每日新聞雷達")
    st.caption("AI ｜ 台灣國際貿易與關稅 ｜ 國際重大新聞 — 每日自動彙整，優先採用官方第一手資料")

    all_topics = topics_mod.enabled_topics()
    snap, date_str = views.snapshot_selector(key="home")
    if not snap:
        views.no_data_hint()
        _sidebar_status()
        return

    total = sum(len(v) for v in snap.get("topics", {}).values())
    official = sum(1 for v in snap.get("topics", {}).values() for a in v if a.get("official"))
    c1, c2, c3 = st.columns(3)
    c1.metric("資料日期", date_str)
    c2.metric("新聞總數", total)
    c3.metric("官方來源", official)
    st.caption(f'最後更新：{snap.get("generated_at", "—")}')
    st.divider()

    for t in all_topics:
        arts = snap.get("topics", {}).get(t["id"], [])
        brief = snap.get("meta", {}).get("briefs", {}).get(t["id"], "")
        st.subheader(f'{t.get("emoji", "📌")} {t["name"]}　`{len(arts)} 則`')
        if brief:
            st.markdown(f"> {brief}")
        if not arts:
            st.caption("今日無資料。")
        for a in arts[:3]:
            views.render_article(a)
        if len(arts) > 3:
            st.caption(f"還有 {len(arts) - 3} 則 — 點左側「{t['name']}」看完整清單")
        st.divider()

    _sidebar_status()


def _sidebar_status():
    with st.sidebar:
        st.divider()
        if llm.available():
            st.caption("🟢 已設定 Groq 金鑰，摘要由 LLM 產生")
        else:
            st.caption("🟡 未設定 GROQ_API_KEY，改用擷取式摘要")


# ── 主題管理 ────────────────────────────────────────────────────
def manage_topics():
    st.title("➕ 主題管理")
    st.caption("輸入一個主題名稱，系統會自動展開搜尋關鍵字並挑選來源，之後每天自動追蹤。")

    with st.form("add_topic"):
        name = st.text_input("新增主題", placeholder="例如：半導體出口管制、碳邊境稅 CBAM、東協經貿")
        use_llm = st.checkbox("用 AI 自動產生關鍵字與來源設定", value=llm.available(),
                              disabled=not llm.available(),
                              help="未設定 GROQ_API_KEY 時會改用規則式展開")
        submitted = st.form_submit_button("建立主題", type="primary")

    if submitted:
        if not name.strip():
            st.error("請輸入主題名稱。")
        else:
            with st.spinner("正在產生搜尋設定…"):
                try:
                    t = topics_mod.add_topic(name, use_llm=use_llm)
                except ValueError as e:
                    st.error(str(e))
                    t = None
            if t:
                how = "AI 自動產生" if t.get("auto_by") == "llm" else "規則式展開"
                st.success(f'已建立「{t["name"]}」（{how}），重新整理後左側就會出現新頁面。')
                st.json({
                    "關鍵字（中）": t["keywords_zh"],
                    "關鍵字（英）": t["keywords_en"],
                    "搜尋查詢": t["news_queries"],
                    "使用來源": [SOURCES[s]["name"] for s in t["sources"] if s in SOURCES],
                })
                if st.button("重新整理頁面"):
                    st.rerun()

    st.divider()
    st.subheader("現有主題")
    all_topics = store.load_topics()
    if not all_topics:
        st.info("尚未有任何主題。")
        return

    for t in all_topics:
        with st.expander(f'{t.get("emoji", "📌")} {t["name"]}'
                         f'{"（內建）" if t.get("builtin") else ""}'
                         f'{"" if t.get("enabled", True) else "　⏸ 已停用"}'):
            st.caption(t.get("description", ""))
            kz = st.text_area("中文關鍵字（逗號分隔）", ", ".join(t.get("keywords_zh", [])),
                              key=f"kz_{t['id']}", height=68)
            ke = st.text_area("英文關鍵字（逗號分隔）", ", ".join(t.get("keywords_en", [])),
                              key=f"ke_{t['id']}", height=68)
            qs = st.text_area("新聞搜尋查詢（一行一組，格式：查詢字串 | zh 或 en）",
                              "\n".join(f'{q["q"]} | {q.get("lang", "zh")}'
                                        for q in t.get("news_queries", [])),
                              key=f"q_{t['id']}", height=90)
            picked = st.multiselect(
                "指定 RSS 來源", options=list(SOURCES.keys()),
                default=[s for s in t.get("sources", []) if s in SOURCES],
                format_func=lambda s: f'{SOURCES[s]["name"]}{"（官方）" if SOURCES[s]["official"] else ""}',
                key=f"src_{t['id']}")
            enabled = st.checkbox("啟用（會出現在側欄並納入每日更新）",
                                  value=t.get("enabled", True), key=f"en_{t['id']}")

            c1, c2, c3 = st.columns(3)
            if c1.button("💾 儲存", key=f"save_{t['id']}"):
                queries = []
                for line in qs.splitlines():
                    if not line.strip():
                        continue
                    parts = [p.strip() for p in line.split("|")]
                    queries.append({"q": parts[0], "lang": parts[1] if len(parts) > 1 else "zh"})
                topics_mod.update_topic(
                    t["id"],
                    keywords_zh=[x.strip() for x in kz.split(",") if x.strip()],
                    keywords_en=[x.strip() for x in ke.split(",") if x.strip()],
                    news_queries=queries, sources=picked, enabled=enabled,
                )
                st.success("已儲存")
                st.rerun()

            if c2.button("🔄 立即抓這個主題", key=f"run_{t['id']}"):
                with st.spinner("抓取中…"):
                    arts, brief = pipeline.update_topic(t, days=3, limit=20,
                                                        use_llm=llm.available())
                    snap = store.merge_into_today(t["id"], arts)
                    if brief:
                        meta = snap.get("meta", {})
                        meta.setdefault("briefs", {})[t["id"]] = brief
                        store.save_news(snap["date"], snap["topics"], meta)
                st.success(f"抓到 {len(arts)} 則，切換到該主題頁面即可查看。")

            if not t.get("builtin"):
                if c3.button("🗑 刪除", key=f"del_{t['id']}"):
                    topics_mod.delete_topic(t["id"])
                    st.rerun()

    _backup_section(all_topics)


def _backup_section(all_topics):
    st.divider()
    st.subheader("💾 主題設定備份")
    st.caption(
        "Streamlit Cloud 的檔案系統在服務重啟後會還原成 GitHub 上的版本。"
        "在網站上新增的主題請下載下來，覆蓋回 repo 的 `data/topics.json` 才會永久保留。"
    )
    st.download_button(
        "下載 topics.json",
        data=json.dumps({"updated_at": store.now_iso(), "topics": all_topics},
                        ensure_ascii=False, indent=2).encode("utf-8"),
        file_name="topics.json", mime="application/json")
    up = st.file_uploader("上傳 topics.json 還原設定", type="json")
    if up is not None and st.button("確認還原"):
        data = json.load(up)
        store.save_topics(data.get("topics", []))
        st.success("已還原主題設定")
        st.rerun()


# ── 更新與設定 ──────────────────────────────────────────────────
def update_page():
    st.title("⚙️ 更新與設定")

    st.subheader("狀態")
    dates = store.available_dates()
    c1, c2 = st.columns(2)
    c1.metric("已累積天數", len(dates))
    c2.metric("最新資料", dates[0] if dates else "—")
    if llm.available():
        st.success(f"Groq 金鑰已設定，摘要模型：`{llm.MODEL}`")
    else:
        st.warning(
            "未偵測到 `GROQ_API_KEY`。網站仍可運作，但摘要會退回「擷取原文前段」模式。\n\n"
            "設定方式：Streamlit Cloud → App settings → Secrets 加入 "
            "`GROQ_API_KEY = \"gsk_...\"`（Groq 免費申請）。"
        )

    st.divider()
    st.subheader("手動更新")
    st.caption("每日排程由 GitHub Actions 在台灣時間早上 7:00 執行；這裡是臨時手動觸發。")
    active = topics_mod.enabled_topics()
    picked = st.multiselect("要更新的主題", [t["id"] for t in active],
                            default=[t["id"] for t in active],
                            format_func=lambda i: next(t["name"] for t in active if t["id"] == i))
    days = st.slider("收錄最近幾天的新聞", 1, 7, 2)
    limit = st.slider("每個主題最多保留幾則", 5, 40, 20)

    if st.button("🚀 立即更新", type="primary", disabled=not picked):
        chosen = [t for t in active if t["id"] in picked]
        bar = st.progress(0.0, text="準備中…")
        box = st.empty()
        done = {"n": 0}

        def progress(msg):
            box.caption(msg)

        for i, t in enumerate(chosen):
            bar.progress(i / len(chosen), text=f'更新中：{t["name"]}')
            arts, brief = pipeline.update_topic(t, days=days, limit=limit,
                                                use_llm=llm.available(), progress=progress)
            snap = store.merge_into_today(t["id"], arts)
            meta = snap.get("meta", {})
            meta.setdefault("briefs", {})
            if brief:
                meta["briefs"][t["id"]] = brief
            meta.setdefault("topic_names", {})[t["id"]] = t["name"]
            store.save_news(snap["date"], snap["topics"], meta)
            done["n"] += len(arts)
        bar.progress(1.0, text="完成")
        box.empty()
        st.success(f"更新完成，共 {done['n']} 則新聞。")

    st.divider()
    st.subheader("每日自動更新")
    st.markdown(
        "本專案內附 `.github/workflows/daily-update.yml`，"
        "在 GitHub 上會每天自動執行抓取並把結果 commit 回 repo，"
        "Streamlit Cloud 偵測到新 commit 後會自動重新部署。\n\n"
        "需要在 GitHub repo 的 **Settings → Secrets and variables → Actions** "
        "加入 `GROQ_API_KEY`。"
    )

    st.divider()
    st.subheader("歷史資料")
    if dates:
        st.write("已有快照：", "、".join(dates[:14]) + ("…" if len(dates) > 14 else ""))
        snap = store.load_news(dates[0])
        st.download_button(
            f"下載 {dates[0]} 的完整資料（JSON）",
            data=json.dumps(snap, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"news-{dates[0]}.json", mime="application/json")
    else:
        st.caption("尚無資料。")


def sources_page():
    views.render_source_catalog()


# ── 動態導覽 ────────────────────────────────────────────────────
def build_nav():
    pages = {
        "總覽": [st.Page(home, title="今日總覽", icon="📡", url_path="home", default=True)],
        "主題頁面": [],
        "設定": [
            st.Page(manage_topics, title="主題管理", icon="➕", url_path="topics"),
            st.Page(update_page, title="更新與設定", icon="⚙️", url_path="update"),
            st.Page(sources_page, title="資料來源", icon="📚", url_path="sources"),
        ],
    }
    for t in topics_mod.enabled_topics():
        fn = functools.partial(views.render_topic_page, t)
        fn.__name__ = f'topic_{t["id"]}'
        pages["主題頁面"].append(
            st.Page(fn, title=t["name"], icon=t.get("emoji", "📌"), url_path=_url_path(t))
        )
    if not pages["主題頁面"]:
        pages.pop("主題頁面")
    return st.navigation(pages)


build_nav().run()
