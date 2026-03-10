import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# ========================
# НАСТРОЙКИ
# ========================
BOT_TOKEN = "7920231183:AAHYslb-DOF7LWJ3gm6ThF5OFmjEShm9u9M"
ADMIN_CHAT_ID = None  # ← ВСТАВЬТЕ СЮДА ВАШ CHAT ID (см. инструкцию ниже)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Хранение состояний пользователей
user_data = {}

# ========================
# ГЛАВНОЕ МЕНЮ
# ========================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("🎬 Начать создавать →", callback_data="start_create")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"✨ *Добро пожаловать в Seedance Studio!*\n\n"
        f"Создавайте захватывающие AI-видео всего за несколько шагов.\n\n"
        f"Опишите вашу идею и выберите параметры — мы сделаем остальное! 🚀",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ========================
# ШАГ 1: Описание идеи
# ========================
async def start_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data[user_id] = {}

    await query.edit_message_text(
        "✍️ *Шаг 1 из 4 — Описание*\n\n"
        "Опишите вашу идею для видео.\n"
        "_Например: Промо-видео чайного магазина в японском стиле, закат над горами..._",
        parse_mode="Markdown"
    )
    context.user_data["step"] = "waiting_description"

# ========================
# ШАГ 2: Выбор модели
# ========================
async def ask_model(update: Update, context: ContextTypes.DEFAULT_TYPE, description: str = None):
    keyboard = [
        [InlineKeyboardButton("⚡ Быстрый Seedance 2.0 (Fast)", callback_data="model_fast")],
        [InlineKeyboardButton("🎯 Seedance 2.0 (качество)", callback_data="model_2")],
        [InlineKeyboardButton("🎵 Seedance 1.5 (из аудио/видео)", callback_data="model_15")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.message:
        await update.message.reply_text(
            "🤖 *Шаг 2 из 4 — Выбор модели*\n\n"
            "Выберите модель генерации:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        await update.callback_query.edit_message_text(
            "🤖 *Шаг 2 из 4 — Выбор модели*\n\n"
            "Выберите модель генерации:",
            parse_mode="Markdown",
            reply_markup=reply_markup
        )

# ========================
# ШАГ 3: Ориентация
# ========================
async def ask_orientation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("🔲 Авто", callback_data="orient_auto"),
         InlineKeyboardButton("🖥 16:9 Пейзаж", callback_data="orient_16_9")],
        [InlineKeyboardButton("📱 9:16 Вертикаль", callback_data="orient_9_16"),
         InlineKeyboardButton("📺 4:3", callback_data="orient_4_3")],
        [InlineKeyboardButton("📋 3:4", callback_data="orient_3_4")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "📐 *Шаг 3 из 4 — Ориентация*\n\n"
        "Выберите формат видео:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ========================
# ШАГ 4: Длительность
# ========================
async def ask_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [
        [InlineKeyboardButton("⚡ 5 секунд", callback_data="dur_5s")],
        [InlineKeyboardButton("🕐 10 секунд", callback_data="dur_10s")],
        [InlineKeyboardButton("🕑 15 секунд", callback_data="dur_15s")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        "⏱ *Шаг 4 из 4 — Длительность*\n\n"
        "Выберите длину видео:",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ========================
# ИТОГ И ОТПРАВКА АДМИНУ
# ========================
async def send_order_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = query.from_user
    data = user_data.get(user_id, {})

    # Красивое резюме для пользователя
    summary = (
        f"✅ *Ваш заказ принят!*\n\n"
        f"📝 *Описание:* {data.get('description', '—')}\n"
        f"🤖 *Модель:* {data.get('model', '—')}\n"
        f"📐 *Формат:* {data.get('orientation', '—')}\n"
        f"⏱ *Длительность:* {data.get('duration', '—')}\n\n"
        f"_Ваш заказ отправлен. Ожидайте готовое видео!_ 🎬"
    )

    await query.edit_message_text(summary, parse_mode="Markdown")

    # Отправка админу
    if ADMIN_CHAT_ID:
        admin_text = (
            f"🔔 *НОВЫЙ ЗАКАЗ!*\n\n"
            f"👤 Пользователь: {user.full_name}\n"
            f"🆔 ID: `{user_id}`\n"
            f"📱 Username: @{user.username or 'нет'}\n\n"
            f"📝 *Описание:* {data.get('description', '—')}\n"
            f"🤖 *Модель:* {data.get('model', '—')}\n"
            f"📐 *Формат:* {data.get('orientation', '—')}\n"
            f"⏱ *Длительность:* {data.get('duration', '—')}"
        )
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_text,
            parse_mode="Markdown"
        )

# ========================
# ОБРАБОТКА ТЕКСТА
# ========================
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    if step == "waiting_description":
        user_data[user_id] = user_data.get(user_id, {})
        user_data[user_id]["description"] = update.message.text
        context.user_data["step"] = None
        await ask_model(update, context, update.message.text)
    else:
        await start(update, context)

# ========================
# ОБРАБОТКА КНОПОК
# ========================
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "start_create":
        await start_create(update, context)

    # Модели
    elif data == "model_fast":
        user_data[user_id]["model"] = "⚡ Быстрый Seedance 2.0 (Fast)"
        await ask_orientation(update, context)
    elif data == "model_2":
        user_data[user_id]["model"] = "🎯 Seedance 2.0"
        await ask_orientation(update, context)
    elif data == "model_15":
        user_data[user_id]["model"] = "🎵 Seedance 1.5"
        await ask_orientation(update, context)

    # Ориентация
    elif data == "orient_auto":
        user_data[user_id]["orientation"] = "🔲 Авто"
        await ask_duration(update, context)
    elif data == "orient_16_9":
        user_data[user_id]["orientation"] = "🖥 16:9 Пейзаж"
        await ask_duration(update, context)
    elif data == "orient_9_16":
        user_data[user_id]["orientation"] = "📱 9:16 Вертикаль"
        await ask_duration(update, context)
    elif data == "orient_4_3":
        user_data[user_id]["orientation"] = "📺 4:3"
        await ask_duration(update, context)
    elif data == "orient_3_4":
        user_data[user_id]["orientation"] = "📋 3:4"
        await ask_duration(update, context)

    # Длительность + финал
    elif data == "dur_5s":
        user_data[user_id]["duration"] = "⚡ 5 секунд"
        await send_order_to_admin(update, context)
    elif data == "dur_10s":
        user_data[user_id]["duration"] = "🕐 10 секунд"
        await send_order_to_admin(update, context)
    elif data == "dur_15s":
        user_data[user_id]["duration"] = "🕑 15 секунд"
        await send_order_to_admin(update, context)

# ========================
# ЗАПУСК
# ========================
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("🤖 Бот запущен! Нажмите Ctrl+C для остановки.")
    app.run_polling()

if __name__ == "__main__":
    main()
