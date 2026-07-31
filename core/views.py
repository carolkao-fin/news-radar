# -*- coding: utf-8 -*-
"""Streamlit 共用畫面元件。"""
import streamlit as st

from . import source_registry, store
from .source_registry import all_sources, sources_by_kind
from .sources import KIND_ORDER, kind_label

CARD_CSS = """
<style>
.nr-card { border:1px solid rgba(49,51,63,.15); border-radius:10px;
           padding:14px 16px; margin-bottom:12px; }
.nr-title { font-size:1.02rem; font-weight:600; line-height:1.45; margin-bottom:6px; }
.nr-title a { text-decoration:none; }
.nr-meta { font-size:.8rem; color:#6b7785; margin-bottom:8px; }
.nr-badge { display:inline-block; padding:1px 7px; border-radius:4px;
            font-size:.72rem; margin-right:6px; vertical-align:1px; }
.nr-official { background:#E4F4F4; color:#0F6E6E; border:1px solid #9FD8D8; }
.nr-media { background:#F1F3F5; color:#5A6672; border:1px solid #DDE1E6; }
.nr-summary { font-size:.92rem; line-height:1.65; margin-bottom:6px; }
.nr-nosum { color:#8a94a0; font-style:italic; }
.nr-bullets { font-size:.86rem; color:#3d4a57; margin:0 0 6px 1.1rem; padding:0; }
.nr-src { font-size:.8rem; }
</style>
"""


def inject_css():
    st.markdown(CARD_CSS, unsafe_allow_html=True)


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def render_article(a):
    badge = ('<span class="nr-badge nr-official">官方來源</span>' if a.get("official")
             else '<span class="nr-badge nr-media">媒體</span>')
    bullets = ""
    if a.get("bullets"):
        items = "".join(f"<li>{_esc(b)}</li>" for b in a["bullets"])
        bullets = f'<ul class="nr-bullets">{items}</ul>'
    via = ""
    if a.get("via") and a["via"] != a["source_name"]:
        via = f'．經由 {_esc(a["via"])}'
    text = (a.get("summary") or "").strip()
    if text:
        summary = f'<div class="nr-summary">{_esc(text)}</div>'
    else:
        summary = ('<div class="nr-summary nr-nosum">'
                   '此來源只提供標題，點連結閱讀原文。</div>')
    st.markdown(
        f'<div class="nr-card">'
        f'<div class="nr-title"><a href="{_esc(a["url"])}" target="_blank">{_esc(a["title"])}</a></div>'
        f'<div class="nr-meta">{badge}{_esc(a["source_name"])}{via}．{_esc(a.get("published_display", ""))}</div>'
        f'{summary}'
        f'{bullets}'
        f'<div class="nr-src">🔗 <a href="{_esc(a["url"])}" target="_blank">前往原始資料</a></div>'
        f'</div>',
        unsafe_allow_html=True,
    )


def snapshot_selector(key="date"):
    """側邊欄的日期選擇；回傳 (snapshot, date_str)。"""
    dates = store.available_dates()
    if not dates:
        return None, None
    with st.sidebar:
        chosen = st.selectbox("📅 選擇日期", dates, index=0, key=f"date_{key}")
    return store.load_news(chosen), chosen


def no_data_hint():
    st.info(
        "目前還沒有任何新聞資料。\n\n"
        "請到左側「⚙️ 更新與設定」頁按下 **立即更新**，"
        "或等待每日排程（台灣時間早上 7:00）自動抓取。"
    )


