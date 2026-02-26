#!/usr/bin/env python3
"""
IPTV Telegram Bot - CSV MASTER SYSTEM
Reads channels from CSV, generates customer playlists
"""

import os
import sys
import json
import csv
import secrets
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# ===== READ ENVIRONMENT VARIABLES =====
print("="*60)
print("IPTV BOT - CSV MASTER SYSTEM")
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

# ===== CSV MASTER FILE =====
MASTER_CSV = "channels.csv"
CUSTOMERS_FILE = "customers.json"

# ===== CSV MANAGEMENT =====

def load_channels_from_csv() -> List[Dict]:
    """Load all channels from master CSV"""
    channels = []
    try:
        if os.path.exists(MASTER_CSV):
            with open(MASTER_CSV, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    channels.append({
                        'name': row.get('name', '').strip(),
                        'url': row.get('url', '').strip(),
                        'group': row.get('group', 'General').strip(),
                        'country': row.get('country', ''),
                        'language': row.get('language', ''),
                        'quality': row.get('quality', 'HD'),
                        'category': row.get('category', ''),
                        'tags': row.get('tags', '')
                    })
            print(f"📺 Loaded {len(channels)} channels from CSV")
        else:
            print(f"⚠️ Master CSV not found: {MASTER_CSV}")
            # Create empty CSV with headers
            with open(MASTER_CSV, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow(['name', 'url', 'group', 'country', 'language', 'quality', 'category', 'tags'])
    except Exception as e:
        print(f"❌ Error loading CSV: {e}")
    return channels

def add_channel_to_csv(name: str, url: str, group: str = "General", **kwargs) -> bool:
    """Add a new channel to the master CSV"""
    try:
        channels = load_channels_from_csv()
        
        # Check if exists
        for ch in channels:
            if ch['name'].lower() == name.lower():
                return False
        
        # Add new channel
        with open(MASTER_CSV, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow([
                name,
                url,
                group,
                kwargs.get('country', ''),
                kwargs.get('language', ''),
                kwargs.get('quality', 'HD'),
                kwargs.get('category', ''),
                kwargs.get('tags', '')
            ])
        return True
    except Exception as e:
        print(f"❌ Error adding to CSV: {e}")
        return False

def remove_channel_from_csv(name: str) -> bool:
    """Remove a channel from master CSV"""
    try:
        channels = load_channels_from_csv()
        new_channels = [ch for ch in channels if ch['name'].lower() != name.lower()]
        
        if len(new_channels) == len(channels):
            return False
        
        # Rewrite CSV
        with open(MASTER_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['name', 'url', 'group', 'country', 'language', 'quality', 'category', 'tags'])
            for ch in new_channels:
                writer.writerow([
                    ch['name'],
                    ch['url'],
                    ch['group'],
                    ch.get('country', ''),
                    ch.get('language', ''),
                    ch.get('quality', 'HD'),
                    ch.get('category', ''),
                    ch.get('tags', '')
                ])
        return True
    except Exception as e:
        print(f"❌ Error removing from CSV: {e}")
        return False

def filter_channels(criteria: Dict) -> List[Dict]:
    """Filter channels based on criteria (for customer playlists)"""
    channels = load_channels_from_csv()
    filtered = channels
    
    # Filter by group
    if 'group' in criteria and criteria['group']:
        filtered = [ch for ch in filtered if ch['group'] == criteria['group']]
    
    # Filter by country
    if 'country' in criteria and criteria['country']:
        filtered = [ch for ch in filtered if ch['country'] == criteria['country']]
    
    # Filter by language
    if 'language' in criteria and criteria['language']:
        filtered = [ch for ch in filtered if ch['language'] == criteria['language']]
    
    # Filter by quality
    if 'quality' in criteria and criteria['quality']:
        filtered = [ch for ch in filtered if ch['quality'] == criteria['quality']]
    
    # Filter by category
    if 'category' in criteria and criteria['category']:
        filtered = [ch for ch in filtered if ch['category'] == criteria['category']]
    
    # Filter by tags (simple contains)
    if 'tags' in criteria and criteria['tags']:
        tags = criteria['tags'].lower()
        filtered = [ch for ch in filtered if tags in ch.get('tags', '').lower()]
    
    return filtered

def get_unique_values(column: str) -> List[str]:
    """Get all unique values from a CSV column"""
    channels = load_channels_from_csv()
    values = set()
    for ch in channels:
        if column in ch and ch[column]:
            values.add(ch[column])
    return sorted(list(values))

# ===== CUSTOMER MANAGEMENT =====

def load_customers() -> Dict:
    """Load customer data"""
    try:
        if os.path.exists(CUSTOMERS_FILE):
            with open(CUSTOMERS_FILE, 'r') as f:
                return json.load(f)
    except:
        pass
    return {}

def save_customers(customers: Dict) -> bool:
    """Save customer data"""
    try:
        with open(CUSTOMERS_FILE, 'w') as f:
            json.dump(customers, f, indent=2)
        return True
    except:
        return False

def create_customer(username: str, days: int, filters: Dict = None) -> Dict:
    """Create a new customer with filters"""
    customers = load_customers()
    
    # Generate unique token
    token = secrets.token_urlsafe(16)
    expires = datetime.now() + timedelta(days=days)
    
    customer = {
        'username': username,
        'created': datetime.now().isoformat(),
        'expires': expires.timestamp(),
        'expires_date': expires.isoformat(),
        'filters': filters or {},
        'active': True,
        'playlist_count': 0
    }
    
    customers[token] = customer
    save_customers(customers)
    
    return {
        'token': token,
        'customer': customer,
        'expires': expires
    }

# ===== TELEGRAM HANDLERS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Welcome message"""
    channels = load_channels_from_csv()
    groups = get_unique_values('group')
    
    await update.message.reply_text(
        f"🎬 **IPTV Bot - CSV Master System**\n\n"
        f"📺 **Total Channels:** {len(channels)}\n"
        f"📊 **Categories:** {', '.join(groups[:5])}...\n\n"
        f"**Admin Commands:**\n"
        f"/add NAME URL [GROUP] - Add channel to CSV\n"
        f"/remove NAME - Remove channel from CSV\n"
        f"/list - List all channels\n"
        f"/groups - Show all groups\n"
        f"/export - Download master CSV\n\n"
        f"**Customer Commands:**\n"
        f"/create USERNAME DAYS [filters] - Create customer\n"
        f"/customers - List all customers\n"
        f"/revoke TOKEN - Revoke customer access",
        parse_mode='Markdown'
    )

async def add_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add channel to master CSV"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: /add NAME URL [GROUP]\n"
            "Example: /add BBC http://example.com/bbc.m3u8 News"
        )
        return
    
    name = context.args[0]
    url = context.args[1]
    group = context.args[2] if len(context.args) > 2 else "General"
    
    if add_channel_to_csv(name, url, group):
        await update.message.reply_text(f"✅ Added to CSV: {name}")
    else:
        await update.message.reply_text(f"❌ Channel '{name}' already exists")

async def list_channels(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List channels from CSV"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    channels = load_channels_from_csv()
    
    if not channels:
        await update.message.reply_text("📭 No channels in CSV")
        return
    
    # Group by category
    groups = {}
    for ch in channels:
        group = ch['group']
        if group not in groups:
            groups[group] = []
        groups[group].append(ch)
    
    msg = "📺 **Master Channel List:**\n\n"
    for group, ch_list in list(groups.items())[:5]:  # Show first 5 groups
        msg += f"**{group}** ({len(ch_list)} channels)\n"
        for ch in ch_list[:3]:  # Show first 3 of each group
            msg += f"  • {ch['name']}\n"
        if len(ch_list) > 3:
            msg += f"  ... and {len(ch_list)-3} more\n"
        msg += "\n"
    
    msg += f"\n**Total:** {len(channels)} channels"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def remove_channel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove channel from CSV"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /remove NAME")
        return
    
    name = context.args[0]
    
    if remove_channel_from_csv(name):
        await update.message.reply_text(f"✅ Removed from CSV: {name}")
    else:
        await update.message.reply_text(f"❌ Channel '{name}' not found")

async def show_groups(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all available groups/categories"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    groups = get_unique_values('group')
    countries = get_unique_values('country')
    languages = get_unique_values('language')
    qualities = get_unique_values('quality')
    
    msg = "📊 **Available Filters:**\n\n"
    msg += f"**Groups:** {', '.join(groups[:10])}\n"
    if len(groups) > 10:
        msg += f"... and {len(groups)-10} more\n\n"
    
    msg += f"**Countries:** {', '.join(countries[:10])}\n\n"
    msg += f"**Languages:** {', '.join(languages[:10])}\n\n"
    msg += f"**Qualities:** {', '.join(qualities)}"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def export_csv(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Download master CSV file"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if os.path.exists(MASTER_CSV):
        with open(MASTER_CSV, 'rb') as f:
            await update.message.reply_document(
                document=f,
                filename=f"master_channels_{datetime.now().strftime('%Y%m%d')}.csv",
                caption=f"✅ Master channel list exported\n"
                        f"📺 Total channels: {len(load_channels_from_csv())}"
            )
    else:
        await update.message.reply_text("❌ Master CSV not found")

async def create_customer_playlist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Create a customer with filtered playlist"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if len(context.args) < 3:
        await update.message.reply_text(
            "Usage: /create USERNAME DAYS filter=value ...\n\n"
            "Examples:\n"
            "/create john 30 group=News\n"
            "/create mary 15 country=UK language=English\n"
            "/create sportsfan 7 group=Sports quality=FHD\n\n"
            "Available filters: group, country, language, quality, category"
        )
        return
    
    username = context.args[0]
    days = int(context.args[1])
    
    # Parse filters
    filters = {}
    for arg in context.args[2:]:
        if '=' in arg:
            key, value = arg.split('=', 1)
            filters[key] = value
    
    # Create customer
    result = create_customer(username, days, filters)
    
    # Get filtered channels for preview
    filtered_channels = filter_channels(filters)
    
    # Generate M3U content
    m3u = f"""#EXTM3U
# IPTV Playlist for: {username}
# Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# Expires: {result['expires'].strftime('%Y-%m-%d')}
# Token: {result['token']}
# Filters: {filters if filters else 'All channels'}
#
# This playlist contains {len(filtered_channels)} channels
#
"""
    
    for ch in filtered_channels:
        m3u += f'#EXTINF:-1 tvg-logo="" group-title="{ch["group"]}",{ch["name"]}\n'
        m3u += f"{ch['url']}\n"
    
    # Send M3U file
    await update.message.reply_document(
        document=m3u.encode('utf-8'),
        filename=f"{username}_iptv.m3u",
        caption=f"✅ **Customer Created**\n\n"
                f"👤 **User:** {username}\n"
                f"⏰ **Expires:** {result['expires'].strftime('%Y-%m-%d')}\n"
                f"📺 **Channels:** {len(filtered_channels)}\n"
                f"🔑 **Token:** {result['token'][:8]}...\n\n"
                f"**Filters:** {filters if filters else 'All channels'}"
    )
    
    # Also send token info
    await update.message.reply_text(
        f"📝 **Customer Token:**\n"
        f"```\n{result['token']}\n```\n"
        f"Save this to manage this customer."
    )

async def list_customers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all active customers"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    customers = load_customers()
    now = datetime.now().timestamp()
    
    if not customers:
        await update.message.reply_text("📭 No customers yet")
        return
    
    msg = "👥 **Active Customers:**\n\n"
    active = 0
    expired = 0
    
    for token, data in list(customers.items())[:10]:
        expires = datetime.fromtimestamp(data['expires'])
        days_left = (expires - datetime.now()).days
        status = "✅" if days_left > 0 else "❌"
        
        if days_left > 0:
            active += 1
        else:
            expired += 1
        
        msg += f"{status} **{data['username']}**\n"
        msg += f"   Expires: {expires.strftime('%Y-%m-%d')} ({days_left} days)\n"
        msg += f"   Filters: {data.get('filters', {})}\n"
        msg += f"   Token: `{token[:8]}...`\n\n"
    
    if len(customers) > 10:
        msg += f"... and {len(customers)-10} more\n\n"
    
    msg += f"**Summary:** {active} active, {expired} expired"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def revoke_customer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Revoke a customer's access"""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /revoke TOKEN")
        return
    
    token = context.args[0]
    customers = load_customers()
    
    if token in customers:
        username = customers[token]['username']
        del customers[token]
        save_customers(customers)
        await update.message.reply_text(f"✅ Revoked access for {username}")
    else:
        await update.message.reply_text("❌ Token not found")

# ===== MAIN FUNCTION =====

def main():
    print("\n🚀 Starting CSV Master Bot...")
    
    # Load CSV on startup
    channels = load_channels_from_csv()
    print(f"✅ CSV loaded: {len(channels)} channels")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Admin commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add", add_channel))
    app.add_handler(CommandHandler("list", list_channels))
    app.add_handler(CommandHandler("remove", remove_channel))
    app.add_handler(CommandHandler("groups", show_groups))
    app.add_handler(CommandHandler("export", export_csv))
    
    # Customer commands
    app.add_handler(CommandHandler("create", create_customer_playlist))
    app.add_handler(CommandHandler("customers", list_customers))
    app.add_handler(CommandHandler("revoke", revoke_customer))
    
    print("✅ Bot is running with CSV master system!")
    print("="*60)
    
    app.run_polling()

if __name__ == "__main__":
    main()
