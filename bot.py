#!/usr/bin/env python3
"""
IPTV Telegram Bot - EXTREME DEBUG VERSION
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta

# ===== READ ENVIRONMENT VARIABLES =====
print("="*60)
print("IPTV BOT STARTING - EXTREME DEBUG MODE")
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

print(f"✅ Bot token: {BOT_TOKEN[:10]}...")
print(f"✅ Admin IDs: {ADMIN_IDS}")

# ===== IMPORTS =====
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ===== EXTREME DEBUG DATA FUNCTIONS =====
CHANNELS_FILE = "channels.json"
VOD_FILE = "vod.json"

def debug_file_status():
    """Print detailed file status"""
    import os
    print("\n📁 FILE STATUS:")
    print(f"Current directory: {os.getcwd()}")
    
    # Check channels.json
    if os.path.exists(CHANNELS_FILE):
        size = os.path.getsize(CHANNELS_FILE)
        print(f"✅ channels.json exists - Size: {size} bytes")
        try:
            with open(CHANNELS_FILE, 'r') as f:
                content = f.read()
                print(f"Content: {content[:200]}")  # First 200 chars
                data = json.loads(content)
                print(f"Parsed: {len(data)} channels")
        except Exception as e:
            print(f"❌ Error reading channels.json: {e}")
    else:
        print(f"❌ channels.json DOES NOT EXIST")
    
    # Check vod.json
    if os.path.exists(VOD_FILE):
        size = os.path.getsize(VOD_FILE)
        print(f"✅ vod.json exists - Size: {size} bytes")
    else:
        print(f"❌ vod.json DOES NOT EXIST")
    print("-"*40)

def load_channels():
    """Load channels with extreme debugging"""
    print("\n📤 LOADING CHANNELS...")
    debug_file_status()
    
    try:
        if os.path.exists(CHANNELS_FILE):
            with open(CHANNELS_FILE, 'r') as f:
                data = json.load(f)
                print(f"✅ Loaded {len(data)} channels from file")
                return data
        else:
            print("ℹ️ No channels file yet, creating empty list")
            return []
    except Exception as e:
        print(f"❌ Error loading channels: {e}")
        return []

def save_channels(channels):
    """Save channels with extreme debugging"""
    print("\n📥 SAVING CHANNELS...")
    print(f"Channels to save: {len(channels)}")
    
    try:
        # Write to file
        with open(CHANNELS_FILE, 'w') as f:
            json.dump(channels, f, indent=2)
        print(f"✅ Wrote to {CHANNELS_FILE}")
        
        # Verify immediately after write
        debug_file_status()
        
        return True
    except Exception as e:
        print(f"❌ Error saving channels: {e}")
        return False

def load_vod():
    """Load VOD items"""
    try:
        if os.path.exists(VOD_FILE):
            with open(VOD_FILE, 'r') as f:
                return json.load(f)
        return []
    except:
        return []

def save_vod(vod_items):
    """Save VOD items"""
    try:
        with open(VOD_FILE, 'w') as f:
            json.dump(vod_items, f, indent=2)
        return True
    except:
        return False

# ===== TELEGRAM HANDLERS =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎬 IPTV Bot - Debug Mode\n\n"
        "Commands:\n"
        "/add NAME URL - Add channel\n"
        "/list - List channels\n"
        "/debug - Show file status"
    )

async def debug(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Debug command to check files"""
    import os
    
    msg = "🔍 **DEBUG INFO**\n\n"
    
    # Check channels.json
    if os.path.exists("channels.json"):
        with open("channels.json", 'r') as f:
            data = json.load(f)
        msg += f"✅ channels.json: {len(data)} channels\n"
    else:
        msg += "❌ channels.json: NOT FOUND\n"
    
    # Check current directory
    msg += f"\n📁 Directory: {os.getcwd()}\n"
    msg += f"📄 Files: {', '.join(os.listdir('.')[:5])}"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Usage: /add NAME URL")
        return
    
    name = context.args[0]
    url = context.args[1]
    
    # Load current channels
    channels = load_channels()
    print(f"Current channels before add: {len(channels)}")
    
    # Add new channel
    channels.append({
        "name": name,
        "url": url,
        "group": "General",
        "added": datetime.now().isoformat()
    })
    
    # Save
    if save_channels(channels):
        await update.message.reply_text(f"✅ Added: {name}")
        # Force another load to verify
        verify = load_channels()
        await update.message.reply_text(f"✅ Verification: {len(verify)} channels in file")
    else:
        await update.message.reply_text("❌ Save failed!")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    channels = load_channels()
    
    if not channels:
        await update.message.reply_text("📭 No channels yet.")
        return
    
    msg = "📺 Your Channels:\n"
    for ch in channels:
        msg += f"\n• {ch['name']} ({ch.get('group', 'General')})"
    msg += f"\n\nTotal: {len(channels)} channels"
    
    await update.message.reply_text(msg)

# ===== MAIN =====
def main():
    print("\n" + "="*60)
    print("STARTING BOT - INITIAL FILE CHECK")
    print("="*60)
    debug_file_status()
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("debug", debug))
    app.add_handler(CommandHandler("add", add_channel))
    app.add_handler(CommandHandler("list", list_channels))
    
    print("\n✅ Bot configured, starting polling...")
    print("="*60)
    
    app.run_polling()

if __name__ == "__main__":
    main()
