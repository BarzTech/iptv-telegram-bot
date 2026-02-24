#!/usr/bin/env python3
"""
IPTV Telegram Bot - GitHub Actions Optimized Version
Suppresses harmless conflict errors
"""

import os
import sys
import json
import logging
import warnings
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Suppress harmless warnings
warnings.filterwarnings("ignore", message="Conflict: terminated by other getUpdates request")

# ============================================
# READ ENVIRONMENT VARIABLES
# ============================================
print("\n" + "="*60)
print("IPTV BOT STARTING ON GITHUB ACTIONS")
print("="*60)

# Get bot token
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    sys.exit(1)
print("✅ BOT_TOKEN found")

# Get MediaFlow URL
MEDIAFLOW_URL = os.environ.get("MEDIAFLOW_URL", "")
if MEDIAFLOW_URL:
    print(f"✅ MEDIAFLOW_URL: {MEDIAFLOW_URL}")

# Get MediaFlow password
MEDIAFLOW_PASS = os.environ.get("MEDIAFLOW_PASS", "")
if MEDIAFLOW_PASS:
    print("✅ MEDIAFLOW_PASS set")

# Get admin IDs
ADMIN_IDS_STR = os.environ.get("ADMIN_IDS", "")
ADMIN_IDS = []
if ADMIN_IDS_STR:
    try:
        for id_str in ADMIN_IDS_STR.split(","):
            if id_str.strip():
                ADMIN_IDS.append(int(id_str.strip()))
        print(f"✅ ADMIN_IDS: {ADMIN_IDS}")
    except Exception as e:
        print(f"⚠️ Error parsing ADMIN_IDS: {e}")

# ============================================
# IMPORTS
# ============================================
try:
    from telegram import Update
    from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
    from telegram.error import Conflict
    print("✅ Telegram imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Setup logging - reduce verbosity
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.WARNING  # Only show warnings and errors
)
logger = logging.getLogger(__name__)

# ============================================
# DATA STORAGE FUNCTIONS
# ============================================
CHANNELS_FILE = "channels.json"
VOD_FILE = "vod.json"

