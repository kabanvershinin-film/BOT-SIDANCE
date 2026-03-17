import logging
import os
import threading
import json
import requests
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, InputMediaVideo
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from openai import AsyncOpenAI

# ── НАСТРОЙКИ И ПЕРЕМЕННЫЕ ОКРУЖЕНИЯ ──────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8450032677:AAFDP6dBe2ZlKRY_u17Uo9crcrc6z7JmxHI") # Ваш токен
ADMIN_CHAT_ID = int(os.environ.get("ADMIN_CHAT_ID", 464450106))
PORT = int(os.environ.get("PORT", 8080))

# Ваш ключ ElSpy AI
ELSPY_API_KEY = os.environ.get("ELSPY_API_KEY", "sk-7660a13fbd6fe78c87706c3fcb4191bf2bd6fe9547222ecd")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

user_data = {}

# Клиент для генерации текста (улучшение промптов)
ai_client = AsyncOpenAI(
    api_key=ELSPY_API_KEY,
    base_url="https://api.ai6700.com/api/v1"
)

# ── ELSYP AI: ОБЯЗАТЕЛЬНЫЕ ШАГИ ИЗ ИНСТРУКЦИИ (ШАГ 1, 2, 3) ──
def init_elspy_capabilities():
    """Синхронизация возможностей платформы при запуске согласно Skill-документу"""
    logger.info("Выполняю обязательную синхронизацию с ElSpy AI...")
    headers = {"Authorization": f"Bearer {ELSPY_API_KEY}"}
    try:
        # Шаг 1: Получаем Skills
        skills_res = requests.get("https://api.ai6700.com/api/v1/skills", headers=headers)
        # Шаг 2: Получаем Guide
        guide_res = requests.get("https://api.ai6700.com/api/v1/skills/guide", headers=headers)
        
        # Шаг 3: Сохраняем в API_CAPABILITIES.md
        if skills_res.status_code == 200:
            with open("API_CAPABILITIES.md", "w", encoding="utf-8") as f:
                f.write("# Доступные модели ElSpy AI\n\n")
                f.write("## 1. Skills (Возможности)\n" + json.dumps(skills_res.json(), indent=2, ensure_ascii=False) + "\n\n")
                if guide_res.status_code == 200:
                    f.write("## 2. Guide (Руководство)\n" + json.dumps(guide_res.json(), indent=2, ensure_ascii=False))
            logger.info("✅ Файл API_CAPABILITIES.md успешно создан/обновлен!")
        else:
            logger.error("❌ Ошибка получения Skills от ElSpy AI.")
    except Exception as e:
        logger.error(f"Ошибка синхронизации ElSpy AI: {e}")

# ── KEEP-ALIVE (ДЛЯ RENDER) ───────────────────────────
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args): pass

def run_health_server():
    HTTPServer(("0.0.0.0", PORT), HealthHandler).serve_forever()

# ── КОМАНДЫ АДМИНИСТРАТОРА (ИЗ ИНСТРУКЦИИ ELSYP) ───────
async def cmd_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Проверка баланса перед платными запросами"""
    if update.effective_user.id != ADMIN_CHAT_ID: return
    headers = {"Authorization": f"Bearer {ELSPY_API_KEY}"}
    try:
        response = requests.get("https://api.ai6700.com/api/v1/skills/balance", headers=headers)
        await update.message.reply_text(f"💰 *Баланс ElSpy AI:*\n`{response.text}`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def cmd_docs(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Скачать файл API_CAPABILITIES.md, который сгенерировал бот"""
    if update.effective_user.id != ADMIN_CHAT_ID: return
    try:
        await update.message.reply_document(document=open("API_CAPABILITIES.md", "rb"), caption="📄 Актуальная документация от ElSpy AI.")
    except FileNotFoundError:
        await update.message.reply_text("Файл еще не скачан с сервера ElSpy AI.")

