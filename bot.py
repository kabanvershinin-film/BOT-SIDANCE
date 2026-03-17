import logging
import os
import threading
import json
import requests
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from openai import AsyncOpenAI

# ── НАСТРОЙКИ И ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ──────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN") # Замените на ваш токен или добавьте в Render
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", 464450106))
PORT = int(os.environ.get("PORT", 8080))

# Ключ ElSpy AI
ELSPY_API_KEY = os.environ.get("ELSPY_API_KEY", "sk-7660a13fbd6fe78c87706c3fcb4191bf2bd6fe9547222ecd")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_data = {}

# Инициализация асинхронного клиента ElSpy AI
ai_client = AsyncOpenAI(
    api_key=ELSPY_API_KEY,
    base_url="https://api.ai6700.com/api/v1"
)

# ── ELSYP AI: ПОДГОТОВКА (Требование платформы) ───────
def init_elspy_capabilities():
    """Синхронизация возможностей платформы при запуске"""
    logger.info("Синхронизация с ElSpy AI...")
    headers = {"Authorization": f"Bearer {ELSPY_API_KEY}"}
    try:
        # Проверка баланса
        bal_res = requests.get("https://api.ai6700.com/api/v1/skills/balance", headers=headers)
        logger.info(f"Баланс ElSpy AI: {bal_res.text}")
        
        # Получение скиллов и гайдов
        skills_res = requests.get("https://api.ai6700.com/api/v1/skills", headers=headers)
        guide_res = requests.get("https://api.ai6700.com/api/v1/skills/guide", headers=headers)
        
        if skills_res.status_code == 200:
            with open("API_CAPABILITIES.md", "w", encoding="utf-8") as f:
                f.write("# Доступные модели ElSpy AI\n\n")
                f.write("## Skills\n" + json.dumps(skills_res.json(), indent=2, ensure_ascii=False) + "\n\n")
                if guide_res.status_code == 200:
                    f.write("## Guide\n" + json.dumps(guide_res.json(), indent=2, ensure_ascii=False))
            logger.info("API_CAPABILITIES.md успешно обновлен.")
    except Exception as e:
        logger.error(f"Ошибка синхронизации ElSpy AI: {e}")

# ── KEEP-ALIVE (ДЛЯ RENDER) ───────────────────────────
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
        "Опишите вашу идею, а наша нейросеть поможет составить идеальный промпт! 🚀",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ── ШАГ 1: Описание ───────────────────────────────────
async def start_create(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_data[query.from_user.id] = {"references":[]}
    await query.edit_message_text(
        "✍️ *Шаг 1 из 6 — Описание идеи*\n\n"
        "Опишите вашу идею для видео своими словами.\n"
        "_Например: Промо-видео чайного магазина в японском стиле, пар идет от чашки..._",
        parse_mode="Markdown"
    )
    context.user_data["step"] = "waiting_description"

# ── ШАГ 2: Промпт (с участием AI) ─────────────────────
async def ask_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE, ai_prompt: str = None):
    keyboard = [[InlineKeyboardButton("✅ Использовать этот AI-промпт", callback_data="use_ai_prompt")],[InlineKeyboardButton("⏭ Пропустить / Ввести свой", callback_data="skip_prompt")]
    ]
    
    msg_text = (
        "📝 *Шаг 2 из 6 — Промпт*\n\n"
        "✨ *Мы автоматически улучшили вашу идею с помощью ElSpy AI:*\n"
        f"`{ai_prompt}`\n\n"
        "Вы можете использовать его, пропустить этот шаг, или просто отправить в чат *свой вариант* текста."
    )
    
    await update.message.reply_text(
        msg_text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    context.user_data["step"] = "waiting_prompt"
    context.user_data["temp_ai_prompt"] = ai_prompt # Сохраняем во временную память

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
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    context.user_data["step"] = "waiting_refs"

# ── ОСТАЛЬНЫЕ ШАГИ (Без изменений) ────────────────────
async def ask_model(update: Update, context: ContextTypes.DEFAULT_TYPE, is_callback=False):
    keyboard = [[InlineKeyboardButton("⚡ Быстрый Seedance 2.0 (Fast)", callback_data="model_fast")],[InlineKeyboardButton("🎯 Seedance 2.0 (качество)", callback_data="model_2")],[InlineKeyboardButton("🎵 Seedance 1.5 (из аудио/видео)", callback_data="model_15")],
    ]
    text = "🤖 *Шаг 4 из 6 — Выбор модели*\n\nВыберите модель генерации:"
    if is_callback:
        await update.callback_query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_orientation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard =[[InlineKeyboardButton("🔲 Авто", callback_data="orient_auto"), InlineKeyboardButton("🖥 16:9 Пейзаж", callback_data="orient_16_9")],[InlineKeyboardButton("📱 9:16 Вертикаль", callback_data="orient_9_16"), InlineKeyboardButton("📺 4:3", callback_data="orient_4_3")],[InlineKeyboardButton("📋 3:4", callback_data="orient_3_4")],
    ]
    await update.callback_query.edit_message_text("📐 *Шаг 5 из 6 — Ориентация*\n\nВыберите формат видео:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def ask_duration(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard =[
        [InlineKeyboardButton("⚡ 5 секунд", callback_data="dur_5s")],[InlineKeyboardButton("🕐 10 секунд", callback_data="dur_10s")],[InlineKeyboardButton("🕑 15 секунд", callback_data="dur_15s")],
    ]
    await update.callback_query.edit_message_text("⏱ *Шаг 6 из 6 — Длительность*\n\nВыберите длину видео:", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# ── ОТПРАВКА ЗАКАЗА АДМИНУ ────────────────────────────
async def send_order_to_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    user = query.from_user
    data = user_data.get(user_id, {})
    refs = data.get("references",[])

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
                f"📋 *Промпт:* `{data.get('prompt', 'не указан')}`\n"
                f"🖼 *Референсов:* {len(refs)} шт\n"
                f"🤖 *Модель:* {data.get('model', '—')}\n"
                f"📐 *Формат:* {data.get('orientation', '—')}\n"
                f"⏱ *Длительность:* {data.get('duration', '—')}\n\n"
                f"📤 Для отправки результата: `/send {user_id}`"
            ),
            parse_mode="Markdown"
        )

        if refs:
            media_group =[]
            for i, ref in enumerate(refs):
                cap = f"🖼 Референсы от @{user.username or user_id}" if i == 0 else None
                if ref["type"] == "photo":
                    media_group.append(InputMediaPhoto(media=ref["file_id"], caption=cap))
                elif ref["type"] == "video":
                    media_group.append(InputMediaVideo(media=ref["file_id"], caption=cap))

            if media_group:
                for i in range(0, len(media_group), 10):
                    try:
                        await context.bot.send_media_group(chat_id=ADMIN_CHAT_ID, media=media_group[i:i+10])
                    except Exception as e:
                        logger.error(f"Media group error: {e}")

