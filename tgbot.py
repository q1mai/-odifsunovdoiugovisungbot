import telebot
import os
import logging
from flask import Flask, request

TOKEN = os.environ.get('BOT_TOKEN', '').strip()
WEBHOOK_URL = os.environ.get('RENDER_EXTERNAL_URL')

print(f"TOKEN задан: {bool(TOKEN)}")
print(f"WEBHOOK_URL: {WEBHOOK_URL}")

# threaded=False — обрабатываем синхронно, чтобы видеть ошибки сразу
bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

@bot.message_handler(commands=['start'])
def start(message):
    print(f"Получена команда /start от {message.chat.id}")
    bot.reply_to(message, "Привет! Я бот на вебхуке.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    print(f"Получено сообщение: {message.text} от {message.chat.id}")
    bot.reply_to(message, f"Ты написал: {message.text}")

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    try:
        json_str = request.get_data().decode('UTF-8')
        update = telebot.types.Update.de_json(json_str)
        bot.process_new_updates([update])
    except Exception as e:
        print(f"ОШИБКА при обработке апдейта: {e}")
        import traceback
        traceback.print_exc()
    return '', 200

@app.route('/', methods=['GET'])
def index():
    return 'Bot is running', 200

print("Пробую установить вебхук...")
try:
    result1 = bot.remove_webhook()
    print(f"remove_webhook результат: {result1}")
    full_url = f"{WEBHOOK_URL}/{TOKEN}"
    print(f"Устанавливаю webhook на: {full_url}")
    result2 = bot.set_webhook(url=full_url)
    print(f"set_webhook результат: {result2}")
except Exception as e:
    print(f"ОШИБКА при установке вебхука: {e}")
print("Блок установки вебхука завершён")