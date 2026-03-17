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
            'model': 'gpt-4',
            'messages': [{'role': 'user', 'content': prompt}],
            'max_tokens': 500
        }
        
        response = requests.post(
            f'{API_BASE}/v1/chat/completions',
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            text = data.get('choices', [{}])[0].get('message', {}).get('content', 'Нет ответа')
            await update.message.reply_text(f'✅ Результат:\n\n{text}')
        else:
            await update.message.reply_text(f'Ошибка API: {response.status_code}')
    except Exception as e:
        await update.message.reply_text(f'Ошибка: {str(e)}')

async def generate_image(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text('Использование: /image <описание>')
        return
    
    prompt = ' '.join(context.args)
    await update.message.reply_text('⏳ Генерирую изображение...')
    
    try:
        payload = {
            'model': 'dall-e-3',
            'prompt': prompt,
            'n': 1,
            'size': '1024x1024'
        }
        
        response = requests.post(
            f'{API_BASE}/v1/images/generations',
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code == 200:
            data = response.json()
            image_url = data.get('data', [{}])[0].get('url', '')
            if image_url:
                await update.message.reply_photo(photo=image_url, caption='✅ Готово!')
            else:
                await update.message.reply_text('Ошибка: нет URL изображения')
        else:
            await update.message.reply_text(f'Ошибка API: {response.status_code}')
    except Exception as e:
        await update.message.reply_text(f'Ошибка: {str(e)}')

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('models', get_models))
    app.add_handler(CommandHandler('balance', check_balance))
    app.add_handler(CommandHandler('text', generate_text))
    app.add_handler(CommandHandler('image', generate_image))
    
    logger.info('Бот запущен...')
    app.run_polling()

if __name__ == '__main__':
    main()
