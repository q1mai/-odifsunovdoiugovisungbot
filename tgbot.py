import telebot
import os
from flask import Flask, request

TOKEN = os.environ.get('BOT_TOKEN')
# Render сам подставит домен твоего сервиса в переменную RENDER_EXTERNAL_URL
WEBHOOK_URL = os.environ.get('RENDER_EXTERNAL_URL')

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# --- Логика бота ---

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я бот на вебхуке.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Ты написал: {message.text}")

# --- Приём запросов от Telegram ---

@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return '', 200

# Простой роут для проверки, что сервис вообще жив
@app.route('/', methods=['GET'])
def index():
    return 'Bot is running', 200

# --- Установка вебхука при старте ---

bot.remove_webhook()
bot.set_webhook(url=f"{WEBHOOK_URL}/{TOKEN}")

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)