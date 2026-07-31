# -*- coding: utf-8 -*-
"""Groq LLM 呼叫封裝（免費方案）。

金鑰來源優先序：環境變數 GROQ_API_KEY → Streamlit secrets。
沒有金鑰時所有函式回傳 None，呼叫端必須有不依賴 LLM 的備援路徑。
"""
import json
import os
import re

MODEL = "llama-3.3-70b-versatile"


SESSION_KEY = "groq_api_key"


def get_api_key():
    """金鑰來源優先序：使用者當場輸入 → 環境變數 → Streamlit secrets。"""
    try:
        import streamlit as st
        typed = str(st.session_state.get(SESSION_KEY, "") or "").strip()
        if typed:
            return typed
    except Exception:
        pass

    key = os.environ.get("GROQ_API_KEY", "").strip()
    if key:
        return key
    try:
        import streamlit as st
        return str(st.secrets.get("GROQ_API_KEY", "")).strip()
    except Exception:
        return ""


def key_source():
    """回傳金鑰來自哪裡，用於在畫面上說明。"""
    try:
        import streamlit as st
        if str(st.session_state.get(SESSION_KEY, "") or "").strip():
            return "session"
    except Exception:
        pass
    if os.environ.get("GROQ_API_KEY", "").strip():
        return "env"
    try:
        import streamlit as st
        if str(st.secrets.get("GROQ_API_KEY", "")).strip():
            return "secrets"
    except Exception:
        pass
    return ""


def test_key():
    """實際打一次 API 確認金鑰有效，回傳 (成功?, 訊息)。"""
    if not get_api_key():
        return False, "尚未提供金鑰。"
    data = chat_json("只回傳 JSON。", '請回傳 {"ok": true}', max_tokens=50)
    if data is None:
        return False, "呼叫失敗，請確認金鑰是否正確、或稍後再試。"
    return True, f"金鑰有效，模型 {MODEL} 回應正常。"


def available():
    return bool(get_api_key())


def chat_json(system_prompt, user_prompt, max_tokens=4000, temperature=0.2):
    """呼叫 Groq 並要求回傳 JSON；失敗時回傳 None 而不是丟例外。"""
    key = get_api_key()
    if not key:
        return None
    try:
        from groq import Groq
        client = Groq(api_key=key)
        resp = client.chat.completions.create(
            model=MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
        )
        return _parse_json(resp.choices[0].message.content)
    except Exception as e:
        print(f"[llm] 呼叫失敗：{type(e).__name__}: {e}")
        return None


def _parse_json(text):
    if not text:
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    # 模型偶爾會包在 ```json 區塊裡
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None
    return None
