# app.py
import os
import asyncio
import json
import time
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

from fastapi import FastAPI
import uvicorn
from redis.asyncio import Redis

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart, Command
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# ================= ENVIRONMENT VARIABLES =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8724636379:AAHfz0pGGGVvutcZNzy0gPpW6o_9ILr4lcA")
OWNER_ID = int(os.getenv("OWNER_ID", "6407533831"))
OWNER_USERNAME = os.getenv("OWNER_USERNAME", "SONY_YAY_0000")
REDIS_URL = os.getenv("REDIS_URL", "redredis://default:gQAAAAAAARwoAAIncDEzZGYwZDhjZmE0YTE0MzU3OTIxNzAwYWZiNWE2OTgxNHAxNzI3NDQ@polished-alien-72744.upstash.io:6379")

# ================= INITIALIZATION =================
redis = Redis.from_url(REDIS_URL, decode_responses=True)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# ================= FASTAPI LIFESPAN =================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Run bot polling in background
    polling_task = asyncio.create_task(dp.start_polling(bot))
    yield
    # Shutdown
    polling_task.cancel()
    await bot.session.close()
    await redis.close()

app = FastAPI(lifespan=lifespan)

# ================= FSM STATES =================
class AnimeState(StatesGroup):
    waiting_for_name = State()

class AddEpState(StatesGroup):
    waiting_for_files = State()

# ================= HELPER FUNCTIONS =================
async def is_premium(user_id: int) -> bool:
    expiry = await redis.get(f"premium:{user_id}")
    if not expiry:
        return False
    if float(expiry) < time.time():
        await redis.delete(f"premium:{user_id}")
        return False
    return True

async def get_anime_keyboard() -> InlineKeyboardMarkup:
    animes = await redis.smembers("anime_list")
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for a in animes:
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"📺 {a}", callback_data=f"anime_{a}")])
    return kb

# ================= 1. START SYSTEM =================
@dp.message(CommandStart())
async def start_cmd(message: Message):
    user_id = str(message.from_user.id)
    await redis.sadd("users", user_id)
    
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎬 Movie"), KeyboardButton(text="📺 Anime")],
            [KeyboardButton(text="🧸 Cartoon"), KeyboardButton(text="💎 Premium")]
        ],
        resize_keyboard=True
    )
    
    welcome_text = (
        "<b>🎉 Welcome to the Ultimate Anime Library! 🎉</b>\n\n"
        "Here you can find high-quality Anime, Movies, and Cartoons directly on Telegram. "
        "Upgrade to Premium to unlock exclusive content and faster access.\n\n"
        "👇 Select an option from the menu below to get started!"
    )
    await message.answer(welcome_text, reply_markup=kb)

# ================= 2. PREMIUM SYSTEM =================
@dp.message(F.text == "💎 Premium")
async def premium_menu(message: Message):
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🥉 Bronze (7 Days) - ₹49", callback_data="plan_bronze")],
            [InlineKeyboardButton(text="🥈 Silver (30 Days) - ₹99", callback_data="plan_silver")],
            [InlineKeyboardButton(text="🥇 Gold (90 Days) - ₹199", callback_data="plan_gold")],
            [InlineKeyboardButton(text="💳 Buy Now (Contact Admin)", url=f"https://t.me/{OWNER_USERNAME}")]
        ]
    )
    await message.answer("<b>💎 Choose a Premium Plan to unlock VIP features:</b>", reply_markup=kb)

@dp.callback_query(F.data.startswith("plan_"))
async def select_plan(callback: CallbackQuery):
    plan = callback.data.split("_")[1]
    user_id = callback.from_user.id
    username = callback.from_user.username or "NoUsername"
    
    await redis.set(f"payment:{user_id}", plan)
    
    # Notify Owner
    admin_msg = (
        f"<b>🔔 New Payment Request!</b>\n\n"
        f"👤 User: {user_id} (@{username})\n"
        f"💎 Plan: <b>{plan.upper()}</b>\n\n"
        f"Approve using command:\n<code>/approve {user_id} {plan}</code>"
    )
    try:
        await bot.send_message(OWNER_ID, admin_msg)
    except Exception:
        pass
        
    await callback.message.answer("✅ <b>Request sent to admin!</b> Please complete your payment via the 'Buy Now' link and wait for approval.")
    await callback.answer()

