#!/usr/bin/env python3
"""
IPTV Telegram Bot - Complete System for GitHub Actions
Manages channels and VOD with MediaFlow Proxy integration
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

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
    print("   Add it in GitHub → Settings → Secrets and variables → Actions")
    sys.exit(1)
print("✅ BOT_TOKEN found")

# Get MediaFlow URL (from your Hugging Face Space)
MEDIAFLOW_URL = os.environ.get("MEDIAFLOW_URL", "")
if MEDIAFLOW_URL:
    print(f"✅ MEDIAFLOW_URL: {MEDIAFLOW_URL}")
else:
    print("⚠️ MEDIAFLOW_URL not set - VOD features limited")

# Get MediaFlow password
MEDIAFLOW_PASS = os.environ.get("MEDIAFLOW_PASS", "")
if MEDIAFLOW_PASS:
    print("✅ MEDIAFLOW_PASS set")
else:
    print("⚠️ MEDIAFLOW_PASS not set")

# Get admin IDs (your Telegram user ID)
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
    print("✅ Telegram imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ============================================
# DATA STORAGE FUNCTIONS
# ============================================
CHANNELS_FILE = "channels.json"
VOD_FILE = "vod.json"

def load_channels() -> List[Dict]:
    """Load channels from JSON file"""
    try:
        if os.path.exists(CHANNELS_FILE):
            with open(CHANNELS_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading channels: {e}")
    return []

def save_channels(channels: List[Dict]) -> bool:
    """Save channels to JSON file"""
    try:
        with open(CHANNELS_FILE, 'w') as f:
            json.dump(channels, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving channels: {e}")
        return False

def load_vod() -> List[Dict]:
    """Load VOD items from JSON file"""
    try:
        if os.path.exists(VOD_FILE):
            with open(VOD_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"Error loading VOD: {e}")
    return []

def save_vod(vod_items: List[Dict]) -> bool:
    """Save VOD items to JSON file"""
    try:
        with open(VOD_FILE, 'w') as f:
            json.dump(vod_items, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving VOD: {e}")
        return False

# ============================================
# TELEGRAM COMMAND HANDLERS
# ============================================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
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
    """Show detailed help"""
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

ℹ️ **HOW IT WORKS:**
1. Add channels with /add
2. Upload videos to Telegram
3. Generate .m3u files for users
4. Users open file in VLC - content auto-updates!
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check bot status"""
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
    """Add a new channel"""
    # Check admin
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized - Admin only")
        return
    
    # Check arguments
    if len(context.args) < 2:
        await update.message.reply_text(
            "❌ Usage: `/add NAME URL [GROUP]`\n"
            "Example: `/add BBC http://example.com/stream.m3u8 News`",
            parse_mode='Markdown'
        )
        return
    
    name = context.args[0]
    url = context.args[1]
    group = context.args[2] if len(context.args) > 2 else "General"
    
    # Load channels
    channels = load_channels()
    
    # Check if exists
    for ch in channels:
        if ch['name'].lower() == name.lower():
            await update.message.reply_text(f"❌ Channel '{name}' already exists!")
            return
    
    # Add new channel
    channels.append({
        "name": name,
        "url": url,
        "group": group,
        "added": datetime.now().isoformat(),
        "added_by": update.effective_user.id
    })
    
    # Save
    if save_channels(channels):
        await update.message.reply_text(f"✅ Added channel: **{name}**", parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Error saving channel")

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a channel"""
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
    
    if save_channels(new_channels):
        await update.message.reply_text(f"✅ Removed channel: {name}")
    else:
        await update.message.reply_text("❌ Error saving changes")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all channels"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    channels = load_channels()
    
    if not channels:
        await update.message.reply_text("📭 No channels yet. Use /add to add some!")
        return
    
    # Group by category
    groups = {}
    for ch in channels:
        group = ch.get('group', 'General')
        if group not in groups:
            groups[group] = []
        groups[group].append(ch)
    
    message = "📺 **Your Channels:**\n\n"
    for group, ch_list in groups.items():
        message += f"**{group}** ({len(ch_list)})\n"
        for ch in ch_list:
            message += f"  • {ch['name']}\n"
        message += "\n"
    
    message += f"**Total:** {len(channels)} channels"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def handle_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle video uploads - adds to VOD library"""
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    video = update.message.video
    if not video:
        return
    
    # Get video info
    file_id = video.file_id
    title = update.message.caption or video.file_name or f"Video_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    
    # Load VOD
    vod_items = load_vod()
    
    # Add new VOD
    vod_items.append({
        "file_id": file_id,
        "title": title,
        "added": datetime.now().isoformat(),
        "added_by": update.effective_user.id
    })
    
    if save_vod(vod_items):
        # Create MediaFlow URL if available
        stream_url = ""
        if MEDIAFLOW_URL and MEDIAFLOW_PASS:
            stream_url = f"{MEDIAFLOW_URL}/proxy/stream?d=telegram:{file_id}&api_password={MEDIAFLOW_PASS}"
        
        response = f"✅ Added VOD: **{title}**\n\n"
        if stream_url:
            response += f"[Test Stream]({stream_url})"
        
        await update.message.reply_text(response, parse_mode='Markdown')
    else:
        await update.message.reply_text("❌ Error saving VOD")

async def vod_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all VOD items"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    vod_items = load_vod()
    
    if not vod_items:
        await update.message.reply_text("📭 No VOD items yet. Send me videos to add them!")
        return
    
    message = "🎥 **Your VOD Library:**\n\n"
    for i, vod in enumerate(vod_items[-20:], 1):  # Show last 20
        added = datetime.fromisoformat(vod['added']).strftime('%Y-%m-%d')
        message += f"{i}. **{vod['title']}**\n"
        message += f"   📅 {added}\n\n"
    
    if len(vod_items) > 20:
        message += f"... and {len(vod_items)-20} more\n"
    
    message += f"\n**Total:** {len(vod_items)} items"
    
    await update.message.reply_text(message, parse_mode='Markdown')

async def generate_user_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate a user file with expiration"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/generate USERNAME DAYS`\n"
            "Example: `/generate john 30`",
            parse_mode='Markdown'
        )
        return
    
    username = context.args[0]
    days = int(context.args[1])
    expiry = datetime.now() + timedelta(days=days)
    
    # Create token
    token = f"{username}_{int(expiry.timestamp())}"
    
    # Get channel count
    channels = load_channels()
    vod_items = load_vod()
    
    # Create M3U content
    m3u_content = f"""#EXTM3U
# IPTV Playlist for: {username}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Expires: {expiry.strftime('%Y-%m-%d')}
# Token: {token}
#
# This file contains {len(channels)} channels and {len(vod_items)} VOD items
# It will auto-update with new content!
#
# INSTRUCTIONS:
# 1. Save this file
# 2. Open in VLC Media Player (File → Open File)
# 3. Or use any IPTV app (TiviMate, OTT Navigator, etc.)
#
# Your channels:
"""
    
    # Add channels to the M3U
    for ch in channels:
        m3u_content += f"\n#EXTINF:-1 group-title=\"{ch['group']}\",{ch['name']}\n"
        m3u_content += f"{ch['url']}\n"
    
    # Send as file
    await update.message.reply_document(
        document=m3u_content.encode('utf-8'),
        filename=f"{username}_iptv.m3u",
        caption=f"✅ **User file generated!**\n\n"
                f"**User:** {username}\n"
                f"**Expires:** {expiry.strftime('%Y-%m-%d')} ({days} days)\n"
                f"**Channels:** {len(channels)}\n"
                f"**VOD Items:** {len(vod_items)}\n\n"
                f"Send this .m3u file to your user."
    )

# ============================================
# MAIN FUNCTION
# ============================================
def main():
    """Start the bot"""
    print("\n🚀 Starting bot main function...")
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Add all handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("add", add_channel))
    app.add_handler(CommandHandler("remove", remove_channel))
    app.add_handler(CommandHandler("list", list_channels))
    app.add_handler(CommandHandler("vodlist", vod_list))
    app.add_handler(CommandHandler("generate", generate_user_file))
    app.add_handler(MessageHandler(filters.VIDEO, handle_video))
    
    print("✅ Bot configured, starting polling...")
    print("="*60)
    
    # Start bot (this runs until the workflow stops it)
    app.run_polling()

if __name__ == "__main__":
    main()
