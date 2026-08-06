import telebot
import os

TOKEN = os.environ.get('BOT_TOKEN')  # токен будем брать из переменной окружения, а не хранить в коде
bot = telebot.TeleBot(TOKEN)

bot.remove_webhook()

@bot.message_handler(commands=['start'])
def start(message):
    bot.reply_to(message, "Привет! Я бот.")

@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, f"Ты написал: {message.text}")

bot.infinity_polling()