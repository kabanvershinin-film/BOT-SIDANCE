import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8450032677:AAFDP6dBe2ZlKRY_u17Uo9crcrc6z7JmxHI")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", 464450106))
PORT = int(os.environ.get("PORT", 8080))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args):
        pass

def run_health_server():
    HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever()

user_data = {}

# ── ГЛАВНОЕ МЕНЮ ──────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎬 Начать создавать →", callback_data="start_create")]]
    await update.message.reply_text(
        "✨ *Добро пожаловать в Seedance Studio!*\n\n"
        "Создавайте захватывающие AI-видео всего за несколько шагов.\n\n"
        "Опишите вашу идею и выберите параметры — мы сделаем остальное! 🚀",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ── ШАГ 1: Описание ───────────────────────────────────
async def start_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_data[query.from_user.id] = {"references": [], "ref_message_ids": []}
    await query.edit_message_text(
        "✍️ *Шаг 1 из 6 — Описание идеи*\n\n"
        "Опишите вашу идею для видео.\n"
        "_Например: Промо-видео чайного магазина в японском стиле..._",
        parse_mode="Markdown"
    )
    context.user_data["step"] = "waiting_description"

# ── ШАГ 2: Промпт ─────────────────────────────────────
async def ask_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("⏭ Пропустить промпт", callback_data="skip_prompt")]]
    await update.message.reply_text(
        "📝 *Шаг 2 из 6 — Промпт*\n\n"
        "Введите детальный промпт для генерации видео.\n"
        "_Опишите стиль, атмосферу, детали сцены..._\n\n"
        "Или нажмите «Пропустить» если не нужен.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data["step"] = "waiting_prompt"

# ── ШАГ 3: Референсы ──────────────────────────────────
async def ask_references(update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    keyboard = [[InlineKeyboardButton("✅ Готово — референсы загружены", callback_data="refs_done")]]
    text = (
        "🖼 *Шаг 3 из 6 — Референсы*\n\n"
        "Прикрепите фото или видео-референсы (можно несколько).\n"
        "Отправляйте по одному файлу.\n\n"
        "Когда загрузите все — нажмите *«Готово»*."
    )
    if is_callback:
        await update.callback_query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    context.user_data["step"] = "waiting_refs"

# ── ШАГ 4: Модель ─────────────────────────────────────
async def ask_model(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    keyboard = [
        [InlineKeyboardButton("⚡ Быстрый Seedance 2.0 (Fast)", callback_data="model_fast")],
        [InlineKeyboardButton("🎯 Seedance 2.0 (качество)", callback_data="model_2")],
        [InlineKeyboardButton("🎵 Seedance 1.5 (из аудио/видео)", callback_data="model_15")],
    ]
    text = "🤖 *Шаг 4 из 6 — Выбор модели*\n\nВыберите модель генерации:"
    if is_callback:
        await update.callback_query.edit_message_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            text, parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ── ШАГ 5: Ориентация ─────────────────────────────────
async def ask_orientation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🔲 Авто", callback_data="orient_auto"),
         InlineKeyboardButton("🖥 16:9 Пейзаж", callback_data="orient_16_9")],
        [InlineKeyboardButton("📱 9:16 Вертикаль", callback_data="orient_9_16"),
         InlineKeyboardButton("📺 4:3", callback_data="orient_4_3")],
        [InlineKeyboardButton("📋 3:4", callback_data="orient_3_4")],
    ]
    await update.callback_query.edit_message_text(
        "📐 *Шаг 5 из 6 — Ориентация*\n\nВыберите формат видео:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ── ШАГ 6: Длительность ───────────────────────────────
async def ask_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("⚡ 5 секунд", callback_data="dur_5s")],
        [InlineKeyboardButton("🕐 10 секунд", callback_data="dur_10s")],
        [InlineKeyboardButton("🕑 15 секунд", callback_data="dur_15s")],
    ]
    await update.callback_query.edit_message_text(
        "⏱ *Шаг 6 из 6 — Длительность*\n\nВыберите длину видео:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ── ОТПРАВКА ЗАКАЗА АДМИНУ ────────────────────────────
async def send_order_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = query.from_user
    data = user_data.get(user_id, {})
    refs = data.get("references", [])

    await query.edit_message_text(
        f"✅ *Ваш заказ принят!*\n\n"
        f"📝 *Описание:* {data.get('description', '—')}\n"
        f"📋 *Промпт:* {data.get('prompt', 'не указан')}\n"
        f"🖼 *Референсов:* {len(refs)} шт\n"
        f"🤖 *Модель:* {data.get('model', '—')}\n"
        f"📐 *Формат:* {data.get('orientation', '—')}\n"
        f"⏱ *Длительность:* {data.get('duration', '—')}\n\n"
        f"_Ожидайте готовое видео!_ 🎬",
        parse_mode="Markdown"
    )

    if ADMIN_CHAT_ID:
        # Отправляем текст заказа
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                f"🔔 *НОВЫЙ ЗАКАЗ!*\n\n"
                f"👤 {user.full_name}\n"
                f"🆔 `{user_id}`\n"
                f"📱 @{user.username or 'нет'}\n\n"
                f"📝 *Описание:* {data.get('description', '—')}\n"
                f"📋 *Промпт:* {data.get('prompt', 'не указан')}\n"
                f"🖼 *Референсов:* {len(refs)} шт\n"
                f"🤖 *Модель:* {data.get('model', '—')}\n"
                f"📐 *Формат:* {data.get('orientation', '—')}\n"
                f"⏱ *Длительность:* {data.get('duration', '—')}"
            ),
            parse_mode="Markdown"
        )

        # Пересылаем все референсы
        for ref in refs:
            try:
                if ref["type"] == "photo":
                    await context.bot.send_photo(
                        chat_id=ADMIN_CHAT_ID,
                        photo=ref["file_id"],
                        caption=f"🖼 Референс от @{user.username or user_id}"
                    )
                elif ref["type"] == "video":
                    await context.bot.send_video(
                        chat_id=ADMIN_CHAT_ID,
                        video=ref["file_id"],
                        caption=f"🎬 Видео-референс от @{user.username or user_id}"
                    )
                elif ref["type"] == "document":
                    await context.bot.send_document(
                        chat_id=ADMIN_CHAT_ID,
                        document=ref["file_id"],
                        caption=f"📎 Файл-референс от @{user.username or user_id}"
                    )
            except Exception as e:
                logger.error(f"Error sending ref: {e}")

