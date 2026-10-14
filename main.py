from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from functools import wraps
from datetime import datetime
import time
import sqlite3
import config

bot = TeleBot(config.TOKEN)
DB_NAME = "onyx.db"
SUPPORT_MODE = set()          # کاربرهایی که تو حالت گفتگو با پشتیبانی‌ان
pending_broadcast = None      # متن پیام همگانی در انتظار تایید
BOT_USERNAME = None

# ==================== دیتابیس ====================

def db():
    return sqlite3.connect(DB_NAME)

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

def init_db():
    con = db(); cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY, name TEXT, username TEXT,
        referrer_id INTEGER, joined_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS orders(
        order_id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER,
        product_name TEXT, details TEXT, price TEXT, status TEXT, created_at TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS faq(
        id INTEGER PRIMARY KEY AUTOINCREMENT, question TEXT, answer TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS products(
        key TEXT PRIMARY KEY, name TEXT, price TEXT,
        description TEXT, extra TEXT, available INTEGER DEFAULT 1)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS support(
        user_id INTEGER PRIMARY KEY, name TEXT, username TEXT, last_time TEXT)""")
    if not cur.execute("SELECT 1 FROM products LIMIT 1").fetchone():
        cur.executemany("INSERT INTO products VALUES(?,?,?,?,?,1)", DEFAULT_PRODUCTS)
    con.commit(); con.close()

DEFAULT_PRODUCTS = [
    ("stars",        "⭐️ استارز تلگرام",                        "دونه‌ای ۴,۵۰۰ تومان", "", "تعداد استارز|یوزرنیم چنل یا پست"),
    ("gift",         "🎁 گیفت تلگرام",                          "-", "", "نوع گیفت|تعداد"),
    ("design_ch",    "🎨 چنل‌های دیزاینی",                      "-", "", "تعداد چنل"),
    ("design_cust",  "🎨 چنل‌های دیزاینی (به سلیقه خودتون)",     "-", "", "سلیقه یا موضوع دلخواه|تعداد چنل"),
    ("scam_design",  "🖥 چنل‌های اسکم دیزاینی",                 "-", "", "تعداد چنل"),
    ("fake_mem",     "👌 ممبر فیک",                             "-", "", "لینک چنل|تعداد ممبر"),
    ("post_view",    "👁 ویو پست",                              "-", "", "لینک پست|تعداد ویو"),
    ("story_view",   "👁 ویو استوری",                           "-", "", "یوزرنیم یا لینک|تعداد ویو"),
    ("story_like",   "❤️ لایک استوری",                          "-", "", "یوزرنیم|تعداد لایک"),
    ("boost",        "🚀 بوست تلگرام",                          "-", "", "لینک چنل|مدت بوست"),
    ("prem_react",   "❤️ ری‌اکشن پرمیوم",                       "-", "", "لینک پست|تعداد ری‌اکشن"),
    ("star_react",   "⭐️ ری‌اکشن استارزی روی پست",              "-", "", "لینک پست|تعداد ری‌اکشن"),
    ("scam_acc",     "🥶 اکانت های اسکم",                       "-", "", "تعداد اکانت"),
    ("sell_ch",      "❄️ فروش چنل های تلگرام (ممبر واقعی)",     "-", "", "موضوع مورد نظر"),
    ("tonkeeper",    "💠 انتقال ارز به تون‌کیپر",               "-", "", "مقدار ارز|آدرس والت"),
    ("tutorial",     "📚 آموزش ساخت چنل‌های دیزاینی",           "-", "", ""),
    ("virtual_num",  "📱 شماره مجازی",                          "-", "", "کشور مورد نظر"),
]

# ---------- توابع دیتابیس ----------

def save_user(uid, first, username, referrer=None):
    con = db(); cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO users VALUES(?,?,?,?,?)",
                (uid, first, username, referrer, now()))
    is_new = cur.rowcount > 0
    con.commit(); con.close()
    return is_new

def count(sql, *args):
    con = db(); r = con.execute(sql, args).fetchone()[0]; con.close(); return r

def get_product(key):
    con = db(); r = con.execute("SELECT * FROM products WHERE key=?", (key,)).fetchone(); con.close(); return r

def all_products():
    con = db(); r = con.execute("SELECT key, name, price, available FROM products").fetchall(); con.close(); return r

def save_product(key, name, price, desc, extra):
    con = db()
    con.execute("INSERT OR REPLACE INTO products VALUES(?,?,?,?,?,1)", (key, name, price, desc, extra))
    con.commit(); con.close()

def toggle_product(key):
    con = db(); con.execute("UPDATE products SET available = 1 - available WHERE key=?", (key,)); con.commit(); con.close()

def delete_product(key):
    con = db(); con.execute("DELETE FROM products WHERE key=?", (key,)); con.commit(); con.close()

def set_price(key, price):
    con = db(); con.execute("UPDATE products SET price=? WHERE key=?", (price, key)); con.commit(); con.close()

def add_order(uid, pname, details, price):
    con = db(); cur = con.cursor()
    cur.execute("INSERT INTO orders(user_id, product_name, details, price, status, created_at) VALUES(?,?,?,?,?,?)",
                (uid, pname, details, price, "⏳ در انتظار بررسی", now()))
    oid = cur.lastrowid
    con.commit(); con.close(); return oid

def get_order(oid):
    con = db(); r = con.execute("SELECT * FROM orders WHERE order_id=?", (oid,)).fetchone(); con.close(); return r

def user_orders(uid):
    con = db(); r = con.execute("""SELECT order_id, product_name, status, created_at
        FROM orders WHERE user_id=? ORDER BY order_id DESC""", (uid,)).fetchall(); con.close(); return r

def update_order_status(oid, status):
    con = db(); con.execute("UPDATE orders SET status=? WHERE order_id=?", (status, oid)); con.commit(); con.close()

def all_user_ids():
    con = db(); r = con.execute("SELECT user_id FROM users").fetchall(); con.close(); return [x[0] for x in r]

def save_faq(q, a):
    con = db(); con.execute("INSERT INTO faq(question, answer) VALUES(?,?)", (q, a)); con.commit(); con.close()

def all_faq():
    con = db(); r = con.execute("SELECT id, question FROM faq").fetchall(); con.close(); return r

def get_faq(fid):
    con = db(); r = con.execute("SELECT question, answer FROM faq WHERE id=?", (fid,)).fetchone(); con.close(); return r

def del_faq(fid):
    con = db(); con.execute("DELETE FROM faq WHERE id=?", (fid,)); con.commit(); con.close()

def touch_support(uid, name, username):
    con = db(); con.execute("INSERT OR REPLACE INTO support VALUES(?,?,?,?)", (uid, name, username, now()))
    con.commit(); con.close()

def recent_supports():
    con = db(); r = con.execute("""SELECT user_id, name, username, last_time FROM support
        ORDER BY last_time DESC LIMIT 10""").fetchall(); con.close(); return r

def invited_list(uid):
    con = db(); r = con.execute("SELECT name FROM users WHERE referrer_id=?", (uid,)).fetchall(); con.close(); return r

# ==================== عضویت اجباری ====================

join_kb = InlineKeyboardMarkup()
join_kb.add(InlineKeyboardButton("📢 عضویت در کانال", url=f"https://t.me/{config.CHANNEL.replace('@', '')}"))
join_kb.add(InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership"))

def is_member(user_id):
    try:
        m = bot.get_chat_member(config.CHANNEL, user_id)
        return m.status in ["member", "administrator", "creator", "restricted"]
    except Exception:
        return False

def membership_required(func):
    @wraps(func)
    def wrapper(message):
        if not is_member(message.from_user.id):
            bot.send_message(message.chat.id, "⚠️ برای استفاده از ربات باید عضو کانال بشی 👇", reply_markup=join_kb)
            return
        return func(message)
    return wrapper

# ==================== منوی اصلی ====================

btn1 = "محصولات🛍"
btn2 = "ثبت سفارش🛒"
btn3 = "پشتیبانی 👤"
btn4 = "سوالات متداول"
btn5 = "پنل ادمین💻"
btn6 = "معرفی به دوستان🎭"
btn7 = "سفارش های من💎"
SUPPORT_EXIT = "🔙 خروج از پشتیبانی"
MENU_TEXTS = {btn1, btn2, btn3, btn4, btn5, btn6, btn7, SUPPORT_EXIT}

WELCOME = """✨ به ربات خدمات مجازی ONYX خوش اومدید 🎉
از دکمه‌های زیر استفاده کنید 🤍"""

main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton(btn1), KeyboardButton(btn2))
main_kb.add(KeyboardButton(btn4))
main_kb.add(KeyboardButton(btn7), KeyboardButton(btn6))
main_kb.add(KeyboardButton(btn3), KeyboardButton(btn5))

support_kb = ReplyKeyboardMarkup(resize_keyboard=True)
support_kb.add(KeyboardButton(SUPPORT_EXIT))

def get_bot_username():
    global BOT_USERNAME
    if not BOT_USERNAME:
        BOT_USERNAME = bot.get_me().username
    return BOT_USERNAME

def is_cancel(message):
    if message.text:
        return message.text.startswith("/") or message.text in MENU_TEXTS
    return False
def cancel_action(message):
    SUPPORT_MODE.discard(message.chat.id)
    bot.send_message(message.chat.id, "❌ عملیات لغو شد.", reply_markup=main_kb)

def reask(chat_id, text, callback, *args):
    msg = bot.send_message(chat_id, text)
    bot.register_next_step_handler(msg, callback, *args)

# ==================== /start ====================

@bot.message_handler(commands=['start'])
def welcome(message):
    SUPPORT_MODE.discard(message.chat.id)
    referrer = None
    parts = message.text.split()
    if len(parts) > 1 and parts[1].isdigit():
        if int(parts[1]) != message.from_user.id:
            referrer = int(parts[1])
    is_new = save_user(message.from_user.id, message.from_user.first_name,
                       f"@{message.from_user.username}" if message.from_user.username else None, referrer)
    if not is_member(message.from_user.id):
        bot.send_message(message.chat.id, "سلام! برای استفاده از ربات اول عضو کانال شو 👇", reply_markup=join_kb)
        return
    txt = WELCOME
    if is_new and referrer:
        inviter = None
        con = db(); r = con.execute("SELECT name FROM users WHERE user_id=?", (referrer,)).fetchone(); con.close()
        if r: inviter = r[0]
        if inviter:
            txt += f"\n\n🎉 تو با لینک دعوت {inviter} اومدی — خوش اومدی!"
    bot.send_message(message.chat.id, txt, reply_markup=main_kb)



@bot.callback_query_handler(func=lambda c: c.data == "check_membership")
def check_membership(call):
    if is_member(call.from_user.id):
        bot.answer_callback_query(call.id, "✅ عضویت تایید شد!")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, WELCOME, reply_markup=main_kb)
    else:
        bot.answer_callback_query(call.id, "هنوز عضو نشدی! اول عضو کانال شو 😅", show_alert=True)
# ==================== حالت پشتیبانی (کاربر → ادمین) ====================

@bot.message_handler(func=lambda m: m.chat.id in SUPPORT_MODE,
                     content_types=['text', 'photo', 'video', 'voice', 'audio', 'document', 'sticker'])
def support_chat(message):
    if message.text and (message.text == SUPPORT_EXIT or message.text.startswith("/")
                         or message.text in MENU_TEXTS):
        SUPPORT_MODE.discard(message.chat.id)
        bot.send_message(message.chat.id, "🔙 از گفتگو با پشتیبانی خارج شدی.", reply_markup=main_kb)
        return
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✍️ پاسخ", callback_data=f"reply:{message.from_user.id}"))
    try:
        bot.copy_message(config.ADMIN_ID, message.chat.id, message.message_id, reply_markup=kb)
        touch_support(message.from_user.id, message.from_user.first_name,
                      f"@{message.from_user.username}" if message.from_user.username else None)
    except Exception:
        pass

# ==================== محصولات ====================

def products_kb():
    rows = all_products()
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(*[InlineKeyboardButton(name, callback_data=f"prod:{key}") for key, name, p, a in rows])
    kb.add(InlineKeyboardButton("🔙 منوی اصلی", callback_data="backmenu"))
    return kb

def show_products(chat_id, text):
    bot.send_message(chat_id, text, reply_markup=products_kb())

@bot.message_handler(func=lambda m: m.text == btn1)
@membership_required
def products_handler(message):
    show_products(message.chat.id, "🛍 محصولات ربات ONYX\nیکی رو انتخاب کن 👇")

@bot.message_handler(func=lambda m: m.text == btn2)
@membership_required
def order_handler(message):
    show_products(message.chat.id, "🛒 برای ثبت سفارش، محصولت رو انتخاب کن 👇")

@bot.callback_query_handler(func=lambda c: c.data == "backprod")
def back_products(call):
    try:
        bot.edit_message_text("🛍 محصولات ربات ONYX\nیکی رو انتخاب کن 👇",
                              call.message.chat.id, call.message.message_id, reply_markup=products_kb())
    except Exception:
        pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "backmenu")
def back_menu(call):
    try:
        bot.edit_message_text("🤍 از دکمه‌های زیر منو استفاده کن:",
                              call.message.chat.id, call.message.message_id)
    except Exception:
        pass
    bot.send_message(call.message.chat.id, "🏠 منوی اصلی:", reply_markup=main_kb)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("prod:"))
def show_product(call):
    key = call.data.split(":", 1)[1]
    row = get_product(key)
    if not row:
        bot.answer_callback_query(call.id, "⚠️ این محصول حذف شده!")
        return
    _, name, price, desc, extra, avail = row
    kb = InlineKeyboardMarkup()
    if avail:
        price_txt = price if price and price != "-" else "برای اطلاع از قیمت به پشتیبانی پیام بده 💬"
        txt = f"{name}\n━━━━━━━━━━\n💰 قیمت: {price_txt}\n"
        if desc and desc != "-":
            txt += f"📝 توضیحات: {desc}\n"
        if extra and extra != "-":
            txt += f"📋 موارد موردنیاز: {'، '.join(extra.split('|'))}\n"
        kb.add(InlineKeyboardButton("🛒 ثبت سفارش و پرداخت", callback_data=f"pay:{key}"))
    else:
        txt = f"{name}\n\n❌ فعلاً موجود نیست!\nبه‌زودی دوباره در دسترس قرار می‌گیره 🙏"
    kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="backprod"))
    try:
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        pass
    bot.answer_callback_query(call.id)

# ==================== فاکتور و فرم سفارش ====================

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay:"))
def pay_page(call):
    key = call.data.split(":", 1)[1]
    row = get_product(key)
    if not row:
        bot.answer_callback_query(call.id, "⚠️ این محصول حذف شده!")
        return
    _, name, price, desc, extra, avail = row
    price_txt = price if price and price != "-" else "توافقی — به پشتیبانی پیام بده"
    txt = f"""💳 روش پرداخت
━━━━━━━━━━
📦 محصول: {name}
💰 مبلغ: {price_txt}
━━━━━━━━━━
روش پرداخت رو انتخاب کن 👇"""
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 پرداخت کارت به کارت", callback_data=f"card:{key}"))
    kb.add(InlineKeyboardButton("🏦 پرداخت از درگاه (به‌زودی)", callback_data="soon"))
    kb.add(InlineKeyboardButton("₿ پرداخت با ارز دیجیتال (به‌زودی)", callback_data="soon"))
    kb.add(InlineKeyboardButton("🅿️ پرداخت با PayPal (به‌زودی)", callback_data="soon"))
    kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data=f"prod:{key}"))
    try:
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "soon")
def pay_soon(call):
    bot.answer_callback_query(call.id, "🚧 این روش پرداخت به‌زودی فعاله!", show_alert=True)

    
@bot.callback_query_handler(func=lambda c: c.data.startswith("card:"))
def card_page(call):
    key = call.data.split(":", 1)[1]
    row = get_product(key)
    if not row:
        bot.answer_callback_query(call.id, "⚠️ این محصول حذف شده!")
        return
    _, name, price, desc, extra, avail = row
    price_txt = price if price and price != "-" else "توافقی — به پشتیبانی پیام بده"
    txt = f"""🧾 فاکتور سفارش
━━━━━━━━━━
📦 محصول: {name}
💰 مبلغ: {price_txt}
━━━━━━━━━━
💳 شماره کارت:
{config.CARD_NUMBER}
👤 به نام: {config.CARD_OWNER}
━━━━━━━━━━
✅ بعد از واریز، دکمه زیر رو بزن و فیش رو بفرست"""
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ واریز کردم — ارسال فیش", callback_data=f"receipt:{key}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت به روش پرداخت", callback_data=f"pay:{key}"))
    try:
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("receipt:"))
def receipt_start(call):
    key = call.data.split(":", 1)[1]
    bot.answer_callback_query(call.id)
    msg = bot.send_message(call.message.chat.id,
        "📝 (۱) نام و نام خانوادگی خودت رو بفرست:\n\n❌ برای لغو، یه دکمه منو بزن یا /cancel")
    bot.register_next_step_handler(msg, form_name, key, {})

def form_name(message, key, data):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(message.chat.id, "⚠️ لطفاً متنی بفرست:\n\n📝 (۱) نام و نام خانوادگی:", form_name, key, data)
    data["name"] = message.text
    ask_extra(message.chat.id, key, data, 0)

def extra_fields(key):
    row = get_product(key)
    if not row or not row[4] or row[4] == "-":
        return []
    return [f.strip() for f in row[4].split("|") if f.strip()]

def ask_extra(chat_id, key, data, idx):
    fields = extra_fields(key)
    if idx >= len(fields):
        return reask(chat_id, "📎 مرحله آخر! عکس فیش واریز رو بفرست:", form_receipt, key, data)
    msg = bot.send_message(chat_id, f"📝 ({idx+2}) «{fields[idx]}» رو بنویس:")
    bot.register_next_step_handler(msg, form_extra, key, data, idx)

def form_extra(message, key, data, idx):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(message.chat.id, "⚠️ لطفاً متنی بفرست:", form_extra, key, data, idx)
    data.setdefault("extra", {})[extra_fields(key)[idx]] = message.text
    ask_extra(message.chat.id, key, data, idx + 1)

def form_receipt(message, key, data):
    if is_cancel(message): return cancel_action(message)
    if message.content_type != "photo":
        return reask(message.chat.id, "📎 لطفاً عکس فیش واریز رو بفرست:", form_receipt, key, data)
    finish_order(message, key, data)

def finish_order(message, key, data):
    row = get_product(key)
    if not row:
        return bot.send_message(message.chat.id, "⚠️ این محصول حذف شده!", reply_markup=main_kb)
    _, name, price, *_ = row
    details = f"👤 نام و نام خانوادگی: {data['name']}"
    for f, v in data.get("extra", {}).items():
        details += f"\n▪️ {f}: {v}"
    oid = add_order(message.from_user.id, name, details, price)
    u = message.from_user
    uname = f"@{u.username}" if u.username else "ندارد"
    admin_txt = f"""🛒 سفارش جدید #{oid}
━━━━━━━━━━
📦 محصول: {name}
💰 مبلغ: {price if price != '-' else 'توافقی'}
━━━━━━━━━━
{details}
━━━━━━━━━━
🔗 یوزرنیم: {uname}
🆔 آیدی مشتری: {u.id}"""
    try:
        bot.send_message(config.ADMIN_ID, admin_txt)
        bot.copy_message(config.ADMIN_ID, message.chat.id, message.message_id, caption="📎 فیش واریز مشتری")
    except Exception:
        pass
    bot.send_message(message.chat.id, f"""✅ سفارش #{oid} ثبت شد!
━━━━━━━━━━
📦 محصول: {name}
📍 وضعیت: ⏳ در انتظار بررسی

پشتیبانی بعد از بررسی فیش باهات در تماسه 🤍""", reply_markup=main_kb)

# ==================== سفارش‌های من ====================

@bot.message_handler(func=lambda m: m.text == btn7)
@membership_required
def my_orders(message):
    rows = user_orders(message.from_user.id)
    if not rows:
        return bot.send_message(message.chat.id, "💎 هنوز سفارشی ثبت نکردی!\nاز بخش «ثبت سفارش🛒» شروع کن 👇", reply_markup=main_kb)
    txt = "💎 سفارش‌های تو:\n\n"
    for oid, pname, status, date in rows:
        txt += f"🧾 سفارش #{oid}\n📦 {pname}\n📅 {date}\n📍 وضعیت: {status}\n━━━━━━━━━━\n"
    bot.send_message(message.chat.id, txt, reply_markup=main_kb)

# ==================== سوالات متداول (کاربر) ====================

@bot.message_handler(func=lambda m: m.text == btn4)
@membership_required
def faq_handler(message):
    rows = all_faq()
    if not rows:
        return bot.send_message(message.chat.id, "❓ فعلاً سوالی ثبت نشده!", reply_markup=main_kb)
    kb = InlineKeyboardMarkup(row_width=1)
    kb.add(*[InlineKeyboardButton(f"❓ {q[:40]}", callback_data=f"faq:{fid}") for fid, q in rows])
    kb.add(InlineKeyboardButton("🔙 منوی اصلی", callback_data="backmenu"))
    bot.send_message(message.chat.id, "❓ سوالات متداول\nروی سوالی که داری کلیک کن 👇", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("faq:"))
def faq_show(call):
    fid = int(call.data.split(":")[1])
    row = get_faq(fid)
    if not row:
        bot.answer_callback_query(call.id, "⚠️ این سوال حذف شده!")
        return
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 بازگشت به سوالات", callback_data="faqlist"))
    try:
        bot.edit_message_text(f"❓ سوال:\n{row[0]}\n\n━━━━━━━━━━\n\n💬 جواب:\n{row[1]}",
                              call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "faqlist")
def faq_list_back(call):
    rows = all_faq()
    kb = InlineKeyboardMarkup(row_width=1)
    if rows:
        kb.add(*[InlineKeyboardButton(f"❓ {q[:40]}", callback_data=f"faq:{fid}") for fid, q in rows])
    kb.add(InlineKeyboardButton("🔙 منوی اصلی", callback_data="backmenu"))
    try:
        bot.edit_message_text("❓ سوالات متداول\nروی سوالی که داری کلیک کن 👇",
                              call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        pass
    bot.answer_callback_query(call.id)

# ==================== معرفی به دوستان ====================

@bot.message_handler(func=lambda m: m.text == btn6)
@membership_required
def referral_handler(message):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📊 آمار من", callback_data="ref:stats"))
    kb.add(InlineKeyboardButton("🔗 لینک دعوت", callback_data="ref:link"))
    bot.send_message(message.chat.id,
        "🎭 معرفی به دوستان\nلینک اختصاصی خودت رو به دوستات بده و دعوت‌هات رو ببین 👇", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data == "ref:stats")
def ref_stats(call):
    rows = invited_list(call.from_user.id)
    names = "\n".join(f"👤 {r[0]}" for r in rows[:30]) or "—"
    txt = f"""📊 آمار دعوت‌های تو
━━━━━━━━━━
👥 تعداد دعوت‌شدگان: {len(rows)} نفر
━━━━━━━━━━
{names}"""
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="refback"))
    try:
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "ref:link")
def ref_link(call):
    link = f"https://t.me/{get_bot_username()}?start={call.from_user.id}"
    txt = f"""🔗 لینک دعوت اختصاصی تو:

{link}

━━━━━━━━━━
📤 این لینک رو برای دوستات بفرست!
هرکس با لینک تو استارت بزنه، دعوت‌شده‌ی تو حساب می‌شه 🎯"""
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="refback"))
    try:
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "refback")
def ref_back(call):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("📊 آمار من", callback_data="ref:stats"))
    kb.add(InlineKeyboardButton("🔗 لینک دعوت", callback_data="ref:link"))
    try:
        bot.edit_message_text("🎭 معرفی به دوستان 👇",
                              call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        pass
    bot.answer_callback_query(call.id)

# ==================== پشتیبانی (کاربر) ====================

@bot.message_handler(func=lambda m: m.text == btn3)
@membership_required
def support_handler(message):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✉️ ارتباط با پشتیبانی", callback_data="sup:chat"))
    kb.add(InlineKeyboardButton("👤 آیدی ادمین", callback_data="sup:id"))
    bot.send_message(message.chat.id, "👤 پشتیبانی ONYX\nیکی رو انتخاب کن 👇", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sup:"))
def support_actions(call):
    act = call.data.split(":")[1]
    kb = InlineKeyboardMarkup()
    if act == "chat":
        SUPPORT_MODE.add(call.message.chat.id)
        bot.edit_message_text("""✉️ گفتگو با پشتیبانی
━━━━━━━━━━
هر متنی یا عکسی بفرستی، مستقیم می‌ره به پشتیبانی 💌
برای خروج، دکمه «🔙 خروج از پشتیبانی» رو بزن.""",
            call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "💬 حالا پیامت رو بنویس:", reply_markup=support_kb)
    else:
        kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="supback"))
        txt = f"""👤 ارتباط با ادمین
━━━━━━━━━━
🆔 آیدی عددی: {config.ADMIN_ID}
🔗 آیدی تلگرام: {config.ADMIN_USERNAME}"""
        try:
            bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=kb)
        except Exception:
            pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "supback")
def sup_back(call):
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✉️ ارتباط با پشتیبانی", callback_data="sup:chat"))
    kb.add(InlineKeyboardButton("👤 آیدی ادمین", callback_data="sup:id"))
    try:
        bot.edit_message_text("👤 پشتیبانی ONYX 👇",
                              call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        pass
    bot.answer_callback_query(call.id)

# پاسخ ادمین به کاربر
@bot.callback_query_handler(func=lambda c: c.data.startswith("reply:"))
def admin_reply(call):
    if call.from_user.id != config.ADMIN_ID: return
    uid = int(call.data.split(":")[1])
    bot.answer_callback_query(call.id)
    msg = bot.send_message(config.ADMIN_ID, f"✍️ پاسخ برای مشتری ({uid}) رو بنویس:")
    bot.register_next_step_handler(msg, send_reply, uid)

def send_reply(message, uid):
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ لطفاً متنی بفرست:", send_reply, uid)
    try:
        bot.send_message(uid, f"📩 پیام از پشتیبانی ONYX:\n\n{message.text}")
        bot.send_message(config.ADMIN_ID, "✅ پاسخ ارسال شد.")
    except Exception:
        bot.send_message(config.ADMIN_ID, "❌ ارسال نشد (کاربر ربات رو بلاک کرده).")

# ==================== پنل ادمین ====================

def admin_kb():
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("📊 آمار", callback_data="adm:stats"),
           InlineKeyboardButton("📦 سفارشات", callback_data="adm:orders"))
    kb.add(InlineKeyboardButton("📢 پیام همگانی", callback_data="adm:broadcast"),
           InlineKeyboardButton("❓ سوالات متداول", callback_data="adm:faq"))
    kb.add(InlineKeyboardButton("🛍 مدیریت محصولات", callback_data="adm:products"),
           InlineKeyboardButton("💬 مکالمات", callback_data="adm:support"))
    kb.add(InlineKeyboardButton("🏠 منوی اصلی", callback_data="adm:menu"))
    return kb

@bot.message_handler(func=lambda m: m.text == btn5)
def admin_panel(message):
    if message.from_user.id != config.ADMIN_ID:
        return bot.send_message(message.chat.id, "⛔️ دسترسی نداری!", reply_markup=main_kb)
    bot.send_message(message.chat.id, "💻 پنل مدیریت ONYX\nیکی رو انتخاب کن:", reply_markup=admin_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm:"))
def admin_actions(call):
    if call.from_user.id != config.ADMIN_ID:
        return bot.answer_callback_query(call.id, "⛔️ دسترسی نداری!", show_alert=True)
    act = call.data.split(":")[1]
    chat, mid = call.message.chat.id, call.message.message_id
    bot.answer_callback_query(call.id)

    if act == "menu":
        return bot.send_message(chat, "🏠 منوی اصلی:", reply_markup=main_kb)

    if act == "stats":
        t = datetime.now().strftime("%Y-%m-%d")
        txt = f"""📊 آمار ربات ONYX
━━━━━━━━━━
👥 کل کاربران: {count('SELECT COUNT(*) FROM users')} نفر
🆕 ثبت‌نام امروز: {count("SELECT COUNT(*) FROM users WHERE joined_at LIKE ?", t + '%')} نفر
📦 کل سفارشات: {count('SELECT COUNT(*) FROM orders')}
⏳ در انتظار بررسی: {count("SELECT COUNT(*) FROM orders WHERE status LIKE '⏳%'")}
🛍 محصولات فعال: {count('SELECT COUNT(*) FROM products WHERE available=1')}"""
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 پنل", callback_data="admback"))
        return try_edit(chat, mid, txt, kb)

    if act == "orders":
        rows = None
        con = db(); rows = con.execute("SELECT order_id, product_name, status FROM orders ORDER BY order_id DESC LIMIT 10").fetchall(); con.close()
        kb = InlineKeyboardMarkup(row_width=1)
        if rows:
            kb.add(*[InlineKeyboardButton(f"{status.split()[0]} #{oid} — {pname[:25]}",
                     callback_data=f"admorder:{oid}") for oid, pname, status in rows])
        else:
            kb.add(InlineKeyboardButton("هنوز سفارشی نیست 🍃", callback_data="noop"))
        kb.add(InlineKeyboardButton("🔙 پنل", callback_data="admback"))
        return try_edit(chat, mid, "📦 ۱۰ سفارش اخیر:\nروی سفارش بزن تا جزئیات و تایید/رد ببینی 👇", kb)

    if act == "broadcast":
        msg = bot.send_message(chat, "📢 متن پیام همگانی رو بفرست:\n(برای لغو /cancel)")
        return bot.register_next_step_handler(msg, bc_text)

    if act == "faq":
        return admin_faq_list(call)

    if act == "products":
        return admin_products_list(call)

    if act == "support":
        rows = recent_supports()
        kb = InlineKeyboardMarkup(row_width=1)
        if rows:
            kb.add(*[InlineKeyboardButton(f"👤 {name} — {lt}", callback_data=f"supchat:{uid}")
                     for uid, name, un, lt in rows])
        else:
            kb.add(InlineKeyboardButton("هنوز پیامی نیست 🍃", callback_data="noop"))
        kb.add(InlineKeyboardButton("🔙 پنل", callback_data="admback"))
        return try_edit(chat, mid, "💬 آخرین کاربرهایی که به پشتیبانی پیام دادن:", kb)

@bot.callback_query_handler(func=lambda c: c.data == "admback")
def adm_back(call):
    if call.from_user.id != config.ADMIN_ID: return
    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text("💻 پنل مدیریت ONYX 👇", call.message.chat.id, call.message.message_id, reply_markup=admin_kb())
    except Exception:
        pass

@bot.callback_query_handler(func=lambda c: c.data == "noop")
def noop(call):
    bot.answer_callback_query(call.id)

def try_edit(chat, mid, txt, kb):
    try:
        bot.edit_message_text(txt, chat, mid, reply_markup=kb)
    except Exception:
        pass

# ---------- جزئیات سفارش + تایید/رد ----------

@bot.callback_query_handler(func=lambda c: c.data.startswith("admorder:"))
def admin_order_detail(call):
    if call.from_user.id != config.ADMIN_ID: return
    oid = int(call.data.split(":")[1])
    bot.answer_callback_query(call.id)
    order_detail_view(call.message.chat.id, call.message.message_id, oid)

def order_detail_view(chat, mid, oid):
    row = get_order(oid)
    if not row:
        return try_edit(chat, mid, "⚠️ سفارش پیدا نشد!", None)
    _, uid, pname, details, price, status, created = row
    con = db(); u = con.execute("SELECT name, username FROM users WHERE user_id=?", (uid,)).fetchone(); con.close()
    uname = u[1] if u and u[1] else "ندارد"
    txt = f"""🧾 سفارش #{oid}
━━━━━━━━━━
📦 محصول: {pname}
💰 مبلغ: {price if price != '-' else 'توافقی'}
📅 تاریخ: {created}
📍 وضعیت: {status}
━━━━━━━━━━
{details}
━━━━━━━━━━
👤 مشتری: {u[0] if u else '؟'}
🔗 یوزرنیم: {uname}
🆔 آیدی: {uid}"""
    kb = InlineKeyboardMarkup()
    if status.startswith("⏳"):
        kb.add(InlineKeyboardButton("✅ تایید", callback_data=f"ost:{oid}:ok"),
               InlineKeyboardButton("❌ رد", callback_data=f"ost:{oid}:no"))
    kb.add(InlineKeyboardButton("🔙 سفارشات", callback_data="adm:orders"))
    try_edit(chat, mid, txt, kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ost:"))
def order_status_change(call):
    if call.from_user.id != config.ADMIN_ID: return
    _, oid, s = call.data.split(":")
    new_status = "✅ تایید شد" if s == "ok" else "❌ رد شد"
    oid = int(oid)
    update_order_status(oid, new_status)
    row = get_order(oid)
    try:
        bot.send_message(row[1], f"""📢 وضعیت سفارش #{oid} تغییر کرد!
📦 محصول: {row[2]}
📍 وضعیت جدید: {new_status}""")
    except Exception:
        pass
    bot.answer_callback_query(call.id, "انجام شد ✅")
    order_detail_view(call.message.chat.id, call.message.message_id, oid)

# ---------- پیام همگانی ----------

def bc_text(message):
    global pending_broadcast
    if is_cancel(message): return cancel_action(message)
    pending_broadcast = message.text
    n = count("SELECT COUNT(*) FROM users")
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton(f"🚀 ارسال به {n} نفر", callback_data="bcgo"),
           InlineKeyboardButton("❌ لغو", callback_data="bcno"))
    bot.send_message(config.ADMIN_ID, f"📢 پیش‌نمایش پیام:\n\n{message.text}\n\n👥 گیرندگان: {n} نفر", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data in ("bcgo", "bcno"))
def bc_do(call):
    global pending_broadcast
    if call.from_user.id != config.ADMIN_ID: return
    bot.answer_callback_query(call.id)
    if call.data == "bcno" or not pending_broadcast:
        pending_broadcast = None
        return try_edit(call.message.chat.id, call.message.message_id, "❌ لغو شد.", None)
    text = pending_broadcast; pending_broadcast = None
    try_edit(call.message.chat.id, call.message.message_id, "⏳ در حال ارسال...", None)
    sent = fail = 0
    for uid in all_user_ids():
        try:
            bot.send_message(uid, f"📢 اطلاعیه ONYX\n\n{text}")
            sent += 1
        except Exception:
            fail += 1
        time.sleep(0.06)
    bot.send_message(config.ADMIN_ID, f"✅ ارسال تمام شد!\n📨 موفق: {sent}\n⛔️ ناموفق: {fail}")

# ---------- مدیریت سوالات متداول (ادمین) ----------

def admin_faq_list(call):
    chat, mid = call.message.chat.id, call.message.message_id
    rows = all_faq()
    kb = InlineKeyboardMarkup(row_width=1)
    if rows:
        kb.add(*[InlineKeyboardButton(f"❓ {q[:35]}", callback_data=f"admfaq:{fid}") for fid, q in rows])
    kb.add(InlineKeyboardButton("➕ افزودن سوال", callback_data="addfaq"))
    kb.add(InlineKeyboardButton("🔙 پنل", callback_data="admback"))
    try_edit(chat, mid, "❓ سوالات متداول (مدیریت):", kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("admfaq:"))
def admin_faq_show(call):
    if call.from_user.id != config.ADMIN_ID: return
    fid = int(call.data.split(":")[1])
    row = get_faq(fid)
    if not row:
        bot.answer_callback_query(call.id, "⚠️ حذف شده!"); return
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🗑 حذف", callback_data=f"delfaq:{fid}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="adm:faq"))
    try_edit(call.message.chat.id, call.message.message_id,
             f"❓ سوال:\n{row[0]}\n\n💬 جواب:\n{row[1]}", kb)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delfaq:"))
def admin_faq_del(call):
    if call.from_user.id != config.ADMIN_ID: return
    del_faq(int(call.data.split(":")[1]))
    bot.answer_callback_query(call.id, "حذف شد 🗑")
    admin_faq_list(call)

@bot.callback_query_handler(func=lambda c: c.data == "addfaq")
def admin_faq_add(call):
    if call.from_user.id != config.ADMIN_ID: return
    bot.answer_callback_query(call.id)
    msg = bot.send_message(config.ADMIN_ID, "❓ سوال رو بفرست:")
    bot.register_next_step_handler(msg, faq_q)

def faq_q(message):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:\n\n❓ سوال:", faq_q)
    msg = bot.send_message(config.ADMIN_ID, "💬 جواب رو بفرست:")
    bot.register_next_step_handler(msg, faq_a, message.text)

def faq_a(message, q):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:\n\n💬 جواب:", faq_a, q)
    save_faq(q, message.text)
    bot.send_message(config.ADMIN_ID, "✅ سوال و جواب ذخیره شد!", reply_markup=admin_kb())

# ---------- مدیریت محصولات (ادمین) ----------

def admin_products_list(call):
    chat, mid = call.message.chat.id, call.message.message_id
    rows = all_products()
    kb = InlineKeyboardMarkup(row_width=1)
    if rows:
        kb.add(*[InlineKeyboardButton(f"{'✅' if a else '❌'} {name[:30]}", callback_data=f"admp:{key}")
                 for key, name, p, a in rows])
    kb.add(InlineKeyboardButton("➕ افزودن محصول", callback_data="addp"))
    kb.add(InlineKeyboardButton("🔙 پنل", callback_data="admback"))
    try_edit(chat, mid, "🛍 مدیریت محصولات:\n(✅ موجود | ❌ ناموجود)", kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("admp:"))
def admin_product_show(call):
    if call.from_user.id != config.ADMIN_ID: return
    key = call.data.split(":", 1)[1]
    row = get_product(key)
    if not row:
        bot.answer_callback_query(call.id, "⚠️ حذف شده!"); return
    _, name, price, desc, extra, avail = row
    txt = f"""🛍 {name}
━━━━━━━━━━
💰 قیمت: {price}
📝 توضیحات: {desc if desc != '-' else '—'}
📋 موارد موردنیاز: {extra.replace('|', '، ') if extra != '-' else '—'}
📍 وضعیت: {'✅ موجود' if avail else '❌ ناموجود'}"""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🔄 موجود / ناموجود", callback_data=f"ptoggle:{key}"))
    kb.add(InlineKeyboardButton("✏️ ویرایش قیمت", callback_data=f"pedit:{key}"))
    kb.add(InlineKeyboardButton("🗑 حذف محصول", callback_data=f"pdel:{key}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="adm:products"))
    try_edit(call.message.chat.id, call.message.message_id, txt, kb)
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("ptoggle:"))
def p_toggle(call):
    if call.from_user.id != config.ADMIN_ID: return
    toggle_product(call.data.split(":", 1)[1])
    bot.answer_callback_query(call.id, "تغییر کرد 🔄")
    admin_products_list(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pdel:"))
def p_del(call):
    if call.from_user.id != config.ADMIN_ID: return
    delete_product(call.data.split(":", 1)[1])
    bot.answer_callback_query(call.id, "حذف شد 🗑")
    admin_products_list(call)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pedit:"))
def p_edit(call):
    if call.from_user.id != config.ADMIN_ID: return
    key = call.data.split(":", 1)[1]
    bot.answer_callback_query(call.id)
    msg = bot.send_message(config.ADMIN_ID, "✏️ قیمت جدید رو بفرست (برای توافقی «-»):")
    bot.register_next_step_handler(msg, p_edit_price, key)

def p_edit_price(message, key):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:", p_edit_price, key)
    set_price(key, message.text)
    bot.send_message(config.ADMIN_ID, "✅ قیمت آپدیت شد!", reply_markup=admin_kb())

@bot.callback_query_handler(func=lambda c: c.data == "addp")
def p_add(call):
    if call.from_user.id != config.ADMIN_ID: return
    bot.answer_callback_query(call.id)
    txt = (
        "🛍 <b>افزودن محصول</b>\n"
        "━━━━━━━━━━\n"
        "📌 از لیست زیر خدمت مورد نظر رو انتخاب کن:\n\n"
        "✨ اسم و فرم سفارش هر خدمت خودکار آماده می‌شه —\n"
        "فقط قیمتشو مشخص می‌کنی!"
    )
    kb = InlineKeyboardMarkup(row_width=1)
    for key, name, price, desc, extra in DEFAULT_PRODUCTS:
        kb.add(InlineKeyboardButton(name, callback_data=f"addtpl:{key}"))
    kb.add(InlineKeyboardButton("✏️ محصول کاملاً جدید (خارج از لیست)", callback_data="addnew"))
    kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="adm:products"))
    try_edit(call.message.chat.id, call.message.message_id, txt, kb)


@bot.callback_query_handler(func=lambda c: c.data == "addnew")
def p_add_new(call):
    if call.from_user.id != config.ADMIN_ID: return
    bot.answer_callback_query(call.id)
    msg = bot.send_message(config.ADMIN_ID, "🛍 (۱) نام محصول رو بفرست:")
    bot.register_next_step_handler(msg, p_add_name)


def p_tpl_price(message, key, name, extra):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:\n\n💰 قیمت:", p_tpl_price, key, name, extra)
    save_product(key, name, message.text, "-", extra)
    bot.send_message(config.ADMIN_ID,
        f"✅ «{name}» با قیمت «{message.text}» ثبت شد!\n"
        "الان تو لیست محصولات کاربرا هست 🛍",
        reply_markup=admin_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("addtpl:"))
def p_add_template(call):
    if call.from_user.id != config.ADMIN_ID: return
    key = call.data.split(":", 1)[1]
    tpl = next((t for t in DEFAULT_PRODUCTS if t[0] == key), None)
    if not tpl:
        bot.answer_callback_query(call.id, "⚠️ قالب پیدا نشد!")
        return
    bot.answer_callback_query(call.id)
    _, name, price, desc, extra = tpl
    fields = [f.strip() for f in extra.split("|") if f.strip()] if extra and extra != "-" else []
    fields_txt = "\n".join(f"  ▪️ {f}" for f in fields) if fields else "  ▪️ (بدون فرم — مستقیم فیش)"
    msg = bot.send_message(config.ADMIN_ID,
        f"💰 قیمت «{name}» رو بفرست:\n\n"
        "━━━━━━━━━━\n"
        f"📋 فرم سفارش این خدمت:\n{fields_txt}\n"
        "━━━━━━━━━━\n\n"
        "✍️ قیمت رو بنویس (برای توافقی «-»):")
    bot.register_next_step_handler(msg, p_tpl_price, key, name, extra)


def p_add_name(message):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:\n\n🛍 (۱) نام محصول:", p_add_name)
    msg = bot.send_message(config.ADMIN_ID, "💰 (۲) قیمت رو بفرست (برای توافقی «-»):")
    bot.register_next_step_handler(msg, p_add_price, message.text)

def p_add_price(message, name):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:\n\n💰 (۲) قیمت:", p_add_price, name)
    msg = bot.send_message(config.ADMIN_ID, "📝 (۳) توضیحات رو بفرست (اگه نداره «-»):")
    bot.register_next_step_handler(msg, p_add_desc, name, message.text)

def p_add_desc(message, name, price):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:\n\n📝 (۳) توضیحات:", p_add_desc, name, price)
    msg = bot.send_message(config.ADMIN_ID,
        "📋 (۴) اطلاعات موردنیاز از مشتری رو با «|» جدا بفرست (اگه نداره «-»):\nمثال: تعداد استارز|یوزرنیم چنل")
    bot.register_next_step_handler(msg, p_add_extra, name, price, message.text)

def p_add_extra(message, name, price, desc):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:", p_add_extra, name, price, desc)
    key = f"c{int(time.time())}"
    save_product(key, name, price, desc, message.text)
    bot.send_message(config.ADMIN_ID, f"✅ محصول «{name}» اضافه شد!", reply_markup=admin_kb())

# ---------- مکالمات (ادمین) ----------

@bot.callback_query_handler(func=lambda c: c.data.startswith("supchat:"))
def supchat_show(call):
    if call.from_user.id != config.ADMIN_ID: return
    uid = int(call.data.split(":")[1])
    rows = recent_supports()
    info = next((r for r in rows if r[0] == uid), None)
    name = info[1] if info else "؟"
    uname = info[2] if info else "ندارد"
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✍️ پاسخ", callback_data=f"reply:{uid}"))
    kb.add(InlineKeyboardButton("🔙 مکالمات", callback_data="adm:support"))
    try_edit(call.message.chat.id, call.message.message_id,
             f"👤 مکالمه با: {name}\n🔗 یوزرنیم: {uname}\n🆔 آیدی: {uid}\n\n"
             "آخرین پیامش بالای همین پیامه 👆 با دکمه «پاسخ» جوابش رو بده:", kb)
    bot.answer_callback_query(call.id)

# ==================== پیام‌های ناشناخته ====================

@bot.message_handler(func=lambda m: True, content_types=['text'])
def fallback(message):
    if not is_member(message.from_user.id):
        return bot.send_message(message.chat.id, "⚠️ اول عضو کانال شو 👇", reply_markup=join_kb)
    bot.send_message(message.chat.id, "🤔 متوجه نشدم! از دکمه‌های منو استفاده کن 🙏", reply_markup=main_kb)


init_db()
print("🤖 ربات ONYX روشن شد!")
bot.infinity_polling()