# ================= 3. ADMIN APPROVAL SYSTEM =================
@dp.message(Command("approve"))
async def approve_user(message: Message):
    if message.from_user.id != OWNER_ID:
        return
    
    args = message.text.split()
    if len(args) != 3:
        return await message.answer("⚠️ <b>Usage:</b> <code>/approve user_id plan</code>")
    
    user_id, plan = args[1], args[2].lower()
    days = {"bronze": 7, "silver": 30, "gold": 90}.get(plan, 0)
    
    if not days:
        return await message.answer("❌ Invalid plan. Use bronze, silver, or gold.")
    
    expiry = datetime.now() + timedelta(days=days)
    await redis.set(f"premium:{user_id}", expiry.timestamp())
    await redis.delete(f"payment:{user_id}")
    
    try:
        await bot.send_message(user_id, f"🎉 <b>Congratulations!</b> Your <b>{plan.upper()}</b> premium plan has been activated. Valid for {days} days.")
    except Exception:
        await message.answer("⚠️ Could not message user directly, but Premium was activated.")
        
    await message.answer(f"✅ User {user_id} successfully approved for {plan.upper()} plan.")

# ================= 4. PREMIUM CHECK SYSTEM (RESTRICTIONS) =================
@dp.message(F.text.in_({"🎬 Movie", "🧸 Cartoon"}))
async def restricted_content(message: Message):
    if not await is_premium(message.from_user.id):
        return await message.answer("🔒 <b>This is a Premium feature!</b>\nPlease buy a subscription from the 💎 Premium menu to unlock Movies and Cartoons.")
    await message.answer("✨ <b>Premium Access Granted!</b> (Category updates coming soon)")

