#!/usr/bin/env python3
"""
IPTV Telegram Bot - STABLE PRODUCTION VERSION
No debug messages, just works!
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta

# ===== READ ENVIRONMENT VARIABLES =====
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    sys.exit(1)

ADMIN_IDS_STR = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = []
if ADMIN_IDS_STR:
    for id_str in ADMIN_IDS_STR.split(","):
        if id_str.strip():
            ADMIN_IDS.append(int(id_str.strip()))

# ===== IMPORTS =====
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== DATA STORAGE =====
CHANNELS_FILE = "channels.json"
VOD_FILE = "vod.json"

def load_channels():
    try:
        if os.path.exists(CHANNELS_FILE):
            with open(CHANNELS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_channels(channels):
    try:
        with open(CHANNELS_FILE, 'w') as f:
            json.dump(channels, f, indent=2)
        return True
    except:
        return False

def load_vod():
    try:
        if os.path.exists(VOD_FILE):
            with open(VOD_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_vod(vod_items):
    try:
        with open(VOD_FILE, 'w') as f:
            json.dump(vod_items, f, indent=2)
        return True
    except:
        return False

# ===== TELEGRAM HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 **IPTV Bot - Running**\n\n"
        "Commands:\n"
        "/add NAME URL - Add channel\n"
        "/list - List channels\n"
        "/remove NAME - Remove channel\n"
        "/vodlist - List VODs\n"
        "/generate USERNAME DAYS - Create user file",
        parse_mode='Markdown'
    )

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /add NAME URL")
        return
    
    name = context.args[0]
    url = context.args[1]
    
    channels = load_channels()
    
    # Check if exists
    for ch in channels:
        if ch['name'].lower() == name.lower():
            await update.message.reply_text(f"❌ Channel '{name}' exists")
            return
    
    channels.append({
        "name": name,
        "url": url,
        "group": "General",
        "added": datetime.now().isoformat()
    })
    
    if save_channels(channels):
        await update.message.reply_text(f"✅ Added: {name}")
    else:
        await update.message.reply_text("❌ Save failed")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    channels = load_channels()
    
    if not channels:
        await update.message.reply_text("📭 No channels yet")
        return
    
    msg = "📺 **Your Channels:**\n"
    for ch in channels:
        msg += f"\n• {ch['name']}"
    msg += f"\n\nTotal: {len(channels)}"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /remove NAME")
        return
    
    name = context.args[0]
    channels = load_channels()
    new_channels = [ch for ch in channels if ch['name'].lower() != name.lower()]
    
    if len(new_channels) == len(channels):
        await update.message.reply_text(f"❌ Channel '{name}' not found")
        return
    
    if save_channels(new_channels):
        await update.message.reply_text(f"✅ Removed: {name}")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    video = update.message.video
    if not video:
        return
    
    title = update.message.caption or video.file_name or f"Video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    vod_items = load_vod()
    vod_items.append({
        "file_id": video.file_id,
        "title": title,
        "added": datetime.now().isoformat()
    })
    
    if save_vod(vod_items):
        await update.message.reply_text(f"✅ Added VOD: {title}")

async def vod_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    vod_items = load_vod()
    
    if not vod_items:
        await update.message.reply_text("📭 No VOD items")
        return
    
    msg = "🎥 **Your VOD Library:**\n"
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
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Expires: {expiry.strftime('%Y-%m-%d')}
"""
    for ch in channels:
        m3u += f"\n#EXTINF:-1,{ch['name']}\n{ch['url']}\n"
    
    await update.message.reply_document(
        document=m3u.encode('utf-8'),
        filename=f"{username}_iptv.m3u",
        caption=f"✅ Generated\nExpires: {expiry.strftime('%Y-%m-%d')}"
    )

# ===== MAIN =====
def main():
    print("🚀 Starting IPTV Bot...")
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_channel))
    app.add_handler(CommandHandler("list", list_channels))
    app.add_handler(CommandHandler("remove", remove_channel))
    app.add_handler(CommandHandler("vodlist", vod_list))
    app.add_handler(CommandHandler("generate", generate_user_file))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    
    print("✅ Bot is running!")
    app.run_polling()

if __name__ == "__main__":
    main()