def render_topic_page(topic):
    """單一主題的完整頁面。"""
    inject_css()
    st.title(f'{topic.get("emoji", "📌")} {topic["name"]}')
    if topic.get("description"):
        st.caption(topic["description"])

    snap, date_str = snapshot_selector(key=topic["id"])
    if not snap:
        no_data_hint()
        return

    articles = snap.get("topics", {}).get(topic["id"], [])
    brief = snap.get("meta", {}).get("briefs", {}).get(topic["id"], "")

    st.caption(f'資料日期 {date_str}．更新時間 {snap.get("generated_at", "—")}')

    if brief:
        st.success(f"**今日重點**\n\n{brief}")

    if not articles:
        st.warning("這個日期的這個主題沒有抓到新聞。可能是來源當天沒有更新，或關鍵字太嚴格。")
        return

    # 篩選列
    c1, c2 = st.columns([1, 2])
    with c1:
        only_official = st.checkbox("只看官方來源", key=f"off_{topic['id']}")
    with c2:
        kw = st.text_input("在本頁搜尋關鍵字", key=f"kw_{topic['id']}",
                           placeholder="例如：關稅、晶片、EU")

    kinds_present = [k for k in KIND_ORDER if any(a.get("kind") == k for a in articles)]
    picked_kinds = kinds_present
    if len(kinds_present) > 1:
        picked_kinds = st.multiselect(
            "來源類別", kinds_present, default=kinds_present,
            format_func=kind_label, key=f"kind_{topic['id']}")

    shown = articles
    if only_official:
        shown = [a for a in shown if a.get("official")]
    if picked_kinds != kinds_present:
        shown = [a for a in shown if a.get("kind") in picked_kinds]
    if kw.strip():
        k = kw.strip().lower()
        shown = [a for a in shown
                 if k in a["title"].lower() or k in (a.get("summary", "") + a.get("raw_summary", "")).lower()]

    official_n = sum(1 for a in articles if a.get("official"))
    st.markdown(f"共 **{len(shown)}** 則（全部 {len(articles)} 則，其中官方來源 {official_n} 則）")
    st.divider()

    for a in shown:
        render_article(a)

    with st.expander("📚 本頁使用的資料來源"):
        used = sorted({a["source_name"] for a in articles})
        for name in used:
            st.markdown(f"- {name}")
        st.caption("所有摘要皆由原始 RSS 描述產生，點擊標題可回到發布方的原始頁面查證。")


def render_source_catalog():
    st.title("📚 資料來源")
    st.caption("本站不採用維基百科等共筆百科；優先使用政府機關與國際組織的第一手發布。")

    all_topics = store.load_topics()
    catalog = all_sources()
    # 每個來源被哪些主題使用
    used_by = {}
    for t in all_topics:
        for sid in t.get("sources", []):
            used_by.setdefault(sid, []).append(t)

    official_n = sum(1 for s in catalog.values() if s["official"])
    custom_n = sum(1 for s in catalog.values() if s.get("custom"))
    c1, c2, c3 = st.columns(3)
    c1.metric("來源總數", len(catalog))
    c2.metric("官方／第一手", official_n)
    c3.metric("自訂來源", custom_n)

    with st.expander("➕ 新增自訂 RSS 來源"):
        _add_source_form(all_topics)

    custom = source_registry.load_custom()
    if custom:
        with st.expander(f"🙋 管理我的自訂來源（{len(custom)}）"):
            _manage_custom_sources(custom, used_by)

    with st.expander("🩺 檢查所有來源是否正常運作"):
        st.caption("實際連線抓一次每個 RSS，確認來源還活著。約需 20～40 秒。")
        if st.button("開始檢查", key="health_check"):
            _run_health_check()

    st.divider()

    for kind, label, desc, items in sources_by_kind():
        st.subheader(f"{label}（{len(items)}）")
        if desc:
            st.caption(desc)
        for sid, s in items:
            badge = ("✅ 官方" if s["official"] else "📰 媒體")
            scope = "全數收錄" if not s.get("broad", True) else "需命中關鍵字"
            mine = "　`🙋 自訂`" if s.get("custom") else ""
            topics_using = used_by.get(sid, [])
            tag = "、".join(f'{t.get("emoji", "")}{t["name"]}' for t in topics_using) or "（目前沒有主題使用）"
            with st.container(border=True):
                st.markdown(f'**{s["name"]}**　`{badge}`　`{s.get("lang", "").upper()}`　`{scope}`{mine}')
                st.caption(s["note"])
                st.caption(f"使用中的主題：{tag}")
                st.code(s["url"], language=None)
        st.write("")

    st.divider()
    st.markdown(
        "#### 關於來源篩選\n"
        "- **全數收錄**：該來源本身就聚焦在主題範圍內（例如 WTO、關務署），最近期的項目全部收進來。\n"
        "- **需命中關鍵字**：內容龐雜的來源（例如 arXiv、聯邦公報、綜合財經媒體），"
        "必須命中主題關鍵字才收錄，避免不相干的內容洗版。\n"
        "- 使用者自訂主題另外會使用 **Google 新聞 RSS** 做關鍵字搜尋，"
        "它回傳的是各家新聞媒體的原始連結，不是百科內容。\n"
        "- 每則新聞都保留原始連結，摘要僅供快速瀏覽，引用請以原文為準。"
    )


