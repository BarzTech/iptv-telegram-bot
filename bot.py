#!/usr/bin/env python3
"""
IPTV Telegram Bot - ULTRA SIMPLE VERSION
Data never disappears!
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta

# ===== READ ENVIRONMENT VARIABLES =====
print("🚀 Starting IPTV Bot...")

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    sys.exit(1)

MEDIAFLOW_URL = os.environ.get("MEDIAFLOW_URL", "")
MEDIAFLOW_PASS = os.environ.get("MEDIAFLOW_PASS", "")
ADMIN_IDS_STR = os.environ.get("ADMIN_IDS", "")

ADMIN_IDS = []
if ADMIN_IDS_STR:
    for id_str in ADMIN_IDS_STR.split(","):
        if id_str.strip():
            ADMIN_IDS.append(int(id_str.strip()))

# ===== SIMPLE DATA STORAGE =====
# We'll use a simple text file - append only!
CHANNELS_LOG = "channels.log"
VOD_LOG = "vod.log"

def load_channels():
    """Load channels from log file"""
    channels = []
    if os.path.exists(CHANNELS_LOG):
        with open(CHANNELS_LOG, 'r') as f:
            for line in f:
                try:
                    channels.append(json.loads(line.strip()))
                except:
                    pass
    print(f"📺 Loaded {len(channels)} channels")
    return channels

def save_channel(name, url, group):
    """Append ONE channel to log file"""
    channel = {
        "name": name,
        "url": url,
        "group": group,
        "added": datetime.now().isoformat()
    }
    with open(CHANNELS_LOG, 'a') as f:
        f.write(json.dumps(channel) + "\n")
    print(f"✅ Saved channel: {name}")
    return True

def remove_channel(name):
    """Remove channel by name (creates new file without it)"""
    channels = load_channels()
    new_channels = [c for c in channels if c['name'].lower() != name.lower()]
    
    # Rewrite entire file
    with open(CHANNELS_LOG, 'w') as f:
        for ch in new_channels:
            f.write(json.dumps(ch) + "\n")
    print(f"✅ Removed channel: {name}")
    return True

def load_vod():
    """Load VOD from log file"""
    vod_items = []
    if os.path.exists(VOD_LOG):
        with open(VOD_LOG, 'r') as f:
            for line in f:
                try:
                    vod_items.append(json.loads(line.strip()))
                except:
                    pass
    print(f"🎥 Loaded {len(vod_items)} VOD items")
    return vod_items

def save_vod(file_id, title):
    """Append ONE VOD to log file"""
    vod = {
        "file_id": file_id,
        "title": title,
        "added": datetime.now().isoformat()
    }
    with open(VOD_LOG, 'a') as f:
        f.write(json.dumps(vod) + "\n")
    print(f"✅ Saved VOD: {title}")
    return True

# ===== TELEGRAM SETUP =====
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 **IPTV Bot - Running!**\n\n"
        "Commands:\n"
        "/add NAME URL [GROUP] - Add channel\n"
        "/remove NAME - Remove channel\n"
        "/list - List channels\n"
        "/vodlist - List VODs\n"
        "/generate USERNAME DAYS - Create user file\n"
        "Send video to add VOD",
        parse_mode='Markdown'
    )

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /add NAME URL [GROUP]")
        return
    
    name = context.args[0]
    url = context.args[1]
    group = context.args[2] if len(context.args) > 2 else "General"
    
    save_channel(name, url, group)
    await update.message.reply_text(f"✅ Added: {name}")

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /remove NAME")
        return
    
    name = context.args[0]
    remove_channel(name)
    await update.message.reply_text(f"✅ Removed: {name}")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    channels = load_channels()
    if not channels:
        await update.message.reply_text("📭 No channels")
        return
    
    msg = "📺 **Channels:**\n"
    for ch in channels:
        msg += f"\n• {ch['name']} ({ch['group']})"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    video = update.message.video
    if not video:
        return
    
    title = update.message.caption or video.file_name or f"Video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    save_vod(video.file_id, title)
    await update.message.reply_text(f"✅ Added VOD: {title}")

async def vod_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    vod_items = load_vod()
    if not vod_items:
        await update.message.reply_text("📭 No VOD")
        return
    
    msg = "🎥 **VOD Library:**\n"
    for i, vod in enumerate(vod_items[-10:], 1):
        msg += f"\n{i}. {vod['title']}"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def generate_user_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /generate USERNAME DAYS")
        return
    
    username = context.args[0]
    days = int(context.args[1])
    expiry = datetime.now() + timedelta(days=days)
    
    channels = load_channels()
    
    m3u = f"""#EXTM3U
# IPTV for: {username}
# Expires: {expiry.strftime('%Y-%m-%d')}
"""
    for ch in channels:
        m3u += f"\n#EXTINF:-1 group-title=\"{ch['group']}\",{ch['name']}\n{ch['url']}\n"
    
    await update.message.reply_document(
        document=m3u.encode('utf-8'),
        filename=f"{username}_iptv.m3u",
        caption=f"✅ Generated\nExpires: {expiry.strftime('%Y-%m-%d')}"
    )

# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_channel))
    app.add_handler(CommandHandler("remove", remove_channel))
    app.add_handler(CommandHandler("list", list_channels))
    app.add_handler(CommandHandler("vodlist", vod_list))
    app.add_handler(CommandHandler("generate", generate_user_file))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    
    print("✅ Bot running!")
    app.run_polling()

if __name__ == "__main__":
    main()
