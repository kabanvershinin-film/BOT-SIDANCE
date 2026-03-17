import logging
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8450032677:AAFDP6dBe2ZlKRY_u17Uo9crcrc6z7JmxHI")
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", 464450106))
PORT = int(os.environ.get("PORT", 8080))

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_data = {}

# ── Keep-alive ────────────────────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args):
        pass

def run_health_server():
    HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever()

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
    user_data[query.from_user.id] = {"references": []}
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
        "Когда загрузите все — нажмите *«Готово»*.\n"
        "Или сразу «Готово» если референсы не нужны."
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
        "✅ *Ваш заказ принят!*\n\n"
        f"📝 *Описание:* {data.get('description', '—')}\n"
        f"📋 *Промпт:* {data.get('prompt', 'не указан')}\n"
        f"🖼 *Референсов:* {len(refs)} шт\n"
        f"🤖 *Модель:* {data.get('model', '—')}\n"
        f"📐 *Формат:* {data.get('orientation', '—')}\n"
        f"⏱ *Длительность:* {data.get('duration', '—')}\n\n"
        "_Ожидайте готовое видео!_ 🎬",
        parse_mode="Markdown"
    )

    if ADMIN_CHAT_ID:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=(
                "🔔 *НОВЫЙ ЗАКАЗ!*\n\n"
                f"👤 {user.full_name}\n"
                f"🆔 `{user_id}`\n"
                f"📱 @{user.username or 'нет'}\n\n"
                f"📝 *Описание:* {data.get('description', '—')}\n"
                f"📋 *Промпт:* {data.get('prompt', 'не указан')}\n"
                f"🖼 *Референсов:* {len(refs)} шт\n"
                f"🤖 *Модель:* {data.get('model', '—')}\n"
                f"📐 *Формат:* {data.get('orientation', '—')}\n"
                f"⏱ *Длительность:* {data.get('duration', '—')}\n\n"
                f"📤 Для отправки результата: /send {user_id}"
            ),
            parse_mode="Markdown"
        )

        # Отправляем референсы альбомом
        if refs:
            media_group = []
            for i, ref in enumerate(refs):
                cap = f"🖼 Референсы от @{user.username or user_id}" if i == 0 else None
                if ref["type"] == "photo":
                    media_group.append(InputMediaPhoto(media=ref["file_id"], caption=cap))
                elif ref["type"] == "video":
                    media_group.append(InputMediaVideo(media=ref["file_id"], caption=cap))

            if media_group:
                for i in range(0, len(media_group), 10):
                    try:
                        await context.bot.send_media_group(
                            chat_id=ADMIN_CHAT_ID,
                            media=media_group[i:i+10]
                        )
                    except Exception as e:
                        logger.error(f"Media group error: {e}")

# ── ОТПРАВКА РЕЗУЛЬТАТА ПОЛЬЗОВАТЕЛЮ ─────────────────
async def cmd_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /send USER_ID — следующий файл уйдёт этому пользователю"""
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    if not context.args:
        await update.message.reply_text(
            "Использование: /send USER_ID\n"
            "Например: /send 464450106\n\n"
            "После этого отправь видео/фото."
        )
        return
    try:
        target_id = int(context.args[0])
        context.user_data["reply_to"] = target_id
        await update.message.reply_text(
            f"✅ Следующий файл уйдёт пользователю `{target_id}`\n\n"
            "Теперь отправь видео или фото.",
            parse_mode="Markdown"
        )
    except Exception:
        await update.message.reply_text("❌ Неверный USER_ID")

async def handle_admin_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Админ отправляет файл — пересылаем пользователю"""
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    target_id = context.user_data.get("reply_to")
    if not target_id:
        return
    msg = update.message
    try:
        if msg.video:
            await context.bot.send_video(
                chat_id=target_id,
                video=msg.video.file_id,
                caption="🎬 *Ваше видео готово!*\n\nСпасибо за заказ в Seedance Studio! 🚀",
                parse_mode="Markdown"
            )
        elif msg.photo:
            await context.bot.send_photo(
                chat_id=target_id,
                photo=msg.photo[-1].file_id,
                caption="🖼 *Ваш результат готов!*\n\nСпасибо за заказ в Seedance Studio! 🚀",
                parse_mode="Markdown"
            )
        elif msg.document:
            await context.bot.send_document(
                chat_id=target_id,
                document=msg.document.file_id,
                caption="📎 *Ваш файл готов!*\n\nСпасибо за заказ в Seedance Studio! 🚀",
                parse_mode="Markdown"
            )
        await msg.reply_text(f"✅ Отправлено пользователю `{target_id}`", parse_mode="Markdown")
        context.user_data.pop("reply_to", None)
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка: {e}")

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
            "📎 Отправьте фото или видео файл.\n"
            "Когда загрузите все — нажмите *«Готово»*.",
            parse_mode="Markdown"
        )
    else:
        await start(update, context)

# ── ОБРАБОТКА МЕДИА (референсы от пользователей) ─────
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Если это админ и у него есть reply_to — передаём в handle_admin_media
    if user_id == ADMIN_CHAT_ID and context.user_data.get("reply_to"):
        await handle_admin_media(update, context)
        return

    step = context.user_data.get("step")
    if step != "waiting_refs":
        return

    user_data.setdefault(user_id, {"references": []})
    refs = user_data[user_id].setdefault("references", [])

    msg = update.message
    if msg.photo:
        refs.append({"type": "photo", "file_id": msg.photo[-1].file_id})
    elif msg.video:
        refs.append({"type": "video", "file_id": msg.video.file_id})
    elif msg.document:
        refs.append({"type": "document", "file_id": msg.document.file_id})

    count = len(refs)
    keyboard = [[InlineKeyboardButton("✅ Готово — референсы загружены", callback_data="refs_done")]]
    await update.message.reply_text(
        f"✅ Референс #{count} добавлен!\n\n"
        f"Всего загружено: *{count}* файлов\n\n"
        "Добавьте ещё или нажмите *«Готово»*.",
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
    app.add_handler(CommandHandler("send", cmd_send))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO | filters.Document.ALL, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("🤖 Бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