# ── КОМАНДЫ АДМИНА ────────────────────────────────────
async def cmd_send(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка ответа пользователю"""
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    if not context.args:
        await update.message.reply_text("Использование: `/send USER_ID`\nПосле этого отправь видео/фото.", parse_mode="Markdown")
        return
    try:
        target_id = int(context.args[0])
        context.user_data["reply_to"] = target_id
        await update.message.reply_text(f"✅ Следующий файл уйдёт пользователю `{target_id}`\nТеперь отправь видео или фото.", parse_mode="Markdown")
    except Exception:
        await update.message.reply_text("❌ Неверный USER_ID")

async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда для проверки баланса ElSpy AI (только админ)"""
    if update.effective_user.id != ADMIN_CHAT_ID:
        return
    
    headers = {"Authorization": f"Bearer {ELSPY_API_KEY}"}
    try:
        response = requests.get("https://api.ai6700.com/api/v1/skills/balance", headers=headers)
        if response.status_code == 200:
            await update.message.reply_text(f"💰 *Баланс ElSpy AI:*\n`{response.text}`", parse_mode="Markdown")
        else:
            await update.message.reply_text(f"⚠️ Ошибка проверки баланса: {response.text}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка соединения: {e}")

async def handle_admin_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_CHAT_ID: return
    target_id = context.user_data.get("reply_to")
    if not target_id: return
    msg = update.message
    try:
        if msg.video: await context.bot.send_video(chat_id=target_id, video=msg.video.file_id, caption="🎬 *Ваше видео готово!*\n\nСпасибо за заказ в Seedance Studio! 🚀", parse_mode="Markdown")
        elif msg.photo: await context.bot.send_photo(chat_id=target_id, photo=msg.photo[-1].file_id, caption="🖼 *Ваш результат готов!*\n\nСпасибо за заказ в Seedance Studio! 🚀", parse_mode="Markdown")
        await msg.reply_text(f"✅ Отправлено пользователю `{target_id}`", parse_mode="Markdown")
        context.user_data.pop("reply_to", None)
    except Exception as e:
        await msg.reply_text(f"❌ Ошибка: {e}")

# ── ОБРАБОТКА ТЕКСТА (Взаимодействие с AI) ─────────────
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = context.user_data.get("step")

    if step == "waiting_description":
        user_description = update.message.text
        user_data.setdefault(user_id, {"references": []})
        user_data[user_id]["description"] = user_description
        context.user_data["step"] = None
        
        # Отправляем сообщение о загрузке
        loading_msg = await update.message.reply_text("⏳ _Анализирую вашу идею и создаю кинематографичный промпт через AI..._", parse_mode="Markdown")
        
        try:
            # Вызов ElSpy AI для улучшения промпта
            response = await ai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are a professional prompt engineer for AI video generation tools like Runway, Midjourney, Sora. User will send a short idea. Reply ONLY with a highly detailed, descriptive, cinematic English prompt. Add camera angles, lighting, style, and atmosphere."},
                    {"role": "user", "content": f"Улучши эту идею для генерации видео: {user_description}"}
                ]
            )
            ai_prompt = response.choices[0].message.content.strip()
            
            await loading_msg.delete()
            await ask_prompt(update, context, ai_prompt=ai_prompt)
            
        except Exception as e:
            logger.error(f"ElSpy AI Error: {e}")
            await loading_msg.delete()
            # Если ошибка - просто переходим к ручному вводу
            await ask_prompt(update, context, ai_prompt="[Ошибка генерации. Введите вручную]")

    elif step == "waiting_prompt":
        user_data.setdefault(user_id, {"references": []})
        user_data[user_id]["prompt"] = update.message.text
        context.user_data["step"] = None
        await ask_references(update, context, is_callback=False)
        
    elif step == "waiting_refs":
        await update.message.reply_text("📎 Отправьте фото или видео файл.\nКогда загрузите все — нажмите *«Готово»*.", parse_mode="Markdown")
    else:
        await start(update, context)

