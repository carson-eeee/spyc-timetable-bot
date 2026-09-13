import os
import json
import time
import urllib.request
import urllib.error

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
NIM_URL = "https://integrate.api.nvidia.com/v1/chat/completions"
NIM_MODELS_URL = "https://integrate.api.nvidia.com/v1/models"   # 🔄 模型列表

SYSTEM_PROMPT = (
    "你是 SPYC Bot 嘅 AI 助手，服務沙田培英書院 (SPYC) 嘅學生。"
    "用繁體中文回答（可以用廣東話口吻），答案要簡潔、準確、有用。"
    "如果學生問功課問題，引導佢思考，唔好直接俾晒答案。"
    "涉及危險或不當內容一律拒絕。"
)

# ============================================================
# 🔄 NIM 模型自動管理
# ============================================================
NIM_CACHE_TTL = 3600   # 模型列表 cache 一個鐘

# 自動轉模型嗰陣嘅揀模型優先次序
NIM_PREFERRED = [
    "meta/llama-3.3-70b-instruct",
    "nvidia/llama-3.1-nemotron-70b-instruct",
    "meta/llama-3.1-70b-instruct",
    "qwen/qwen2.5-72b-instruct",
    "mistralai/mixtral-8x22b-instruct",
    "deepseek-ai/deepseek-r1",
    "meta/llama-3.1-8b-instruct",
    "qwen/qwen2.5-7b-instruct",
]
NIM_FALLBACK = "meta/llama-3.3-70b-instruct"

# 呢啲 keyword 嘅模型唔係傾偈用（embedding/畫圖/語音嗰啲），自動揀嗰陣跳過
NIM_EXCLUDE_KEYWORDS = (
    "embed", "rerank", "retriever", "clip", "sdxl", "stable-diffusion",
    "flux", "sana", "cosmos", "ocr", "whisper", "tts", "asr", "guard",
    "vlm", "nv-dinov2", "segformer", "detr",
)

_nim_cache = {"models": None, "fetched_at": 0}
_current_nim_model = None


# ============================================================
# 基本檢查
# ============================================================
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


# ============================================================
# HTTP helpers
# ============================================================
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


def _get_json_auth(url, api_key, timeout=15):
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {api_key}"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        try:
            body = e.read().decode("utf-8", "ignore")[:300]
        except Exception:
            body = ""
        raise RuntimeError(f"HTTP {e.code}: {body}") from None


# ============================================================
# 🔄 NIM 模型列表 + 自動轉模型
# ============================================================
def fetch_nim_models(force=False):
    """攞 NIM 而家可用嘅模型列表（cache 1 個鐘）。
    Return model ID list；完全失敗 return []。"""
    global _nim_cache
    now = time.time()
    if (not force and _nim_cache["models"] is not None
            and now - _nim_cache["fetched_at"] < NIM_CACHE_TTL):
        return _nim_cache["models"]

    api_key = (os.getenv("NIM_API_KEY") or "").strip()
    if not api_key:
        return []
    try:
        data = _get_json_auth(NIM_MODELS_URL, api_key)
        models = sorted(m.get("id") for m in data.get("data", []) if m.get("id"))
        if models:
            _nim_cache = {"models": models, "fetched_at": now}
        return models
    except Exception as e:
        print(f"❌ [ai] 攞 NIM 模型列表失敗: {e}")
        # 攞唔到新嘅就退返用舊 cache
        return _nim_cache["models"] or []


def current_nim_model():
    """而家實際用緊嘅 NIM model"""
    return _current_nim_model


def _chat_suitable(m):
    """係咪一個用嚟傾偈嘅模型"""
    ml = m.lower()
    if any(k in ml for k in NIM_EXCLUDE_KEYWORDS):
        return False
    return "instruct" in ml or "deepseek" in ml


def _pick_nim_model(requested=None, exclude=None):
    """揀實際用嘅 NIM model：
    requested 唔喺可用列表 → 按偏好自動轉。
    Return 最終揀咗嘅 model ID。"""
    global _current_nim_model
    available = [m for m in fetch_nim_models() if m != exclude]

    # 候選優先次序：指令參數 > 而家用開嘅 > .env 設定
    candidates = []
    if requested:
        candidates.append(requested)
    if _current_nim_model:
        candidates.append(_current_nim_model)
    env_model = (os.getenv("NIM_MODEL") or "").strip()
    if env_model:
        candidates.append(env_model)

    if available:
        # ① 候選有邊個啱用邊個
        for c in candidates:
            if c in available:
                _current_nim_model = c
                return c

        # ② 全部候選都落架 → 按偏好清單揀
        for p in NIM_PREFERRED:
            if p in available:
                was = candidates[0] if candidates else "?"
                print(f"🔄 [ai] NIM 模型 '{was}' 已唔再提供服務，自動轉用 '{p}'")
                _current_nim_model = p
                return p

        # ③ 偏好都冇 → 揀任何一個傾偈用嘅模型
        for m in available:
            if _chat_suitable(m):
                print(f"🔄 [ai] NIM 模型自動轉用 '{m}'")
                _current_nim_model = m
                return m

        # ④ 有咩用咩
        _current_nim_model = available[0]
        return available[0]

    # 攞唔到模型列表（API 出事）→ 照用候選，出事再由 retry 機制處理
    if candidates:
        return candidates[0]
    return NIM_FALLBACK


def _is_model_error(msg):
    """判斷 NIM 錯誤係咪『個 model 唔存在／已下架』"""
    m = (msg or "").lower()
    if "404" in m:
        return True
    if "model" in m:
        for kw in ("not found", "not available", "unavailable",
                   "does not exist", "invalid", "decommission", "no longer"):
            if kw in m:
                return True
    return False


# ============================================================
# Gemini
# ============================================================
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


# ============================================================
# NIM（有自動轉模型 + 重試）
# ============================================================
def _nim_chat(api_key, model, question):
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
        return text, model
    except (KeyError, IndexError):
        raise RuntimeError("NIM 冇回應內容")


def _ask_nim(question, model=None):
    api_key = os.getenv("NIM_API_KEY").strip()
    use_model = _pick_nim_model(model)
    try:
        text, used = _nim_chat(api_key, use_model, question)
        return text, f"nim · {used}"
    except RuntimeError as e:
        # 疑似個模型掛咗 → force refresh 列表，換個模型重試一次
        if _is_model_error(str(e)):
            fetch_nim_models(force=True)
            new_model = _pick_nim_model(exclude=use_model)
            if new_model and new_model != use_model:
                print(f"🔄 [ai] NIM '{use_model}' call 失敗，改用 '{new_model}' 重試")
                try:
                    text, used = _nim_chat(api_key, new_model, question)
                    return text, f"nim · {used}"
                except Exception:
                    pass
        raise


# ============================================================
# 統一入口
# ============================================================
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