# ── ОБРАБОТКА ТЕКСТА ──────────────────────────────────
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    if step == "waiting_description":
        user_data.setdefault(user_id, {"references": []})
        user_data[user_id]["description"] = update.message.text
        context.user_data["step"] = None
        await ask_prompt(update, context)

    elif step == "waiting_prompt":
        user_data.setdefault(user_id, {"references": []})
        user_data[user_id]["prompt"] = update.message.text
        context.user_data["step"] = None
        await ask_references(update, context, is_callback=False)

    elif step == "waiting_refs":
        await update.message.reply_text(
            "📎 Отправьте фото или видео файл, а не текст.\n"
            "Когда загрузите все референсы — нажмите *«Готово»*.",
            parse_mode="Markdown"
        )
    else:
        await start(update, context)

# ── ОБРАБОТКА МЕДИА (референсы) ───────────────────────
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    if step != "waiting_refs":
        return

    user_data.setdefault(user_id, {"references": []})
    refs = user_data[user_id].setdefault("references", [])

    msg = update.message
    if msg.photo:
        file_id = msg.photo[-1].file_id
        refs.append({"type": "photo", "file_id": file_id})
    elif msg.video:
        refs.append({"type": "video", "file_id": msg.video.file_id})
    elif msg.document:
        refs.append({"type": "document", "file_id": msg.document.file_id})

    count = len(refs)
    keyboard = [[InlineKeyboardButton("✅ Готово — референсы загружены", callback_data="refs_done")]]
    await update.message.reply_text(
        f"✅ Референс #{count} добавлен!\n\n"
        f"Всего загружено: *{count}* файлов\n\n"
        f"Добавьте ещё или нажмите *«Готово»*.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ── ОБРАБОТКА КНОПОК ──────────────────────────────────
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "start_create":
        await start_create(update, context)

    elif data == "skip_prompt":
        user_data.setdefault(user_id, {"references": []})
        user_data[user_id]["prompt"] = "не указан"
        context.user_data["step"] = None
        await ask_references(update, context, is_callback=True)

    elif data == "refs_done":
        context.user_data["step"] = None
        await ask_model(update, context, is_callback=True)

    elif data == "model_fast":
        user_data[user_id]["model"] = "⚡ Быстрый Seedance 2.0 (Fast)"
        await ask_orientation(update, context)
    elif data == "model_2":
        user_data[user_id]["model"] = "🎯 Seedance 2.0"
        await ask_orientation(update, context)
    elif data == "model_15":
        user_data[user_id]["model"] = "🎵 Seedance 1.5"
        await ask_orientation(update, context)

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

    elif data == "dur_5s":
        user_data[user_id]["duration"] = "⚡ 5 секунд"
        await send_order_to_admin(update, context)
    elif data == "dur_10s":
        user_data[user_id]["duration"] = "🕐 10 секунд"
        await send_order_to_admin(update, context)
    elif data == "dur_15s":
        user_data[user_id]["duration"] = "🕑 15 секунд"
        await send_order_to_admin(update, context)

# ── ЗАПУСК ────────────────────────────────────────────
def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 Бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
