# -*- coding: utf-8 -*-
"""Streamlit 共用畫面元件。"""
import streamlit as st

from . import store
from .sources import SOURCES

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
    summary = _esc(a.get("summary") or a.get("raw_summary") or "（無摘要）")
    st.markdown(
        f'<div class="nr-card">'
        f'<div class="nr-title"><a href="{_esc(a["url"])}" target="_blank">{_esc(a["title"])}</a></div>'
        f'<div class="nr-meta">{badge}{_esc(a["source_name"])}{via}．{_esc(a.get("published_display", ""))}</div>'
        f'<div class="nr-summary">{summary}</div>'
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

    shown = articles
    if only_official:
        shown = [a for a in shown if a.get("official")]
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
    st.title("📚 資料來源清單")
    st.caption("本站不採用維基百科等共筆百科；優先使用政府機關與國際組織的第一手發布。")
    official = [(k, v) for k, v in SOURCES.items() if v["official"]]
    media = [(k, v) for k, v in SOURCES.items() if not v["official"]]

    st.subheader(f"✅ 官方／第一手來源（{len(official)}）")
    for _, s in official:
        st.markdown(f"**{s['name']}** — {s['note']}  \n`{s['url']}`")
    st.subheader(f"📰 媒體來源（{len(media)}）")
    for _, s in media:
        st.markdown(f"**{s['name']}** — {s['note']}  \n`{s['url']}`")
    st.divider()
    st.markdown(
        "使用者自訂主題另外會使用 **Google 新聞 RSS** 做關鍵字搜尋，"
        "它回傳的是各家新聞媒體的原始連結，不是百科內容。"
    )
