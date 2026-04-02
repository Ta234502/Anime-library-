💀 TVR Anime SaaS Bot

A powerful Telegram Anime Library Bot built with aiogram v3, FastAPI, and Redis (Upstash) — designed for Railway deployment.

---

🚀 Features

🎬 Content System

- Anime Library with buttons
- Episode upload system (1.mp4, 2.mp4 strict order)
- Auto episode buttons
- Video streaming with captions

💎 Premium System

- Bronze / Silver / Gold plans
- Manual payment (DM owner)
- Admin approval system
- Auto expiry system

🧠 Smart Features

- Auto episode order check (no wrong sequence)
- User analytics (total users, premium users)
- Redis-based fast storage
- Clean UI with buttons

🌐 Web Panel (API)

- "/stats" → users, premium, anime count
- "/payments" → pending payments
- "/premium" → active users

---

🛠️ Tech Stack

- Python (aiogram v3)
- FastAPI
- Redis (Upstash)
- Railway (Hosting)

---

⚙️ Setup & Deployment (Railway)

1. Upload Project

Upload files to GitHub:

- "app.py"
- "requirements.txt"
- "Procfile"

2. Deploy on Railway

- Create new project
- Deploy from GitHub
- Add environment variables:

BOT_TOKEN=your_bot_token
OWNER_ID=your_id
REDIS_URL=your_upstash_url

3. Start Command

Railway automatically uses:

web: uvicorn app:app --host 0.0.0.0 --port $PORT

---

📦 Commands

Command| Description
/start| Start bot
/premium| Show plans
/approve user_id plan| Activate premium
/addanime| Add anime
/done| Finish episode upload

---

⚠️ Disclaimer

This software is provided "AS IS".
The developer is not responsible for any misuse, damage, or issues caused.

---

👑 Owner

- Developer: TVR Developer
- Contact: https://t.me/SONY_YAY_0000

---

💀 Final Note

This bot is designed for learning + SaaS development purposes.

For full multi-bot SaaS (clone system), VPS deployment is required.

---
