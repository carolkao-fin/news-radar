# -*- coding: utf-8 -*-
"""每日新聞雷達 — Streamlit 入口。

側邊欄的主題頁面是依 data/topics.json 動態產生的，
使用者新增主題後就會多出一個獨立頁面。
"""
import functools
import json
import re
from datetime import date, timedelta

import streamlit as st

from core import (github_sync, keywords as keywords_mod, llm, pipeline, report,
                  source_registry, store, topics as topics_mod, views)
from core.defaults import BUILTIN_TOPICS, DEFAULT_DAYS, MAX_DAYS

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

    for category, items in topics_mod.grouped_topics():
        st.markdown(f"### {category}")
        for t in items:
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
            st.caption("🟢 摘要由 Groq LLM 產生")
        else:
            st.caption("🟡 未設定 Groq 金鑰，摘要為原文清理版　—　"
                       "可到「⚙️ 更新與設定」啟用")


# ── 主題管理 ────────────────────────────────────────────────────
def _keyword_tools(t):
    """關鍵字的兩個自動化工具：重新產生、從實際新聞建議。"""
    k1, k2 = st.columns(2)

    if k1.button("♻️ 重新產生關鍵字", key=f"regen_{t['id']}",
                 help="依主題名稱重新展開，會與現有關鍵字合併，不會蓋掉你手動加的"):
        with st.spinner("產生中…"):
            added, how = topics_mod.regenerate_keywords(t["id"], use_llm=llm.available())
        label = "AI 產生" if how == "llm" else "詞庫展開"
        if added:
            st.success(f'（{label}）新增了 {len(added)} 個：{"、".join(added)}')
        else:
            st.info(f"（{label}）沒有可以再補的關鍵字。")
        st.rerun()

    if k2.button("💡 從實際新聞建議", key=f"sugg_{t['id']}",
                 help="試抓一次這個主題的新聞，統計實際出現的高頻詞"):
        with st.spinner("試抓並統計中…"):
            zh, en, n = topics_mod.suggest_keywords(t)
        st.session_state[f"sugg_res_{t['id']}"] = (zh, en, n)

    res = st.session_state.get(f"sugg_res_{t['id']}")
    if res:
        zh, en, n = res
        st.caption(f"從最近 {n} 則新聞統計出的候選詞：")
        if not (zh or en):
            st.info("沒有找到值得補充的新詞彙，現有關鍵字的涵蓋率應該已經夠了。")
        else:
            # 太籠統的詞（台灣、中國、科技⋯）仍然列出，但不預設勾選：
            # 這類詞在台灣媒體幾乎每篇都會出現，加進去等於沒有篩選
            default = [k for k in zh if not keywords_mod.is_broad_term(k)][:6]
            picked = st.multiselect("勾選要加入的關鍵字", zh + en,
                                    default=default, key=f"pick_{t['id']}")
            st.caption("灰色未勾選的通常是太籠統的詞（例如「台灣」「科技」），"
                       "加進去反而會抓到不相干的報導。")
            if st.button("加入選取的關鍵字", key=f"addkw_{t['id']}", disabled=not picked):
                cur_zh = list(t.get("keywords_zh", []))
                cur_en = list(t.get("keywords_en", []))
                for k in picked:
                    bucket = cur_en if k.isascii() else cur_zh
                    if k not in bucket:
                        bucket.append(k)
                topics_mod.update_topic(t["id"], keywords_zh=cur_zh, keywords_en=cur_en)
                st.session_state.pop(f"sugg_res_{t['id']}", None)
                st.success(f'已加入 {len(picked)} 個關鍵字')
                st.rerun()


