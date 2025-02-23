import nest_asyncio
import asyncio
import json
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, CallbackContext, ConversationHandler

USER_DATA_FILE = "users.json"

def load_users():
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_users(users):
    with open(USER_DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

users = load_users()

TOKEN = "YOUR_BOT_TOKEN"
ADMIN_ID = YOUR_ID 

ASK_QUESTION, ANSWER_QUESTION, BROADCAST, SEND_USER_MESSAGE = range(4)

async def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    keyboard = [[KeyboardButton("📱 Raqam yuborish", request_contact=True)]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_text("📞 Iltimos, telefon raqamingizni yuboring:", reply_markup=reply_markup)


async def contact_handler(update: Update, context: CallbackContext):
    contact = update.message.contact
    user = update.message.from_user
    full_name = f"{user.first_name} {user.last_name or ''}".strip()
    phone_number = contact.phone_number

    users[str(user.id)] = {"name": full_name, "phone": phone_number, "chat_id": user.id}
    save_users(users)

    if user.id == ADMIN_ID:
        keyboard = [[KeyboardButton("👥 Foydalanuvchilar"), KeyboardButton("📢 Hamma foydalanuvchilarga xabar")]]
    else:
        keyboard = [[KeyboardButton("❓ Admin-ga savol berish"), KeyboardButton("📢 Hamma foydalanuvchilarga xabar")]]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(f"👋 Assalomu alaykum, {full_name}! ✅\n📞 Raqamingiz saqlandi.",
                                    reply_markup=reply_markup)


async def show_users(update: Update, context: CallbackContext):
    if update.message.from_user.id != ADMIN_ID:
        return
    keyboard = [[InlineKeyboardButton(user_data["name"], callback_data=f"user_{user_id}")] for user_id, user_data in
                users.items()]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("👥 Foydalanuvchilar ro‘yxati:", reply_markup=reply_markup)


async def select_user(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.data.split("_")[1]
    context.user_data["selected_user"] = user_id
    await query.message.reply_text(f"✍️ {users[user_id]['name']} ga yuboriladigan xabarni kiriting:")
    return SEND_USER_MESSAGE


async def send_user_message(update: Update, context: CallbackContext):
    selected_user = context.user_data.get("selected_user")
    if not selected_user:
        await update.message.reply_text("❌ Xatolik yuz berdi.")
        return ConversationHandler.END

    message = update.message.text
    try:
        await context.bot.send_message(chat_id=users[selected_user]["chat_id"], text=f"📩 Admin xabari:\n💬 {message}")
        await update.message.reply_text(f"✅ Xabar {users[selected_user]['name']} ga yuborildi.")
    except Exception:
        await update.message.reply_text("❌ Xabar yuborilmadi.")
    return ConversationHandler.END


async def ask_admin(update: Update, context: CallbackContext):
    await update.message.reply_text("❓ Admin-ga yuboriladigan savolni kiriting:")
    return ASK_QUESTION


async def send_question(update: Update, context: CallbackContext):
    user = update.message.from_user
    message = update.message.text
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"📩 Yangi savol: {message}\n👤 {user.full_name}",
        reply_markup=InlineKeyboardMarkup(
            [[InlineKeyboardButton("✍️ Javob berish", callback_data=f"answer_{user.id}")]]
        )
    )
    await update.message.reply_text("✅ Savolingiz yuborildi. Admin tez orada javob beradi.")
    return ConversationHandler.END


async def answer_question(update: Update, context: CallbackContext):
    query = update.callback_query
    await query.answer()
    user_id = query.data.split("_")[1]
    context.user_data["selected_user"] = user_id
    await query.message.reply_text("✍️ Javobingizni kiriting:")
    return ANSWER_QUESTION


async def send_answer(update: Update, context: CallbackContext):
    selected_user = context.user_data.get("selected_user")
    if not selected_user:
        await update.message.reply_text("❌ Xatolik yuz berdi.")
        return ConversationHandler.END
    message = update.message.text
    try:
        await context.bot.send_message(chat_id=users[selected_user]["chat_id"], text=f"📩 Admin javobi:\n💬 {message}")
        await update.message.reply_text("✅ Javob yuborildi.")
    except Exception:
        await update.message.reply_text("❌ Javob yuborilmadi.")
    return ConversationHandler.END


async def broadcast(update: Update, context: CallbackContext):
    await update.message.reply_text("📢 Hamma foydalanuvchilarga yuboriladigan xabarni kiriting:")
    return BROADCAST


async def send_broadcast(update: Update, context: CallbackContext):
    message = update.message.text
    sender_id = str(update.message.from_user.id)
    sender_name = users.get(sender_id, {}).get("name", "Noma'lum foydalanuvchi")
    sent_count = 0

    for user_id, user_data in users.items():
        try:
            await context.bot.send_message(
                chat_id=user_data["chat_id"],
                text=f"👤 {sender_name}\n📢 Umumiy xabar:\n💬 {message}"
            )
            sent_count += 1
        except Exception:
            pass

    await update.message.reply_text(f"✅ Xabar {sent_count} ta foydalanuvchiga yuborildi.")
    return ConversationHandler.END



app = Application.builder().token(TOKEN).build()

conv_send_user_message = ConversationHandler(
    entry_points=[CallbackQueryHandler(select_user, pattern=r"^user_\d+$")],
    states={SEND_USER_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_user_message)]},
    fallbacks=[]
)

conv_ask_admin = ConversationHandler(
    entry_points=[MessageHandler(filters.Text("❓ Admin-ga savol berish"), ask_admin)],
    states={ASK_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_question)]},
    fallbacks=[]
)

conv_answer_question = ConversationHandler(
    entry_points=[CallbackQueryHandler(answer_question, pattern=r"^answer_\d+$")],
    states={ANSWER_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_answer)]},
    fallbacks=[]
)

conv_broadcast = ConversationHandler(
    entry_points=[MessageHandler(filters.Text("📢 Hamma foydalanuvchilarga xabar"), broadcast)],
    states={BROADCAST: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_broadcast)]},
    fallbacks=[]
)

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.CONTACT, contact_handler))
app.add_handler(conv_send_user_message)
app.add_handler(conv_ask_admin)
app.add_handler(conv_answer_question)
app.add_handler(conv_broadcast)
app.add_handler(MessageHandler(filters.Text("👥 Foydalanuvchilar"), show_users))

async def main():
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("🤖 Bot ishlamoqda...")

# 🔄 Google Colab’da `asyncio` bilan ishlash uchun `nest_asyncio`
nest_asyncio.apply()

# 🔥 Asosiy event loop
loop = asyncio.get_event_loop()
loop.run_until_complete(main())
