# 🤖 SPYC Timetable Bot

A Discord bot for Sha Tin Pui Ying College (SPYC) students — timetables, weather, AI assistant and more, all in one place.

**English** | [繁體中文](#-繁體中文)

---

## 🇬🇧 English

### ✨ Features

- 📅 **Timetable lookup** — any class, any day, with ⬅️➡️ navigation buttons
- 🌤️ **Weather** — current weather, hourly forecast (Sha Tin), 9-day forecast, and "do I need to go to school?" check based on HK weather warnings
- 🎯 **DSE countdown** — automatically shown for S6 classes, plus a dedicated `/dse` command
- 🤖 **AI assistant** — ask questions via Google Gemini or NVIDIA NIM (auto-fallback)
- 📱 **QR code generator** — turn any link or text into a QR code
- 👤 **Info commands** — avatar, user info, server info
- 📮 **Anonymous feedback box** — students submit suggestions, admins get auto-notified
- 🛡️ **Admin tools** — usage statistics, command logs, user blacklist
- 🧠 **Memory** — each user can save their default class & display style

### 📋 Requirements

- Python **3.10 or above**
- A Discord account

### 🚀 How to Run (for people who downloaded this project)

#### 1. Install Python

Download from [python.org](https://python.org). During installation, **tick "Add Python to PATH"** — this is important!

#### 2. Install dependencies

Open a terminal (Command Prompt / PowerShell) in the project folder:

```cmd
pip install -r requirements.txt
```

#### 3. Create your bot on Discord

1. Go to the [Discord Developer Portal](https://discord.com/developers/applications) → **New Application** → give it a name
2. Go to the **Bot** tab → enable these **Privileged Gateway Intents**:
   - ✅ MESSAGE CONTENT INTENT
   - ✅ SERVER MEMBERS INTENT
3. Click **Reset Token** → copy the token
4. The **Application ID** is on the **General Information** page — copy it too

#### 4. Create the `.env` file

In the project folder, create a file named `.env` (no `.txt` extension!):

```
DISCORD_TOKEN=your_bot_token_here
APPLICATION_ID=your_application_id_here
ADMIN_IDS=your_discord_user_id
```

> To find your user ID: enable **Developer Mode** in Discord settings (Advanced), then right-click your avatar → **Copy User ID**.

**Optional — AI features** (`/ask`):

```
GEMINI_API_KEY=get_from_aistudio.google.com
NIM_API_KEY=nvapi-xxx_from_build.nvidia.com
AI_PROVIDER=auto
GEMINI_MODEL=gemini-2.0-flash
NIM_MODEL=meta/llama-3.1-8b-instruct
```

AI works with either key — Gemini is preferred, NIM is the fallback.

#### 5. Invite the bot to your server

Developer Portal → OAuth2 → URL Generator:
- Scopes: `bot`, `applications.commands`
- Permissions: Send Messages, Embed Links, Read Message History, Attach Files

#### 6. Run!

```cmd
python main.py
```

You should see:

```
✅ Synced 29 slash commands
🤖 Logged in as YourBot (ID: xxx)
```

Discord may need 1–5 minutes to show new commands — restart your Discord client (Ctrl+R) if they don't appear.

### 📁 Project Structure — What Each File Does

```
spyc-timetable-bot/
│
├── main.py                🚀 Entry point — starts the bot, loads all cogs,
│                            syncs commands, clears duplicate guild commands
├── requirements.txt       📦 Python package list (pip install -r requirements.txt)
├── .env                   🔑 Your secret keys (NEVER commit to GitHub!)
├── .env.example           📄 Template showing what to put in .env
│
├── cogs/                  💬 All Discord command groups
│   ├── timetable_cog.py   📅 /timetable /today /events /dse /setclass /myclass /help
│   │                      ⬅️➡️ Also contains the navigation buttons (prev/next/today)
│   ├── weather_cog.py     🌤️ /weather /hourly /forecast /school
│   ├── info_cog.py        👤 /avatar /userinfo /serverinfo
│   ├── qr_cog.py          📱 /qr — QR code generator
│   ├── ai_cog.py          🤖 /ask — AI assistant with rate limiting
│   └── admin_cog.py       🛡️ Admin: /stats* /logs /blacklist* /feedback*
│                            (auto-records every command used)
│
├── utils/                 🛠️ Helper modules (no commands here)
│   ├── api.py             🌐 SPYC timetable API client (iot.spyc.hk)
│   ├── embeds.py          ⏰ Lesson times (TIME_SLOTS), subject names,
│   │                      DSE exam date, all embed builders, help menu
│   ├── weather.py         🌦️ HK Observatory + Open-Meteo fetching,
│   │                      school closure logic (typhoon/rainstorm)
│   ├── render.py          🖼️ Pillow image renderer for image-mode timetable
│   └── ai.py              🧠 Gemini + NVIDIA NIM API clients
│
└── (auto-generated on first run — you don't create these)
    ├── user_data.json     🧠 Users' default class & display style
    ├── admin_stats.json   📊 Usage statistics
    ├── blacklist.json     🚫 Blocked users
    └── feedback.json      📮 Feedback entries
```

**Want to change something?**

| I want to change... | Edit this |
|---|---|
| Lesson start times | `utils/embeds.py` → `TIME_SLOTS` |
| Where recess/lunch appears | `utils/embeds.py` → `BREAK_BEFORE` |
| DSE exam date | `utils/embeds.py` → `DSE_EXAM_DATE` |
| Subject Chinese names | `utils/embeds.py` → `SUBJECT_NAMES` |
| AI personality / system prompt | `utils/ai.py` → `SYSTEM_PROMPT` |
| AI rate limit | `cogs/ai_cog.py` → `MAX_PER_HOUR` |
| Bot status message | `main.py` → `on_ready` |

### 📜 Commands

#### 📅 Timetable

| Command | Description |
|---|---|
| `/timetable <class> [day] [style]` | View a timetable (text or image) |
| `/today [class] [style]` | Today's timetable + events |
| `/events [date]` | School events |
| `/dse` | DSE countdown |
| `/setclass <class> [style]` | Set your default class & display style |
| `/myclass` | Show your settings |

#### 🌤️ Weather

| Command | Description |
|---|---|
| `/weather` | Current weather + school status + UV/wind/rainfall |
| `/hourly [hours]` | Sha Tin hourly forecast (next 4–24 hours) |
| `/forecast` | 9-day forecast + general situation |
| `/school` | Do I need to go to school? (based on warnings) |

#### 🤖 Other

| Command | Description |
|---|---|
| `/ask <question> [provider]` | Ask the AI assistant |
| `/qr <text> [scale]` | Generate a QR code |
| `/avatar [user]` | View an avatar in HD |
| `/userinfo [user]` | User info |
| `/serverinfo` | Server info |
| `/feedback <message>` | Submit (anonymous) feedback |
| `/help` | Help menu |

#### 🛡️ Admin

| Command | Description |
|---|---|
| `/stats` | Usage overview |
| `/stats_daily [days]` | Daily usage trend |
| `/stats_commands` | Command ranking |
| `/stats_users` | Most active users |
| `/logs [count]` | Recent command log |
| `/stats_export` | Export stats (JSON) |
| `/blacklist_add <user> [reason]` | Block a user |
| `/blacklist_remove <user>` | Unblock a user |
| `/blacklist_list` | View blacklist |
| `/feedback_list [page]` | View feedback box |
| `/feedback_resolve <id>` | Mark feedback resolved |
| `/feedback_setchannel [#channel]` | Auto-forward feedback |

Admins = server administrators **and** user IDs in `.env` → `ADMIN_IDS`.

### ❓ FAQ

**Q: The bot doesn't respond.**
A: Check (1) the token in `.env` is correct, (2) MESSAGE CONTENT INTENT is enabled, (3) the bot is in your server.

**Q: Slash commands don't show up.**
A: Discord needs 1–5 minutes to sync. Restart your Discord client (Ctrl+R) if needed.

**Q: Commands appear twice.**
A: Leftover guild-scoped commands. The bot clears them automatically on startup — restart the bot, then Ctrl+R your Discord.

**Q: Weather says "資料攞唔到" (data unavailable).**
A: The HKO or Open-Meteo server may be unreachable. Check the console for the exact error. The bot automatically falls back from HKO → Open-Meteo.

**Q: `/ask` says no API key.**
A: Add `GEMINI_API_KEY` or `NIM_API_KEY` to `.env` and restart. See links above.

**Q: Lesson times are wrong.**
A: Edit `TIME_SLOTS` at the top of `utils/embeds.py`.

---

## 🇭🇰 繁體中文

### ✨ 功能

- 📅 **時間表查詢** — 任何班別、任何日子，設有 ⬅️➡️ 翻頁按鈕
- 🌤️ **天氣功能** — 現時天氣、沙田逐小時預報、九日預報，仲會根據天氣警告判斷「使唔使返學」
- 🎯 **DSE 倒數** — 中六班別自動顯示倒數，亦有 `/dse` 指令
- 🤖 **AI 助手** — 可用 Google Gemini 或 NVIDIA NIM（自動後備切換）
- 📱 **QR Code 產生器** — 將任何連結或文字轉換成 QR Code
- 👤 **資訊指令** — 頭像、用戶資料、伺服器資料
- 📮 **匿名意見箱** — 學生匿名遞交意見，管理員自動收到通知
- 🛡️ **管理員工具** — 使用統計、指令記錄、用戶封鎖
- 🧠 **記憶功能** — 每位用戶可儲存預設班別及顯示方式

### 📋 系統需求

- Python **3.10 或以上**
- Discord 帳號

### 🚀 運行方法（下載咗成個 project 嘅人）

#### 1. 安裝 Python

去 [python.org](https://python.org) 下載。安裝時**必須勾選「Add Python to PATH」** — 好重要！

#### 2. 安裝依賴套件

喺專案資料夾開 terminal（Command Prompt / PowerShell）：

```cmd
pip install -r requirements.txt
```

#### 3. 建立 Discord Bot

1. 去 [Discord Developer Portal](https://discord.com/developers/applications) → **New Application** → 輸入名稱
2. 進入 **Bot** 頁面 → 開啟以下 **Privileged Gateway Intents**：
   - ✅ MESSAGE CONTENT INTENT
   - ✅ SERVER MEMBERS INTENT
3. 點擊 **Reset Token** → 複製 Token
4. **Application ID** 在 **General Information** 頁面 — 同樣複製

#### 4. 建立 `.env` 檔案

喺專案資料夾建立一個名叫 `.env` 嘅檔案（**唔好有** `.txt` 副檔名！）：

```
DISCORD_TOKEN=你的Bot_Token
APPLICATION_ID=你的Application_ID
ADMIN_IDS=你的Discord用戶ID
```

> 查看用戶 ID 方法：Discord 設定 → Advanced → 開啟**開發者模式**，然後右擊自己頭像 → **複製用戶 ID**。

**可選 — AI 功能**（`/ask`）：

```
GEMINI_API_KEY=由_aistudio.google.com_申請
NIM_API_KEY=nvapi-xxx_由_build.nvidia.com_申請
AI_PROVIDER=auto
GEMINI_MODEL=gemini-2.0-flash
NIM_MODEL=meta/llama-3.1-8b-instruct
```

AI 功能有其中一條 key 就得 — 預設用 Gemini，NIM 做後備。

#### 5. 邀請 Bot 加入伺服器

Developer Portal → OAuth2 → URL Generator：
- Scopes：`bot`、`applications.commands`
- Permissions：Send Messages、Embed Links、Read Message History、Attach Files

#### 6. 啟動！

```cmd
python main.py
```

應該會見到：

```
✅ Synced 29 slash commands
🤖 Logged in as YourBot (ID: xxx)
```

Discord 需要 1–5 分鐘先會顯示新指令 — 如果冇出現，重啟 Discord 用戶端（Ctrl+R）。

### 📁 專案結構 — 每個檔案係做咩嘅

```
spyc-timetable-bot/
│
├── main.py                🚀 入口檔案 — 啟動 bot、載入所有 cog、
│                            同步指令、清除重複嘅 guild 指令
├── requirements.txt       📦 Python 套件清單 (pip install -r requirements.txt)
├── .env                   🔑 你嘅密鑰（千祈唔好 commit 上 GitHub！）
├── .env.example           📄 .env 範本
│
├── cogs/                  💬 所有 Discord 指令組
│   ├── timetable_cog.py   📅 /timetable /today /events /dse /setclass /myclass /help
│   │                      ⬅️➡️ 仲有翻頁按鈕（前一日／後一日／今日）
│   ├── weather_cog.py     🌤️ /weather /hourly /forecast /school
│   ├── info_cog.py        👤 /avatar /userinfo /serverinfo
│   ├── qr_cog.py          📱 /qr — QR Code 產生器
│   ├── ai_cog.py           🤖 /ask — AI 助手（設有限流）
│   └── admin_cog.py       🛡️ 管理員：/stats* /logs /blacklist* /feedback*
│                            （自動記錄所有指令使用）
│
├── utils/                 🛠️ 輔助模組（呢度冇指令）
│   ├── api.py             🌐 SPYC 時間表 API 客戶端 (iot.spyc.hk)
│   ├── embeds.py          ⏰ 上堂時間 (TIME_SLOTS)、科目名對照、
│   │                      DSE 考試日期、所有 embed 產生器、說明選單
│   ├── weather.py         🌦️ 天文台 + Open-Meteo 抓取、
│   │                      停課判斷邏輯（風球／暴雨）
│   ├── render.py          🖼️ Pillow 圖片渲染（圖片模式時間表）
│   └── ai.py              🧠 Gemini + NVIDIA NIM API 客戶端
│
└──（首次運行自動生成 — 唔使自己建立）
    ├── user_data.json     🧠 用戶預設班別及顯示方式
    ├── admin_stats.json   📊 使用統計數據
    ├── blacklist.json     🚫 封鎖名單
    └── feedback.json      📮 意見記錄
```

**想改嘢？**

| 想改… | 改呢度 |
|---|---|
| 上堂開始時間 | `utils/embeds.py` → `TIME_SLOTS` |
| 小息／午膳出現位置 | `utils/embeds.py` → `BREAK_BEFORE` |
| DSE 考試日期 | `utils/embeds.py` → `DSE_EXAM_DATE` |
| 科目中文名 | `utils/embeds.py` → `SUBJECT_NAMES` |
| AI 性格／系統提示 | `utils/ai.py` → `SYSTEM_PROMPT` |
| AI 限流次數 | `cogs/ai_cog.py` → `MAX_PER_HOUR` |
| Bot 狀態文字 | `main.py` → `on_ready` |

### 📜 指令一覽

#### 📅 時間表

| 指令 | 說明 |
|---|---|
| `/timetable <班別> [Day] [style]` | 查詢時間表（文字或圖片） |
| `/today [班別] [style]` | 今日時間表＋活動 |
| `/events [日期]` | 查詢學校活動 |
| `/dse` | DSE 倒數 |
| `/setclass <班別> [style]` | 設定預設班別及顯示方式 |
| `/myclass` | 顯示你的設定 |

#### 🌤️ 天氣

| 指令 | 說明 |
|---|---|
| `/weather` | 現時天氣＋返學狀態＋紫外線／風／雨量 |
| `/hourly [小時]` | 沙田逐小時預報（未來 4–24 小時） |
| `/forecast` | 九日預報＋天氣概況 |
| `/school` | 而家使唔使返學？（根據警告判斷） |

#### 🤖 其他

| 指令 | 說明 |
|---|---|
| `/ask <問題> [引擎]` | 問 AI 助手 |
| `/qr <文字> [大小]` | 產生 QR Code |
| `/avatar [用戶]` | 查看高清頭像 |
| `/userinfo [用戶]` | 用戶資料 |
| `/serverinfo` | 伺服器資料 |
| `/feedback <意見>` | 遞交（匿名）意見 |
| `/help` | 顯示說明 |

#### 🛡️ 管理員

| 指令 | 說明 |
|---|---|
| `/stats` | 使用統計總覽 |
| `/stats_daily [日數]` | 每日用量趨勢 |
| `/stats_commands` | 指令用量排行 |
| `/stats_users` | 最活躍用戶排行 |
| `/logs [數量]` | 最近指令記錄 |
| `/stats_export` | 匯出統計數據（JSON） |
| `/blacklist_add <用戶> [原因]` | 封鎖用戶 |
| `/blacklist_remove <用戶>` | 解除封鎖 |
| `/blacklist_list` | 查看封鎖名單 |
| `/feedback_list [頁數]` | 查看意見箱 |
| `/feedback_resolve <編號>` | 標記意見為已處理 |
| `/feedback_setchannel <#頻道>` | 設定意見自動轉發 |

管理員 = 伺服器管理員 **以及** `.env` → `ADMIN_IDS` 入面嘅用戶。

### ❓ 常見問題

**問：Bot 沒有反應。**
答：請檢查（1）`.env` 內的 Token 是否正確、（2）是否已開啟 MESSAGE CONTENT INTENT、（3）Bot 是否已加入伺服器。

**問：Slash 指令沒有出現。**
答：Discord 需要 1–5 分鐘同步。如仍未出現，請重啟 Discord 用戶端（Ctrl+R）。

**問：指令出現兩次。**
答：這是殘留的伺服器專屬指令。Bot 啟動時會自動清除 — 重啟 Bot 後再 Ctrl+R 即可。

**問：天氣顯示「資料攞唔到」。**
答：天文台或 Open-Meteo 伺服器可能暫時連不上。查看 console 入面嘅具體錯誤。Bot 會自動由天文台切換去 Open-Meteo 後備。

**問：`/ask` 話冇 API key。**
答：喺 `.env` 加 `GEMINI_API_KEY` 或 `NIM_API_KEY` 再重啟。申請連結見上面。

**問：上課時間錯誤。**
答：編輯 `utils/embeds.py` 頂部的 `TIME_SLOTS`。

---

### 🙏 Credits

- Data source: [iot.spyc.hk](https://iot.spyc.hk) · [香港天文台](https://www.hko.gov.hk) · [Open-Meteo](https://open-meteo.com)
- Reference: [sayatodev/siu-ying-v2](https://github.com/sayatodev/siu-ying-v2)
- Made with ❤️ for SPYC students