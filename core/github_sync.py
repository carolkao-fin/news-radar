# -*- coding: utf-8 -*-
"""把設定檔自動寫回 GitHub repo，讓使用者的修改能撐過重新部署。

Streamlit Community Cloud 的檔案系統是暫時性的：服務重啟或每次重新部署，
容器都會還原成 GitHub 上的版本。因此使用者在網站上新增的主題、類別、自訂來源
若只寫進本機檔案，重新部署就會消失。

這裡用 GitHub Contents API 把 `data/topics.json` 與 `data/sources.json`
直接 commit 回 repo —— 之後不管重啟幾次，容器拉到的都是使用者最新的設定。

沒有設定 Token 時所有函式安全地不做事（`enabled()` 回傳 False），
使用者仍可用「下載／上傳 JSON」的手動方式保存，網站功能不受影響。
"""
import base64
import json
import os

import requests

API = "https://api.github.com"
SESSION_KEY = "github_token"
DEFAULT_REPO = "carolkao-fin/news-radar"
DEFAULT_BRANCH = "main"
TIMEOUT = 20


# ── 設定來源 ────────────────────────────────────────────────────
def _secret(name):
    try:
        import streamlit as st
        return str(st.secrets.get(name, "") or "").strip()
    except Exception:
        return ""


def get_token():
    """優先序：使用者當場輸入 → 環境變數 → Streamlit secrets。"""
    try:
        import streamlit as st
        typed = str(st.session_state.get(SESSION_KEY, "") or "").strip()
        if typed:
            return typed
    except Exception:
        pass
    return os.environ.get("GITHUB_TOKEN", "").strip() or _secret("GITHUB_TOKEN")


def token_source():
    try:
        import streamlit as st
        if str(st.session_state.get(SESSION_KEY, "") or "").strip():
            return "session"
    except Exception:
        pass
    if os.environ.get("GITHUB_TOKEN", "").strip():
        return "env"
    if _secret("GITHUB_TOKEN"):
        return "secrets"
    return ""


def get_repo():
    return (os.environ.get("GITHUB_SYNC_REPO", "").strip()
            or _secret("GITHUB_REPO") or DEFAULT_REPO)


def get_branch():
    return (os.environ.get("GITHUB_SYNC_BRANCH", "").strip()
            or _secret("GITHUB_BRANCH") or DEFAULT_BRANCH)


def in_actions():
    """在 GitHub Actions 裡跑的時候不要回寫，排程本來就會自己 commit。"""
    return os.environ.get("GITHUB_ACTIONS", "").lower() == "true"


def enabled():
    return bool(get_token()) and not in_actions()


def status():
    """給畫面用的狀態摘要。"""
    return {
        "enabled": enabled(),
        "token_source": token_source(),
        "repo": get_repo(),
        "branch": get_branch(),
        "in_actions": in_actions(),
    }


