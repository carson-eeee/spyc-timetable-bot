import json
import re
import asyncio
import urllib.request
from datetime import datetime

HKO_BASE = "https://data.weather.gov.hk/weatherAPI/opendata/weather.php"

# 📍 沙田市中心座標
SHA_TIN_LAT = 22.3811
SHA_TIN_LON = 114.1866

OPENMETEO_CURRENT_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={SHA_TIN_LAT}&longitude={SHA_TIN_LON}"
    "&current=temperature_2m,relative_humidity_2m,weather_code"
)
OPENMETEO_HOURLY_URL = (
    "https://api.open-meteo.com/v1/forecast"
    f"?latitude={SHA_TIN_LAT}&longitude={SHA_TIN_LON}"
    "&hourly=temperature_2m,precipitation_probability,weather_code"
    "&forecast_days=2&timezone=Asia%2FHong_Kong"
)

# 🚫 呢啲警告生效 = 唔使返學
STOP_RE = re.compile(r"(八號|九號|十號|黑色暴雨)")
# ⚠️ 呢啲照返學，但要留意
CAUTION_RE = re.compile(r"(三號|紅色暴雨|黃色暴雨|雷暴|強烈季候風信號)")

HKO_ICON_EMOJI = {
    50: "☀️", 51: "🌤️", 52: "⛅", 53: "☁️", 54: "🌫️",
    60: "🌦️", 61: "🌧️", 62: "🌧️", 63: "🌧️", 64: "⛈️", 65: "⛈️",
    70: "🌙", 76: "🌫️", 77: "🌤️", 80: "🌫️", 81: "🌫️", 82: "🌫️",
    83: "🌤️", 84: "🌤️", 85: "🌨️",
}

OM_CODE_EMOJI = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌧️", 56: "🌧️", 57: "🌧️",
    61: "🌧️", 63: "🌧️", 65: "🌧️", 66: "🌧️", 67: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "🌨️", 77: "🌨️",
    80: "🌦️", 81: "🌧️", 82: "🌧️",
    85: "🌨️", 86: "🌨️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}


def _get_json(url, timeout=15):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


async def _fetch(url):
    """唔會 throw：失敗 return None，同時 print 真正原因出 console"""
    try:
        return await asyncio.to_thread(_get_json, url)
    except Exception as e:
        print(f"❌ [weather] 攞唔到 {url.split('?')[0]} → {type(e).__name__}: {e}")
        return None


# ==================== 天文台 API ====================

async def fetch_current(lang="tc"):
    """現時天氣"""
    return await _fetch(f"{HKO_BASE}?dataType=rhrread&lang={lang}")


async def fetch_forecast(lang="tc"):
    """本地天氣預報（概況 + 今明兩日）"""
    return await _fetch(f"{HKO_BASE}?dataType=flw&lang={lang}")


async def fetch_9day(lang="tc"):
    """九日天氣預報"""
    return await _fetch(f"{HKO_BASE}?dataType=fnd&lang={lang}")


async def fetch_warnings(lang="tc"):
    """現行警告"""
    return await _fetch(f"{HKO_BASE}?dataType=warnsum&lang={lang}")


async def fetch_tips(lang="tc"):
    """特別天氣提示"""
    return await _fetch(f"{HKO_BASE}?dataType=swt&lang={lang}")


# ==================== Open-Meteo（沙田）====================

async def fetch_hourly_shatin():
    """沙田逐小時預報（溫度／降雨機率）"""
    return await _fetch(OPENMETEO_HOURLY_URL)


# ==================== 解析 ====================

def extract_warning_names(warnsum_data):
    """由 warnsum 抽出警告名稱 list"""
    if not warnsum_data:
        return []
    names = []
    for m in warnsum_data.get("warningMessage", []):
        if isinstance(m, str):
            names.append(m.strip())
        elif isinstance(m, dict):
            n = m.get("name", "").strip()
            if n:
                names.append(n)
    return [n for n in names if n]


def extract_tips(swt_data):
    """抽出特別天氣提示 list"""
    if not swt_data:
        return []
    out = []
    for t in swt_data.get("swt", []):
        d = (t.get("desc") or "").strip()
        if d:
            out.append(d)
    return out