# ================= 5. ANIME LIBRARY SYSTEM =================
@dp.message(Command("addanime"))
async def add_anime(message: Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer("📝 Send the name of the new Anime:")
    await state.set_state(AnimeState.waiting_for_name)

@dp.message(AnimeState.waiting_for_name)
async def save_anime_name(message: Message, state: FSMContext):
    anime_name = message.text.strip()
    await redis.sadd("anime_list", anime_name)
    await state.clear()
    await message.answer(f"✅ <b>Added {anime_name} to the library!</b>\nUse the 📺 Anime menu to add episodes to it.")

@dp.message(F.text == "📺 Anime")
async def show_anime_list_msg(message: Message):
    kb = await get_anime_keyboard()
    if not kb.inline_keyboard:
        return await message.answer("📭 No anime available currently. Check back later!")
    await message.answer("📺 <b>Select an Anime to watch:</b>", reply_markup=kb)

@dp.callback_query(F.data == "back_to_anime")
async def back_to_anime_cb(callback: CallbackQuery):
    kb = await get_anime_keyboard()
    await callback.message.edit_text("📺 <b>Select an Anime to watch:</b>", reply_markup=kb)

# ================= 6. EPISODE & 7. BUTTON SYSTEM =================
@dp.callback_query(F.data.startswith("anime_"))
async def show_episodes(callback: CallbackQuery):
    anime_name = callback.data.split("_", 1)[1]
    eps = await redis.hkeys(f"anime_eps:{anime_name}")
    
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    sorted_eps = sorted([int(e) for e in eps])
    
    row = []
    for ep in sorted_eps:
        row.append(InlineKeyboardButton(text=f"Ep {ep}", callback_data=f"play_{anime_name}_{ep}"))
        if len(row) == 4:
            kb.inline_keyboard.append(row)
            row = []
    if row:
        kb.inline_keyboard.append(row)
        
    if callback.from_user.id == OWNER_ID:
        kb.inline_keyboard.append([InlineKeyboardButton(text="➕ Add Episodes", callback_data=f"addeps_{anime_name}")])
        
    kb.inline_keyboard.append([InlineKeyboardButton(text="🔙 Back", callback_data="back_to_anime")])
    
    await callback.message.edit_text(f"📺 <b>{anime_name}</b>\n\nSelect an episode:", reply_markup=kb)

@dp.callback_query(F.data.startswith("addeps_"))
async def add_eps_start(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        return
    
    anime_name = callback.data.split("_", 1)[1]
    eps = await redis.hkeys(f"anime_eps:{anime_name}")
    next_ep = max([int(e) for e in eps] + [0]) + 1
    
    await state.update_data(anime=anime_name, expected_ep=next_ep)
    await state.set_state(AddEpState.waiting_for_files)
    
    await callback.message.answer(
        f"📤 <b>Upload Mode: {anime_name}</b>\n\n"
        f"Send episode video files one by one.\n"
        f"Expected file name: <code>{next_ep}.mp4</code>\n\n"
        f"Send /done when finished."
    )
    await callback.answer()

@dp.message(Command("done"), AddEpState.waiting_for_files)
async def done_uploading(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("✅ Upload mode closed.")

@dp.message(AddEpState.waiting_for_files, F.video | F.document)
async def receive_episode(message: Message, state: FSMContext):
    data = await state.get_data()
    expected_ep = data['expected_ep']
    anime_name = data['anime']
    
    video_obj = message.video or message.document
    file_name = getattr(video_obj, 'file_name', '')
    
    if file_name != f"{expected_ep}.mp4":
        return await message.answer(f"❌ <b>Wrong order or format!</b>\nExpected: <code>{expected_ep}.mp4</code>\nGot: <code>{file_name}</code>")
    
    duration = getattr(video_obj, 'duration', 0)
    ep_data = json.dumps({"file_id": video_obj.file_id, "duration": duration})
    
    await redis.hset(f"anime_eps:{anime_name}", expected_ep, ep_data)
    await state.update_data(expected_ep=expected_ep + 1)
    
    await message.answer(f"✅ <b>Episode {expected_ep} saved!</b>\nNow send <code>{expected_ep + 1}.mp4</code> or /done.")

# ================= 8. AUTO CAPTION SYSTEM =================
@dp.callback_query(F.data.startswith("play_"))
async def play_episode(callback: CallbackQuery):
    _, anime_name, ep = callback.data.split("_", 2)
    ep_data_str = await redis.hget(f"anime_eps:{anime_name}", ep)
    
    if not ep_data_str:
        return await callback.answer("Episode not found!", show_alert=True)
    
    ep_data = json.loads(ep_data_str)
    
    # Format Duration
    duration_sec = ep_data.get('duration', 0)
    m, s = divmod(duration_sec, 60)
    h, m = divmod(m, 60)
    duration_str = f"{h:d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"
    
    caption = (
        f"🎬 <b>Name:</b> {anime_name}\n"
        f"🔢 <b>Episode:</b> {ep}\n"
        f"⏱ <b>Duration:</b> {duration_str}\n\n"
        f"🌟 <b>Credit:</b> @{OWNER_USERNAME}"
    )
    
    await callback.message.answer_video(ep_data['file_id'], caption=caption)
    await callback.answer()

# ================= 9 & 10. WEB PANEL (FastAPI) & ANALYTICS =================
@app.get("/")
async def index():
    return {"status": "success", "message": "Anime SaaS Bot & Web Panel Running!"}

@app.get("/stats")
async def get_stats():
    total_users = await redis.scard("users")
    anime_count = await redis.scard("anime_list")
    premium_keys = await redis.keys("premium:*")
    
    # Auto-cleanup expired while counting
    active_premium = 0
    current_time = time.time()
    for k in premium_keys:
        if float(await redis.get(k)) > current_time:
            active_premium += 1
        else:
            await redis.delete(k)

    return {
        "total_users": total_users,
        "premium_users": active_premium,
        "anime_count": anime_count
    }

@app.get("/payments")
async def pending_payments():
    keys = await redis.keys("payment:*")
    payments = {}
    for k in keys:
        user_id = k.split(":")[1]
        payments[user_id] = await redis.get(k)
    return {"pending_payments": payments}

@app.get("/premium")
async def active_premium():
    keys = await redis.keys("premium:*")
    premium = {}
    current_time = time.time()
    for k in keys:
        user_id = k.split(":")[1]
        expiry = float(await redis.get(k))
        if expiry > current_time:
            premium[user_id] = datetime.fromtimestamp(expiry).strftime('%Y-%m-%d %H:%M:%S')
        else:
            await redis.delete(k)
    return {"active_premium": premium}