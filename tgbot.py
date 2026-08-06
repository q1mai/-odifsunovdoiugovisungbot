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
    bot.send_message(message.chat.id, "Привет! Я бот на вебхуке.")

@bot.message_handler(func=lambda message: 'ты че кот на скейте' in message.text)
def kot(message):
    bot.send_photo(message.chat_id, 'https://www.meme-arsenal.com/create/chose?tag=%D0%A2%D0%B5%D1%80%D0%BF%D0%B8%D0%BB%D0%B0')
    bot.send_message(message.chat_id, 'не пиши сюда больше')

GROUP_CHAT_ID = -5363411318

@bot.message_handler(commands=['savemymessages'])
def forward_to_group(message):
    chat_id = message.chat.id
    user = message.from_user
    username = f"@{user.username}" if user.username else user.first_name

    text_to_group = f"Сообщение от {username} (id: {user.id}):\n{message.text}"

    bot.send_message(GROUP_CHAT_ID, text_to_group)
    bot.reply_to(message, "Спасибо, твоё сообщение получено!")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    print(f"Получено сообщение: {message.text} от {message.chat.id}")
    bot.reply_to(message, "Ты написал: {message.text}")


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