def manage_topics():
    st.title("➕ 主題管理")
    st.caption("輸入一個主題名稱，系統會自動展開搜尋關鍵字並挑選來源，之後每天自動追蹤。")

    cats = topics_mod.all_categories()
    with st.form("add_topic"):
        name = st.text_input("新增主題", placeholder="例如：半導體出口管制、碳邊境稅 CBAM、東協經貿")
        c1, c2 = st.columns(2)
        with c1:
            cat_choice = st.selectbox("歸到哪個類別", ["（讓系統自動判斷）"] + cats + ["＋ 新增類別"])
        with c2:
            new_cat = st.text_input("新類別名稱", placeholder="上方選「＋ 新增類別」時填寫")
        use_llm = st.checkbox("用 AI 自動產生關鍵字與來源設定", value=llm.available(),
                              disabled=not llm.available(),
                              help="沒有金鑰時改用內建的領域詞庫展開，一樣會產生多個關鍵字")
        trial = st.checkbox("建立後立刻試抓一次，並從實際新聞建議更多關鍵字",
                            value=True, help="會多花 10～30 秒")
        submitted = st.form_submit_button("建立主題", type="primary")

    if submitted:
        category = None
        if cat_choice == "＋ 新增類別":
            category = new_cat.strip()
            if not category:
                st.error("選了「＋ 新增類別」就要填類別名稱。")
                submitted = False
        elif cat_choice != "（讓系統自動判斷）":
            category = cat_choice

        if submitted and not name.strip():
            st.error("請輸入主題名稱。")
        elif submitted:
            with st.spinner("正在產生搜尋設定…"):
                try:
                    t = topics_mod.add_topic(name, use_llm=use_llm, category=category)
                except ValueError as e:
                    st.error(str(e))
                    t = None
            if t:
                how = "AI 自動產生" if t.get("auto_by") == "llm" else "規則式展開"
                st.success(f'已建立「{t["name"]}」（{how}），歸類到「{t["category"]}」，'
                           f"左側該類別下會出現新頁面。")
                st.json({
                    "類別": t["category"],
                    "關鍵字（中）": t["keywords_zh"],
                    "關鍵字（英）": t["keywords_en"],
                    "搜尋查詢": t["news_queries"],
                    "使用來源": [source_registry.source_name(s) for s in t["sources"]],
                })
                if trial:
                    with st.spinner("試抓中…"):
                        zh, en, n = topics_mod.suggest_keywords(t)
                    if n:
                        st.info(f"試抓到 **{n} 則**新聞。")
                        if zh or en:
                            st.markdown("從實際內容看，這些詞也常出現，可以考慮補進關鍵字：")
                            st.code("、".join(zh[:12] + en[:4]), language=None)
                            st.caption("展開下方該主題的設定即可加入。")
                    else:
                        st.warning(
                            "試抓不到新聞。可能是關鍵字太窄、或這個主題最近沒有報導 —— "
                            "可以在下方加幾個同義詞，或把收錄天數拉長。")
                if st.button("重新整理頁面"):
                    st.rerun()

    st.divider()
    st.subheader("現有主題")
    all_topics = store.load_topics()
    if not all_topics:
        st.info("目前沒有任何主題。")
        if st.button("🔄 還原內建的三個主題", type="primary"):
            topics_mod.restore_builtins()
            st.rerun()
        return

    missing = [b["name"] for b in BUILTIN_TOPICS
               if b["id"] not in {t["id"] for t in all_topics}]
    if missing:
        st.info(f'已刪除的內建主題：{"、".join(missing)}')
        if st.button("🔄 還原這些內建主題"):
            restored = topics_mod.restore_builtins()
            st.success(f'已還原：{"、".join(restored)}')
            st.rerun()

    for t in all_topics:
        with st.expander(f'{t.get("emoji", "📌")} {t["name"]}'
                         f'　`{topics_mod.category_of(t)}`'
                         f'{"（內建）" if t.get("builtin") else ""}'
                         f'{"" if t.get("enabled", True) else "　⏸ 已停用"}'):
            st.caption(t.get("description", ""))
            cc1, cc2 = st.columns(2)
            with cc1:
                cur = topics_mod.category_of(t)
                opts = cats + ([cur] if cur not in cats else []) + ["＋ 新增類別"]
                pick = st.selectbox("類別", opts, index=opts.index(cur), key=f"cat_{t['id']}")
            with cc2:
                typed = st.text_input("新類別名稱", key=f"newcat_{t['id']}",
                                      placeholder="左邊選「＋ 新增類別」時填寫")
            kz = st.text_area("中文關鍵字（逗號分隔）", ", ".join(t.get("keywords_zh", [])),
                              key=f"kz_{t['id']}", height=68)
            ke = st.text_area("英文關鍵字（逗號分隔）", ", ".join(t.get("keywords_en", [])),
                              key=f"ke_{t['id']}", height=68)
            _keyword_tools(t)
            qs = st.text_area("新聞搜尋查詢（一行一組，格式：查詢字串 | zh 或 en）",
                              "\n".join(f'{q["q"]} | {q.get("lang", "zh")}'
                                        for q in t.get("news_queries", [])),
                              key=f"q_{t['id']}", height=90)
            catalog = source_registry.all_sources()
            picked = st.multiselect(
                "指定 RSS 來源（只會從這裡列出的來源抓取）",
                options=list(catalog.keys()),
                default=[s for s in t.get("sources", []) if s in catalog],
                format_func=lambda s: (
                    f'{catalog[s]["name"]}'
                    f'{"（官方）" if catalog[s]["official"] else ""}'
                    f'{"（自訂）" if catalog[s].get("custom") else ""}'),
                key=f"src_{t['id']}",
                help="要加入清單裡沒有的網站，到「📚 資料來源」頁新增自訂 RSS 來源。")

            dc1, dc2 = st.columns(2)
            with dc1:
                days_val = st.number_input(
                    "收錄最近幾天（0 = 用全域預設）", min_value=0, max_value=MAX_DAYS,
                    value=int(t.get("days") or 0), step=1, key=f"days_{t['id']}",
                    help=f"全域預設是 {DEFAULT_DAYS} 天。發布頻率低的主題可以設長一點。")
            with dc2:
                search_on = st.checkbox(
                    "併用 Google 新聞搜尋", value=t.get("search_enabled", True),
                    key=f"srch_{t['id']}",
                    help="取消勾選就只會從上面指定的 RSS 來源抓取，完全不使用搜尋結果。")
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
                category = typed.strip() if pick == "＋ 新增類別" else pick
                if not category:
                    st.error("選了「＋ 新增類別」就要填類別名稱。")
                else:
                    topics_mod.update_topic(
                        t["id"], category=category,
                        keywords_zh=[x.strip() for x in kz.split(",") if x.strip()],
                        keywords_en=[x.strip() for x in ke.split(",") if x.strip()],
                        news_queries=queries, sources=picked, enabled=enabled,
                        days=int(days_val) or None, search_enabled=search_on,
                    )
                    st.success("已儲存")
                    st.rerun()

            if c2.button("🔄 立即抓這個主題", key=f"run_{t['id']}"):
                with st.spinner("抓取中…"):
                    arts, brief = pipeline.update_topic(t, limit=20,
                                                        use_llm=llm.available())
                    snap = store.merge_into_today(t["id"], arts)
                    if brief:
                        meta = snap.get("meta", {})
                        meta.setdefault("briefs", {})[t["id"]] = brief
                        store.save_news(snap["date"], snap["topics"], meta)
                st.success(f"抓到 {len(arts)} 則，切換到該主題頁面即可查看。")

            if t.get("builtin") and c3.button("↩️ 還原出廠設定", key=f"reset_{t['id']}"):
                topics_mod.reset_topic(t["id"])
                st.success("已還原成出廠設定")
                st.rerun()

            st.divider()
            confirm = st.checkbox("我要刪除這個主題", key=f"cfm_{t['id']}")
            if st.button("🗑 刪除主題", key=f"del_{t['id']}", disabled=not confirm):
                topics_mod.delete_topic(t["id"])
                st.rerun()
            if t.get("builtin"):
                st.caption("內建主題刪掉之後，可以在上方用「還原內建主題」加回來。")

    _backup_section(all_topics)