def _add_source_form(all_topics):
    st.caption(
        "貼上任何網站的 RSS／Atom 網址就能加入。系統會先實際連線驗證，"
        "抓不到內容不會加進來。常見位置：網站頁尾的 RSS 圖示，或網址後面加 `/feed`、`/rss`。"
    )
    with st.form("add_source"):
        url = st.text_input("RSS 網址", placeholder="https://example.com/feed")
        name = st.text_input("來源名稱", placeholder="例如：工商時報 產業版")
        c1, c2 = st.columns(2)
        with c1:
            kind = st.selectbox("來源類別", KIND_ORDER, index=KIND_ORDER.index("media"),
                                format_func=kind_label)
        with c2:
            official = st.checkbox("這是官方／第一手來源",
                                   help="政府機關、國際組織或發布方自己的網站才勾選")
        scope = st.radio(
            "收錄方式",
            ["需命中主題關鍵字", "最近期項目全數收錄"],
            help="綜合型來源（例如整站新聞）選前者，避免不相干內容洗版；"
                 "本身就聚焦在單一主題的來源才選後者。",
        )
        attach = st.multiselect(
            "要加入哪些主題", [t["id"] for t in all_topics],
            format_func=lambda i: next(
                f'{t.get("emoji", "")}{t["name"]}' for t in all_topics if t["id"] == i),
        )
        note = st.text_input("說明（選填）", placeholder="這個來源提供什麼內容")
        submitted = st.form_submit_button("驗證並新增", type="primary")

    if not submitted:
        return
    if not url.strip() or not name.strip():
        st.error("網址與名稱都要填。")
        return

    with st.spinner("正在連線驗證…"):
        ok, msg, info = source_registry.probe_feed(url.strip())
    if not ok:
        st.error(msg)
        return

    try:
        sid, src = source_registry.add_custom_source(
            name=name, url=url, kind=kind, official=official,
            broad=(scope == "需命中主題關鍵字"), lang=info.get("lang", "zh"), note=note,
        )
    except ValueError as e:
        st.error(str(e))
        return

    st.success(f'✅ {msg}，已新增「{src["name"]}」（語言判定：{src["lang"].upper()}）')
    st.caption("最新幾則標題：")
    for t in info.get("sample", []):
        st.markdown(f"- {t}")

    if attach:
        topics = store.load_topics()
        for t in topics:
            if t["id"] in attach and sid not in t.get("sources", []):
                t.setdefault("sources", []).append(sid)
        store.save_topics(topics)
        names = [t["name"] for t in topics if t["id"] in attach]
        st.success(f'已加入主題：{"、".join(names)}')
    else:
        st.info("尚未指定主題。到「主題管理」頁的來源清單勾選它，才會開始抓取。")


def _manage_custom_sources(custom, used_by):
    for sid, s in custom.items():
        with st.container(border=True):
            using = used_by.get(sid, [])
            st.markdown(f'**{s["name"]}**　`{kind_label(s.get("kind", "media"))}`')
            st.code(s["url"], language=None)
            st.caption(f'使用中的主題：{"、".join(t["name"] for t in using) or "（無）"}')
            c1, c2 = st.columns([1, 3])
            with c1:
                confirm = st.checkbox("確認刪除", key=f"cfmsrc_{sid}")
            with c2:
                if st.button("🗑 刪除這個來源", key=f"delsrc_{sid}", disabled=not confirm):
                    source_registry.delete_custom_source(sid)
                    st.success(f'已刪除「{s["name"]}」，並從所有主題中移除。')
                    st.rerun()


def _run_health_check():
    """實際連線每個來源，回報可用狀態。"""
    from concurrent.futures import ThreadPoolExecutor

    from . import collector

    items = list(all_sources().items())
    bar = st.progress(0.0, text="檢查中…")
    results = []

    def probe(item):
        sid, s = item
        try:
            entries = collector.fetch_feed(s["url"])
            return sid, s["name"], len(entries)
        except Exception:
            return sid, s["name"], 0

    with ThreadPoolExecutor(max_workers=8) as ex:
        for i, r in enumerate(ex.map(probe, items)):
            results.append(r)
            bar.progress((i + 1) / len(items), text=f"檢查中… {i + 1}/{len(items)}")
    bar.empty()

    dead = [r for r in results if r[2] == 0]
    alive = [r for r in results if r[2] > 0]
    if dead:
        st.error(f"有 {len(dead)} 個來源抓不到內容，建議到主題管理頁把它們移除：")
        for _, name, _ in dead:
            st.markdown(f"- ❌ **{name}**")
    else:
        st.success(f"全部 {len(alive)} 個來源都正常。")
    with st.expander(f"正常的來源（{len(alive)}）"):
        for _, name, n in sorted(alive, key=lambda x: -x[2]):
            st.markdown(f"- ✅ {name} — {n} 則")