async def cmd_feedback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отправка баг-репорта в ElSpy AI (Требование инструкции)"""
    if update.effective_user.id != ADMIN_CHAT_ID: return
    
    text = " ".join(context.args)
    if not text:
        await update.message.reply_text("Использование: `/feedback Ваш текст ошибки`", parse_mode="Markdown")
        return

    headers = {"Authorization": f"Bearer {ELSPY_API_KEY}", "Content-Type": "application/json"}
    payload = {"type": "接口报错", "question": text, "endpoint": "API", "context": "Telegram Bot"}
    try:
        res = requests.post("https://api.ai6700.com/api/v1/skills/feedback", headers=headers, json=payload)
        await update.message.reply_text(f"✅ Фидбек отправлен: {res.status_code}\nОтвет: {res.text}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка отправки: {e}")

# ── ГЕНЕРАЦИЯ ВИДЕО ЧЕРЕЗ ELSYP AI ────────────────────
async def process_video_generation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    data = user_data.get(user_id, {})
    
    await query.edit_message_text(
        "⏳ *Ваш заказ отправлен в нейросеть!*\n\nГенерация видео занимает время. Я пришлю результат сюда, как только он будет готов! 🎬",
        parse_mode="Markdown"
    )

    # Запускаем фоновый процесс генерации видео
    asyncio.create_task(generate_and_send_video(user_id, data, context))

async def generate_and_send_video(user_id, data, context):
    headers = {"Authorization": f"Bearer {ELSPY_API_KEY}", "Content-Type": "application/json"}
    
    # ПРИМЕР: Название модели (Вам нужно будет уточнить его в файле /docs)
    model_name = "seedance-2"
    if "Fast" in data.get('model', ''): model_name = "seedance-fast"

    # Формируем запрос
    payload = {
        "model": model_name,
        "prompt": data.get('prompt', 'Cinematic video')
    }

    try:
        # Отправляем задачу на генерацию видео
        # URL нужно сверить с документацией (API_CAPABILITIES.md)
        submit_url = "https://api.ai6700.com/api/v1/video/submit" 
        submit_res = requests.post(submit_url, headers=headers, json=payload)
        
        if submit_res.status_code != 200:
            await context.bot.send_message(user_id, f"❌ Ошибка API ElSpy (Submit): {submit_res.text}")
            return
            
        task_id = submit_res.json().get("task_id")

        if not task_id:
            await context.bot.send_message(user_id, "❌ Не удалось получить ID задачи от API.")
            return

        # Проверяем статус видео (Polling)
        fetch_url = f"https://api.ai6700.com/api/v1/video/status/{task_id}"
        
        video_url = None
        for _ in range(30): # Ждем до 5 минут (30 раз по 10 сек)
            await asyncio.sleep(10)
            status_res = requests.get(fetch_url, headers=headers)
            
            if status_res.status_code == 200:
                result_data = status_res.json()
                status = result_data.get("status")
                
                if status in["success", "completed"]:
                    video_url = result_data.get("video_url")
                    break
                elif status in ["failed", "error"]:
                    await context.bot.send_message(user_id, "❌ Нейросеть выдала ошибку при генерации.")
                    return

        if video_url:
            await context.bot.send_video(
                chat_id=user_id, video=video_url, 
                caption="✨ *Ваше видео готово!*\nСгенерировано через ElSpy AI 🚀", parse_mode="Markdown"
            )
        else:
            await context.bot.send_message(user_id, "⚠️ Время ожидания вышло.")

    except Exception as e:
        await context.bot.send_message(user_id, f"❌ Ошибка сервера: {e}")

# ── ВОРОНКА И КНОПКИ (Упрощенно для примера) ──────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("🎬 Создать видео", callback_data="start_create")]]
    await update.message.reply_text("✨ Добро пожаловать!", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    
    if query.data == "start_create":
        user_data[user_id] = {}
        await query.edit_message_text("✍️ Введите идею для видео:")
        context.user_data["step"] = "waiting_prompt"
        
    elif query.data == "dur_5s": # Если нажата финальная кнопка "5 сек"
        user_data[user_id]["duration"] = "5s"
        await process_video_generation(update, context) # <-- ТУТ ЗАПУСКАЕТСЯ АВТО-ГЕНЕРАЦИЯ ВИДЕО

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    step = context.user_data.get("step")
    
    if step == "waiting_prompt":
        user_data[user_id]["prompt"] = update.message.text
        context.user_data["step"] = None
        
        # Сразу предлагаем сгенерировать
        keyboard = [[InlineKeyboardButton("⚡ Начать генерацию", callback_data="dur_5s")]]
        await update.message.reply_text("✅ Промпт принят. Нажмите кнопку, чтобы запустить нейросеть:", reply_markup=InlineKeyboardMarkup(keyboard))

# ── ЗАПУСК БОТА ───────────────────────────────────────
def main():
    threading.Thread(target=run_health_server, daemon=True).start()
    init_elspy_capabilities() # ВЫПОЛНЕНИЕ ТРЕБОВАНИЯ ДОКУМЕНТАЦИИ ПРИ ЗАПУСКЕ
    
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", cmd_balance))
    app.add_handler(CommandHandler("docs", cmd_docs))
    app.add_handler(CommandHandler("feedback", cmd_feedback))
    app.add_handler(CallbackQueryHandler(handle_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🤖 Бот запущен и синхронизирован с ElSpy AI!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