_GH_SOURCE_LABEL = {
    "session": "你剛才在這一頁輸入的（只在這個瀏覽器分頁有效）",
    "env": "環境變數 GITHUB_TOKEN",
    "secrets": "Streamlit Secrets",
}


def _github_sync_section():
    """設定 GitHub Token 後，主題／類別／自訂來源的每次修改都會自動寫回 repo，
    重新部署時容器拉到的就是使用者的最新設定。"""
    st.subheader("🔗 自動保存到 GitHub")
    s = github_sync.status()

    if s["enabled"]:
        st.success(
            f'已啟用自動保存 —— 新增或修改主題、類別、自訂來源時，會自動寫回 '
            f'`{s["repo"]}`（`{s["branch"]}` 分支）。重新部署後設定會保留。'
            f'　金鑰來源：{_GH_SOURCE_LABEL.get(s["token_source"], s["token_source"])}'
        )
        last = github_sync.last_result()
        if last:
            (st.caption if last["ok"] else st.error)(
                f'最近一次同步：{last["msg"]}')
        st.caption(
            "每次同步都是一個 commit，Streamlit Cloud 會因此重新部署一次（約 1 分鐘）。"
            "內容沒有實際變動時不會產生 commit。")
    else:
        st.warning(
            "**尚未啟用自動保存。** 目前在網站上新增的主題與類別只存在這個容器裡，"
            "Streamlit Cloud 重新部署（例如每天排程 commit 新聞後）就會還原成 GitHub 上的版本。"
            "設定 Token 之後就不用再手動下載 `topics.json`。"
        )

    with st.expander("🔑 設定 GitHub Token", expanded=not s["enabled"]):
        st.markdown(
            "**產生 Token**：GitHub → Settings → Developer settings → "
            "Personal access tokens → **Fine-grained tokens** → Generate new token\n\n"
            f"- Repository access：只選 `{s['repo']}` 這一個 repo\n"
            "- Permissions → Repository permissions → **Contents 設為 Read and write**\n\n"
            "**設定位置**（擇一，效果不同）：\n"
            "1. **下方直接貼上** — 立刻可用，但只在目前這個瀏覽器分頁有效，適合先試。\n"
            "2. **Streamlit Secrets**（Manage app → Settings → Secrets）— "
            "**建議用這個**，重開也還在：\n"
            "```toml\n"
            'GITHUB_TOKEN = "github_pat_..."\n'
            f'GITHUB_REPO = "{github_sync.DEFAULT_REPO}"   # 預設值，用自己的 repo 才要改\n'
            f'GITHUB_BRANCH = "{github_sync.DEFAULT_BRANCH}"\n'
            "```"
        )
        typed = st.text_input("GitHub Token", type="password",
                              value=st.session_state.get(github_sync.SESSION_KEY, ""),
                              placeholder="github_pat_...")
        c1, c2, c3 = st.columns(3)
        if c1.button("套用 Token"):
            st.session_state[github_sync.SESSION_KEY] = typed.strip()
            st.rerun()
        if c2.button("清除", disabled=not st.session_state.get(github_sync.SESSION_KEY)):
            st.session_state[github_sync.SESSION_KEY] = ""
            st.rerun()
        if c3.button("🧪 測試 Token"):
            with st.spinner("連線 GitHub…"):
                ok, msg = github_sync.test_token()
            (st.success if ok else st.error)(msg)

    if s["enabled"]:
        c1, c2 = st.columns(2)
        if c1.button("⬆️ 立即把目前設定推回 GitHub",
                     help="平常存檔就會自動同步，這是手動補推一次"):
            with st.spinner("同步中…"):
                results = [
                    github_sync.push_text(
                        store.TOPICS_REPO_PATH,
                        store.topics_json(store.load_topics()),
                        "更新主題設定（來自網站）"),
                    github_sync.push_text(
                        source_registry.CUSTOM_REPO_PATH,
                        source_registry.custom_json(source_registry.load_custom()),
                        "更新自訂 RSS 來源（來自網站）"),
                ]
            for ok, msg in results:
                (st.success if ok else st.error)(msg)

        if c2.button("⬇️ 從 GitHub 取回設定",
                     help="用 repo 上的版本覆蓋這個容器裡的設定"):
            with st.spinner("讀取中…"):
                try:
                    topics_text, _ = github_sync.pull_text(store.TOPICS_REPO_PATH)
                    src_text, _ = github_sync.pull_text(source_registry.CUSTOM_REPO_PATH)
                except Exception as e:  # noqa: BLE001
                    topics_text = src_text = None
                    st.error(f"讀取失敗：{e}")
            if topics_text:
                store.save_topics(json.loads(topics_text).get("topics", []), sync=False)
                if src_text:
                    source_registry.save_custom(
                        json.loads(src_text).get("sources", {}), sync=False)
                st.success("已用 GitHub 上的版本覆蓋主題與自訂來源設定。")
                st.rerun()
            elif topics_text is None:
                st.warning("GitHub 上找不到 data/topics.json。")


