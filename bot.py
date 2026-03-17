import os
import requests
import json
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

load_dotenv()

TELEGRAM_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
API_KEY = os.getenv('API_KEY')
API_BASE = 'https://api.ai6700.com/api'

headers = {'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        'Привет! Я бот с AI.\n\n'
        '/text <промпт> - генерировать текст\n'
        '/image <описание> - генерировать изображение\n'
        '/models - список моделей\n'
        '/balance - баланс'
    )

async def get_models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(f'{API_BASE}/v1/skills', headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            text = json.dumps(data, indent=2, ensure_ascii=False)[:1000]
            await update.message.reply_text(f'Модели:\n{text}')
        else:
            await update.message.reply_text(f'Ошибка: {response.status_code}')
    except Exception as e:
        await update.message.reply_text(f'Ошибка: {str(e)}')

async def check_balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        response = requests.get(f'{API_BASE}/v1/skills/balance', headers=headers, timeout=10)
        if response.status_code == 200:
            data = response.json()
            await update.message.reply_text(f'Баланс: {json.dumps(data, ensure_ascii=False)}')
        else:
            await update.message.reply_text(f'Ошибка: {response.status_code}')
    except Exception as e:
        await update.message.reply_text(f'Ошибка: {str(e)}')

async def generate_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('Использование: /text <промпт>')
        return
    
    prompt = ' '.join(context.args)
    await update.message.reply_text('⏳ Генерирую текст...')
    
    try:
        payload = {
            'model': 
