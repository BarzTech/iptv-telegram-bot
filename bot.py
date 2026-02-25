#!/usr/bin/env python3
"""
IPTV Telegram Bot - CSV STORAGE VERSION
Channels stored in CSV for permanent, editable storage
"""

import os
import sys
import csv
import json
from datetime import datetime, timedelta
from typing import List, Dict

# ===== READ ENVIRONMENT VARIABLES =====
print("="*60)
print("IPTV BOT STARTING - CSV STORAGE")
print("="*60)

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
    print(f"✅ Admin IDs: {ADMIN_IDS}")

# ===== IMPORTS =====
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== CSV FILE STORAGE =====
CHANNELS_CSV = "channels.csv"
VOD_CSV = "vod.csv"

def init_csv_files():
    """Create CSV files with headers if they don't exist"""
    # Channels CSV: name, url, group, added_date
    if not os.path.exists(CHANNELS_CSV):
        with open(CHANNELS_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['name', 'url', 'group', 'added_date'])
        print(f"✅ Created {CHANNELS_CSV}")
    
    # VOD CSV: title, file_id, source, added_date
    if not os.path.exists(VOD_CSV):
        with open(VOD_CSV, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(['title', 'url', 'file_id', 'source', 'added_date'])
        print(f"✅ Created {VOD_CSV}")

def load_channels() -> List[Dict]:
    """Load channels from CSV file"""
    channels = []
    try:
        if os.path.exists(CHANNELS_CSV):
            with open(CHANNELS_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                channels = list(reader)
            print(f"📺 Loaded {len(channels)} channels from CSV")
    except Exception as e:
        print(f"⚠️ Error loading channels: {e}")
    return channels

def save_channels(channels: List[Dict]) -> bool:
    """Save channels to CSV file"""
    try:
        with open(CHANNELS_CSV, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['name', 'url', 'group', 'added_date']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(channels)
        print(f"✅ Saved {len(channels)} channels to CSV")
        return True
    except Exception as e:
        print(f"❌ Error saving channels: {e}")
        return False

def add_channel_to_csv(name: str, url: str, group: str = "Live") -> bool:
    """Append a single channel to CSV (more efficient)"""
    try:
        with open(CHANNELS_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([name, url, group, datetime.now().isoformat()])
        print(f"✅ Appended channel: {name}")
        return True
    except Exception as e:
        print(f"❌ Error appending channel: {e}")
        return False

def load_vod() -> List[Dict]:
    """Load VOD items from CSV"""
    vod_items = []
    try:
        if os.path.exists(VOD_CSV):
            with open(VOD_CSV, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                vod_items = list(reader)
            print(f"🎥 Loaded {len(vod_items)} VOD items from CSV")
    except Exception as e:
        print(f"⚠️ Error loading VOD: {e}")
    return vod_items

def save_vod(vod_items: List[Dict]) -> bool:
    """Save VOD items to CSV"""
    try:
        with open(VOD_CSV, 'w', newline='', encoding='utf-8') as f:
            fieldnames = ['title', 'url', 'file_id', 'source', 'added_date']
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(vod_items)
        print(f"✅ Saved {len(vod_items)} VOD items to CSV")
        return True
    except Exception as e:
        print(f"❌ Error saving VOD: {e}")
        return False

def add_vod_to_csv(title: str, url: str = "", file_id: str = "", source: str = "telegram") -> bool:
    """Append a single VOD to CSV"""
    try:
        with open(VOD_CSV, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([title, url, file_id, source, datetime.now().isoformat()])
        print(f"✅ Appended VOD: {title}")
        return True
    except Exception as e:
        print(f"❌ Error appending VOD: {e}")
        return False

# Initialize CSV files on startup
init_csv_files()

# ===== TELEGRAM HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 **IPTV Bot - CSV Storage Version**\n\n"
        "**Commands:**\n"
        "/add NAME URL - Add live channel\n"
        "/list - List all channels\n"
        "/remove NAME - Remove channel\n"
        "Send any video - Add to VOD library\n"
        "/vodlist - List all VOD items\n"
        "/generate USERNAME DAYS - Create user file\n\n"
        "**Data stored in CSV files - permanent and editable!**",
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
    group = context.args[2] if len(context.args) > 2 else "Live"
    
    # Check if channel already exists
    channels = load_channels()
    for ch in channels:
        if ch['name'].lower() == name.lower():
            await update.message.reply_text(f"❌ Channel '{name}' already exists!")
            return
    
    # Append to CSV
    if add_channel_to_csv(name, url, group):
        await update.message.reply_text(f"✅ Added channel: {name}")
    else:
        await update.message.reply_text("❌ Failed to save channel")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    channels = load_channels()
    
    if not channels:
        await update.message.reply_text("📭 No channels yet")
        return
    
    msg = "📺 **Your Channels:**\n\n"
    for i, ch in enumerate(channels, 1):
        msg += f"{i}. **{ch['name']}** ({ch.get('group', 'Live')})\n"
    
    msg += f"\n**Total:** {len(channels)} channels"
    
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
    
    # Filter out the channel
    new_channels = [ch for ch in channels if ch['name'].lower() != name.lower()]
    
    if len(new_channels) == len(channels):
        await update.message.reply_text(f"❌ Channel '{name}' not found")
        return
    
    # Save all channels (rewrite entire file)
    if save_channels(new_channels):
        await update.message.reply_text(f"✅ Removed channel: {name}")
    else:
        await update.message.reply_text("❌ Failed to save changes")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video uploads - saves to CSV"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    # Get video info
    video = update.message.video
    if not video:
        document = update.message.document
        if document and document.mime_type and 'video' in document.mime_type:
            file_id = document.file_id
            title = update.message.caption or document.file_name or "Unnamed Video"
        else:
            await update.message.reply_text("Please send a video file")
            return
    else:
        file_id = video.file_id
        title = update.message.caption or video.file_name or f"Video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Append to CSV
    if add_vod_to_csv(title, "", file_id, "telegram"):
        # Count total VODs
        vod_items = load_vod()
        await update.message.reply_text(
            f"✅ **Added to VOD Library**\n\n"
            f"**Title:** {title}\n"
            f"**Total VODs:** {len(vod_items)}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Failed to save VOD")

async def vod_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    vod_items = load_vod()
    
    if not vod_items:
        await update.message.reply_text("📭 No VOD items yet")
        return
    
    msg = "🎥 **Your VOD Library:**\n\n"
    for i, vod in enumerate(vod_items[-20:], 1):
        msg += f"{i}. **{vod['title']}**\n"
    
    msg += f"\n**Total:** {len(vod_items)} items"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def generate_user_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate M3U file from CSV data"""
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
    vod_items = load_vod()
    
    # Build M3U
    m3u = f"""#EXTM3U
# IPTV Playlist for: {username}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Expires: {expiry.strftime('%Y-%m-%d')}
# Data source: CSV files
#
# This file contains {len(channels)} live channels and {len(vod_items)} VOD items
#
"""
    
    # Live channels
    if channels:
        m3u += "#" + "="*50 + "\n"
        m3u += "# LIVE CHANNELS\n"
        m3u += "#" + "="*50 + "\n\n"
        
        for ch in channels:
            m3u += f'#EXTINF:-1 group-title="{ch.get("group", "Live")}",{ch["name"]}\n'
            m3u += f"{ch['url']}\n"
        
        m3u += "\n"
    
    # VOD section
    if vod_items:
        m3u += "#" + "="*50 + "\n"
        m3u += "# VOD LIBRARY\n"
        m3u += "#" + "="*50 + "\n\n"
        
        for vod in vod_items:
            if vod.get('source') == 'screenpal' and vod.get('url'):
                # External URL
                m3u += f'#EXTINF:-1 group-title="VOD",{vod["title"]}\n'
                m3u += f"{vod['url']}\n\n"
            elif vod.get('file_id'):
                # Telegram video with instructions
                m3u += f'#EXTINF:-1 group-title="VOD - Telegram",{vod["title"]}\n'
                m3u += f"# File ID: {vod['file_id']}\n"
                m3u += "# Use @SaveStreamBot to download\n\n"
    
    await update.message.reply_document(
        document=m3u.encode('utf-8'),
        filename=f"{username}_iptv.m3u",
        caption=f"✅ **User file generated!**\n\n"
                f"**User:** {username}\n"
                f"**Expires:** {expiry.strftime('%Y-%m-%d')}\n"
                f"**📺 Live Channels:** {len(channels)}\n"
                f"**🎥 VOD Items:** {len(vod_items)}\n\n"
                f"Data stored in CSV files in your repository!"
    )

# ===== ADD EXTERNAL VOD COMMAND =====
async def add_external_vod(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add VOD from external URL (ScreenPal, etc.) - Usage: /addext TITLE URL"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /addext TITLE URL")
        return
    
    title = " ".join(context.args[:-1])
    url = context.args[-1]
    
    if add_vod_to_csv(title, url, "", "screenpal"):
        await update.message.reply_text(f"✅ Added external VOD: {title}")
    else:
        await update.message.reply_text("❌ Failed to save")

# ===== MAIN =====
def main():
    print("\n🚀 Starting bot with CSV storage...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_channel))
    app.add_handler(CommandHandler("list", list_channels))
    app.add_handler(CommandHandler("remove", remove_channel))
    app.add_handler(CommandHandler("vodlist", vod_list))
    app.add_handler(CommandHandler("generate", generate_user_file))
    app.add_handler(CommandHandler("addext", add_external_vod))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_video))
    
    print("✅ Bot is running! Send /start to test")
    print("="*60)
    
    app.run_polling()

if __name__ == "__main__":
    main()