def _backup_section(all_topics):
    st.divider()
    _github_sync_section()

    st.divider()
    st.subheader("💾 手動備份")
    st.caption(
        "沒有設定 GitHub Token 時的備援方式："
        "把 `topics.json` 下載下來，覆蓋回 repo 的 `data/topics.json` 並 push，設定才會永久保留。"
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
_KEY_SOURCE_LABEL = {
    "session": "你剛才在這一頁輸入的（只在這個瀏覽器分頁有效）",
    "env": "環境變數 GROQ_API_KEY",
    "secrets": "Streamlit Secrets",
}


def _summary_section():
    """AI 摘要設定：金鑰、測試、只重新產生摘要。"""
    st.subheader("✍️ AI 摘要")

    src = llm.key_source()
    if src:
        st.success(f"已啟用 AI 摘要，模型 `{llm.MODEL}`　—　金鑰來源：{_KEY_SOURCE_LABEL[src]}")
    else:
        st.warning(
            "目前沒有 Groq 金鑰，摘要是**清理後的原文前段**（不是 AI 寫的），"
            "各主題的「今日重點」導讀也不會產生。"
        )

    with st.expander("🔑 設定 Groq 金鑰", expanded=not src):
        st.markdown(
            "Groq 免費申請：https://console.groq.com/keys\n\n"
            "**三種設定方式，效果不同：**\n"
            "1. **下方直接貼上** — 立刻可用，但只在目前這個瀏覽器分頁有效，關掉就沒了。適合先試用。\n"
            "2. **Streamlit Secrets**（Manage app → Settings → Secrets）— "
            "網站上按「立即更新」時會用到，重開也還在。\n"
            "3. **GitHub Actions Secret**（repo → Settings → Secrets and variables → Actions）— "
            "**每日排程要用這個**，只設 Streamlit 的話，每天自動抓的摘要還是原文前段。"
        )
        typed = st.text_input("Groq API Key", type="password",
                              value=st.session_state.get(llm.SESSION_KEY, ""),
                              placeholder="gsk_...")
        c1, c2 = st.columns(2)
        if c1.button("套用金鑰"):
            st.session_state[llm.SESSION_KEY] = typed.strip()
            st.rerun()
        if c2.button("清除", disabled=not st.session_state.get(llm.SESSION_KEY)):
            st.session_state[llm.SESSION_KEY] = ""
            st.rerun()
        if st.button("🧪 測試金鑰是否有效"):
            with st.spinner("呼叫 Groq…"):
                ok, msg = llm.test_key()
            (st.success if ok else st.error)(msg)

    st.caption(
        "重新產生摘要不會重新連線抓新聞，只是把已經抓下來的內容重新寫一次摘要，"
        "設定金鑰後用這個最快。"
    )
    active = topics_mod.enabled_topics()
    if st.button("✍️ 重新產生今天的摘要", type="primary" if src else "secondary",
                 disabled=not active):
        box = st.empty()
        with st.spinner("產生中…"):
            snap, n = pipeline.resummarize(
                active, use_llm=llm.available(), progress=lambda m: box.caption(m))
        box.empty()
        if not snap:
            st.error("今天還沒有抓到任何新聞，請先按下方的「立即更新」。")
        else:
            how = "AI 摘要" if src else "原文清理"
            st.success(f"已重新產生 {n} 則摘要（{how}）。")


def update_page():
    st.title("⚙️ 更新與設定")

    st.subheader("狀態")
    dates = store.available_dates()
    c1, c2 = st.columns(2)
    c1.metric("已累積天數", len(dates))
    c2.metric("最新資料", dates[0] if dates else "—")
    st.divider()
    _summary_section()

    st.divider()
    st.subheader("手動更新")
    st.caption("每日排程由 GitHub Actions 在台灣時間早上 7:00 執行；這裡是臨時手動觸發。")
    active = topics_mod.enabled_topics()
    picked = st.multiselect("要更新的主題", [t["id"] for t in active],
                            default=[t["id"] for t in active],
                            format_func=lambda i: next(t["name"] for t in active if t["id"] == i))
    days = st.slider("收錄最近幾天的新聞", 1, MAX_DAYS, DEFAULT_DAYS,
                     help="這是全域預設值；主題若自己設定了天數，會以主題的設定為準。"
                          "官方機關發布頻率低，窗口拉長比較不會空頁。")
    limit = st.slider("每個主題最多保留幾則", 5, 60, 20)

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
        st.caption("要匯出成 Word 或打包 JSON，請到左側「📥 下載紀錄」頁自由選擇期間。")
        snap = store.load_news(dates[0])
        st.download_button(
            f"下載 {dates[0]} 的完整資料（JSON）",
            data=json.dumps(snap, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"news-{dates[0]}.json", mime="application/json")

        if github_sync.enabled():
            st.caption(
                "在網站上按「立即更新」抓到的新聞只存在這個容器裡，"
                "重新部署後會還原成 GitHub 上的版本（排程抓的則不受影響）。"
                "想留住剛才手動抓的結果，按這裡推回 repo。")
            if st.button(f"⬆️ 把 {dates[0]} 的快照推回 GitHub"):
                with st.spinner("同步中…"):
                    ok, msg = github_sync.push_text(
                        f"data/news/{dates[0]}.json",
                        json.dumps(snap, ensure_ascii=False, indent=2),
                        f"更新 {dates[0]} 新聞快照（來自網站）")
                (st.success if ok else st.error)(msg)
    else:
        st.caption("尚無資料。")


# ── 下載紀錄 ────────────────────────────────────────────────────
def _range_presets(d_min, d_max):
    """快速選擇按鈕；直接改寫 date_input 的 session_state 再 rerun。"""
    c1, c2, c3, c4 = st.columns(4)
    presets = [(c1, "最近 7 天", 6), (c2, "最近 30 天", 29),
               (c3, "最近 90 天", 89), (c4, "全部", None)]
    for col, label, back in presets:
        if col.button(label, key=f"preset_{label}", use_container_width=True):
            start = d_min if back is None else max(d_min, d_max - timedelta(days=back))
            st.session_state["dl_range"] = (start, d_max)
            st.rerun()


def download_page():
    st.title("📥 下載紀錄")
    st.caption("自由選擇期間，把過去累積的每日新聞匯出成 Word 檔（.docx）留存或轉寄。")

    dates = store.available_dates()
    if not dates:
        views.no_data_hint()
        return

    d_min, d_max = date.fromisoformat(dates[-1]), date.fromisoformat(dates[0])
    st.caption(f"目前資料庫涵蓋 {d_min} ～ {d_max}，共 {len(dates)} 天。")

    if "dl_range" not in st.session_state:
        st.session_state["dl_range"] = (max(d_min, d_max - timedelta(days=6)), d_max)
    _range_presets(d_min, d_max)
    picked = st.date_input("下載期間（點兩次選起訖日）", min_value=d_min, max_value=d_max,
                           key="dl_range", format="YYYY-MM-DD")

    if not isinstance(picked, (tuple, list)) or len(picked) != 2:
        st.info("請再點一次選擇結束日期。")
        return
    start, end = picked
    sel = report.dates_in_range(start, end)
    if not sel:
        st.warning(f"{start} ～ {end} 之間沒有任何快照。"
                   "每日排程從建站當天才開始累積，請把期間往後拉。")
        return
    st.success(f"選取 {start} ～ {end}，其中 **{len(sel)} 天**有資料。")

    # ── 內容選項 ──
    avail_topics = report.topics_in_dates(sel)
    picked_topics = st.multiselect(
        "要包含的主題", [tid for tid, _ in avail_topics],
        default=[tid for tid, _ in avail_topics],
        format_func=lambda i: next(n for t, n in avail_topics if t == i),
        help="只列出這段期間實際有資料的主題（含已刪除的舊主題）。")

    with st.expander("⚙️ 版面與內容設定"):
        c1, c2 = st.columns(2)
        with c1:
            only_official = st.checkbox("只收錄官方／第一手來源", value=False)
            include_summary = st.checkbox("包含摘要內文", value=True)
            include_bullets = st.checkbox("包含重點條列", value=True)
        with c2:
            include_overview = st.checkbox("附上各日則數總表", value=True)
            oldest_first = st.checkbox("日期由舊到新排列", value=False,
                                       help="不勾選則與網站一致，最新的日期排在最前面。")
            limit = st.number_input("每個主題每天最多幾則（0 = 全部）",
                                    min_value=0, max_value=60, value=0, step=5)

    if not picked_topics:
        st.warning("至少要選一個主題。")
        return

    preview = report.collect(sel, topic_ids=set(picked_topics),
                             only_official=only_official,
                             limit_per_topic=int(limit))
    n_articles = sum(len(arts) for _d, _s, blocks in preview
                     for _tid, _name, _brief, arts in blocks)
    st.caption(f"預計匯出 {len(preview)} 天、{n_articles} 則新聞。")

    if st.button("📄 產生 Word 檔", type="primary", disabled=not n_articles):
        with st.spinner("排版中…"):
            try:
                st.session_state["dl_docx"] = report.build_docx(
                    sel, topic_ids=set(picked_topics), only_official=only_official,
                    include_summary=include_summary, include_bullets=include_bullets,
                    include_overview=include_overview, limit_per_topic=int(limit),
                    oldest_first=oldest_first)
                st.session_state["dl_docx_name"] = report.filename(sel, "docx")
            except Exception as e:  # noqa: BLE001 — 直接把錯誤顯示給使用者
                st.session_state.pop("dl_docx", None)
                st.error(f"產生失敗：{e}")
    if not n_articles:
        st.warning("目前的篩選條件下沒有任何新聞，調整主題或取消「只收錄官方來源」再試。")

    blob = st.session_state.get("dl_docx")
    if blob:
        st.download_button(
            f'⬇️ 下載 {st.session_state["dl_docx_name"]}（{len(blob) / 1024:.0f} KB）',
            data=blob, file_name=st.session_state["dl_docx_name"], type="primary",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

    st.divider()
    st.caption("需要原始資料做後續處理時，可以打包這段期間的 JSON 快照。")
    st.download_button(
        f"下載原始 JSON（{len(sel)} 天，zip）",
        data=report.build_json_zip(sel),
        file_name=report.filename(sel, "zip"), mime="application/zip")


def sources_page():
    views.render_source_catalog()


# ── 動態導覽 ────────────────────────────────────────────────────
def build_nav():
    """側邊欄：總覽 →（依類別分組的主題頁）→ 設定。"""
    topics_mod.ensure_topics()
    pages = {
        "總覽": [st.Page(home, title="今日總覽", icon="📡", url_path="home", default=True)],
    }
    for category, items in topics_mod.grouped_topics():
        group = []
        for t in items:
            fn = functools.partial(views.render_topic_page, t)
            fn.__name__ = f'topic_{t["id"]}'
            group.append(
                st.Page(fn, title=t["name"], icon=t.get("emoji", "📌"), url_path=_url_path(t))
            )
        if group:
            # 用 extend 而非直接指派，萬一使用者把類別命名成「總覽」也不會蓋掉既有頁面
            pages.setdefault(category, []).extend(group)
    pages.setdefault("設定", []).extend([
        st.Page(manage_topics, title="主題管理", icon="➕", url_path="topics"),
        st.Page(update_page, title="更新與設定", icon="⚙️", url_path="update"),
        st.Page(download_page, title="下載紀錄", icon="📥", url_path="download"),
        st.Page(sources_page, title="資料來源", icon="📚", url_path="sources"),
    ])
    return st.navigation(pages)


build_nav().run()
