import telebot
import os
import logging
from flask import Flask, request

TOKEN = os.environ.get('BOT_TOKEN', '').strip()
WEBHOOK_URL = os.environ.get('RENDER_EXTERNAL_URL')

print(f"TOKEN задан: {bool(TOKEN)}")
print(f"WEBHOOK_URL: {WEBHOOK_URL}")

bot = telebot.TeleBot(TOKEN, threaded=False)
app = Flask(__name__)

GROUP_CHAT_ID = -5363411318

forwarding = {}

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Привет! Я бот на вебхуке.")

@bot.message_handler(commands=['savemymessages'])
def start_forwarding(message):
    chat_id = message.chat.id
    forwarding[chat_id] = True
    bot.reply_to(message, "Окей, теперь пересылаю все твои сообщения в группу. Напиши /stopforwarding, чтобы остановить.")

@bot.message_handler(commands=['stopforwarding'])
def stop_forwarding(message):
    chat_id = message.chat.id
    forwarding[chat_id] = False
    bot.reply_to(message, "Окей, больше не пересылаю сообщения.")

@bot.message_handler(func=lambda message: 'кот на скейте' in message.text.lower())
def kot(message):
    with open('90a9908220459a3e851c2d9db9db28ed.jpg', 'rb') as photo:
        bot.send_photo(message.chat.id, photo)
    bot.send_message(message.chat.id, 'не пиши сюда больше')

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    chat_id = message.chat.id
    print(f"Получено сообщение: {message.text} от {chat_id}")

    if forwarding.get(chat_id):
        user = message.from_user
        username = f"@{user.username}" if user.username else user.first_name
        text_to_group = f"Сообщение от {username} (id: {user.id}):\n{message.text}"
        bot.send_message(GROUP_CHAT_ID, text_to_group)
    else:
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