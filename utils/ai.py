import os
import json
import urllib.request
import urllib.error

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

SYSTEM_PROMPT = (
    "你是 SPYC Bot 嘅 AI 助手，服務沙田培英書院 (SPYC) 嘅學生。"
    "用繁體中文回答（可以用廣東話口吻），答案要簡潔、準確、有用。"
    "如果學生問功課問題，引導佢思考，唔好直接俾晒答案。"
    "涉及危險或不當內容一律拒絕。"
)


def gemini_available():
    return bool((os.getenv("GEMINI_API_KEY") or "").strip())


def nim_available():
    return bool((os.getenv("NIM_API_KEY") or "").strip())


def default_provider():
    """auto: gemini 優先，其次 nim，冇 key return None"""
    pref = (os.getenv("AI_PROVIDER") or "auto").strip().lower()
    if pref == "gemini" and gemini_available():
        return "gemini"
    if pref == "nim" and nim_available():
        return "nim"
    if gemini_available():
        return "gemini"
    if nim_available():
        return "nim"
    return None


def _post_json(url, payload, headers, timeout=45):
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "ignore")[:300]
        except Exception:
            body = ""
        raise RuntimeError(f"HTTP {e.code}: {body}") from None


def _ask_gemini(question, model=None):
    api_key = os.getenv("GEMINI_API_KEY").strip()
    model = (model or os.getenv("GEMINI_MODEL") or "gemini-2.0-flash").strip()
    url = GEMINI_URL.format(model=model) + f"?key={api_key}"
    payload = {
        "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
        "contents": [{"role": "user", "parts": [{"text": question}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
    }
    data = _post_json(url, payload, {"Content-Type": "application/json"})
    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
        if not text:
            raise KeyError
        return text, f"gemini · {model}"
    except (KeyError, IndexError):
        try:
            reason = data["candidates"][0].get("finishReason", "?")
        except Exception:
            reason = "?"
        raise RuntimeError(f"Gemini 冇回應內容（{reason}）")


def _ask_nim(question, model=None):
    api_key = os.getenv("NIM_API_KEY").strip()
    model = (model or os.getenv("NIM_MODEL") or "meta/llama-3.1-8b-instruct").strip()
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "max_tokens": 1024,
        "temperature": 0.7,
    }
    data = _post_json(
        NIM_URL,
        payload,
        {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
    )
    try:
        text = (data["choices"][0]["message"]["content"] or "").strip()
        if not text:
            raise KeyError
        return text, f"nim · {model}"
    except (KeyError, IndexError):
        raise RuntimeError("NIM 冇回應內容")


def ask_ai(question, provider=None, model=None):
    """同步函數 — cog 入面用 asyncio.to_thread 包住佢。
    Return (answer, provider_label)。"""
    prov = provider or default_provider()
    if prov == "gemini":
        if not gemini_available():
            raise RuntimeError("NO_KEY:GEMINI")
        return _ask_gemini(question, model)
    if prov == "nim":
        if not nim_available():
            raise RuntimeError("NO_KEY:NIM")
        return _ask_nim(question, model)
    raise RuntimeError("NO_PROVIDER")