from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import config
import sqlite3

bot = TeleBot(config.TOKEN)
#عضویت اجباری
join_kb = InlineKeyboardMarkup()
join_kb.add(InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{config.CHANNEL.replace('@', '')}"))
join_kb.add(InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership"))

def is_member(user_id):
    try:
        member = bot.get_chat_member(config.CHANNEL, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False
    

btn1 = "محصولات🛍"
btn2 = "ثبت سفارش🛒"
btn3 = "پشتیبانی 👤"
btn4 = "سوالات متداول"
btn5 = "پنل ادمین💻"
btn6 = "معرفی به دوستان🎭"
btn7 = "سفارش های من💎"

WELCOME_MESSAGE = """
    سلام به ربات خدمات مجازی ONYX خوش اومدید🎉
از دکمه های زیر استفاده کنید🤍
    """

main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton(btn1),KeyboardButton(btn2))
main_kb.add(KeyboardButton(btn4))
main_kb.add(KeyboardButton(btn7),KeyboardButton(btn6))
main_kb.add(KeyboardButton(btn3),KeyboardButton(btn5))

@bot.message_handler(commands=['start'])
def welcome(message):
    if not is_member(message.from_user.id):
        bot.send_message(message.chat.id,
            "سلام! برای استفاده از ربات اول عضو کانال شو 👇",
            reply_markup=join_kb)
        return

    bot.send_message(message.chat.id, WELCOME_MESSAGE, reply_markup=main_kb)

#عضویت اجباری
@bot.callback_query_handler(func=lambda call: call.data == "check_membership")
def check_membership(call):
    if is_member(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ عضویت تایید شد!")
        bot.edit_message_text("✅ عضویت تایید شد!", call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, WELCOME_MESSAGE, reply_markup=main_kb)
    else:
        bot.answer_callback_query(call.id, "هنوز عضو نشدی! اول عضو کانال شو 😅", show_alert=True)

bot.infinity_polling()