def load_channels() -> List[Dict]:
    try:
        if os.path.exists(CHANNELS_FILE):
            with open(CHANNELS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_channels(channels: List[Dict]) -> bool:
    try:
        with open(CHANNELS_FILE, 'w') as f:
            json.dump(channels, f, indent=2)
        return True
    except:
        return False

def load_vod() -> List[Dict]:
    try:
        if os.path.exists(VOD_FILE):
            with open(VOD_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return []

def save_vod(vod_items: List[Dict]) -> bool:
    try:
        with open(VOD_FILE, 'w') as f:
            json.dump(vod_items, f, indent=2)
        return True
    except:
        return False

# ============================================
# TELEGRAM COMMAND HANDLERS
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 **IPTV Manager Bot - Running!**\n\n"
        "**Commands:**\n"
        "/help - Show all commands\n"
        "/status - Bot status\n"
        "/add NAME URL [GROUP] - Add channel\n"
        "/remove NAME - Remove channel\n"
        "/list - List channels\n"
        "/vodlist - List VOD items\n"
        "/generate USERNAME DAYS - Create user file\n\n"
        "Send any video to add to VOD library",
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
📺 **CHANNEL COMMANDS:**

`/add NAME URL [GROUP]` - Add new channel
  Example: `/add BBC http://example.com/stream.m3u8 News`

`/remove NAME` - Remove channel by name
  Example: `/remove BBC`

`/list` - Show all channels

🎥 **VOD COMMANDS:**

Send any video file to bot - Adds to VOD library
`/vodlist` - List all VOD items

👥 **USER MANAGEMENT:**

`/generate USERNAME DAYS` - Create user file
  Example: `/generate john 30` (30-day access)

`/status` - Check bot status
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    channels = load_channels()
    vod_items = load_vod()
    
    status_text = f"✅ **Bot Status: Running**\n\n"
    status_text += f"**Your ID:** `{user_id}`\n"
    status_text += f"**Admin:** {'✅' if user_id in ADMIN_IDS else '❌'}\n\n"
    status_text += f"**📺 Channels:** {len(channels)}\n"
    status_text += f"**🎥 VOD Items:** {len(vod_items)}\n"
    status_text += f"**🌐 MediaFlow:** {'✅' if MEDIAFLOW_URL else '❌'}\n\n"
    status_text += f"**Runtime:** GitHub Actions (hourly runs)"
    
    await update.message.reply_text(status_text, parse_mode='Markdown')

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
    
    channels = load_channels()
    
    for ch in channels:
        if ch['name'].lower() == name.lower():
            await update.message.reply_text(f"❌ Channel '{name}' already exists!")
            return
    
    channels.append({
        "name": name,
        "url": url,
        "group": group,
        "added": datetime.now().isoformat()
    })
    
    if save_channels(channels):
        await update.message.reply_text(f"✅ Added channel: **{name}**", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Error saving channel")

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
        await update.message.reply_text(f"✅ Removed channel: {name}")
    else:
        await update.message.reply_text("❌ Error saving changes")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    channels = load_channels()
    
    if not channels:
        await update.message.reply_text("📭 No channels yet.")
        return
    
    message = "📺 **Your Channels:**\n\n"
    for ch in channels:
        message += f"• **{ch['name']}** ({ch.get('group', 'General')})\n"
    
    message += f"\n**Total:** {len(channels)} channels"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    video = update.message.video
    if not video:
        return
    
    file_id = video.file_id
    title = update.message.caption or video.file_name or f"Video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    vod_items = load_vod()
    
    vod_items.append({
        "file_id": file_id,
        "title": title,
        "added": datetime.now().isoformat()
    })
    
    if save_vod(vod_items):
        response = f"✅ Added VOD: **{title}**\n\n"
        if MEDIAFLOW_URL and MEDIAFLOW_PASS:
            stream_url = f"{MEDIAFLOW_URL}/proxy/stream?d=telegram:{file_id}&api_password={MEDIAFLOW_PASS}"
            response += f"[Test Stream]({stream_url})"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Error saving VOD")

async def vod_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    vod_items = load_vod()
    
    if not vod_items:
        await update.message.reply_text("📭 No VOD items yet.")
        return
    
    message = "🎥 **Your VOD Library:**\n\n"
    for i, vod in enumerate(vod_items[-10:], 1):
        message += f"{i}. **{vod['title']}**\n"
    
    message += f"\n**Total:** {len(vod_items)} items"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def generate_user_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: `/generate USERNAME DAYS`", parse_mode='Markdown')
        return
    
    username = context.args[0]
    days = int(context.args[1])
    expiry = datetime.now() + timedelta(days=days)
    
    channels = load_channels()
    
    m3u_content = f"""#EXTM3U
# IPTV Playlist for: {username}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Expires: {expiry.strftime('%Y-%m-%d')}
#
# Your channels:
"""
    
    for ch in channels:
        m3u_content += f"\n#EXTINF:-1 group-title=\"{ch['group']}\",{ch['name']}\n"
        m3u_content += f"{ch['url']}\n"
    
    await update.message.reply_document(
        document=m3u_content.encode('utf-8'),
        filename=f"{username}_iptv.m3u",
        caption=f"✅ Generated for {username}\nExpires: {expiry.strftime('%Y-%m-%d')}"
    )

# ============================================
# MAIN FUNCTION
# ============================================
def main():
    """Start the bot"""
    print("\n🚀 Starting bot...")
    
    try:
        # Create application
        app = Application.builder().token(BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("status", status))
        app.add_handler(CommandHandler("add", add_channel))
        app.add_handler(CommandHandler("remove", remove_channel))
        app.add_handler(CommandHandler("list", list_channels))
        app.add_handler(CommandHandler("vodlist", vod_list))
        app.add_handler(CommandHandler("generate", generate_user_file))
        app.add_handler(MessageHandler(filters.VIDEO, handle_video))
        
        print("✅ Bot ready! Listening for commands...")
        print("="*60)
        
        # Start bot
        app.run_polling()
        
    except Exception as e:
        if "Conflict" in str(e):
            # This is normal - ignore it
            pass
        else:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    main()
