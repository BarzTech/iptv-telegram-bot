#!/usr/bin/env python3
"""
IPTV Telegram Bot - COMPLETE VERSION WITH VOD SUPPORT
Channels and VOD both work in VLC
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict

# ===== READ ENVIRONMENT VARIABLES =====
print("="*60)
print("IPTV BOT STARTING - VOD ENABLED")
print("="*60)

BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    print("❌ ERROR: BOT_TOKEN not set!")
    sys.exit(1)

# Read MediaFlow credentials (CRITICAL FOR VOD)
MEDIAFLOW_URL = os.environ.get("MEDIAFLOW_URL", "")
MEDIAFLOW_PASS = os.environ.get("MEDIAFLOW_PASS", "")

if MEDIAFLOW_URL and MEDIAFLOW_PASS:
    print("✅ MediaFlow configured - VOD will work")
else:
    print("⚠️ MediaFlow not configured - VOD will not stream")
    print("   Add MEDIAFLOW_URL and MEDIAFLOW_PASS to GitHub Secrets")

# Read admin IDs
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

# ===== DATA STORAGE =====
CHANNELS_FILE = "channels.json"
VOD_FILE = "vod.json"

def load_channels() -> List[Dict]:
    """Load channels from JSON file"""
    try:
        if os.path.exists(CHANNELS_FILE):
            with open(CHANNELS_FILE, 'r') as f:
                data = json.load(f)
                print(f"📺 Loaded {len(data)} channels")
                return data
    except Exception as e:
        print(f"⚠️ Error loading channels: {e}")
    return []

def save_channels(channels: List[Dict]) -> bool:
    """Save channels to JSON file"""
    try:
        with open(CHANNELS_FILE, 'w') as f:
            json.dump(channels, f, indent=2)
        print(f"✅ Saved {len(channels)} channels")
        return True
    except Exception as e:
        print(f"❌ Error saving channels: {e}")
        return False

def load_vod() -> List[Dict]:
    """Load VOD items from JSON file"""
    try:
        if os.path.exists(VOD_FILE):
            with open(VOD_FILE, 'r') as f:
                data = json.load(f)
                print(f"🎥 Loaded {len(data)} VOD items")
                return data
    except Exception as e:
        print(f"⚠️ Error loading VOD: {e}")
    return []

def save_vod(vod_items: List[Dict]) -> bool:
    """Save VOD items to JSON file"""
    try:
        with open(VOD_FILE, 'w') as f:
            json.dump(vod_items, f, indent=2)
        print(f"✅ Saved {len(vod_items)} VOD items")
        return True
    except Exception as e:
        print(f"❌ Error saving VOD: {e}")
        return False

# ===== TELEGRAM HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    await update.message.reply_text(
        "🎬 **IPTV Bot - Running**\n\n"
        "**Commands:**\n"
        "/add NAME URL - Add live channel\n"
        "/list - List all channels\n"
        "/remove NAME - Remove channel\n"
        "Send any video - Add to VOD library\n"
        "/vodlist - List all VOD items\n"
        "/generate USERNAME DAYS - Create user file\n\n"
        "**Example:**\n"
        "/add BBC http://example.com/stream.m3u8",
        parse_mode='Markdown'
    )

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a live channel"""
    # Check admin
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    # Check arguments
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: /add NAME URL\n"
            "Example: /add BBC http://example.com/stream.m3u8"
        )
        return
    
    name = context.args[0]
    url = context.args[1]
    
    # Load current channels
    channels = load_channels()
    
    # Check if channel already exists
    for ch in channels:
        if ch['name'].lower() == name.lower():
            await update.message.reply_text(f"❌ Channel '{name}' already exists!")
            return
    
    # Add new channel
    channels.append({
        "name": name,
        "url": url,
        "group": "Live",
        "added": datetime.now().isoformat(),
        "added_by": update.effective_user.id
    })
    
    # Save
    if save_channels(channels):
        await update.message.reply_text(f"✅ Added live channel: {name}")
    else:
        await update.message.reply_text("❌ Failed to save channel")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all live channels"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    channels = load_channels()
    
    if not channels:
        await update.message.reply_text("📭 No channels yet. Use /add to add some!")
        return
    
    # Build message
    msg = "📺 **Your Live Channels:**\n\n"
    for i, ch in enumerate(channels, 1):
        msg += f"{i}. **{ch['name']}**\n"
    
    msg += f"\n**Total:** {len(channels)} channels"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a live channel"""
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
    
    # Save
    if save_channels(new_channels):
        await update.message.reply_text(f"✅ Removed channel: {name}")
    else:
        await update.message.reply_text("❌ Failed to save changes")

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video uploads - adds to VOD library"""
    # Check admin
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    # Get video info
    video = update.message.video
    if not video:
        # Check if it's a document that might be a video
        document = update.message.document
        if document and document.mime_type and 'video' in document.mime_type:
            # It's a video file sent as document
            file_id = document.file_id
            file_name = document.file_name or "Unnamed Video"
            title = update.message.caption or file_name
        else:
            await update.message.reply_text("Please send a video file")
            return
    else:
        # It's a regular video message
        file_id = video.file_id
        title = update.message.caption or video.file_name or f"Video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Load existing VOD
    vod_items = load_vod()
    
    # Check if already exists (optional)
    for vod in vod_items:
        if vod['file_id'] == file_id:
            await update.message.reply_text("⚠️ This video is already in your VOD library")
            return
    
    # Add new VOD
    vod_items.append({
        "file_id": file_id,
        "title": title,
        "added": datetime.now().isoformat(),
        "added_by": update.effective_user.id
    })
    
    # Save
    if save_vod(vod_items):
        # Create preview URL if MediaFlow is configured
        preview = ""
        if MEDIAFLOW_URL and MEDIAFLOW_PASS:
            preview = f"\nPreview: {MEDIAFLOW_URL}/proxy/stream?d=telegram:{file_id}&api_password={MEDIAFLOW_PASS}"
        
        await update.message.reply_text(
            f"✅ **Added to VOD Library**\n\n"
            f"**Title:** {title}\n"
            f"**Total VODs:** {len(vod_items)}{preview}",
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text("❌ Failed to save VOD")

async def vod_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all VOD items"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    vod_items = load_vod()
    
    if not vod_items:
        await update.message.reply_text("📭 No VOD items yet. Send me videos to add them!")
        return
    
    # Build message
    msg = "🎥 **Your VOD Library:**\n\n"
    for i, vod in enumerate(vod_items[-20:], 1):  # Show last 20
        added = datetime.fromisoformat(vod['added']).strftime('%Y-%m-%d')
        msg += f"{i}. **{vod['title']}**\n"
        msg += f"   📅 {added}\n\n"
    
    if len(vod_items) > 20:
        msg += f"... and {len(vod_items)-20} more\n"
    
    msg += f"\n**Total:** {len(vod_items)} items"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def generate_user_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a user file with BOTH channels AND VOD"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: /generate USERNAME DAYS\n"
            "Example: /generate john 30"
        )
        return
    
    username = context.args[0]
    days = int(context.args[1])
    expiry = datetime.now() + timedelta(days=days)
    
    # Load BOTH channels and VOD
    channels = load_channels()
    vod_items = load_vod()
    
    # Start building the M3U file
    m3u = f"""#EXTM3U
# IPTV Playlist for: {username}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Expires: {expiry.strftime('%Y-%m-%d')}
#
# This file contains {len(channels)} live channels and {len(vod_items)} VOD items
#
"""
    
    # ===== LIVE CHANNELS SECTION =====
    if channels:
        m3u += "#" + "="*50 + "\n"
        m3u += "# LIVE CHANNELS\n"
        m3u += "#" + "="*50 + "\n\n"
        
        for ch in channels:
            # Add channel info
            m3u += f'#EXTINF:-1 tvg-logo="" group-title="{ch.get("group", "Live")}",{ch["name"]}\n'
            m3u += f"{ch['url']}\n"
        
        m3u += "\n"
    
    # ===== VOD SECTION =====
    if vod_items:
        m3u += "#" + "="*50 + "\n"
        m3u += "# VOD LIBRARY (Movies & Videos)\n"
        m3u += "#" + "="*50 + "\n\n"
        
        for vod in vod_items:
            # Check if MediaFlow is configured
            if MEDIAFLOW_URL and MEDIAFLOW_PASS:
                # Create streaming URL through MediaFlow
                stream_url = f"{MEDIAFLOW_URL}/proxy/stream?d=telegram:{vod['file_id']}&api_password={MEDIAFLOW_PASS}"
                
                # Add VOD entry
                m3u += f'#EXTINF:-1 type="vod" group-title="VOD",{vod["title"]}\n'
                m3u += f"{stream_url}\n\n"
            else:
                # Without MediaFlow, add instructions
                m3u += f'#EXTINF:-1 group-title="VOD",{vod["title"]} (VOD requires MediaFlow setup)\n'
                m3u += "# To enable VOD streaming, configure MEDIAFLOW_URL and MEDIAFLOW_PASS\n\n"
    
    # ===== INSTRUCTIONS =====
    m3u += "#" + "="*50 + "\n"
    m3u += "# INSTRUCTIONS\n"
    m3u += "#" + "="*50 + "\n"
    m3u += "# 1. Save this file\n"
    m3u += "# 2. Open VLC Media Player\n"
    m3u += "# 3. File → Open File → Select this .m3u file\n"
    m3u += "# 4. Enjoy your channels and videos!\n"
    
    # Send the file
    await update.message.reply_document(
        document=m3u.encode('utf-8'),
        filename=f"{username}_iptv.m3u",
        caption=f"✅ **User file generated!**\n\n"
                f"**User:** {username}\n"
                f"**Expires:** {expiry.strftime('%Y-%m-%d')}\n"
                f"**📺 Live Channels:** {len(channels)}\n"
                f"**🎥 VOD Items:** {len(vod_items)}\n\n"
                f"Open this .m3u file in VLC to watch."
    )

# ===== MAIN FUNCTION =====
def main():
    """Start the bot"""
    print("\n🚀 Starting bot...")
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_channel))
    app.add_handler(CommandHandler("list", list_channels))
    app.add_handler(CommandHandler("remove", remove_channel))
    app.add_handler(CommandHandler("vodlist", vod_list))
    app.add_handler(CommandHandler("generate", generate_user_file))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    app.add_handler(MessageHandler(filters.Document.ALL, handle_video))  # Also handle video files sent as documents
    
    print("✅ Bot is running! Send /start to test")
    print("="*60)
    
    # Start bot
    app.run_polling()

if __name__ == "__main__":
    main()
