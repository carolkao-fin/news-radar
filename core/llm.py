# -*- coding: utf-8 -*-
"""Groq LLM 呼叫封裝（免費方案）。

金鑰來源優先序：環境變數 GROQ_API_KEY → Streamlit secrets。
沒有金鑰時所有函式回傳 None，呼叫端必須有不依賴 LLM 的備援路徑。
"""
import json
import os
import re

MODEL = "llama-3.3-70b-versatile"


def get_api_key():
    key = os.environ.get("GROQ_API_KEY", "").strip()
    if key:
        return key
    try:
        import streamlit as st
        return str(st.secrets.get("GROQ_API_KEY", "")).strip()
    except Exception:
        return ""


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