# ── API ────────────────────────────────────────────────────────
def _headers():
    return {
        "Authorization": f"Bearer {get_token()}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _contents_url(path):
    return f"{API}/repos/{get_repo()}/contents/{path}"


def _get_sha(path):
    """檔案在 repo 裡目前的 sha；不存在時回傳 None（代表要新建）。"""
    r = requests.get(_contents_url(path), headers=_headers(),
                     params={"ref": get_branch()}, timeout=TIMEOUT)
    if r.status_code == 404:
        return None
    r.raise_for_status()
    return r.json().get("sha")


def pull_text(path):
    """讀 repo 上該檔案的內容，回傳 (文字, sha)；不存在時回傳 (None, None)。"""
    r = requests.get(_contents_url(path), headers=_headers(),
                     params={"ref": get_branch()}, timeout=TIMEOUT)
    if r.status_code == 404:
        return None, None
    r.raise_for_status()
    data = r.json()
    return base64.b64decode(data["content"]).decode("utf-8"), data.get("sha")


def _same_content(a, b):
    """比較兩份 JSON 是否實質相同 —— `updated_at` 只是存檔時間戳，不算差異。

    不忽略它的話，按一次「儲存」但什麼都沒改也會產生 commit，
    而每個 commit 都會觸發 Streamlit Cloud 重新部署。
    """
    if a == b:
        return True
    try:
        da, db = json.loads(a), json.loads(b)
    except (ValueError, TypeError):
        return False
    if isinstance(da, dict) and isinstance(db, dict):
        da.pop("updated_at", None)
        db.pop("updated_at", None)
        return da == db
    return False


def push_text(path, text, message):
    """把文字內容 commit 到 repo，回傳 (成功?, 訊息)。

    內容實質相同時直接跳過，避免產生一堆空 commit
    （每個 commit 都會觸發 Streamlit Cloud 重新部署）。
    """
    if not get_token():
        return False, "尚未設定 GitHub Token。"
    if in_actions():
        return False, "在 GitHub Actions 環境中不做回寫。"

    try:
        current, sha = pull_text(path)
        if current is not None and _same_content(current, text):
            return True, f"{path} 內容與 GitHub 上相同，不需要更新。"

        payload = {
            "message": message,
            "content": base64.b64encode(text.encode("utf-8")).decode("ascii"),
            "branch": get_branch(),
        }
        if sha:
            payload["sha"] = sha
        r = requests.put(_contents_url(path), headers=_headers(),
                         json=payload, timeout=TIMEOUT)
        if r.status_code == 409:
            # 別人（例如每日排程）剛好也在改，取新的 sha 再試一次
            payload["sha"] = _get_sha(path)
            r = requests.put(_contents_url(path), headers=_headers(),
                             json=payload, timeout=TIMEOUT)
        if r.status_code in (200, 201):
            return True, f"已同步 {path} 到 {get_repo()}（{get_branch()} 分支）。"
        return False, _error_message(r)
    except requests.RequestException as e:
        return False, f"連線 GitHub 失敗：{e}"


def _error_message(r):
    try:
        msg = r.json().get("message", r.text[:200])
    except ValueError:
        msg = r.text[:200]
    hints = {
        401: "Token 無效或已過期。",
        403: "Token 權限不足，需要對這個 repo 的 Contents 寫入權限。",
        404: "找不到 repo 或分支，請確認 GITHUB_REPO 設定正確、且 Token 看得到這個 repo。",
        422: "分支名稱或檔案路徑有誤。",
    }
    return f"GitHub 回應 {r.status_code}：{hints.get(r.status_code, '')}{msg}"


def test_token():
    """實際打一次 API 確認 Token 可用且對該 repo 有寫入權限。"""
    if not get_token():
        return False, "尚未設定 GitHub Token。"
    try:
        r = requests.get(f"{API}/repos/{get_repo()}", headers=_headers(), timeout=TIMEOUT)
        if r.status_code != 200:
            return False, _error_message(r)
        perms = r.json().get("permissions", {})
        if not perms.get("push"):
            return False, (f"Token 讀得到 {get_repo()}，但沒有寫入權限。"
                           "請確認 fine-grained token 的 Contents 設為 Read and write。")
        return True, f"Token 有效，對 {get_repo()} 有寫入權限。"
    except requests.RequestException as e:
        return False, f"連線 GitHub 失敗：{e}"


# ── 給 store / source_registry 呼叫的自動同步 ──────────────────
def autosync(path, text, message):
    """存檔後順手回寫 GitHub。失敗不丟例外，只把結果記在 session 供畫面顯示。"""
    if not enabled():
        return None
    ok, msg = push_text(path, text, message)
    try:
        import streamlit as st
        st.session_state["gh_last_sync"] = {"ok": ok, "msg": msg, "path": path}
    except Exception:
        pass
    return ok, msg


def last_result():
    try:
        import streamlit as st
        return st.session_state.get("gh_last_sync")
    except Exception:
        return None
