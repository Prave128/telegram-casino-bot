"""
PAYMENT BOT - Handles all deposits and withdrawals
Run this alongside your game bot
"""

import asyncio
import random
import sqlite3
import qrcode
from io import BytesIO
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler, 
    MessageHandler, ContextTypes, filters, ConversationHandler
)

# ==================== YOUR PAYMENT BOT TOKEN ====================
PAYMENT_BOT_TOKEN = "8580916830:AAHArAlaDnGpj5N07RdfGYXS5EJ7dLKEN_0"

# ==================== YOUR PAYMENT DETAILS ====================
UPI_ID = "praveennnnnguru@fam"      # Your UPI ID
UPI_NAME = "Raju kumar"            # Your name
UPI_NUMBER = "97867574963"            # Your phone
QR_CODE_PATH = "upi_qr.png"          # Your QR code file

BANK_NAME = "Don't pay"
ACCOUNT_NUMBER = "12345678901"
IFSC_CODE = "IFSC0001234"
ACCOUNT_HOLDER = "No Name"

# Game Bot Info (your existing game bot)
GAME_BOT_USERNAME = "Paymentboy_bot"  # CHANGE THIS to your game bot's username
GAME_BOT_LINK = f"https://t.me/{GAME_BOT_USERNAME}"

# Settings
MIN_DEPOSIT = 10
MIN_WITHDRAW = 50
WITHDRAWAL_FEE = 5
ADMIN_ID = 5943318266  # Your Telegram ID

# ==================== DATABASE (same as game bot) ====================
conn = sqlite3.connect('casino.db', check_same_thread=False)
c = conn.cursor()

# Users table (shared with game bot)
c.execute('''CREATE TABLE IF NOT EXISTS users
             (user_id INTEGER PRIMARY KEY, 
              username TEXT,
              balance INTEGER DEFAULT 0)''')

# Transactions table
c.execute('''CREATE TABLE IF NOT EXISTS transactions
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              txn_id TEXT UNIQUE,
              user_id INTEGER,
              type TEXT,
              amount INTEGER,
              method TEXT,
              status TEXT,
              upi_id TEXT,
              time TEXT)''')
conn.commit()

# ==================== CONVERSATION STATES ====================
(DEPOSIT_AMOUNT, DEPOSIT_SCREENSHOT, 
 WITHDRAW_AMOUNT, WITHDRAW_UPI) = range(4)

# ==================== PENDING TRANSACTIONS ====================
pending_deposits = {}
pending_withdrawals = {}

# ==================== HELPER FUNCTIONS ====================
def get_balance(user_id):
    c.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    result = c.fetchone()
    return result[0] if result else 0

def update_balance(user_id, amount):
    c.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
    conn.commit()

def create_user(user_id, username=None):
    c.execute("INSERT OR IGNORE INTO users (user_id, username, balance) VALUES (?, ?, ?)",
             (user_id, username, 0))
    conn.commit()

def generate_txn_id():
    import hashlib
    import time
    txn = f"TXN{int(time.time())}{random.randint(1000,9999)}"
    return hashlib.md5(txn.encode()).hexdigest()[:12].upper()

