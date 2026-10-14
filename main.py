from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import config
import sqlite3

bot = TeleBot(config.TOKEN)

btn1 = "محصولات🛍"
btn2 = "ثبت سفارش🛒"
btn3 = "پشتیبانی 👤"
btn4 = "سوالات متداول"
btn5 = "پنل ادمین💻"
btn6 = "معرفی به دوستان🎭"
btn7 = "سفارش های من💎"

main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton(btn1),KeyboardButton(btn2))
main_kb.add(KeyboardButton(btn4))
main_kb.add(KeyboardButton(btn7),KeyboardButton(btn6))
main_kb.add(KeyboardButton(btn3),KeyboardButton(btn5))

@bot.message_handler(commands=['start'])
def welcome(message):
    WELCOME_MESSAGE = """
    سلام به ربات خدمات مجازی ONYX خوش اومدید🎉
از دکمه های زیر استفاده کنید🤍
    """
    first=message.from_user.first_name or ""
    last =message.from_user.last_name or ""
    bot.send_message(message.chat.id,WELCOME_MESSAGE,reply_markup=main_kb)

bot.infinity_polling()