# ── ОБРАБОТКА МЕДИА ───────────────────────────────────
async def handle_media(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id == ADMIN_CHAT_ID and context.user_data.get("reply_to"):
        await handle_admin_media(update, context)
        return
    step = context.user_data.get("step")
    if step != "waiting_refs": return

    user_data.setdefault(user_id, {"references": []})
    refs = user_data[user_id].setdefault("references",[])
    msg = update.message
    if msg.photo: refs.append({"type": "photo", "file_id": msg.photo[-1].file_id})
    elif msg.video: refs.append({"type": "video", "file_id": msg.video.file_id})

    count = len(refs)
    keyboard = [[InlineKeyboardButton("✅ Готово — референсы загружены", callback_data="refs_done")]]
    await update.message.reply_text(f"✅ Референс #{count} добавлен!\nДобавьте ещё или нажмите *«Готово»*.", parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

# ── ОБРАБОТКА КНОПОК ──────────────────────────────────
async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data == "start_create":
        await start_create(update, context)
    
    # Использование сгенерированного AI промпта
    elif data == "use_ai_prompt":
        user_data.setdefault(user_id, {"references": []})
        user_data[user_id]["prompt"] = context.user_data.get("temp_ai_prompt", "AI Prompt Error")
        context.user_data["step"] = None
        await ask_references(update, context, is_callback=True)
        
    elif data == "skip_prompt":
        user_data.setdefault(user_id, {"references":[]})
        user_data[user_id]["prompt"] = "не указан"
        context.user_data["step"] = None
        await ask_references(update, context, is_callback=True)
        
    elif data == "refs_done": await ask_model(update, context, is_callback=True)
    elif data == "model_fast": user_data[user_id]["model"] = "⚡ Быстрый"; await ask_orientation(update, context)
    elif data == "model_2": user_data[user_id]["model"] = "🎯 Качество"; await ask_orientation(update, context)
    elif data == "model_15": user_data[user_id]["model"] = "🎵 Аудио/Видео"; await ask_orientation(update, context)
    elif data == "orient_auto": user_data[user_id]["orientation"] = "🔲 Авто"; await ask_duration(update, context)
    elif data == "orient_16_9": user_data[user_id]["orientation"] = "🖥 16:9"; await ask_duration(update, context)
    elif data == "orient_9_16": user_data[user_id]["orientation"] = "📱 9:16"; await ask_duration(update, context)
    elif data == "orient_4_3": user_data[user_id]["orientation"] = "📺 4:3"; await ask_duration(update, context)
    elif data == "orient_3_4": user_data[user_id]["orientation"] = "📋 3:4"; await ask_duration(update, context)
    elif data == "dur_5s": user_data[user_id]["duration"] = "5 сек"; await send_order_to_admin(update, context)
    elif data == "dur_10s": user_data[user_id]["duration"] = "10 сек"; await send_order_to_admin(update, context)
    elif data == "dur_15s": user_data[user_id]["duration"] = "15 сек"; await send_order_to_admin(update, context)

# ── ЗАПУСК ────────────────────────────────────────────
def main():
    # Запуск фонового сервера для Render
    threading.Thread(target=run_health_server, daemon=True).start()
    
    # Подготовка ElSpy (скачивание документации)
    init_elspy_capabilities()
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("send", cmd_send))
    app.add_handler(CommandHandler("balance", cmd_balance)) # Команда проверки баланса
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.PHOTO | filters.VIDEO, handle_media))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🤖 Бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