def save_transaction(txn_id, user_id, type, amount, method, status, upi_id=None):
    c.execute('''INSERT INTO transactions 
                 (txn_id, user_id, type, amount, method, status, upi_id, time)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
              (txn_id, user_id, type, amount, method, status, upi_id, 
               datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()

# ==================== START COMMAND ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username
    create_user(user_id, username)
    
    balance = get_balance(user_id)
    
    text = (
        f"💰 PAYMENT BOT\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Your Balance: {balance} coins\n"
        f"1 Coin = ₹1\n\n"
        f"🎮 Play Games: @{GAME_BOT_USERNAME}\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"Choose an option:"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📥 DEPOSIT", callback_data="deposit"),
         InlineKeyboardButton("📤 WITHDRAW", callback_data="withdraw")],
        [InlineKeyboardButton("📜 HISTORY", callback_data="history"),
         InlineKeyboardButton("🎮 PLAY GAMES", url=GAME_BOT_LINK)],
        [InlineKeyboardButton("📞 CONTACT ADMIN", url=f"tg://user?id={ADMIN_ID}")]
    ])
    
    await update.message.reply_text(text, reply_markup=keyboard)

# ==================== DEPOSIT ====================
async def deposit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = f"📥 DEPOSIT MENU\n\nMin: ₹{MIN_DEPOSIT}\nChoose method:"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 UPI (Instant)", callback_data="deposit_upi")],
        [InlineKeyboardButton("🏦 BANK Transfer", callback_data="deposit_bank")],
        [InlineKeyboardButton("🔙 BACK", callback_data="start")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard)

async def deposit_upi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = f"📱 UPI DEPOSIT\n\n"
    text += f"UPI ID: {UPI_ID}\n"
    text += f"Name: {UPI_NAME}\n"
    text += f"Phone: {UPI_NUMBER}\n\n"
    text += f"1️⃣ Send amount to above UPI\n"
    text += f"2️⃣ Enter amount below\n"
    text += f"3️⃣ Send screenshot\n\n"
    text += f"Min: ₹{MIN_DEPOSIT}"
    
    # Send QR code
    try:
        with open(QR_CODE_PATH, 'rb') as f:
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=f,
                caption="📸 Scan this QR code to pay"
            )
    except:
        await query.message.reply_text("⚠️ QR code not found, but UPI ID is above")
    
    await query.edit_message_text(text)
    await query.message.reply_text("💰 Enter amount to deposit (in ₹):")
    
    return DEPOSIT_AMOUNT

async def deposit_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        amount = int(update.message.text)
        if amount < MIN_DEPOSIT:
            await update.message.reply_text(f"❌ Minimum deposit is ₹{MIN_DEPOSIT}")
            return ConversationHandler.END
    except:
        await update.message.reply_text("❌ Please enter a valid number")
        return ConversationHandler.END
    
    context.user_data['deposit_amount'] = amount
    await update.message.reply_text("📤 Now send the payment screenshot:")
    
    return DEPOSIT_SCREENSHOT

async def deposit_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.photo:
        await update.message.reply_text("❌ Please send a screenshot")
        return DEPOSIT_SCREENSHOT
    
    user = update.effective_user
    amount = context.user_data['deposit_amount']
    txn_id = generate_txn_id()
    
    # Save pending
    pending_deposits[txn_id] = {
        'user_id': user.id,
        'username': user.username or user.first_name,
        'amount': amount,
        'time': datetime.now().strftime("%H:%M")
    }
    
    # Save to DB
    save_transaction(txn_id, user.id, 'deposit', amount, 'UPI', 'pending')
    
    # Notify admin
    caption = f"🔔 NEW DEPOSIT\n"
    caption += f"User: {user.first_name} (@{user.username})\n"
    caption += f"Amount: ₹{amount}\n"
    caption += f"TXN ID: {txn_id}\n\n"
    caption += f"Approve: /approve {txn_id}"
    
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=update.message.photo[-1].file_id,
        caption=caption
    )
    
    await update.message.reply_text(
        f"✅ Deposit request sent!\n"
        f"TXN ID: {txn_id}\n\n"
        f"Your coins will be added within 5-10 minutes.\n"
        f"Then play at: @{GAME_BOT_USERNAME}"
    )
    
    context.user_data.clear()
    return ConversationHandler.END

async def deposit_bank(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    text = f"🏦 BANK TRANSFER\n\n"
    text += f"Bank: {BANK_NAME}\n"
    text += f"Account: {ACCOUNT_NUMBER}\n"
    text += f"IFSC: {IFSC_CODE}\n"
    text += f"Holder: {ACCOUNT_HOLDER}\n\n"
    text += f"After transfer, send screenshot to admin"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 BACK", callback_data="deposit")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard)

# ==================== WITHDRAW ====================
async def withdraw_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    balance = get_balance(user_id)
    
    text = f"📤 WITHDRAW\n\n"
    text += f"Your Balance: {balance} coins\n"
    text += f"Minimum: ₹{MIN_WITHDRAW}\n"
    text += f"Fee: ₹{WITHDRAWAL_FEE}\n\n"
    text += "Available: UPI only"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📱 UPI", callback_data="withdraw_upi")],
        [InlineKeyboardButton("🔙 BACK", callback_data="start")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard)

async def withdraw_upi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("💰 Enter amount to withdraw (in ₹):")
    return WITHDRAW_AMOUNT

async def withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    balance = get_balance(user_id)
    
    try:
        amount = int(update.message.text)
        if amount < MIN_WITHDRAW:
            await update.message.reply_text(f"❌ Minimum withdrawal is ₹{MIN_WITHDRAW}")
            return ConversationHandler.END
        if amount + WITHDRAWAL_FEE > balance:
            await update.message.reply_text(f"❌ Insufficient balance! You need {amount + WITHDRAWAL_FEE} coins")
            return ConversationHandler.END
    except:
        await update.message.reply_text("❌ Please enter a valid number")
        return ConversationHandler.END
    
    context.user_data['withdraw_amount'] = amount
    await update.message.reply_text("📱 Enter your UPI ID (e.g., name@okhdfcbank):")
    return WITHDRAW_UPI

async def withdraw_upi_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    upi_id = update.message.text
    amount = context.user_data['withdraw_amount']
    
    if '@' not in upi_id:
        await update.message.reply_text("❌ Invalid UPI ID! Please enter a valid UPI ID")
        return WITHDRAW_UPI
    
    txn_id = generate_txn_id()
    total_deduct = amount + WITHDRAWAL_FEE
    
    # Deduct balance immediately
    update_balance(user.id, -total_deduct)
    
    # Save pending
    pending_withdrawals[txn_id] = {
        'user_id': user.id,
        'username': user.username or user.first_name,
        'amount': amount,
        'upi_id': upi_id,
        'fee': WITHDRAWAL_FEE
    }
    
    # Save to DB
    save_transaction(txn_id, user.id, 'withdraw', amount, 'UPI', 'pending', upi_id)
    
    # Notify admin
    admin_msg = f"🔔 NEW WITHDRAWAL\n"
    admin_msg += f"User: {user.first_name} (@{user.username})\n"
    admin_msg += f"Amount: ₹{amount}\n"
    admin_msg += f"Fee: ₹{WITHDRAWAL_FEE}\n"
    admin_msg += f"UPI: {upi_id}\n"
    admin_msg += f"TXN: {txn_id}\n\n"
    admin_msg += f"Approve: /withdraw_approve {txn_id}"
    
    await context.bot.send_message(ADMIN_ID, admin_msg)
    
    await update.message.reply_text(
        f"✅ Withdrawal request sent!\n"
        f"TXN ID: {txn_id}\n"
        f"Amount: ₹{amount}\n"
        f"Fee: ₹{WITHDRAWAL_FEE}\n"
        f"Deducted: ₹{total_deduct}\n\n"
        f"Payment will be sent within 24 hours."
    )
    
    context.user_data.clear()
    return ConversationHandler.END

# ==================== HISTORY ====================
async def history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    c.execute('''SELECT txn_id, type, amount, status, time 
                 FROM transactions WHERE user_id = ? 
                 ORDER BY id DESC LIMIT 10''', (user_id,))
    txns = c.fetchall()
    
    if not txns:
        text = "📜 No transactions yet"
    else:
        text = "📜 RECENT TRANSACTIONS\n━━━━━━━━━━━━━━━━━━\n"
        for txn in txns:
            emoji = "📥" if txn[1] == 'deposit' else "📤"
            status = "✅" if txn[3] == 'completed' else "⏳"
            text += f"{emoji}{status} ₹{txn[2]} - {txn[0]}\n"
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔙 BACK", callback_data="start")]
    ])
    
    await query.edit_message_text(text, reply_markup=keyboard)

# ==================== ADMIN COMMANDS ====================
async def approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve deposit - /approve TXN123"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    try:
        txn_id = context.args[0].upper()
        
        if txn_id not in pending_deposits:
            await update.message.reply_text(f"❌ Transaction {txn_id} not found")
            return
        
        data = pending_deposits[txn_id]
        
        # Add balance
        update_balance(data['user_id'], data['amount'])
        
        # Update DB
        c.execute("UPDATE transactions SET status = 'completed' WHERE txn_id = ?", (txn_id,))
        conn.commit()
        
        # Notify user
        await context.bot.send_message(
            data['user_id'],
            f"✅ Deposit Approved!\n"
            f"Amount: ₹{data['amount']}\n"
            f"New Balance: {get_balance(data['user_id'])} coins\n\n"
            f"Play now: @{GAME_BOT_USERNAME}"
        )
        
        await update.message.reply_text(f"✅ Approved ₹{data['amount']} for {data['username']}")
        del pending_deposits[txn_id]
        
    except IndexError:
        await update.message.reply_text("Usage: /approve TXN123")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def withdraw_approve(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Approve withdrawal - /withdraw_approve TXN123"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    try:
        txn_id = context.args[0].upper()
        
        if txn_id not in pending_withdrawals:
            await update.message.reply_text(f"❌ Transaction {txn_id} not found")
            return
        
        data = pending_withdrawals[txn_id]
        
        # Update DB
        c.execute("UPDATE transactions SET status = 'completed' WHERE txn_id = ?", (txn_id,))
        conn.commit()
        
        # Show payment details
        await update.message.reply_text(
            f"✅ SEND PAYMENT\n"
            f"Amount: ₹{data['amount']}\n"
            f"To UPI: {data['upi_id']}\n"
            f"User: {data['username']}\n\n"
            f"After sending, use:\n/confirm {txn_id}"
        )
        
    except IndexError:
        await update.message.reply_text("Usage: /withdraw_approve TXN123")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def confirm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Confirm payment sent - /confirm TXN123"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    try:
        txn_id = context.args[0].upper()
        
        if txn_id not in pending_withdrawals:
            await update.message.reply_text(f"❌ Transaction {txn_id} not found")
            return
        
        data = pending_withdrawals[txn_id]
        
        # Notify user
        await context.bot.send_message(
            data['user_id'],
            f"✅ Payment Confirmed!\n"
            f"₹{data['amount']} sent to your UPI\n"
            f"TXN ID: {txn_id}"
        )
        
        await update.message.reply_text(f"✅ Payment confirmed for {data['username']}")
        del pending_withdrawals[txn_id]
        
    except IndexError:
        await update.message.reply_text("Usage: /confirm TXN123")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

async def pending(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show all pending transactions"""
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("❌ Unauthorized")
        return
    
    text = "📋 PENDING TRANSACTIONS\n━━━━━━━━━━━━━━━━━━\n\n"
    
    text += "📥 DEPOSITS:\n"
    if not pending_deposits:
        text += "• None\n"
    else:
        for txn, data in pending_deposits.items():
            text += f"• {txn}: ₹{data['amount']} - {data['username']}\n"
    
    text += "\n📤 WITHDRAWALS:\n"
    if not pending_withdrawals:
        text += "• None\n"
    else:
        for txn, data in pending_withdrawals.items():
            text += f"• {txn}: ₹{data['amount']} - {data['username']} → {data['upi_id']}\n"
    
    await update.message.reply_text(text)

# ==================== MAIN ====================
def main():
    print("💰 PAYMENT BOT STARTING...")
    print(f"UPI ID: {UPI_ID}")
    print(f"Game Bot: @{GAME_BOT_USERNAME}")
    print(f"Admin ID: {ADMIN_ID}")
    
    app = ApplicationBuilder().token(PAYMENT_BOT_TOKEN).build()
    
    # Basic commands
    app.add_handler(CommandHandler("start", start))
    
    # Admin commands
    app.add_handler(CommandHandler("approve", approve))
    app.add_handler(CommandHandler("withdraw_approve", withdraw_approve))
    app.add_handler(CommandHandler("confirm", confirm))
    app.add_handler(CommandHandler("pending", pending))
    
    # Callback handlers
    app.add_handler(CallbackQueryHandler(deposit_menu, pattern="^deposit$"))
    app.add_handler(CallbackQueryHandler(withdraw_menu, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(history, pattern="^history$"))
    app.add_handler(CallbackQueryHandler(start, pattern="^start$"))
    app.add_handler(CallbackQueryHandler(deposit_bank, pattern="^deposit_bank$"))
    
    # Deposit conversation
    deposit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(deposit_upi, pattern="^deposit_upi$")],
        states={
            DEPOSIT_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, deposit_amount)],
            DEPOSIT_SCREENSHOT: [MessageHandler(filters.PHOTO, deposit_screenshot)],
        },
        fallbacks=[]
    )
    
    # Withdrawal conversation
    withdraw_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(withdraw_upi, pattern="^withdraw_upi$")],
        states={
            WITHDRAW_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_amount)],
            WITHDRAW_UPI: [MessageHandler(filters.TEXT & ~filters.COMMAND, withdraw_upi_id)],
        },
        fallbacks=[]
    )
    
    app.add_handler(deposit_conv)
    app.add_handler(withdraw_conv)
    
    print("✅ PAYMENT BOT IS RUNNING!")
    app.run_polling()

if __name__ == "__main__":
    main()