def school_status(warning_names):
    """判斷學生使唔使返學 → (level, emoji, title, detail)"""
    text = "；".join(warning_names)
    if STOP_RE.search(text):
        return ("STOP", "🔴", "唔使返學！",
                "而家有 8 號或以上熱帶氣旋警告／黑色暴雨警告，學校停課。安心留喺屋企 😴")
    if CAUTION_RE.search(text):
        return ("CAUTION", "🟡", "照返學，但要留意！",
                "而家有 3 號風球／暴雨等警告生效，中學照常上課。帶定遮 ☂️ 留意最新公佈。")
    return ("OK", "🟢", "照返學", "而家冇影響上課嘅天氣警告。")


def parse_hourly(om_data, hours=12):
    """解析 Open-Meteo 逐小時數據 → 由而家開始未來 N 個鐘"""
    if not om_data:
        return []
    h = om_data.get("hourly", {})
    times = h.get("time", [])
    temps = h.get("temperature_2m", [])
    rains = h.get("precipitation_probability", [])
    codes = h.get("weather_code", [])

    now_hour = datetime.now().replace(minute=0, second=0, microsecond=0)
    out = []
    for i, t in enumerate(times):
        try:
            dt = datetime.strptime(t, "%Y-%m-%dT%H:%M")
        except (ValueError, TypeError):
            continue
        if dt < now_hour:
            continue
        out.append({
            "time": dt,
            "temp": temps[i] if i < len(temps) else None,
            "rain": rains[i] if i < len(rains) else None,
            "code": codes[i] if i < len(codes) else None,
        })
        if len(out) >= hours:
            break
    return out


# ==================== 總結 ====================

async def get_summary():
    """一次過攞現時天氣 + 警告 + 停課判斷（天文台失敗自動用 Open-Meteo）"""
    temp = hum = None
    emoji = "🌡️"
    updated = ""
    source = ""
    uv = None
    uv_desc = ""
    wind = None
    rain_max = None

    # ① 天文台
    cur = await fetch_current()
    if cur:
        try:
            temp = cur["temperature"]["value"]
            hum = cur["humidity"]["value"]
            emoji = HKO_ICON_EMOJI.get(cur.get("icon"), "🌡️")
            updated = cur.get("updateTime", "")
            source = "香港天文台"
        except (KeyError, TypeError):
            temp = None

        # 紫外線（夜晚會冇 → 跳過）
        try:
            v = cur["uvindex"]["value"]
            if isinstance(v, (int, float)):
                uv = v
                uv_desc = cur["uvindex"].get("desc") or ""
        except (KeyError, TypeError):
            pass

        # 風
        try:
            spd = cur["windinfo"]["speed"]["value"]
            if isinstance(spd, (int, float)):
                wind = f"{cur['windinfo'].get('direction', '')} {spd} km/h".strip()
        except (KeyError, TypeError):
            pass

        # 過去一小時最高雨量
        try:
            rd = cur.get("rainfall", {}).get("data", [])
            best = max(rd, key=lambda x: x.get("max") or 0)
            if best.get("max"):
                rain_max = best["max"]
        except Exception:
            pass

    # ② 天文台死咗 → Open-Meteo（沙田）
    if temp is None:
        om = await _fetch(OPENMETEO_CURRENT_URL)
        c = (om or {}).get("current", {})
        if c.get("temperature_2m") is not None:
            temp = c["temperature_2m"]
            hum = c.get("relative_humidity_2m")
            emoji = OM_CODE_EMOJI.get(c.get("weather_code"), "🌡️")
            updated = c.get("time", "")
            source = "Open-Meteo (沙田)"

    # ③ 警告
    warn = await fetch_warnings()
    warnings = extract_warning_names(warn)
    level, s_emoji, title, detail = school_status(warnings)

    if temp is not None:
        hum_str = f" · 💧 {hum}%" if hum is not None else ""
        line = f"{emoji} **{temp}°C**{hum_str}"
        plain = f"{emoji} {temp}°C{hum_str}"
    else:
        line = "🌡️ 天氣資料暫時攞唔到"
        plain = line

    if warn is None:
        detail += "\n⚠️ （暫時攞唔到警告資料，請自行確認最新天氣警告）"

    return {
        "line": line,
        "plain": plain,
        "warnings": warnings,
        "level": level,
        "emoji": s_emoji,
        "title": title,
        "detail": detail,
        "updated": updated[:16].replace("T", " "),
        "source": source,
        "uv": uv,
        "uv_desc": uv_desc,
        "wind": wind,
        "rain_max": rain_max,
    }