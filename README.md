# SPYC 時間表 Discord Bot

幫沙田培英書院學生快速查詢時間表嘅 Discord Bot。

---

## 安裝 (Windows)

### 1. 安裝 Python
- 去 python.org 下載 Python 3.10+
- **重要**：安裝時 tick 晒「Add Python to PATH」

### 2. 下載呢個 project
- 解壓呢個 zip 檔案
- 打開 Command Prompt (cmd) 或者 PowerShell
- cd 入去個 folder：
```cmd
cd C:\Users\你個名\Downloads\spyc-timetable-bot
```

### 3. 安裝套件
```cmd
pip install -r requirements.txt
```

### 4. 設定 Discord Bot Token
1. 去 Discord Developer Portal (discord.com/developers/applications)
2. New Application -> 改名做你鍾意嘅名
3. 左邊揀 **Bot** -> Add Bot
4. 開啟以下權限：
   - MESSAGE CONTENT INTENT
   - SERVER MEMBERS INTENT
5. 按 **Reset Token** -> Copy token
6. 喺 project folder 入面，複製 `.env.example` 做 `.env`
7. 用 Notepad 開 `.env`，貼入你個 token：
```
DISCORD_TOKEN=你個token貼呢度
APPLICATION_ID=你個application_id
```

> Application ID 喺 Discord Developer Portal -> General Information 入面搵

### 5. 邀請 Bot 入你個 Server
1. 喺 Discord Developer Portal -> OAuth2 -> URL Generator
2. Scopes 揀 `bot` 同 `applications.commands`
3. Bot Permissions 揀：
   - Send Messages
   - Embed Links
   - Read Message History
   - Use Slash Commands
   - Mention @everyone, @here, All Roles
4. Copy 個 generated URL，貼去 browser，揀你個 server 邀請

### 6. 執行 Bot
```cmd
python main.py
```

見到 `Logged in as...` 就代表成功！

或者你可以直接 double-click `start.bat`。

---

## 部署到 bot-hosting.net

你朋友推薦嘅 bot-hosting.net 係一個免費 Discord bot hosting。

### 步驟：

1. 去 bot-hosting.net 開帳號
2. Create Server -> 揀 **Python**
3. 上傳你個 project（用 Git 或者 FTP）
4. 設定 Environment Variables：
   - `DISCORD_TOKEN`
   - `APPLICATION_ID`
5. Start Command 填：`python main.py`
6. 開機！

> 注意：免費 tier 可能有 usage limit，如果 bot 多 server 用可能會唔夠

---

## 指令一覽

| Slash Command | 說明 | 例子 |
|--------------|------|------|
| `/timetable <班別> [Day]` | 查時間表 | `/timetable 1A A` |
| `/today [班別]` | 今日時間表+活動 | `/today 2B` |
| `/events [日期]` | 查學校活動 | `/events 5/9/2026` |
| `/setclass <班別>` | 設定預設班別 | `/setclass 1A` |
| `/myclass` | 睇已設定班別 | - |
| `/help` | 幫助 | - |

| Mention Command | 說明 | 例子 |
|----------------|------|------|
| `@Bot timetable <班別> [Day]` | 查時間表 | `@Bot timetable 1A` |
| `@Bot today [班別]` | 查今日 | `@Bot today` |
| `@Bot events [日期]` | 查活動 | `@Bot events` |
| `@Bot help` | 幫助 | `@Bot help` |

---

## 常見問題

**Q: 點解個 bot 冇反應？**
A: 檢查：
1. `.env` 入面嘅 token 係咪啱
2. 有冇開啟 MESSAGE CONTENT INTENT
3. 有冇 invite 個 bot 入 server

**Q: Slash command 冇出現？**
A: 等 1-5 分鐘，Discord 需要時間 sync。或者重新 invite 個 bot。

**Q: 顯示 "無法連接到時間表伺服器"？**
A: SPYC 個 server 可能 down 咗，等陣再試。

**Q: 點改啲課堂名嘅顯示？**
A: 改 `utils/embeds.py` 入面嘅 `create_timetable_embed` function。

---

## 關於

Data source: iot.spyc.hk
參考: github.com/sayatodev/siu-ying-v2

Made with love for SPYC students
