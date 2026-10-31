import os
import subprocess
import sys

# ---------------------------
# AUTO-INSTALL DEPENDENCIES
# ---------------------------
def install_requirements():
    required_packages = {
        "flask": "flask",
        "telegram": "python-telegram-bot",
        "requests": "requests"
    }
    for module_name, package_name in required_packages.items():
        try:
            __import__(module_name)
        except ImportError:
            print(f"📦 Installing missing package: {package_name}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])

install_requirements()

import asyncio
import json
import random
import time
import threading
import requests
from flask import Flask
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters
import logging

# ---------------------------
# CONFIG & ENVIRONMENT SETUP
# ---------------------------
TOKENS_FILE = "tokens.txt"
TOKENS = []

env_tokens = os.environ.get("BOT_TOKENS") or os.environ.get("TOKENS")
if env_tokens:
    TOKENS = [t.strip() for t in env_tokens.replace(",", " ").split() if t.strip()]

if not TOKENS and os.path.exists(TOKENS_FILE):
    with open(TOKENS_FILE, "r") as f:
        TOKENS = [line.strip() for line in f if line.strip()]

if not TOKENS:
    print("❌ No tokens found! Please set 'BOT_TOKENS' in Render environment variables or create tokens.txt.")
    exit(1)

OWNER_ID = 6133172474
SUDO_FILE = "sudo.json"

# ---------------------------
# GLOBAL STATE MANAGEMENT
# ---------------------------
if os.path.exists(SUDO_FILE):
    try:
        with open(SUDO_FILE, "r") as f:
            _loaded = json.load(f)
            SUDO_USERS = set(int(x) for x in _loaded)
    except Exception:
        SUDO_USERS = {OWNER_ID}
else:
    SUDO_USERS = {OWNER_ID}

SUDO_USERS.add(OWNER_ID)
with open(SUDO_FILE, "w") as f: json.dump(list(SUDO_USERS), f)

def save_sudo():
    with open(SUDO_FILE, "w") as f: json.dump(list(SUDO_USERS), f)

group_tasks = {}         
swipe_tasks = {}         # Stores message_id: asyncio.Task
autoreply_targets = {}   # Stores user_id: text
spam_tasks = {}          # Stores chat_id: asyncio.Task
poll_tasks = {}          # Stores chat_id: asyncio.Task
slay_mode = {}
pfp_loop_tasks = {}     
saved_pfp_bytes = []    
apps, bots = [], []
delay = 0.05

logging.basicConfig(level=logging.WARNING)

# ---------------------------
# FLASK WEB APP (DASHBOARD)
# ---------------------------
app_flask = Flask(__name__)

@app_flask.route("/")
def index():
    return """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>VIVEK SAMRAJYA - Ultimate Control Center</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                background-color: #070707;
                color: #ffffff;
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                overflow: hidden;
            }
            .container {
                text-align: center;
                background: rgba(15, 15, 15, 0.9);
                border: 2px solid #ff2222;
                padding: 50px 70px;
                border-radius: 24px;
                box-shadow: 0 0 40px rgba(255, 34, 34, 0.5);
            }
            h1 {
                font-family: 'Georgia', serif;
                font-size: 3rem;
                font-weight: 900;
                font-style: italic;
                color: #ff3333;
                text-shadow: 0 0 20px rgba(255, 0, 0, 0.9);
                letter-spacing: 3px;
                margin-bottom: 20px;
            }
            .subtitle {
                font-size: 1.1rem;
                color: #aaaaaa;
                letter-spacing: 2px;
                margin-bottom: 30px;
                text-transform: uppercase;
            }
            .chakra-loader {
                width: 90px;
                height: 90px;
                border: 6px dashed #ff2222;
                border-top: 6px solid transparent;
                border-radius: 50%;
                margin: 0 auto 25px auto;
                animation: spin 1s linear infinite;
                box-shadow: 0 0 25px rgba(255, 0, 0, 0.7);
            }
            @keyframes spin {
                0% { transform: rotate(0deg); }
                100% { transform: rotate(360deg); }
            }
            .status {
                font-size: 1.15rem;
                color: #00ff66;
                font-weight: bold;
                letter-spacing: 1.5px;
                background: rgba(0, 255, 102, 0.12);
                padding: 10px 20px;
                border-radius: 10px;
                display: inline-block;
                border: 1px solid rgba(0, 255, 102, 0.4);
                box-shadow: 0 0 15px rgba(0, 255, 102, 0.2);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="chakra-loader"></div>
            <h1><i>VIVEK SAMRAJYA</i></h1>
            <div class="subtitle">⚡ High-Performance Multi-Bot Architecture ⚡</div>
            <div class="status">🚀 Status: Fully Operational & Online 24/7</div>
        </div>
    </body>
    </html>
    """

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app_flask.run(host="0.0.0.0", port=port)

# ---------------------------
# SELF-PING MECHANISM
# ---------------------------
def self_ping():
    app_url = os.environ.get("RENDER_EXTERNAL_URL", "http://127.0.0.1:8080")
    while True:
        try:
            time.sleep(300)
            requests.get(app_url)
        except Exception:
            pass

# ---------------------------
# DECORATORS
# ---------------------------
def only_sudo(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user:
            return
        uid = update.effective_user.id
        if uid not in SUDO_USERS:
            return await update.message.reply_text("❌ Access Denied: You are not authorized as an Administrator.")
        return await func(update, context)
    return wrapper

def only_owner(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.effective_user:
            return
        uid = update.effective_user.id
        if uid != OWNER_ID:
            return await update.message.reply_text("❌ Access Denied: Only Vivek (Owner) can execute this command.")
        return await func(update, context)
    return wrapper

# ---------------------------
# FIXED BACKGROUND WORKERS
# ---------------------------
NCEMO_EMOJIS = ["😋","😝","😜","🤪","😑","🤫","🤭","🥱","🤗","😡","😠","😤","😎","🥸","😹","💫","⭐","✨","🔥","⚡"]

async def bot_loop(bot, chat_id, base, mode):
    i = 0
    while True:
        try:
            text = f"{base} {NCEMO_EMOJIS[i % len(NCEMO_EMOJIS)]}"
            await bot.set_chat_title(chat_id, text)
            i += 1
            await asyncio.sleep(delay)
        except Exception:
            await asyncio.sleep(1)

async def pfp_loop_task(bot, chat_id):
    while True:
        try:
            if saved_pfp_bytes:
                photo_bytes = random.choice(saved_pfp_bytes)
                await bot.set_chat_photo(chat_id=chat_id, photo=bytes(photo_bytes))
            await asyncio.sleep(max(5.0, delay * 20))
        except Exception:
            await asyncio.sleep(3)

async def swipe_worker(message, text):
    while True:
        try:
            await message.reply_text(text, quote=True)
            await asyncio.sleep(max(0.1, delay))
        except Exception:
            await asyncio.sleep(0.5)

async def spam_worker(bot, chat_id, text):
    while True:
        try:
            await bot.send_message(chat_id=chat_id, text=text)
            await asyncio.sleep(max(0.05, delay))
        except Exception:
            await asyncio.sleep(0.5)

async def poll_worker(bot, chat_id, question_text):
    emoji_sets = [["🔥", "⚡", "🗿", "🚀"], ["💥", "👑", "🎯", "💎"], ["⭐", "💀", "🌪️", "🔥"]]
    while True:
        try:
            options = [f"{question_text} {e}" for e in random.choice(emoji_sets)]
            await bot.send_poll(chat_id=chat_id, question=question_text, options=options, is_anonymous=False)
            await asyncio.sleep(max(0.5, delay * 5))
        except Exception:
            await asyncio.sleep(1)

# ---------------------------
# COMMAND HANDLERS
# ---------------------------
async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔥 Welcome to Vivek Samrajya Control Core!\nType /menu or /assist to access the command suite.")

async def assist_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    menu_text = (
        "⚡ **VIVEK SAMRAJYA - COMMAND SUITE** ⚡\n\n"
        "👑 **Group Name & Loop Management:**\n"
        "• `/gcnc <text>` - Start continuous name rotation loop.\n"
        "• `/ncemo <text>` - Start emoji suffix rotation loop.\n"
        "• `/pausegcnc` - Terminate loops in current chat.\n"
        "• `/pauseall` - Terminate all active loops.\n"
        "• `/delay <seconds>` - Universal execution speed controller.\n\n"
        "⚔️ **Advanced Target Controls:**\n"
        "• `/swipe <text>` (Reply to Msg) - Continuous swipe/quote spam on that specific message until `/swipeend`.\n"
        "• `/swipeend` (Reply to Msg) - Stop swipe loop.\n"
        "• `/autoreply <text>` (Reply to User) - Auto-replies whenever the target texts until `/autoreplyend`.\n"
        "• `/autoreplyend` (Reply to User) - Stop autoreply.\n"
        "• `/spam <text>` (Reply to User) - Continuous burst spam until `/spamend`.\n"
        "• `/spamend` (Reply to User) - Stop spam loop.\n"
        "• `/poll <text>` (Reply to User) - Continuous poll spam until `/pollend`.\n"
        "• `/pollend` (Reply to User) - Stop poll spam.\n\n"
        "⚡ **Group Wide Slay Mode:**\n"
        "• `/slay <text>` - Set custom prefix for group messages.\n"
        "• `/stopslay` - Disable group slay mode.\n\n"
        "🖼 **Profile & Identity Controls:**\n"
        "• `/dp` (Reply to Image) - Set replied image as bot profile picture instantly.\n"
        "• `/name <text>` - Change all bots' first name instantly.\n"
        "• `/startpfp` (Reply to Image) - Start continuous group PFP rotation loop.\n"
        "• `/stoppfp` - Stop group PFP rotation loop.\n\n"
        "🛡 **Administration:**\n"
        "• `/addadmin` / `/deladmin` / `/adminlist`\n"
        "• `/ping` - Check latency."
    )
    await update.message.reply_text(menu_text, parse_mode="Markdown")

async def ping_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    start_time = time.time()
    msg = await update.message.reply_text("🏓 Calculating system latency...")
    latency = int((time.time() - start_time) * 1000)
    await msg.edit_text(f"🏓 System Operational! ✅ Latency: {latency} ms")

async def myid(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Your Unique Telegram ID: `{update.effective_user.id}`", parse_mode="Markdown")

# --- Group Loop Commands ---
@only_sudo
async def gcnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Syntax Error: `/gcnc <text>`", parse_mode="Markdown")
    base = " ".join(context.args)
    chat_id = update.message.chat_id
    await update.message.reply_text("🚀 Group name loop initiated successfully.")
    group_tasks.setdefault(chat_id, {})
    for bot in bots:
        if bot.id not in group_tasks[chat_id]:
            task = asyncio.create_task(bot_loop(bot, chat_id, base, "raid"))
            group_tasks[chat_id][bot.id] = task

@only_sudo
async def ncemo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Syntax Error: `/ncemo <text>`", parse_mode="Markdown")
    base = " ".join(context.args)
    chat_id = update.message.chat_id
    await update.message.reply_text("✨ Emoji rotation loop initiated.")
    group_tasks.setdefault(chat_id, {})
    for bot in bots:
        if bot.id not in group_tasks[chat_id]:
            task = asyncio.create_task(bot_loop(bot, chat_id, base, "emoji"))
            group_tasks[chat_id][bot.id] = task

@only_sudo
async def pausegcnc(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in group_tasks:
        for task in group_tasks[chat_id].values():
            task.cancel()
        group_tasks[chat_id] = {}
        await update.message.reply_text("⏹ Loops successfully terminated in this chat.")
    else:
        await update.message.reply_text("⚠️ No active loops found in this chat.")

@only_sudo
async def pauseall(update: Update, context: ContextTypes.DEFAULT_TYPE):
    for chat_id in list(group_tasks.keys()):
        for task in group_tasks[chat_id].values():
            task.cancel()
        group_tasks[chat_id] = {}
    for task in swipe_tasks.values():
        task.cancel()
    swipe_tasks.clear()
    for task in spam_tasks.values():
        task.cancel()
    spam_tasks.clear()
    for task in poll_tasks.values():
        task.cancel()
    poll_tasks.clear()
    autoreply_targets.clear()
    for chat_id in list(pfp_loop_tasks.keys()):
        for task in pfp_loop_tasks[chat_id].values():
            task.cancel()
        pfp_loop_tasks[chat_id] = {}
    await update.message.reply_text("⏹ Global termination executed successfully: All tasks halted.")

@only_sudo
async def delay_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global delay
    if not context.args:
        return await update.message.reply_text(f"⏱ Universal Execution Delay: {delay}s")
    try:
        delay = max(0.02, float(context.args[0]))
        await update.message.reply_text(f"✅ Universal delay updated to {delay}s")
    except ValueError:
        await update.message.reply_text("⚠️ Invalid numerical format.")

# --- Fixed Target Commands ---
@only_sudo
async def swipe_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Please reply to a specific message to swipe on it.")
    if not context.args:
        return await update.message.reply_text("⚠️ Syntax Error: `/swipe <text>`", parse_mode="Markdown")
    
    msg_id = update.message.reply_to_message.message_id
    text = " ".join(context.args)
    
    if msg_id in swipe_tasks:
        swipe_tasks[msg_id].cancel()
        
    task = asyncio.create_task(swipe_worker(update.message.reply_to_message, text))
    swipe_tasks[msg_id] = task
    await update.message.reply_text(f"⚡ Continuous swipe loop started on the replied message.", parse_mode="Markdown")

@only_sudo
async def swipeend_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Please reply to the swiped message.")
    msg_id = update.message.reply_to_message.message_id
    if msg_id in swipe_tasks:
        swipe_tasks[msg_id].cancel()
        del swipe_tasks[msg_id]
        await update.message.reply_text(f"🛑 Swipe loop stopped for this message.", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ No active swipe loop running for this message.")

@only_sudo
async def autoreply_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Please reply to a user's message.")
    if not context.args:
        return await update.message.reply_text("⚠️ Syntax Error: `/autoreply <text>`", parse_mode="Markdown")
    
    uid = update.message.reply_to_message.from_user.id
    text = " ".join(context.args)
    autoreply_targets[uid] = text
    await update.message.reply_text(f"🔄 Autoreply engaged for user ID `{uid}`. Bot will reply whenever they text.", parse_mode="Markdown")

@only_sudo
async def autoreplyend_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message:
        return await update.message.reply_text("⚠️ Please reply to the target user's message.")
    uid = update.message.reply_to_message.from_user.id
    if uid in autoreply_targets:
        del autoreply_targets[uid]
        await update.message.reply_text(f"🛑 Autoreply disengaged for user ID `{uid}`.", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ No active autoreply found for this user.")

@only_sudo
async def spam_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Syntax Error: `/spam <text>`", parse_mode="Markdown")
    
    text = " ".join(context.args)
    chat_id = update.message.chat_id
    
    if chat_id in spam_tasks:
        spam_tasks[chat_id].cancel()
        
    if bots:
        task = asyncio.create_task(spam_worker(bots[0], chat_id, text))
        spam_tasks[chat_id] = task
        await update.message.reply_text(f"💥 Continuous chat spam started.", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ No active bot instances available.")

@only_sudo
async def spamend_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in spam_tasks:
        spam_tasks[chat_id].cancel()
        del spam_tasks[chat_id]
        await update.message.reply_text(f"🛑 Chat spam loop stopped.", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ No active spam loop found in this chat.")

@only_sudo
async def poll_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Syntax Error: `/poll <text>`", parse_mode="Markdown")
    
    question_text = " ".join(context.args)
    chat_id = update.message.chat_id
    
    if chat_id in poll_tasks:
        poll_tasks[chat_id].cancel()
        
    if bots:
        task = asyncio.create_task(poll_worker(bots[0], chat_id, question_text))
        poll_tasks[chat_id] = task
        await update.message.reply_text(f"📊 Continuous custom poll spam started.", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ No active bot instances available.")

@only_sudo
async def pollend_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in poll_tasks:
        poll_tasks[chat_id].cancel()
        del poll_tasks[chat_id]
        await update.message.reply_text(f"🛑 Poll spam stopped in this chat.", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ No active poll spam found in this chat.")

@only_sudo
async def slay_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Syntax Error: `/slay <text>`", parse_mode="Markdown")
    prefix = " ".join(context.args)
    chat_id = update.message.chat_id
    slay_mode[chat_id] = prefix
    await update.message.reply_text(f"⚡ Group Slay Mode activated with prefix: `{prefix}`", parse_mode="Markdown")

@only_sudo
async def stopslay_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in slay_mode:
        slay_mode.pop(chat_id, None)
        await update.message.reply_text("🛑 Group Slay Mode deactivated.")
    else:
        await update.message.reply_text("⚠️ Slay mode is not active in this chat.")

# --- Profile & Identity Controls ---
@only_sudo
async def dp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        return await update.message.reply_text("⚠️ Please reply to an image to set it as the bots' profile picture.")
    
    photo = update.message.reply_to_message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    
    success_count = 0
    for bot in bots:
        try:
            await bot.set_chat_photo(chat_id=bot.id, photo=bytes(photo_bytes))
            success_count += 1
        except Exception:
            pass
            
    await update.message.reply_text(f"🖼 Profile picture successfully updated across {success_count} bot instances!")

@only_sudo
async def name_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        return await update.message.reply_text("⚠️ Syntax Error: `/name <new_bot_name>`", parse_mode="Markdown")
    
    new_name = " ".join(context.args)
    success_count = 0
    for bot in bots:
        try:
            await bot.set_my_name(new_name)
            success_count += 1
        except Exception as e:
            print(f"Error setting name: {e}")
            
    await update.message.reply_text(f"✏️ Bot name successfully updated to `{new_name}` across {success_count} bot instances!", parse_mode="Markdown")

@only_sudo
async def startpfp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.reply_to_message or not update.message.reply_to_message.photo:
        return await update.message.reply_text("⚠️ Please reply to an image to start the group PFP rotation loop.")
    
    photo = update.message.reply_to_message.photo[-1]
    file = await context.bot.get_file(photo.file_id)
    photo_bytes = await file.download_as_bytearray()
    
    saved_pfp_bytes.append(photo_bytes)
    chat_id = update.message.chat_id
    
    pfp_loop_tasks.setdefault(chat_id, {})
    for bot in bots:
        if bot.id not in pfp_loop_tasks[chat_id]:
            task = asyncio.create_task(pfp_loop_task(bot, chat_id))
            pfp_loop_tasks[chat_id][bot.id] = task
            
    await update.message.reply_text("🔄 Group Profile Picture (PFP) rotation loop successfully started!")

@only_sudo
async def stoppfp_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    if chat_id in pfp_loop_tasks:
        for task in pfp_loop_tasks[chat_id].values():
            task.cancel()
        pfp_loop_tasks[chat_id] = {}
        await update.message.reply_text("🛑 Group Profile Picture rotation loop stopped.")
    else:
        await update.message.reply_text("⚠️ No active PFP loop running in this chat.")

# --- Strict Owner-Protected Admin Management ---
@only_owner
async def addadmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        uid = update.message.reply_to_message.from_user.id
        SUDO_USERS.add(uid)
        save_sudo()
        await update.message.reply_text(f"✅ User ID `{uid}` successfully promoted to Administrator by Owner.", parse_mode="Markdown")
    else:
        await update.message.reply_text("⚠️ Please reply to the user you wish to promote.")

@only_owner
async def deladmin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.reply_to_message:
        uid = update.message.reply_to_message.from_user.id
        if uid == OWNER_ID:
            return await update.message.reply_text("❌ Security Error: Cannot remove the primary owner.")
        if uid in SUDO_USERS:
            SUDO_USERS.remove(uid)
            save_sudo()
            await update.message.reply_text(f"🗑 User ID `{uid}` successfully removed from administrators.", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ This user is not an administrator.")
    else:
        await update.message.reply_text("⚠️ Please reply to the administrator you wish to remove.")

@only_sudo
async def adminlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    admins = "\n".join([f"• `{uid}`" + (" (Owner)" if uid == OWNER_ID else "") for uid in SUDO_USERS])
    await update.message.reply_text(f"👑 **Authorized Administrator Roster:**\n\n{admins}", parse_mode="Markdown")

# --- Auto-Reply Trigger Engine ---
async def auto_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.from_user:
        return
    uid = update.message.from_user.id
    chat_id = update.message.chat_id
    
    if uid in autoreply_targets:
        text = autoreply_targets[uid]
        asyncio.create_task(update.message.reply_text(text))

    if chat_id in slay_mode:
        prefix = slay_mode[chat_id]
        text = f"{prefix} {random.choice(NCEMO_EMOJIS)}"
        asyncio.create_task(update.message.reply_text(text))

# ---------------------------
# BUILD APP & HIGH-PERFORMANCE POLLING
# ---------------------------
def build_app(token):
    app = (
        Application.builder()
        .token(token)
        .read_timeout(7)
        .write_timeout(7)
        .connect_timeout(7)
        .pool_timeout(7)
        .build()
    )
    
    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(CommandHandler("assist", assist_cmd))
    app.add_handler(CommandHandler("menu", assist_cmd))
    app.add_handler(CommandHandler("ping", ping_cmd))
    app.add_handler(CommandHandler("myid", myid))
    app.add_handler(CommandHandler("gcnc", gcnc))
    app.add_handler(CommandHandler("ncemo", ncemo))
    app.add_handler(CommandHandler("pausegcnc", pausegcnc))
    app.add_handler(CommandHandler("pauseall", pauseall))
    app.add_handler(CommandHandler("delay", delay_cmd))
    
    app.add_handler(CommandHandler("swipe", swipe_cmd))
    app.add_handler(CommandHandler("swipeend", swipeend_cmd))
    app.add_handler(CommandHandler("autoreply", autoreply_cmd))
    app.add_handler(CommandHandler("autoreplyend", autoreplyend_cmd))
    app.add_handler(CommandHandler("spam", spam_cmd))
    app.add_handler(CommandHandler("spamend", spamend_cmd))
    app.add_handler(CommandHandler("poll", poll_cmd))
    app.add_handler(CommandHandler("pollend", pollend_cmd))
    
    app.add_handler(CommandHandler("slay", slay_cmd))
    app.add_handler(CommandHandler("stopslay", stopslay_cmd))
    
    app.add_handler(CommandHandler("dp", dp_cmd))
    app.add_handler(CommandHandler("name", name_cmd))
    app.add_handler(CommandHandler("startpfp", startpfp_cmd))
    app.add_handler(CommandHandler("stoppfp", stoppfp_cmd))
    
    app.add_handler(CommandHandler("addadmin", addadmin))
    app.add_handler(CommandHandler("deladmin", deladmin))
    app.add_handler(CommandHandler("adminlist", adminlist))
    
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_replies), group=1)
    return app

async def run_all_bots():
    global apps, bots
    for token in TOKENS:
        if token.strip():
            try:
                app = build_app(token)
                apps.append(app)
                bots.append(app.bot)
            except Exception as e:
                print(f"Failed building app instance: {e}")

    for app in apps:
        try:
            await app.initialize()
            await app.start()
            await app.updater.start_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)
        except Exception as e:
            print(f"Failed starting app instance: {e}")

    print("⚡ VIVEK SAMRAJYA BOTS FULLY ONLINE AND SECURED ⚡")
    await asyncio.Event().wait()

if __name__ == "__main__":
    ping_thread = threading.Thread(target=self_ping)
    ping_thread.daemon = True
    ping_thread.start()

    flask_thread = threading.Thread(target=run_flask)
    flask_thread.daemon = True
    flask_thread.start()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(run_all_bots())
