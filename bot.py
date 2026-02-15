import asyncio
import random
import sqlite3
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
    MessageHandler, ContextTypes, filters, ConversationHandler
)
from telegram.constants import ParseMode

TOKEN = "8236403757:AAFt7OA7aQYvgJzrS70jZmOazC47joW0YUQ"

# ==================== YOUR PAYMENT BOT ====================
PAYMENT_BOT_USERNAME = "Paymentboy_bot"
PAYMENT_BOT_LINK = f"https://t.me/{PAYMENT_BOT_USERNAME}"

# ==================== ADMIN SETTINGS ====================
ADMIN_IDS = [5943318266]  # Your Telegram ID
PENDING_TOPUPS = {}  # Store pending balance top-ups

# ==================== GROUP SETTINGS ====================
active_games = {}  # Format: {(chat_id, user_id): game_data}
user_sessions = {}  # Store user data per chat

# ==================== DATABASE SETUP ====================
conn = sqlite3.connect('casino.db', check_same_thread=False)
c = conn.cursor()

# Create tables with all required columns
c.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY, 
              username TEXT,
              balance INTEGER DEFAULT 100,
              total_won INTEGER DEFAULT 0,
              total_lost INTEGER DEFAULT 0,
              games_played INTEGER DEFAULT 0,
              joined_date TEXT DEFAULT CURRENT_DATE)''')

c.execute('''CREATE TABLE IF NOT EXISTS transactions
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              user_id INTEGER,
              amount INTEGER,
              type TEXT,
              admin_id INTEGER,
              timestamp TEXT DEFAULT CURRENT_TIMESTAMP)''')
conn.commit()

print("✅ Database setup complete with all columns")

# ==================== DATABASE FUNCTIONS ====================
def get_balance(user_id):
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    return result[0] if result else 100

def update_balance(user_id, amount):
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def create_user(user_id, username=None):
    c.execute("INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?, 100)",
             (user_id, username))
    conn.commit()

def add_transaction(user_id, amount, type, admin_id=None):
    c.execute("INSERT INTO transactions (user_id, amount, type, admin_id) VALUES (?, ?, ?, ?)",
             (user_id, amount, type, admin_id))
    conn.commit()

def get_user_stats(user_id):
    c.execute("SELECT balance, total_won, total_lost, games_played FROM users WHERE user_id = ?", (user_id,))
    return c.fetchone()

def get_all_users():
    c.execute("SELECT user_id, username, balance FROM users ORDER BY balance DESC LIMIT 20")
    return c.fetchall()

# ==================== BET AMOUNTS ====================
BET_OPTIONS = [10, 20, 50, 100, 200, 500, 1000, 2000, 5000, 10000]
DEFAULT_BET = 10

# ==================== START COMMAND ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    chat_id = update.effective_chat.id
    chat_type = update.effective_chat.type
    
    create_user(user_id, username)
    balance = get_balance(user_id)
    
    # Check if user is admin
    is_admin = user_id in ADMIN_IDS
    
    if chat_type in ["group", "supergroup"]:
        welcome_text = (
            f"🎰 **CASINO BOT JOINED GROUP!** 🎰\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 Your Balance: **{balance:,}₹**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**Commands:**\n"
            f"/start - all games u see\n"
                    )
        if is_admin:
            welcome_text += f"/admin - Admin panel (admins only)\n"
    else:
        welcome_text = (
            f"🎰 **WELCOME TO CASINO** 🎰\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Your Balance: **{balance:,}₹**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Select a game below:"
        )
    
    # Create keyboard as a list of lists
    keyboard = [
        [
            InlineKeyboardButton("🎲 DICE", callback_data="select_dice"),
            InlineKeyboardButton("🎯 DART", callback_data="select_dart")
        ],
        [
            InlineKeyboardButton("🎳 BOWLING", callback_data="select_bowling"),
            InlineKeyboardButton("⚽ FOOTBALL", callback_data="select_football")
        ],
        [
            InlineKeyboardButton("🎰 SLOT", callback_data="select_slot"),
            InlineKeyboardButton("🃏 CARDS", callback_data="select_cards")
        ],
        [
            InlineKeyboardButton("🎡 ROULETTE", callback_data="select_roulette"),
            InlineKeyboardButton("📈 CRASH", callback_data="select_crash")
        ],
        [
            InlineKeyboardButton("💰 ADD COINS", url=PAYMENT_BOT_LINK),
            InlineKeyboardButton("📊 STATS", callback_data="show_stats")
        ],
        [
            InlineKeyboardButton("📜 RULES", callback_data="show_rules"),
            InlineKeyboardButton("🔄 BALANCE", callback_data="show_balance")
        ]
    ]
    
    # Add admin button if user is admin
    if is_admin:
        keyboard.append([InlineKeyboardButton("👑 ADMIN PANEL", callback_data="admin_panel")])
    
    await update.message.reply_text(welcome_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

# ==================== MENU COMMAND ====================
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = get_balance(user_id)
    
    text = (
        f"🎰 **CASINO MENU** 🎰\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Your Balance: **{balance:,}₹**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"Select a game:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🎲 DICE", callback_data="select_dice"),
            InlineKeyboardButton("🎯 DART", callback_data="select_dart")
        ],
        [
            InlineKeyboardButton("🎳 BOWLING", callback_data="select_bowling"),
            InlineKeyboardButton("⚽ FOOTBALL", callback_data="select_football")
        ],
        [
            InlineKeyboardButton("🎰 SLOT", callback_data="select_slot"),
            InlineKeyboardButton("🃏 CARDS", callback_data="select_cards")
        ],
        [
            InlineKeyboardButton("🎡 ROULETTE", callback_data="select_roulette"),
            InlineKeyboardButton("📈 CRASH", callback_data="select_crash")
        ]
    ])
    
    await update.message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

# ==================== BALANCE COMMAND ====================
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = get_balance(user_id)
    
    await update.message.reply_text(
        f"💰 **Your Balance:** {balance:,}₹\n\n"
        f"Need more? @{PAYMENT_BOT_USERNAME}",
        parse_mode=ParseMode.MARKDOWN
    )

# ==================== STATS COMMAND ====================
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name
    stats = get_user_stats(user_id)
    
    if stats:
        balance, won, lost, games = stats
        win_rate = (won / (won + lost) * 100) if (won + lost) > 0 else 0
        
        text = (
            f"📊 **{username}'s STATISTICS**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Balance: {balance:,}₹\n"
            f"🎮 Games Played: {games}\n"
            f"✅ Total Won: {won:,}₹\n"
            f"❌ Total Lost: {lost:,}₹\n"
            f"📈 Win Rate: {win_rate:.1f}%\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━"
        )
    else:
        text = "📊 No stats available yet!"
    
    await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)

# ==================== RULES COMMAND ====================
async def rules(update: Update, context: ContextTypes.DEFAULT_TYPE):
    rules_text = (
        "📜 **COMPLETE GAME RULES** 📜\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "🎲 **DICE GAME**\n"
        "• ODD (1,3,5) - Win 2x bet\n"
        "• EVEN (2,4,6) - Win 2x bet\n"
        "• SMALL (1,2,3) - Win 2x bet\n"
        "• BIG (4,5,6) - Win 2x bet\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "🎯 **DART GAME**\n"
        "• You vs Bot\n"
        "• Higher score wins\n"
        "• Win = 2x bet\n"
        "• Draw = Get bet back\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "🎳 **BOWLING GAME**\n"
        "• You vs Bot\n"
        "• Higher score wins\n"
        "• Win = 2x bet\n"
        "• Draw = Get bet back\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "⚽ **FOOTBALL GAME**\n"
        "• You vs Bot\n"
        "• Higher score wins\n"
        "• Win = 2x bet\n"
        "• Draw = Get bet back\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "🎰 **SLOT MACHINE**\n"
        "• 7️⃣ 7️⃣ 7️⃣ = 10x JACKPOT!\n"
        "• 💎 💎 💎 = 7x DIAMOND!\n"
        "• 🎰 🎰 🎰 = 5x TRIPLE!\n"
        "• 🍒🍒🍒/🍋🍋🍋/🍊🍊🍊 = 3x\n"
        "• Any 2 matching = 2x\n"
        "• No match = 0x\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "🃏 **CARDS GAME**\n"
        "• First card is shown\n"
        "• Predict HIGHER or LOWER\n"
        "• Correct = 2x bet\n"
        "• Same card = Tie (bet back)\n"
        "• Wrong = Lose bet\n"
        "• Card values: 2<3<4<5<6<7<8<9<10<J<Q<K<A\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "🎡 **ROULETTE**\n"
        "• RED (18 numbers) = 2x\n"
        "• BLACK (18 numbers) = 2x\n"
        "• GREEN (0) = 36x JACKPOT!\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "📈 **CRASH GAME**\n"
        "• Multiplier starts at 1.0x\n"
        "• Type 'CASH' anytime to collect\n"
        "• If it crashes before cash out = Lose\n"
        "• Win = Bet × Multiplier\n"
        "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        "💰 **HOW TO ADD COINS**\n"
        f"• Use @{PAYMENT_BOT_USERNAME}\n"
        "• Deposit via UPI/Bank/Crypto\n"
        "• Coins added automatically\n"
        "━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    await update.message.reply_text(rules_text, parse_mode=ParseMode.MARKDOWN)

# ==================== ADMIN PANEL ====================
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Access Denied! You are not an admin.")
        return
    
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        message = query.message
        edit = True
    else:
        message = update.message
        edit = False
    
    text = (
        f"👑 **ADMIN CONTROL PANEL** 👑\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Welcome Admin!\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"**Quick Actions:**\n"
        f"• Add balance to users\n"
        f"• View all users\n"
        f"• Check pending top-ups\n"
        f"• Connect with @{PAYMENT_BOT_USERNAME}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💰 ADD BALANCE", callback_data="admin_add_balance")],
        [InlineKeyboardButton("📋 VIEW ALL USERS", callback_data="admin_view_users")],
        [InlineKeyboardButton("⏳ PENDING TOP-UPS", callback_data="admin_pending")],
        [InlineKeyboardButton("📊 STATISTICS", callback_data="admin_stats")],
        [InlineKeyboardButton("🔙 BACK TO MENU", callback_data="back_to_games")]
    ])
    
    if edit:
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    else:
        await message.reply_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

# ==================== ADMIN ADD BALANCE ====================
async def admin_add_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ Access Denied!")
        return
    
    text = (
        f"💰 **ADD BALANCE**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        f"To add balance to a user, use:\n"
        f"`/addbalance USER_ID AMOUNT`\n\n"
        f"Example: `/addbalance 123456789 500`\n\n"
        f"Or click the button below to view all users and their IDs"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 VIEW ALL USERS", callback_data="admin_view_users")],
        [InlineKeyboardButton("🔙 BACK TO ADMIN", callback_data="admin_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

# ==================== ADMIN VIEW USERS ====================
async def admin_view_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ Access Denied!")
        return
    
    users = get_all_users()
    
    text = "📋 **TOP 20 USERS BY BALANCE**\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
    for i, (uid, uname, bal) in enumerate(users, 1):
        name = uname if uname else f"User{uid}"
        text += f"{i}. `{uid}` | {name} | {bal}₹\n"
    
    text += "\n━━━━━━━━━━━━━━━━━━━━━━━\nUse `/addbalance USER_ID AMOUNT` to add coins"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 BACK TO ADMIN", callback_data="admin_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

# ==================== ADMIN STATS ====================
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ Access Denied!")
        return
    
    c.execute("SELECT COUNT(*) FROM users")
    total_users = c.fetchone()[0]
    
    c.execute("SELECT SUM(balance) FROM users")
    total_balance = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(total_won) FROM users")
    total_won = c.fetchone()[0] or 0
    
    c.execute("SELECT SUM(total_lost) FROM users")
    total_lost = c.fetchone()[0] or 0
    
    c.execute("SELECT COUNT(*) FROM transactions WHERE type='deposit'")
    total_deposits = c.fetchone()[0]
    
    text = (
        f"📊 **BOT STATISTICS**\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Total Users: {total_users}\n"
        f"💰 Total Balance: {total_balance:,}₹\n"
        f"✅ Total Won: {total_won:,}₹\n"
        f"❌ Total Lost: {total_lost:,}₹\n"
        f"📈 House Edge: {((total_lost - total_won)/max(total_lost,1)*100):.1f}%\n"
        f"💳 Total Deposits: {total_deposits}\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🤖 Payment Bot: @{PAYMENT_BOT_USERNAME}"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 BACK TO ADMIN", callback_data="admin_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

# ==================== ADMIN PENDING ====================
async def admin_pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ Access Denied!")
        return
    
    if not PENDING_TOPUPS:
        text = "📭 No pending top-ups at the moment."
    else:
        text = "⏳ **PENDING TOP-UPS**\n━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        for txn_id, data in list(PENDING_TOPUPS.items())[:10]:
            text += f"📌 `{txn_id}` | User: {data['user_id']} | Amount: {data['amount']}₹\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 BACK TO ADMIN", callback_data="admin_panel")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

# ==================== ADD BALANCE COMMAND ====================
async def addbalance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ Access Denied!")
        return
    
    try:
        args = context.args
        if len(args) != 2:
            await update.message.reply_text(
                "❌ Usage: `/addbalance USER_ID AMOUNT`\n"
                "Example: `/addbalance 123456789 500`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        target_id = int(args[0])
        amount = int(args[1])
        
        if amount <= 0:
            await update.message.reply_text("❌ Amount must be positive!")
            return
        
        # Get user info
        c.execute("SELECT username FROM users WHERE user_id = ?", (target_id,))
        user = c.fetchone()
        
        if not user:
            # Create user if doesn't exist
            create_user(target_id, f"User{target_id}")
            username = f"User{target_id}"
        else:
            username = user[0] or f"User{target_id}"
        
        # Add balance
        update_balance(target_id, amount)
        add_transaction(target_id, amount, "admin_add", user_id)
        
        # Try to notify user
        try:
            await context.bot.send_message(
                target_id,
                f"✅ **Balance Updated!**\n"
                f"Admin added **{amount}₹** to your account.\n"
                f"New Balance: **{get_balance(target_id)}₹**",
                parse_mode=ParseMode.MARKDOWN
            )
        except:
            pass
        
        await update.message.reply_text(
            f"✅ Added **{amount}₹** to user **{username}** (ID: `{target_id}`)\n"
            f"New Balance: **{get_balance(target_id)}₹**",
            parse_mode=ParseMode.MARKDOWN
        )
        
    except ValueError:
        await update.message.reply_text("❌ Invalid amount! Please enter a number.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {str(e)}")

# ==================== BUTTON CALLBACK HANDLER ====================
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    data = query.data
    
    if data == "show_balance":
        balance = get_balance(user_id)
        await query.edit_message_text(
            f"💰 **Your Balance:** {balance:,}₹\n\n"
            f"Need more? @{PAYMENT_BOT_USERNAME}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 BACK", callback_data="back_to_games")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "show_stats":
        stats_data = get_user_stats(user_id)
        username = query.from_user.username or query.from_user.first_name
        
        if stats_data:
            bal, won, lost, games = stats_data
            win_rate = (won / (won + lost) * 100) if (won + lost) > 0 else 0
            
            text = (
                f"📊 **{username}'s STATISTICS**\n"
                f"━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"💰 Balance: {bal:,}₹\n"
                f"🎮 Games: {games}\n"
                f"✅ Won: {won:,}₹\n"
                f"❌ Lost: {lost:,}₹\n"
                f"📈 Win Rate: {win_rate:.1f}%"
            )
        else:
            text = "📊 No stats available yet!"
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 BACK", callback_data="back_to_games")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "show_rules":
        rules_text = (
            "📜 **QUICK RULES** 📜\n"
            "━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🎲 **DICE** - Odd/Even/Small/Big = 2x\n"
            "🎯 **DART** - Beat Bot = 2x\n"
            "🎳 **BOWLING** - Beat Bot = 2x\n"
            "⚽ **FOOTBALL** - Beat Bot = 2x\n"
            "🎰 **SLOT** - 3 match = 3-10x, 2 match = 2x\n"
            "🃏 **CARDS** - Higher/Lower correct = 2x\n"
            "🎡 **ROULETTE** - Red/Black = 2x, Green = 36x\n"
            "📈 **CRASH** - Type 'CASH' to collect\n\n"
            "For complete rules, use /rules"
        )
        
        await query.edit_message_text(
            rules_text,
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 BACK", callback_data="back_to_games")
            ]]),
            parse_mode=ParseMode.MARKDOWN
        )
    
    elif data == "back_to_games":
        balance = get_balance(user_id)
        text = (
            f"🎰 **CASINO GAMES** 🎰\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n"
            f"💰 Your Balance: **{balance:,}₹**\n"
            f"━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"Select a game:"
        )
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎲 DICE", callback_data="select_dice"),
                InlineKeyboardButton("🎯 DART", callback_data="select_dart")
            ],
            [
                InlineKeyboardButton("🎳 BOWLING", callback_data="select_bowling"),
                InlineKeyboardButton("⚽ FOOTBALL", callback_data="select_football")
            ],
            [
                InlineKeyboardButton("🎰 SLOT", callback_data="select_slot"),
                InlineKeyboardButton("🃏 CARDS", callback_data="select_cards")
            ],
            [
                InlineKeyboardButton("🎡 ROULETTE", callback_data="select_roulette"),
                InlineKeyboardButton("📈 CRASH", callback_data="select_crash")
            ],
            [
                InlineKeyboardButton("💰 ADD COINS", url=PAYMENT_BOT_LINK),
                InlineKeyboardButton("📊 STATS", callback_data="show_stats")
            ]
        ])
        
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)
    
    elif data.startswith("select_"):
        game = data.replace("select_", "")
        text = f"**{game.upper()} GAME**\n━━━━━━━━━━━━━━━━━━━━━━━\n\nSelect your bet amount:"
        await show_bet_options(query, game, text)
    
    elif data.startswith("bet_"):
        await handle_bet_selection(query, context, user_id, chat_id, data)
    
    elif data.startswith("play_dice_"):
        await play_dice(query, context, user_id, chat_id, data)
    
    elif data.startswith("cards_"):
        await play_cards(query, context, user_id, chat_id, data)
    
    elif data.startswith("roulette_"):
        await play_roulette(query, context, user_id, chat_id, data)
    
    elif data == "crash_start":
        await crash_start(query, context, user_id, chat_id)
    
    # Admin panel callbacks
    elif data == "admin_panel":
        await admin_panel(update, context)
    elif data == "admin_add_balance":
        await admin_add_balance(update, context)
    elif data == "admin_view_users":
        await admin_view_users(update, context)
    elif data == "admin_stats":
        await admin_stats(update, context)
    elif data == "admin_pending":
        await admin_pending(update, context)

# ==================== BET OPTIONS ====================
async def show_bet_options(query, game, text):
    bet_buttons = []
    row = []
    for i, bet in enumerate(BET_OPTIONS):
        row.append(InlineKeyboardButton(f"{bet}₹", callback_data=f"bet_{game}_{bet}"))
        if (i + 1) % 3 == 0 or i == len(BET_OPTIONS) - 1:
            bet_buttons.append(row)
            row = []
    
    bet_buttons.append([
        InlineKeyboardButton("⚡ HALF", callback_data=f"bet_{game}_half"),
        InlineKeyboardButton("⚡ FULL", callback_data=f"bet_{game}_full")
    ])
    bet_buttons.append([
        InlineKeyboardButton("🔙 BACK", callback_data="back_to_games")
    ])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(bet_buttons))

# ==================== HANDLE BET SELECTION ====================
async def handle_bet_selection(query, context, user_id, chat_id, data):
    parts = data.split('_')
    game = parts[1]
    bet_value = parts[2]
    
    balance = get_balance(user_id)
    
    if bet_value == "half":
        bet_amount = balance // 2
        if bet_amount < 10:
            bet_amount = 10
    elif bet_value == "full":
        bet_amount = balance
    else:
        bet_amount = int(bet_value)
    
    if bet_amount > balance:
        await query.edit_message_text(
            f"❌ Insufficient Balance!\nYour balance: {balance}₹",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 BACK", callback_data=f"select_{game}")
            ]])
        )
        return
    
    # Store in context
    context.user_data[f"{chat_id}_{user_id}_bet"] = bet_amount
    context.user_data[f"{chat_id}_{user_id}_game"] = game
    
    if game == "slot":
        await play_slot(query, context, user_id, chat_id, bet_amount)
    elif game == "cards":
        await start_cards_game(query, context, user_id, chat_id, bet_amount)
    elif game == "roulette":
        await show_roulette_options(query, bet_amount)
    elif game == "crash":
        await start_crash_game(query, context, user_id, bet_amount)
    elif game == "dice":
        await show_dice_options(query, bet_amount)
    elif game in ["dart", "bowling", "football"]:
        await show_bot_game_instructions(query, game, bet_amount)

# ==================== DICE GAME ====================
async def show_dice_options(query, bet_amount):
    text = f"🎲 DICE\nBet: {bet_amount}₹ | Win: {bet_amount*2}₹\n\nChoose:"
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("ODD", callback_data=f"play_dice_odd_{bet_amount}"),
            InlineKeyboardButton("EVEN", callback_data=f"play_dice_even_{bet_amount}")
        ],
        [
            InlineKeyboardButton("1-3", callback_data=f"play_dice_small_{bet_amount}"),
            InlineKeyboardButton("4-6", callback_data=f"play_dice_big_{bet_amount}")
        ],
        [InlineKeyboardButton("🔙 CHANGE BET", callback_data="select_dice")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard)

async def play_dice(query, context, user_id, chat_id, data):
    parts = data.split('_')
    choice = parts[2]
    bet_amount = int(parts[3])
    
    balance = get_balance(user_id)
    if balance < bet_amount:
        await query.edit_message_text("❌ Insufficient Balance!")
        return
    
    update_balance(user_id, -bet_amount)
    
    await query.edit_message_text("🎲 Rolling dice...")
    
    dice_msg = await context.bot.send_dice(chat_id=chat_id, emoji="🎲")
    await asyncio.sleep(3)
    roll = dice_msg.dice.value
    
    win = False
    if choice == "odd" and roll in [1,3,5]: win = True
    elif choice == "even" and roll in [2,4,6]: win = True
    elif choice == "small" and roll in [1,2,3]: win = True
    elif choice == "big" and roll in [4,5,6]: win = True
    
    if win:
        winnings = bet_amount * 2
        update_balance(user_id, winnings)
        result_text = "✅ WIN"
    else:
        winnings = 0
        result_text = "❌ LOSE"
    
    new_balance = get_balance(user_id)
    
    result_msg = (
        f"{result_text}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Dice: {roll}\n"
        f"Choice: {choice.upper()}\n"
        f"Bet: {bet_amount}₹\n"
        f"{'Won: +' + str(winnings) + '₹' if win else 'Lost: -' + str(bet_amount) + '₹'}\n"
        f"Balance: {new_balance}₹"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎲 PLAY AGAIN", callback_data="select_dice"),
         InlineKeyboardButton("🏠 MENU", callback_data="back_to_games")]
    ])
    
    await context.bot.send_message(chat_id, result_msg, reply_markup=keyboard)

# ==================== BOT GAMES (DART, BOWLING, FOOTBALL) ====================
async def show_bot_game_instructions(query, game, bet_amount):
    game_names = {"dart": "🎯 DART", "bowling": "🎳 BOWLING", "football": "⚽ FOOTBALL"}
    text = f"{game_names[game]}\nBet: {bet_amount}₹ | Win: {bet_amount*2}₹\n\nType 'OK start' to begin!"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 CHANGE BET", callback_data=f"select_{game}")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard)

# ==================== SLOT GAME ====================
async def play_slot(query, context, user_id, chat_id, bet_amount):
    balance = get_balance(user_id)
    if balance < bet_amount:
        await query.edit_message_text("❌ Insufficient Balance!")
        return
    
    update_balance(user_id, -bet_amount)
    await query.edit_message_text("🎰 Spinning...")
    
    msg1 = await context.bot.send_dice(chat_id=chat_id, emoji="🎰")
    await asyncio.sleep(2)
    msg2 = await context.bot.send_dice(chat_id=chat_id, emoji="🎰")
    await asyncio.sleep(2)
    msg3 = await context.bot.send_dice(chat_id=chat_id, emoji="🎰")
    await asyncio.sleep(2)
    
    symbols = ["🍒", "🍋", "🍊", "7️⃣", "💎", "🎰"]
    s1 = symbols[msg1.dice.value % 6]
    s2 = symbols[msg2.dice.value % 6]
    s3 = symbols[msg3.dice.value % 6]
    
    if s1 == s2 == s3:
        multiplier = 10 if s1 == "7️⃣" else 7 if s1 == "💎" else 5 if s1 == "🎰" else 3
        win = True
    elif s1 == s2 or s2 == s3 or s1 == s3:
        multiplier = 2
        win = True
    else:
        multiplier = 0
        win = False
    
    winnings = bet_amount * multiplier if win else 0
    
    if win:
        update_balance(user_id, winnings)
    
    new_balance = get_balance(user_id)
    
    result_msg = (
        f"{'🎉 WIN' if win else '😢 LOSE'}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{s1} | {s2} | {s3}\n"
        f"Multiplier: {multiplier}x\n"
        f"Bet: {bet_amount}₹\n"
        f"{'Won: +' + str(winnings) + '₹' if win else 'Lost: -' + str(bet_amount) + '₹'}\n"
        f"Balance: {new_balance}₹"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎰 PLAY AGAIN", callback_data="select_slot"),
         InlineKeyboardButton("🏠 MENU", callback_data="back_to_games")]
    ])
    
    await context.bot.send_message(chat_id, result_msg, reply_markup=keyboard)

# ==================== CARDS GAME ====================
async def start_cards_game(query, context, user_id, chat_id, bet_amount):
    cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    first_card = random.choice(cards)
    
    context.user_data[f"{chat_id}_{user_id}_first_card"] = first_card
    
    text = f"🃏 CARDS\nBet: {bet_amount}₹\n\nFirst Card: {first_card}\nHigher or Lower?"
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🔴 HIGHER", callback_data=f"cards_higher_{bet_amount}"),
            InlineKeyboardButton("⚫ LOWER", callback_data=f"cards_lower_{bet_amount}")
        ],
        [InlineKeyboardButton("🔙 CHANGE BET", callback_data="select_cards")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard)

async def play_cards(query, context, user_id, chat_id, data):
    parts = data.split('_')
    choice = parts[1]
    bet_amount = int(parts[2])
    
    first_card = context.user_data.get(f"{chat_id}_{user_id}_first_card")
    if not first_card:
        await query.edit_message_text("❌ Game expired!")
        return
    
    balance = get_balance(user_id)
    if balance < bet_amount:
        await query.edit_message_text("❌ Insufficient Balance!")
        return
    
    update_balance(user_id, -bet_amount)
    
    cards = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
    values = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10, 'J':11, 'Q':12, 'K':13, 'A':14}
    
    second_card = random.choice(cards)
    first_val = values[first_card]
    second_val = values[second_card]
    
    if choice == "higher" and second_val > first_val:
        win = True
    elif choice == "lower" and second_val < first_val:
        win = True
    elif second_val == first_val:
        win = "tie"
    else:
        win = False
    
    if win == True:
        winnings = bet_amount * 2
        update_balance(user_id, winnings)
        result_text = "✅ WIN"
    elif win == "tie":
        winnings = bet_amount
        update_balance(user_id, bet_amount)
        result_text = "⚖️ TIE"
    else:
        winnings = 0
        result_text = "❌ LOSE"
    
    new_balance = get_balance(user_id)
    
    result_msg = (
        f"{result_text}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"First: {first_card} | Second: {second_card}\n"
        f"Bet: {bet_amount}₹\n"
        f"{'Won: +' + str(winnings) + '₹' if win == True else 'Tie: 0₹' if win == 'tie' else 'Lost: -' + str(bet_amount) + '₹'}\n"
        f"Balance: {new_balance}₹"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🃏 PLAY AGAIN", callback_data="select_cards"),
         InlineKeyboardButton("🏠 MENU", callback_data="back_to_games")]
    ])
    
    await query.edit_message_text(result_msg, reply_markup=keyboard)
    context.user_data.pop(f"{chat_id}_{user_id}_first_card", None)

# ==================== ROULETTE GAME ====================
async def show_roulette_options(query, bet_amount):
    text = f"🎡 ROULETTE\nBet: {bet_amount}₹\n\nChoose color:"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔴 RED (2x)", callback_data=f"roulette_red_{bet_amount}")],
        [InlineKeyboardButton("⚫ BLACK (2x)", callback_data=f"roulette_black_{bet_amount}")],
        [InlineKeyboardButton("🟢 GREEN (36x)", callback_data=f"roulette_green_{bet_amount}")],
        [InlineKeyboardButton("🔙 CHANGE BET", callback_data="select_roulette")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard)

async def play_roulette(query, context, user_id, chat_id, data):
    parts = data.split('_')
    color = parts[1]
    bet_amount = int(parts[2])
    
    balance = get_balance(user_id)
    if balance < bet_amount:
        await query.edit_message_text("❌ Insufficient Balance!")
        return
    
    update_balance(user_id, -bet_amount)
    await query.edit_message_text("🎡 Spinning...")
    
    await context.bot.send_dice(chat_id=chat_id, emoji="🎰")
    await asyncio.sleep(3)
    
    number = random.randint(0, 36)
    if number == 0:
        result_color = "green"
    elif number in [1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36]:
        result_color = "red"
    else:
        result_color = "black"
    
    if color == result_color:
        multiplier = 36 if color == "green" else 2
        winnings = bet_amount * multiplier
        update_balance(user_id, winnings)
        result_text = "✅ WIN"
    else:
        winnings = 0
        result_text = "❌ LOSE"
    
    new_balance = get_balance(user_id)
    
    result_msg = (
        f"{result_text}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Number: {number} ({result_color})\n"
        f"Bet: {bet_amount}₹\n"
        f"{'Won: +' + str(winnings) + '₹' if winnings > 0 else 'Lost: -' + str(bet_amount) + '₹'}\n"
        f"Balance: {new_balance}₹"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🎡 PLAY AGAIN", callback_data="select_roulette"),
         InlineKeyboardButton("🏠 MENU", callback_data="back_to_games")]
    ])
    
    await context.bot.send_message(chat_id, result_msg, reply_markup=keyboard)

# ==================== CRASH GAME ====================
async def start_crash_game(query, context, user_id, bet_amount):
    context.user_data[f"{query.message.chat_id}_{user_id}_crash"] = {
        'bet': bet_amount,
        'active': False
    }
    
    text = f"📈 CRASH\nBet: {bet_amount}₹\n\nClick START to begin!"
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🚀 START", callback_data="crash_start")],
        [InlineKeyboardButton("🔙 CHANGE BET", callback_data="select_crash")]
    ])
    await query.edit_message_text(text, reply_markup=keyboard)

async def crash_start(query, context, user_id, chat_id):
    crash_data = context.user_data.get(f"{chat_id}_{user_id}_crash", {})
    bet_amount = crash_data.get('bet', 10)
    
    balance = get_balance(user_id)
    if balance < bet_amount:
        await query.edit_message_text("❌ Insufficient Balance!")
        return
    
    update_balance(user_id, -bet_amount)
    await query.edit_message_text("📈 Crash starting...")
    
    dice_msg = await context.bot.send_dice(chat_id=chat_id, emoji="🎲")
    await asyncio.sleep(3)
    
    crash_point = round(1.5 + (dice_msg.dice.value * 0.5), 2)
    
    crash_data['active'] = True
    crash_data['crashed'] = False
    crash_data['crash_point'] = crash_point
    crash_data['multiplier'] = 1.0
    
    msg = await context.bot.send_message(
        chat_id,
        f"📈 CRASH\nMultiplier: 1.0x\n\nType 'CASH' to collect!"
    )
    crash_data['msg_id'] = msg.message_id
    
    for i in range(20):
        if not crash_data.get('active', False):
            break
        if crash_data['multiplier'] >= crash_point - 0.2:
            break
        
        await asyncio.sleep(0.5)
        crash_data['multiplier'] = round(crash_data['multiplier'] + 0.15, 2)
        
        await context.bot.edit_message_text(
            f"📈 CRASH\nMultiplier: {crash_data['multiplier']}x\n\nType 'CASH' to collect!",
            chat_id=chat_id,
            message_id=crash_data['msg_id']
        )

# ==================== TEXT HANDLER ====================
async def group_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text.lower()
    
    # Handle crash game cash out
    crash_data = context.user_data.get(f"{chat_id}_{user_id}_crash", {})
    if crash_data.get('active', False) and text == "cash":
        if crash_data.get('crashed', False):
            return
        
        crash_data['active'] = False
        crash_data['crashed'] = True
        
        multiplier = crash_data.get('multiplier', 1.0)
        bet_amount = crash_data.get('bet', 10)
        
        winnings = int(bet_amount * multiplier)
        update_balance(user_id, winnings)
        
        new_balance = get_balance(user_id)
        
        await update.message.reply_text(
            f"✅ CASHED OUT at {multiplier}x!\n"
            f"Won: +{winnings}₹\nBalance: {new_balance}₹"
        )
        
        try:
            await context.bot.edit_message_text(
                f"📈 CASHED OUT at {multiplier}x",
                chat_id=chat_id,
                message_id=crash_data['msg_id']
            )
        except:
            pass
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📈 PLAY AGAIN", callback_data="select_crash"),
             InlineKeyboardButton("🏠 MENU", callback_data="back_to_games")]
        ])
        await update.message.reply_text("Play again?", reply_markup=keyboard)
    
    # Handle OK start for bot games
    elif text == "ok start":
        game = context.user_data.get(f"{chat_id}_{user_id}_game")
        bet = context.user_data.get(f"{chat_id}_{user_id}_bet")
        
        if game in ["dart", "bowling", "football"] and bet:
            await start_bot_game(update, context, game, bet)

async def start_bot_game(update, context, game, bet_amount):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    balance = get_balance(user_id)
    if balance < bet_amount:
        await update.message.reply_text("❌ Insufficient Balance!")
        return
    
    update_balance(user_id, -bet_amount)
    
    emoji_map = {'dart': '🎯', 'bowling': '🎳', 'football': '⚽'}
    emoji = emoji_map.get(game)
    
    bot_msg = await context.bot.send_dice(chat_id=chat_id, emoji=emoji)
    await asyncio.sleep(3)
    bot_score = bot_msg.dice.value
    
    active_games[(chat_id, user_id)] = {
        'game': game,
        'bet': bet_amount,
        'bot_score': bot_score
    }
    
    await update.message.reply_text(f"🤖 Bot: {bot_score}\nYour turn! Send {emoji}")

# ==================== DICE HANDLER ====================
async def group_dice_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    
    if (chat_id, user_id) not in active_games:
        return
    
    game_data = active_games[(chat_id, user_id)]
    user_score = update.message.dice.value
    bot_score = game_data['bot_score']
    bet_amount = game_data['bet']
    game = game_data['game']
    
    if user_score > bot_score:
        winnings = bet_amount * 2
        update_balance(user_id, winnings)
        result = "✅ YOU WIN!"
    elif user_score < bot_score:
        winnings = 0
        result = "❌ YOU LOSE!"
    else:
        winnings = bet_amount
        update_balance(user_id, bet_amount)
        result = "⚖️ DRAW!"
    
    new_balance = get_balance(user_id)
    
    result_msg = (
        f"{result}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Bot: {bot_score} | You: {user_score}\n"
        f"Bet: {bet_amount}₹\n"
        f"{'Won: +' + str(winnings) + '₹' if winnings > bet_amount else 'Lost: -' + str(bet_amount) + '₹' if winnings == 0 else 'Draw: 0₹'}\n"
        f"Balance: {new_balance}₹"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton(f"PLAY AGAIN", callback_data=f"select_{game}"),
         InlineKeyboardButton("MENU", callback_data="back_to_games")]
    ])
    
    await update.message.reply_text(result_msg, reply_markup=keyboard)
    
    del active_games[(chat_id, user_id)]

# ==================== MAIN ====================
def main():
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("rules", rules))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("addbalance", addbalance))
    
    # Callback handler
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Message handlers
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, group_text_handler))
    app.add_handler(MessageHandler(filters.Dice.ALL, group_dice_handler))
    
    print("🎰 CASINO BOT - FULLY LOADED!")
    print(f"✅ All 8 games working with rules!")
    print(f"✅ Admin panel with balance management!")
    print(f"✅ Payment bot connected: @{PAYMENT_BOT_USERNAME}")
    print(f"✅ Commands: /start, /menu, /balance, /stats, /rules, /admin")
    print(f"📱 Add bot to group and use /menu")
    app.run_polling()

if __name__ == "__main__":
    main()