from telebot import TeleBot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from functools import wraps
from datetime import datetime
import time
import sqlite3
import config
import html as html_mod
import sys
sys.stdout.reconfigure(encoding='utf-8')


bot = TeleBot(config.TOKEN)
DB_NAME = "onyx.db"
SUPPORT_MODE = set()
pending_broadcast = None
BOT_USERNAME = None
pending_wh_post = None

# ==================== دیتابیس ====================

def db():
    con = sqlite3.connect(DB_NAME)
    con.row_factory = sqlite3.Row 
    return con

def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")

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

def init_db():
    con = db(); cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS users(
        user_id INTEGER PRIMARY KEY, name TEXT, username TEXT,
        referrer_id INTEGER, joined_at TEXT,
        points INTEGER DEFAULT 0, wallet_notified INTEGER DEFAULT 0)""")
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
    cur.execute("""CREATE TABLE IF NOT EXISTS sub_products(
        id INTEGER PRIMARY KEY AUTOINCREMENT, device_key TEXT,
        name TEXT, price TEXT, available INTEGER DEFAULT 1,
        min_qty TEXT DEFAULT '-', max_qty TEXT DEFAULT '-')""")
    for col in ("points", "wallet_notified"):
        try:
            cur.execute(f"ALTER TABLE users ADD COLUMN {col} INTEGER DEFAULT 0")
        except Exception:
            pass
    for col in ("min_qty", "max_qty"):
        try:
            cur.execute(f"ALTER TABLE sub_products ADD COLUMN {col} TEXT DEFAULT '-'")
        except Exception:
            pass
    cur.execute("UPDATE users SET points=0 WHERE points IS NULL")
    cur.execute("UPDATE users SET wallet_notified=0 WHERE wallet_notified IS NULL")
    cur.execute("UPDATE sub_products SET min_qty='-' WHERE min_qty IS NULL")
    cur.execute("UPDATE sub_products SET max_qty='-' WHERE max_qty IS NULL")
    cur.execute("""CREATE TABLE IF NOT EXISTS settings(
        k TEXT PRIMARY KEY, value TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS channels(
        id INTEGER PRIMARY KEY AUTOINCREMENT, ch TEXT UNIQUE)""")
    if cur.execute("SELECT value FROM settings WHERE k='channels_seeded'").fetchone() is None:
        if getattr(config, "CHANNEL", None):
            cur.execute("INSERT OR IGNORE INTO channels(ch) VALUES(?)", (config.CHANNEL,))
        cur.execute("INSERT OR REPLACE INTO settings(k, value) VALUES('channels_seeded','1')")
    if not cur.execute("SELECT 1 FROM products LIMIT 1").fetchone():
        cur.executemany("INSERT INTO products VALUES(?,?,?,?,?,1)", DEFAULT_PRODUCTS)
    con.commit(); con.close()

# ---------- توابع دیتابیس ----------

def count(sql, *args):
    con = db(); r = con.execute(sql, args).fetchone()[0]; con.close(); return r

# ----- محصولات اصلی (دستگاه‌ها) -----

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

# ----- زیرمحصولات (محصولات داخل هر دستگاه) -----

def all_sub_products(device_key):
    con = db()
    rows = con.execute("SELECT * FROM sub_products WHERE device_key=? ORDER BY id", (device_key,)).fetchall()
    con.close(); return rows

def save_sub_product(device_key, name, price, min_qty="-", max_qty="-"):
    con = db(); cur = con.cursor()
    cur.execute("INSERT INTO sub_products(device_key, name, price, min_qty, max_qty) VALUES(?,?,?,?,?)",
                (device_key, name, price, min_qty, max_qty))
    con.commit(); con.close()

def get_sub_product(sid):
    con = db()
    row = con.execute("SELECT * FROM sub_products WHERE id=?", (sid,)).fetchone()
    con.close(); return row

def delete_sub_product(sid):
    con = db()
    con.execute("DELETE FROM sub_products WHERE id=?", (sid,))
    con.commit(); con.close()

def toggle_sub_product(sid):
    con = db()
    con.execute("UPDATE sub_products SET available = 1 - available WHERE id=?", (sid,))
    con.commit(); con.close()

def set_sub_price(sid, price):
    con = db(); con.execute("UPDATE sub_products SET price=? WHERE id=?", (price, sid)); con.commit(); con.close()

def set_sub_qty(sid, mn, mx):
    con = db(); con.execute("UPDATE sub_products SET min_qty=?, max_qty=? WHERE id=?", (mn, mx, sid)); con.commit(); con.close()

# ----- کاربران و پوینت -----

def save_user(uid, first, username, referrer=None):
    con = db(); cur = con.cursor()
    cur.execute("""INSERT OR IGNORE INTO users(user_id, name, username, referrer_id, joined_at)
                   VALUES(?,?,?,?,?)""", (uid, first, username, referrer, now()))
    is_new = cur.rowcount > 0
    con.commit(); con.close()
    return is_new

def get_points(uid):
    con = db()
    r = con.execute("SELECT points FROM users WHERE user_id=?", (uid,)).fetchone()
    con.close()
    return (r["points"] or 0) if r else 0

def add_points(uid, amount):
    con = db(); cur = con.cursor()
    cur.execute("UPDATE users SET points = points + ? WHERE user_id=?", (amount, uid))
    con.commit(); con.close()

def wallet_notify(uid):
    con = db()
    r = con.execute("SELECT points, wallet_notified, name, username FROM users WHERE user_id=?", (uid,)).fetchone()
    con.close()
    if not r or (r["points"] or 0) < 50 or r["wallet_notified"]:
        return
    con = db(); con.execute("UPDATE users SET wallet_notified=1 WHERE user_id=?", (uid,)); con.commit(); con.close()
    try:
        bot.send_message(config.ADMIN_ID,
            "🎉 یک کاربر به ۵۰ پوینت رسید!\n"
            "━━━━━━━━━━\n"
            f"👤 اسم: {r['name']}\n"
            f"🔗 یوزرنیم: {r['username'] or 'ندارد'}\n"
            f"🆔 آیدی عددی: {uid}\n"
            f"💎 پوینت: {r['points']}")
    except Exception:
        pass

# ----- سفارش‌ها -----

def add_order(uid, pname, details, price):
    con = db(); cur = con.cursor()
    cur.execute("INSERT INTO orders(user_id, product_name, details, price, status, created_at) VALUES(?,?,?,?,?,?)",
                (uid, pname, details, price, "⏳ در انتظار بررسی", now()))
    oid = cur.lastrowid
    con.commit(); con.close(); return oid

def get_order(oid):
    con = db(); r = con.execute("SELECT * FROM orders WHERE order_id=?", (oid,)).fetchone(); con.close(); return r

def user_orders(uid):
    con = db()
    r = con.execute("""SELECT order_id, product_name, status, created_at
        FROM orders WHERE user_id=? ORDER BY order_id DESC""", (uid,)).fetchall()
    con.close(); return r

def update_order_status(oid, status):
    con = db(); con.execute("UPDATE orders SET status=? WHERE order_id=?", (status, oid)); con.commit(); con.close()

def all_user_ids():
    con = db(); r = con.execute("SELECT user_id FROM users").fetchall(); con.close(); return [x[0] for x in r]

# ----- سوالات متداول -----

def save_faq(q, a):
    con = db(); con.execute("INSERT INTO faq(question, answer) VALUES(?,?)", (q, a)); con.commit(); con.close()

def all_faq():
    con = db(); r = con.execute("SELECT id, question FROM faq").fetchall(); con.close(); return r

def get_faq(fid):
    con = db(); r = con.execute("SELECT question, answer FROM faq WHERE id=?", (fid,)).fetchone(); con.close(); return r

def del_faq(fid):
    con = db(); con.execute("DELETE FROM faq WHERE id=?", (fid,)); con.commit(); con.close()

# ----- پشتیبانی و دعوت -----

def touch_support(uid, name, username):
    con = db(); con.execute("INSERT OR REPLACE INTO support VALUES(?,?,?,?)", (uid, name, username, now()))
    con.commit(); con.close()

def recent_supports():
    con = db()
    r = con.execute("""SELECT user_id, name, username, last_time FROM support
        ORDER BY last_time DESC LIMIT 10""").fetchall()
    con.close(); return r

def invited_list(uid):
    con = db(); r = con.execute("SELECT name FROM users WHERE referrer_id=?", (uid,)).fetchall(); con.close(); return r

# ----- تنظیمات (چنل انبار) -----

def get_setting(key, default=None):
    con = db()
    r = con.execute("SELECT value FROM settings WHERE k=?", (key,)).fetchone()
    con.close()
    return r["value"] if r else default

def set_setting(key, value):
    con = db(); cur = con.cursor()
    cur.execute("INSERT OR REPLACE INTO settings(k, value) VALUES(?,?)", (key, value))
    con.commit(); con.close()


# ==================== عضویت اجباری ====================

def build_join_kb():
    kb = InlineKeyboardMarkup(row_width=1)
    for row in all_channels():
        ch = row["ch"]
        kb.add(InlineKeyboardButton(f"📢 عضویت در {ch}", url=f"https://t.me/{ch.replace('@', '')}"))
    kb.add(InlineKeyboardButton("✅ عضو شدم", callback_data="check_membership"))
    return kb

def is_member(user_id):
    chans = all_channels()
    if not chans:
        return True   # چنلی ثبت نشده، همه آزادن
    for row in chans:
        ch = row["ch"]
        try:
            m = bot.get_chat_member(ch, user_id)
            if m.status not in ["member", "administrator", "creator", "restricted"]:
                return False
        except Exception:
            continue 
    return True

def membership_required(func):
    @wraps(func)
    def wrapper(message):
        if not is_member(message.from_user.id):
            bot.send_message(message.chat.id, "سلام! برای استفاده از ربات اول عضو کانال شو 👇", reply_markup=build_join_kb())
            return
        return func(message)
    return wrapper


# ----- چنل‌های عضویت اجباری -----

def add_channel(ch):
    con = db(); cur = con.cursor()
    cur.execute("INSERT OR IGNORE INTO channels(ch) VALUES(?)", (ch,))
    con.commit(); con.close()

def del_channel(cid):
    con = db(); con.execute("DELETE FROM channels WHERE id=?", (cid,)); con.commit(); con.close()

def all_channels():
    con = db()
    rows = con.execute("SELECT id, ch FROM channels ORDER BY id").fetchall()
    con.close(); return rows

# ==================== منوی اصلی ====================

btn1 = "محصولات🛍"
btn2 = "ثبت سفارش🛒"
btn3 = "پشتیبانی 👤"
btn4 = "سوالات متداول"
btn5 = "پنل ادمین💻"
btn6 = "معرفی به دوستان🎭"
btn7 = "سفارش های من💎"
btn8 = "کیف پول💰"
SUPPORT_EXIT = "🔙 خروج از پشتیبانی"
MENU_TEXTS = {btn1, btn2, btn3, btn4, btn5, btn6, btn7, btn8, SUPPORT_EXIT}

WELCOME = """✨ به ربات خدمات مجازی ONYX خوش اومدید 🎉
از دکمه‌های زیر استفاده کنید 🤍"""

main_kb = ReplyKeyboardMarkup(resize_keyboard=True)
main_kb.add(KeyboardButton(btn1), KeyboardButton(btn2))
main_kb.add(KeyboardButton(btn4))
main_kb.add(KeyboardButton(btn7), KeyboardButton(btn6))
main_kb.add(KeyboardButton(btn8))
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
        bot.send_message(message.chat.id, "سلام! برای استفاده از ربات اول عضو کانال شو 👇", reply_markup=build_join_kb())
        return
    txt = WELCOME
    if is_new and referrer:
        con = db()
        r = con.execute("SELECT name FROM users WHERE user_id=?", (referrer,)).fetchone()
        con.close()
        if r:
            txt += f"\n\n🎉 تو با لینک دعوت {r['name']} اومدی — خوش اومدی!"
            add_points(referrer, 10)
            wallet_notify(referrer)
            try:
                bot.send_message(referrer,
                    f"🎭 دعوت موفق!\n\n"
                    f"👤 {message.from_user.first_name} با لینک تو ربات رو استارت زد\n"
                    f"💰 ۱۰ پوینت به کیف پولت اضافه شد!")
            except Exception:
                pass
    bot.send_message(message.chat.id, txt, reply_markup=main_kb)

@bot.message_handler(commands=['cancel'])
def cancel_cmd(message):
    cancel_action(message)

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

# ==================== محصولات (کاربر) ====================

def products_kb():
    rows = all_products()
    kb = InlineKeyboardMarkup(row_width=2)
    if rows:
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
        bot.answer_callback_query(call.id, "⚠️ این دستگاه حذف شده!")
        return
    name, price, desc, extra, avail = row["name"], row["price"], row["description"], row["extra"], row["available"]
    subs = all_sub_products(key)
    if not avail:
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="backprod"))
        try:
            bot.edit_message_text(
                f"{name}\n\n❌ فعلاً موجود نیست!\nبه‌زودی دوباره در دسترس قرار می‌گیره 🙏",
                call.message.chat.id, call.message.message_id, reply_markup=kb)
        except Exception:
            pass
        return bot.answer_callback_query(call.id)
    if not subs:
        bot.answer_callback_query(call.id,
            "⚠️ برای این دستگاه هنوز محصولی ثبت نشده! به پشتیبانی اطلاع بده 💬", show_alert=True)
        return
    txt = (
        f"{name}\n"
        "━━━━━━━━━━\n"
        "🛍 محصولات این خدمت رو انتخاب کن 👇"
    )
    kb = InlineKeyboardMarkup()
    for s in subs:
        badge = "✅" if s["available"] else "❌"
        kb.add(InlineKeyboardButton(f"{s['name']} — {s['price']} {badge}", callback_data=f"sub:{s['id']}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="backprod"))
    try:
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        pass
    bot.answer_callback_query(call.id)

# ==================== خرید زیرمحصول (مسیر اصلی) ====================

@bot.callback_query_handler(func=lambda c: c.data.startswith("sub:"))
def sub_product_view(call):
    sid = int(call.data.split(":", 1)[1])
    s = get_sub_product(sid)
    if not s:
        bot.answer_callback_query(call.id, "⚠️ این محصول حذف شده!")
        return
    if not s["available"]:
        bot.answer_callback_query(call.id, "❌ این محصول فعلاً ناموجوده!", show_alert=True)
        return
    device = get_product(s["device_key"])
    dname = device["name"] if device else ""
    has_limit = s["min_qty"] and s["min_qty"] != "-"
    txt = (
        f"{dname}\n"
        f"🛍 محصول: {s['name']}\n"
        "━━━━━━━━━━\n"
        f"💰 قیمت: {s['price']}\n"
        + (f"🔢 حداقل: {s['min_qty']} | حداکثر: {s['max_qty']}\n" if has_limit else "")
        + "━━━━━━━━━━\n"
        "آماده‌ی خریدی؟ 👇"
    )
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("🛒 ثبت سفارش و پرداخت", callback_data=f"pay_sub:{sid}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data=f"prod:{s['device_key']}"))
    try:
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay_sub:"))
def pay_sub(call):
    sid = int(call.data.split(":", 1)[1])
    s = get_sub_product(sid)
    if not s or not s["available"]:
        return bot.answer_callback_query(call.id, "❌ ناموجود!", show_alert=True)
    device = get_product(s["device_key"])
    dname = device["name"] if device else ""
    full_name = f"{dname} — {s['name']}"
    price_txt = s["price"] if s["price"] and s["price"] != "-" else "توافقی — به پشتیبانی پیام بده"
    txt = f"""💳 روش پرداخت
━━━━━━━━━━
📦 محصول: {full_name}
💰 مبلغ: {price_txt}
━━━━━━━━━━
روش پرداخت رو انتخاب کن 👇"""
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("💳 پرداخت کارت به کارت", callback_data=f"card_sub:{sid}"))
    kb.add(InlineKeyboardButton("🏦 پرداخت از درگاه (به‌زودی)", callback_data="soon"))
    kb.add(InlineKeyboardButton("₿ پرداخت با ارز دیجیتال (به‌زودی)", callback_data="soon"))
    kb.add(InlineKeyboardButton("🅿️ پرداخت با PayPal (به‌زودی)", callback_data="soon"))
    kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data=f"prod:{s['device_key']}"))
    try:
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data == "soon")
def pay_soon(call):
    bot.answer_callback_query(call.id, "🚧 این روش پرداخت به‌زودی فعاله!", show_alert=True)

@bot.callback_query_handler(func=lambda c: c.data.startswith("card_sub:"))
def card_sub(call):
    sid = int(call.data.split(":", 1)[1])
    s = get_sub_product(sid)
    if not s or not s["available"]:
        return bot.answer_callback_query(call.id, "❌ ناموجود!", show_alert=True)
    device = get_product(s["device_key"])
    dname = device["name"] if device else ""
    full_name = f"{dname} — {s['name']}"
    price_txt = s["price"] if s["price"] and s["price"] != "-" else "توافقی — به پشتیبانی پیام بده"
    txt = f"""🧾 فاکتور سفارش
━━━━━━━━━━
📦 محصول: {full_name}
💰 مبلغ: {price_txt}
━━━━━━━━━━
💳 شماره کارت:
{config.CARD_NUMBER}
👤 به نام: {config.CARD_OWNER}
━━━━━━━━━━
✅ بعد از واریز، دکمه زیر رو بزن و فیش رو بفرست"""
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ واریز کردم — ارسال فیش", callback_data=f"receipt_sub:{sid}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت به روش پرداخت", callback_data=f"pay_sub:{sid}"))
    try:
        bot.edit_message_text(txt, call.message.chat.id, call.message.message_id, reply_markup=kb)
    except Exception:
        pass
    bot.answer_callback_query(call.id)

@bot.callback_query_handler(func=lambda c: c.data.startswith("receipt_sub:"))
def receipt_sub_start(call):
    sid = int(call.data.split(":", 1)[1])
    s = get_sub_product(sid)
    if not s:
        return bot.answer_callback_query(call.id, "⚠️ این محصول حذف شده!")
    bot.answer_callback_query(call.id)
    if s["min_qty"] and s["min_qty"] != "-":
        msg = bot.send_message(call.message.chat.id,
            f"🔢 چند تا می‌خوای؟\n\n"
            f"❗️ حداقل: {s['min_qty']}\n"
            f"❗️ حداکثر: {s['max_qty']}\n\n"
            "عدد رو بنویس:")
        bot.register_next_step_handler(msg, sub_ask_qty, sid, {})
        return
    msg = bot.send_message(call.message.chat.id,
        "📝توضیحات برای ادمین ارسال کنید:\n\n❌ برای لغو، یه دکمه منو بزن یا /cancel")
    bot.register_next_step_handler(msg, form_sub_name, sid, {})

def sub_ask_qty(message, sid, data):
    s = get_sub_product(sid)
    if is_cancel(message): return cancel_action(message)
    if not s:
        return bot.send_message(message.chat.id, "⚠️ این محصول حذف شده!", reply_markup=main_kb)
    if not message.text or not message.text.strip().isdigit():
        msg = bot.send_message(message.chat.id, "⚠️ فقط عدد بفرست (مثلا: 250):\n\n🔢 چند تا می‌خوای؟")
        bot.register_next_step_handler(msg, sub_ask_qty, sid, data)
        return
    qty = int(message.text.strip())
    mn, mx = s["min_qty"], s["max_qty"]
    try:
        lo = int(mn) if mn and mn != "-" else 1
        hi = int(mx) if mx and mx != "-" else 10**9
    except ValueError:
        lo, hi = 1, 10**9
    if qty < lo or qty > hi:
        msg = bot.send_message(message.chat.id,
            f"⚠️ تعداد باید بین {lo} تا {hi} باشه!\n\n🔢 دوباره بفرست:")
        bot.register_next_step_handler(msg, sub_ask_qty, sid, data)
        return
    data["qty"] = qty
    msg = bot.send_message(message.chat.id,
        "📝توضیحات برای ادمین ارسال کنید:\n\n❌ برای لغو، یه دکمه منو بزن یا /cancel")
    bot.register_next_step_handler(msg, form_sub_name, sid, data)

def form_sub_name(message, sid, data):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(message.chat.id, "⚠️ لطفاً متنی بفرست:\n\n📝 نام و نام خانوادگی:", form_sub_name, sid, data)
    data["name"] = message.text
    msg = bot.send_message(message.chat.id, "📎 مرحله آخر! عکس فیش واریز رو بفرست:")
    bot.register_next_step_handler(msg, form_sub_receipt, sid, data)

def form_sub_receipt(message, sid, data):
    if is_cancel(message): return cancel_action(message)
    if message.content_type != "photo":
        return reask(message.chat.id, "📎 لطفاً عکس فیش واریز رو بفرست:", form_sub_receipt, sid, data)
    finish_sub_order(message, sid, data)

def finish_sub_order(message, sid, data):
    s = get_sub_product(sid)
    if not s:
        return bot.send_message(message.chat.id, "⚠️ این محصول حذف شده!", reply_markup=main_kb)
    device = get_product(s["device_key"])
    dname = device["name"] if device else ""
    full_name = f"{dname} — {s['name']}"
    price = s["price"]
    details = f"👤 نام و نام خانوادگی: {data['name']}"
    if "qty" in data:
        details += f"\n▪️ تعداد: {data['qty']}"
    oid = add_order(message.from_user.id, full_name, details, price)
    u = message.from_user
    uname = f"@{u.username}" if u.username else "ندارد"
    admin_txt = f"""🛒 سفارش جدید #{oid}
━━━━━━━━━━
📦 محصول: {full_name}
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
    add_points(message.from_user.id, 5)
    wallet_notify(message.from_user.id)
    bot.send_message(message.chat.id, f"""✅ سفارش #{oid} ثبت شد!
━━━━━━━━━━
📦 محصول: {full_name}
📍 وضعیت: ⏳ در انتظار بررسی
💰 ۵ پوینت به کیف پولت اضافه شد!

پشتیبانی بعد از بررسی فیش باهات در تماسه 🤍""", reply_markup=main_kb)

# ==================== فاکتور و فرم سفارش (دستگاه بدون زیرمحصول) ====================

@bot.callback_query_handler(func=lambda c: c.data.startswith("pay:"))
def pay_page(call):
    key = call.data.split(":", 1)[1]
    row = get_product(key)
    if not row:
        bot.answer_callback_query(call.id, "⚠️ این محصول حذف شده!")
        return
    name, price = row["name"], row["price"]
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

@bot.callback_query_handler(func=lambda c: c.data.startswith("card:"))
def card_page(call):
    key = call.data.split(":", 1)[1]
    row = get_product(key)
    if not row:
        bot.answer_callback_query(call.id, "⚠️ این محصول حذف شده!")
        return
    name, price = row["name"], row["price"]
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
    if not row or not row["extra"] or row["extra"] == "-":
        return []
    return [f.strip() for f in row["extra"].split("|") if f.strip()]

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
    name, price = row["name"], row["price"]
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
    add_points(message.from_user.id, 5)
    wallet_notify(message.from_user.id)
    bot.send_message(message.chat.id, f"""✅ سفارش #{oid} ثبت شد!
━━━━━━━━━━
📦 محصول: {name}
📍 وضعیت: ⏳ در انتظار بررسی
💰 ۵ پوینت به کیف پولت اضافه شد!

پشتیبانی بعد از بررسی فیش باهات در تماسه 🤍""", reply_markup=main_kb)

# ==================== کیف پول ====================

@bot.message_handler(func=lambda m: m.text == btn8)
@membership_required
def wallet_handler(message):
    uid = message.from_user.id
    pts = get_points(uid)
    orders_cnt = count("SELECT COUNT(*) FROM orders WHERE user_id=?", uid)
    invites = count("SELECT COUNT(*) FROM users WHERE referrer_id=?", uid)
    if pts >= 50:
        goal_txt = "🎉 به ۵۰ پوینت رسیدی! پشتیبانی به‌زودی باهات در تماسه 🤍"
    else:
        goal_txt = f"🎯 {50 - pts} پوینت تا جایزه‌ی ۵۰ تایی مونده!"
    txt = f"""💰 کیف پول تو
━━━━━━━━━━
💎 پوینت فعلی: {pts}
━━━━━━━━━━
🛒 هر سفارش ثبت‌شده = ۵ پوینت
👥 هر دعوت موفق = ۱۰ پوینت
━━━━━━━━━━
📊 سفارش‌ها: {orders_cnt} | دعوت‌ها: {invites}
━━━━━━━━━━
{goal_txt}"""
    bot.send_message(message.chat.id, txt, reply_markup=main_kb)

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
        bot.edit_message_text(f"❓ سوال:\n{row['question']}\n\n━━━━━━━━━━\n\n💬 جواب:\n{row['answer']}",
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
💎 پوینت دعوت: {len(rows) * 10}
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
هرکس با لینک تو استارت بزنه، 💰 ۱۰ پوینت می‌گیری 🎯"""
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
    if act == "chat":
        SUPPORT_MODE.add(call.message.chat.id)
        try:
            bot.edit_message_text("""✉️ گفتگو با پشتیبانی
━━━━━━━━━━
هر متنی یا عکسی بفرستی، مستقیم می‌ره به پشتیبانی 💌
برای خروج، دکمه «🔙 خروج از پشتیبانی» رو بزن.""",
                call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(call.message.chat.id, "💬 حالا پیامت رو بنویس:", reply_markup=support_kb)
    else:
        kb = InlineKeyboardMarkup()
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
    kb.add(InlineKeyboardButton("💰 کیف پول‌ها", callback_data="adm:wallets"),
           InlineKeyboardButton("📦 چنل انبار", callback_data="adm:warehouse"))
    kb.add(InlineKeyboardButton("📢 چنل‌های اجباری", callback_data="adm:channels"),
           InlineKeyboardButton("🏠 منوی اصلی", callback_data="adm:menu"))
    return kb


@bot.message_handler(func=lambda m: m.text == btn5)
def admin_panel(message):
    if message.from_user.id != config.ADMIN_ID:
        return bot.send_message(message.chat.id, "⛔️ دسترسی نداری!", reply_markup=main_kb)
    bot.send_message(message.chat.id, "💻 پنل مدیریت ONYX\nیکی رو انتخاب کن:", reply_markup=admin_kb())

def channels_view(chat, mid):
    rows = all_channels()
    kb = InlineKeyboardMarkup(row_width=1)
    if rows:
        for row in rows:
            kb.add(InlineKeyboardButton(f"🗑 {row['ch']}", callback_data=f"delchan:{row['id']}"))
    else:
        kb.add(InlineKeyboardButton("چنلی ثبت نشده 🍃", callback_data="noop"))
    kb.add(InlineKeyboardButton("➕ افزودن چنل", callback_data="addchan"))
    kb.add(InlineKeyboardButton("🔙 پنل", callback_data="admback"))
    try_edit(chat, mid, "📢 چنل‌های عضویت اجباری:\n(برای حذف، روی چنل بزن 👇)", kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("delchan:"))
def delchan_handler(call):
    if call.from_user.id != config.ADMIN_ID: return
    del_channel(int(call.data.split(":")[1]))
    bot.answer_callback_query(call.id, "حذف شد 🗑")
    channels_view(call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda c: c.data == "addchan")
def addchan_start(call):
    if call.from_user.id != config.ADMIN_ID: return
    bot.answer_callback_query(call.id)
    msg = bot.send_message(config.ADMIN_ID,
        "📢 آیدی چنل اجباری جدید رو بفرست (مثل @mychannel):\n\n"
        "⚠️ ربات باید تو این چنل «ادمین» باشه تا بتونه عضویت رو چک کنه!\n"
        "❌ برای لغو /cancel")
    bot.register_next_step_handler(msg, addchan_save)

def addchan_save(message):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:\n\n📢 آیدی چنل (مثل @mychannel):", addchan_save)
    ch = message.text.strip()
    try:
        info = bot.get_chat(ch)
    except Exception:
        return reask(config.ADMIN_ID, "❌ این آیدی پیدا نشد!\n\n📢 دوباره بفرست:", addchan_save)
    if info.type != "channel":
        return reask(config.ADMIN_ID, f"⚠️ «{ch}» چنل نیست!\n\n📢 آیدی یه چنل واقعی بفرست:", addchan_save)
    try:
        me = bot.get_chat_member(ch, bot.get_me().id)
        if me.status not in ["administrator", "creator"]:
            return reask(config.ADMIN_ID,
                "⚠️ ربات تو این چنل ادمین نیست!\n"
                "اول ربات رو ادمین کن، بعد دوباره بفرست:\n\n📢 آیدی چنل:", addchan_save)
    except Exception:
        return reask(config.ADMIN_ID,
            "⚠️ نتونستم وضعیت ربات رو تو چنل چک کنم!\n"
            "ربات رو ادمین کن و دوباره بفرست:\n\n📢 آیدی چنل:", addchan_save)
    add_channel(ch)
    bot.send_message(config.ADMIN_ID,
        f"✅ چنل «{info.title}» ({ch}) به عضویت اجباری اضافه شد!", reply_markup=admin_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("adm:"))
def admin_actions(call):
    if call.from_user.id != config.ADMIN_ID:
        return bot.answer_callback_query(call.id, "⛔️ دسترسی نداری!", show_alert=True)
    act = call.data.split(":", 1)[1]
    chat, mid = call.message.chat.id, call.message.message_id
    bot.answer_callback_query(call.id)

    if act == "menu":
        return bot.send_message(chat, "🏠 منوی اصلی:", reply_markup=main_kb)

    if act == "channels":
        return channels_view(chat, mid)

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
        con = db()
        rows = con.execute("SELECT order_id, product_name, status FROM orders ORDER BY order_id DESC LIMIT 10").fetchall()
        con.close()
        kb = InlineKeyboardMarkup(row_width=1)
        if rows:
            kb.add(*[InlineKeyboardButton(f"{status.split()[0]} #{oid} — {pname[:25]}",
                     callback_data=f"admorder:{oid}") for oid, pname, status in rows])
        else:
            kb.add(InlineKeyboardButton("هنوز سفارشی نیست 🍃", callback_data="noop"))
        kb.add(InlineKeyboardButton("🔙 پنل", callback_data="admback"))
        return try_edit(chat, mid, "📦 ۱۰ سفارش اخیر:\nروی سفارش بزن تا جزئیات و تایید/رد ببینی 👇", kb)

    if act == "wallets":
        con = db()
        rows = con.execute("""SELECT name, username, user_id, points FROM users
                              WHERE points >= 50 ORDER BY points DESC LIMIT 30""").fetchall()
        con.close()
        if rows:
            lines = "\n".join(
                f"💎 {r['points']} پوینت — {r['name']} ({r['username'] or 'بدون یوزرنیم'})\n🆔 {r['user_id']}"
                for r in rows)
            txt = f"💰 کاربران با ۵۰ پوینت یا بیشتر:\n\n{lines}"
        else:
            txt = "هنوز کسی به ۵۰ پوینت نرسیده 🍃"
        kb = InlineKeyboardMarkup()
        kb.add(InlineKeyboardButton("🔙 پنل", callback_data="admback"))
        return try_edit(chat, mid, txt, kb)

    if act == "warehouse":
        ch = get_setting("warehouse_channel")
        if ch:
            txt = (f"📦 چنل انبار\n"
                   "━━━━━━━━━━\n"
                   f"🔗 چنل فعلی: {ch}\n\n"
                   "ℹ️ وقتی زیرمحصول جدید اضافه کنی، ازت می‌پرسه\n"
                   "که تو چنل پستش کنه یا نه ✅")
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("✏️ تغییر چنل", callback_data="whset"))
            kb.add(InlineKeyboardButton("🧪 تست ارسال", callback_data="whtest"))
        else:
            txt = ("📦 چنل انبار\n"
                   "━━━━━━━━━━\n"
                   "❌ هنوز چنلی ثبت نشده!\n\n"
                   "ℹ️ با ثبت چنل انبار، بعد از افزودن هر زیرمحصول\n"
                   "ازت می‌پرسه که با فرم تبلیغاتی تو چنل پست بشه.")
            kb = InlineKeyboardMarkup()
            kb.add(InlineKeyboardButton("➕ ثبت چنل", callback_data="whset"))
        kb.add(InlineKeyboardButton("🔙 پنل", callback_data="admback"))
        return try_edit(chat, mid, txt, kb)

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

@bot.callback_query_handler(func=lambda c: c.data.startswith("supchat:"))
def admin_supchat(call):
    if call.from_user.id != config.ADMIN_ID: return
    uid = int(call.data.split(":", 1)[1])
    bot.answer_callback_query(call.id)
    con = db()
    u = con.execute("SELECT name, username FROM users WHERE user_id=?", (uid,)).fetchone()
    con.close()
    name = u["name"] if u else "؟"
    uname = u["username"] if u else None
    txt = f"""👤 مکالمه با {name}
🔗 یوزرنیم: {uname or 'ندارد'}
🆔 آیدی: {uid}"""
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✍️ پاسخ", callback_data=f"reply:{uid}"))
    kb.add(InlineKeyboardButton("🔙 مکالمات", callback_data="adm:support"))
    try_edit(call.message.chat.id, call.message.message_id, txt, kb)

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
    uid, pname, details, price, status, created = (row["user_id"], row["product_name"],
        row["details"], row["price"], row["status"], row["created_at"])
    con = db()
    u = con.execute("SELECT name, username FROM users WHERE user_id=?", (uid,)).fetchone()
    con.close()
    uname = u["username"] if u and u["username"] else "ندارد"
    txt = f"""🧾 سفارش #{oid}
━━━━━━━━━━
📦 محصول: {pname}
💰 مبلغ: {price if price != '-' else 'توافقی'}
📅 تاریخ: {created}
📍 وضعیت: {status}
━━━━━━━━━━
{details}
━━━━━━━━━━
👤 مشتری: {u['name'] if u else '؟'}
🔗 یوزرنیم: {uname}
🆔 آیدی: {uid}"""
    kb = InlineKeyboardMarkup()
    if status.startswith("⏳"):
        kb.add(InlineKeyboardButton("✅ تایید", callback_data=f"ost:{oid}:ok"),
               InlineKeyboardButton("❌ رد", callback_data=f"ost:{oid}:no"))
    kb.add(InlineKeyboardButton("✅ اتمام کار و اطلاع به مشتری", callback_data=f"ordone:{oid}"))
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
        bot.send_message(row["user_id"], f"""📢 وضعیت سفارش #{oid} تغییر کرد!
📦 محصول: {row['product_name']}
📍 وضعیت جدید: {new_status}""")
    except Exception:
        pass
    bot.answer_callback_query(call.id, "انجام شد ✅")
    order_detail_view(call.message.chat.id, call.message.message_id, oid)


@bot.callback_query_handler(func=lambda c: c.data.startswith("ordone:"))
def order_done_notify(call):
    if call.from_user.id != config.ADMIN_ID: return
    oid = int(call.data.split(":")[1])
    bot.answer_callback_query(call.id)
    msg = bot.send_message(config.ADMIN_ID,
        f"📩 پیامی که می‌خوای به مشتری سفارش #{oid} برسه رو بنویس:\n\n"
        "(مثلاً: سفارشت آماده شد و استارزها ارسال شد ✅)\n"
        "❌ برای لغو /cancel")
    bot.register_next_step_handler(msg, order_done_send, oid)

def order_done_send(message, oid):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:", order_done_send, oid)
    row = get_order(oid)
    if not row:
        return bot.send_message(config.ADMIN_ID, "⚠️ سفارش پیدا نشد!")
    if not row["status"].startswith("❌"):
        update_order_status(oid, "📦 تحویل شد")
        new_status = "📦 تحویل شد"
    else:
        new_status = row["status"]
    try:
        bot.send_message(row["user_id"],
            f"🎉 سفارش #{oid} آماده شد!\n"
            "━━━━━━━━━━\n"
            f"📦 محصول: {row['product_name']}\n"
            f"📍 وضعیت: {new_status}\n"
            "━━━━━━━━━━\n"
            f"💬 پیام پشتیبانی:\n{message.text}\n\n"
            "🤍 ONYX — از اعتمادت ممنونیم!")
        bot.send_message(config.ADMIN_ID,
            f"✅ اطلاع‌رسانی سفارش #{oid} انجام شد!", reply_markup=admin_kb())
    except Exception:
        bot.send_message(config.ADMIN_ID, "❌ ارسال نشد (کاربر ربات رو بلاک کرده).")

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
             f"❓ سوال:\n{row['question']}\n\n💬 جواب:\n{row['answer']}", kb)
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

# ---------- مدیریت محصولات اصلی (ادمین) ----------

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
    name, price, desc, extra, avail = (row["name"], row["price"], row["description"], row["extra"], row["available"])
    extra_txt = extra.replace('|', '، ') if extra and extra != '-' else '—'
    txt = f"""🛍 {name}
━━━━━━━━━━
💰 قیمت: {price}
📝 توضیحات: {desc if desc != '-' else '—'}
📋 موارد موردنیاز: {extra_txt}
📍 وضعیت: {'✅ موجود' if avail else '❌ ناموجود'}"""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🔄 موجود / ناموجود", callback_data=f"ptoggle:{key}"))
    kb.add(InlineKeyboardButton("✏️ ویرایش قیمت", callback_data=f"pedit:{key}"))
    kb.add(InlineKeyboardButton(f"🧩 محصولات ({len(all_sub_products(key))})", callback_data=f"subs:{key}"))
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
        "🛍 افزودن محصول (دستگاه)\n"
        "━━━━━━━━━━\n"
        "📌 از لیست زیر خدمت مورد نظر رو انتخاب کن:\n\n"
        "✨ بعد از ساخت، از صفحه‌ی مدیریت محصول، دکمه «🧩 محصولات» رو بزن\n"
        "و محصولاتی که کاربر می‌بینه رو اضافه کن!"
    )
    kb = InlineKeyboardMarkup(row_width=1)
    for key, name, price, desc, extra in DEFAULT_PRODUCTS:
        kb.add(InlineKeyboardButton(name, callback_data=f"addtpl:{key}"))
    kb.add(InlineKeyboardButton("✏️ محصول کاملاً جدید (خارج از لیست)", callback_data="addnew"))
    kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data="adm:products"))
    try_edit(call.message.chat.id, call.message.message_id, txt, kb)

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
    fields_txt = "\n".join(f"  ▪️ {f}" for f in fields) if fields else "  ▪️ (بدون فرم)"
    msg = bot.send_message(config.ADMIN_ID,
        f"💰 قیمت «{name}» رو بفرست:\n\n"
        "━━━━━━━━━━\n"
        f"📋 فرم سفارش این خدمت:\n{fields_txt}\n"
        "━━━━━━━━━━\n\n"
        "✍️ قیمت رو بنویس (برای توافقی «-»):")
    bot.register_next_step_handler(msg, p_tpl_price, key, name, extra)

def p_tpl_price(message, key, name, extra):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:\n\n💰 قیمت:", p_tpl_price, key, name, extra)
    save_product(key, name, message.text, "-", extra)
    bot.send_message(config.ADMIN_ID,
        f"✅ «{name}» ساخته شد!\n\n"
        "🧩 حالا از صفحه‌ی مدیریت محصول، دکمه «🧩 محصولات» رو بزن "
        "و محصولاتی که کاربر می‌بینه رو بهش اضافه کن.",
        reply_markup=admin_kb())

@bot.callback_query_handler(func=lambda c: c.data == "addnew")
def p_add_new(call):
    if call.from_user.id != config.ADMIN_ID: return
    bot.answer_callback_query(call.id)
    msg = bot.send_message(config.ADMIN_ID, "🛍 (۱) نام محصول رو بفرست:")
    bot.register_next_step_handler(msg, p_add_name)

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
    key = "c" + str(int(time.time()))
    save_product(key, name, message.text, "-", "-")
    bot.send_message(config.ADMIN_ID,
        f"✅ «{name}» ساخته شد!\n\n"
        "🧩 حالا از صفحه‌ی مدیریت محصول، دکمه «🧩 محصولات» رو بزن "
        "و محصولاتی که کاربر می‌بینه رو بهش اضافه کن.",
        reply_markup=admin_kb())

# ---------- مدیریت زیرمحصولات هر دستگاه (ادمین) ----------

@bot.callback_query_handler(func=lambda c: c.data.startswith("subs:"))
def admin_subs_list(call):
    if call.from_user.id != config.ADMIN_ID: return
    key = call.data.split(":", 1)[1]
    bot.answer_callback_query(call.id)
    admin_subs_view(call.message.chat.id, call.message.message_id, key)

def admin_subs_view(chat, mid, key):
    row = get_product(key)
    if not row:
        return try_edit(chat, mid, "⚠️ این دستگاه حذف شده!", None)
    subs = all_sub_products(key)
    kb = InlineKeyboardMarkup(row_width=1)
    if subs:
        for s in subs:
            badge = "✅" if s["available"] else "❌"
            kb.add(InlineKeyboardButton(f"{badge} {s['name']} — {s['price']}", callback_data=f"sshow:{s['id']}"))
    else:
        kb.add(InlineKeyboardButton("هنوز محصولی نیست 🍃", callback_data="noop"))
    kb.add(InlineKeyboardButton("➕ افزودن محصول به این دستگاه", callback_data=f"addsub:{key}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data=f"admp:{key}"))
    try_edit(chat, mid, f"🧩 محصولات «{row['name']}»:", kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sshow:"))
def admin_sub_show(call):
    if call.from_user.id != config.ADMIN_ID: return
    sid = int(call.data.split(":", 1)[1])
    bot.answer_callback_query(call.id)
    admin_sub_show_view(call.message.chat.id, call.message.message_id, sid)

def admin_sub_show_view(chat, mid, sid):
    s = get_sub_product(sid)
    if not s:
        return try_edit(chat, mid, "⚠️ این محصول حذف شده!", None)
    device = get_product(s["device_key"])
    dname = device["name"] if device else ""
    qty_txt = f"{s['min_qty']} تا {s['max_qty']}" if s["min_qty"] and s["min_qty"] != "-" else "بدون محدودیت"
    txt = f"""🧩 {s['name']}
━━━━━━━━━━
🖥 دستگاه: {dname}
💰 قیمت: {s['price']}
🔢 محدودیت تعداد: {qty_txt}
📍 وضعیت: {'✅ موجود' if s['available'] else '❌ ناموجود'}"""
    kb = InlineKeyboardMarkup(row_width=2)
    kb.add(InlineKeyboardButton("🔄 موجود/ناموجود", callback_data=f"stoggle:{sid}"))
    kb.add(InlineKeyboardButton("✏️ قیمت", callback_data=f"sprice:{sid}"))
    kb.add(InlineKeyboardButton("🔢 حداقل/حداکثر", callback_data=f"sqty:{sid}"))
    kb.add(InlineKeyboardButton("🗑 حذف", callback_data=f"sdel:{sid}"))
    kb.add(InlineKeyboardButton("🔙 بازگشت", callback_data=f"subs:{s['device_key']}"))
    try_edit(chat, mid, txt, kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("stoggle:"))
def admin_sub_toggle(call):
    if call.from_user.id != config.ADMIN_ID: return
    sid = int(call.data.split(":", 1)[1])
    toggle_sub_product(sid)
    bot.answer_callback_query(call.id, "تغییر کرد 🔄")
    admin_sub_show_view(call.message.chat.id, call.message.message_id, sid)

@bot.callback_query_handler(func=lambda c: c.data.startswith("sdel:"))
def admin_sub_del(call):
    if call.from_user.id != config.ADMIN_ID: return
    sid = int(call.data.split(":", 1)[1])
    s = get_sub_product(sid)
    if s:
        delete_sub_product(sid)
        bot.answer_callback_query(call.id, "حذف شد 🗑")
        admin_subs_view(call.message.chat.id, call.message.message_id, s["device_key"])
    else:
        bot.answer_callback_query(call.id, "⚠️ حذف شده!")

@bot.callback_query_handler(func=lambda c: c.data.startswith("sprice:"))
def admin_sub_price(call):
    if call.from_user.id != config.ADMIN_ID: return
    sid = int(call.data.split(":", 1)[1])
    bot.answer_callback_query(call.id)
    msg = bot.send_message(config.ADMIN_ID, "✏️ قیمت جدید رو بفرست (برای توافقی «-»):")
    bot.register_next_step_handler(msg, sub_price_save, sid)

def sub_price_save(message, sid):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:", sub_price_save, sid)
    set_sub_price(sid, message.text)
    bot.send_message(config.ADMIN_ID, "✅ قیمت آپدیت شد!", reply_markup=admin_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("sqty:"))
def admin_sub_qty(call):
    if call.from_user.id != config.ADMIN_ID: return
    sid = int(call.data.split(":", 1)[1])
    bot.answer_callback_query(call.id)
    msg = bot.send_message(config.ADMIN_ID, "🔢 حداقل تعداد رو بفرست (بدون محدودیت = «-»):")
    bot.register_next_step_handler(msg, sub_qty_min, sid)

def sub_qty_min(message, sid):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:", sub_qty_min, sid)
    msg = bot.send_message(config.ADMIN_ID, "🔢 حداکثر تعداد رو بفرست (بدون محدودیت = «-»):")
    bot.register_next_step_handler(msg, sub_qty_max, sid, message.text)

def sub_qty_max(message, sid, mn):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:", sub_qty_max, sid, mn)
    set_sub_qty(sid, mn, message.text)
    bot.send_message(config.ADMIN_ID, "✅ محدودیت تعداد آپدیت شد!", reply_markup=admin_kb())

@bot.callback_query_handler(func=lambda c: c.data.startswith("addsub:"))
def admin_sub_add(call):
    if call.from_user.id != config.ADMIN_ID: return
    key = call.data.split(":", 1)[1]
    bot.answer_callback_query(call.id)
    msg = bot.send_message(config.ADMIN_ID, "🧩 (۱) نام محصول رو بفرست:")
    bot.register_next_step_handler(msg, sub_add_name, key)

def sub_add_name(message, key):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:\n\n🧩 (۱) نام محصول:", sub_add_name, key)
    msg = bot.send_message(config.ADMIN_ID, "💰 (۲) قیمت رو بفرست (برای توافقی «-»):")
    bot.register_next_step_handler(msg, sub_add_price, key, message.text)

def sub_add_price(message, key, name):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:\n\n💰 (۲) قیمت:", sub_add_price, key, name)
    msg = bot.send_message(config.ADMIN_ID, "🔢 (۳) حداقل تعداد رو بفرست (بدون محدودیت = «-»):")
    bot.register_next_step_handler(msg, sub_add_min, key, name, message.text)

def sub_add_min(message, key, name, price):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:", sub_add_min, key, name, price)
    msg = bot.send_message(config.ADMIN_ID, "🔢 (۴) حداکثر تعداد رو بفرست (بدون محدودیت = «-»):")
    bot.register_next_step_handler(msg, sub_add_max, key, name, price, message.text)

def sub_add_max(message, key, name, price, mn):
    global pending_wh_post
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:", sub_add_max, key, name, price, mn)
    mx = message.text
    save_sub_product(key, name, price, mn, mx)
    ch = get_setting("warehouse_channel")
    if not ch:
        bot.send_message(config.ADMIN_ID,
            f"✅ «{name}» به دستگاه اضافه شد!\n"
            "الان کاربرا می‌تونن ببیننش 🛍\n\n"
            "💡 برای پست خودکار تو چنل انبار، اول از پنل ادمین چنل رو ثبت کن.",
            reply_markup=admin_kb())
        return
    pending_wh_post = (key, name, price, mn)
    kb = InlineKeyboardMarkup()
    kb.add(InlineKeyboardButton("✅ آره، پستش کن", callback_data="whpost:yes"),
           InlineKeyboardButton("❌ نه، لازم نیست", callback_data="whpost:no"))
    bot.send_message(config.ADMIN_ID,
        f"✅ «{name}» به دستگاه اضافه شد!\n\n"
        "📦 این محصول تو چنل انبار هم پست بشه؟",
        reply_markup=kb)

# ==================== چنل انبار ====================

@bot.callback_query_handler(func=lambda c: c.data == "whset")
def wh_set(call):
    if call.from_user.id != config.ADMIN_ID: return
    bot.answer_callback_query(call.id)
    msg = bot.send_message(config.ADMIN_ID,
        "📦 آیدی چنل انبار رو بفرست (مثل @onyx_store):\n\n"
        "⚠️ قبلش حتماً ربات رو تو چنل «ادمین» کن با دسترسی ارسال پیام!\n"
        "❌ برای لغو /cancel")
    bot.register_next_step_handler(msg, wh_save)

def wh_save(message):
    if is_cancel(message): return cancel_action(message)
    if not message.text:
        return reask(config.ADMIN_ID, "⚠️ متنی بفرست:\n\n📦 آیدی چنل (مثل @onyx_store):", wh_save)
    ch = message.text.strip()
    try:
        test = bot.send_message(ch, "🔌 تست اتصال چنل انبار...")
        try:
            bot.delete_message(ch, test.message_id)
        except Exception:
            pass
    except Exception:
        return reask(config.ADMIN_ID,
            "❌ نتونستم به این چنل پیام بدم!\n"
            "مطمئن شو ربات تو چنل «ادمین» شده با دسترسی ارسال پیام.\n\n"
            "📦 دوباره آیدی چنل رو بفرست:", wh_save)
    set_setting("warehouse_channel", ch)
    bot.send_message(config.ADMIN_ID, f"✅ چنل انبار ثبت شد: {ch}", reply_markup=admin_kb())

def warehouse_post_text(key, name, price, mn):
    device = get_product(key)
    dname = device["name"] if device else ""
    price_txt = price if price and price != "-" else "توافقی — دایرکت پیام بده"
    bot_user = f"@{get_bot_username()}"
    txt = (
        "<b>𓆩 𝐎𝐍𝐘𝐗 𝐒𝐓𝐎𝐑𝐄 𓆪</b>\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        f"⭐ <b>{html_mod.escape(name)}</b>\n\n"
        f"{html_mod.escape(dname)}\n\n"
    )
    if mn and mn != "-":
        txt += f"▪️ حداقل سفارش: {html_mod.escape(mn)} عدد\n"
    txt += (
        f"▪️ قیمت هر عدد: {html_mod.escape(price_txt)}\n\n"
        "💎 ساده، شیک و اقتصادی\n\n"
        "🛍 ثبت سفارش از طریق ربات:\n"
        f"🤖 {bot_user}\n\n"
        f"👤 ارتباط مستقیم: {config.ADMIN_USERNAME}\n\n"
        "━━━━━━━━━━━━━━━━━━\n"
        "<b>𓆩 𝐎𝐍𝐘𝐗 𝐒𝐓𝐎𝐑𝐄 𓆪 🖤</b>"
    )
    return txt

@bot.callback_query_handler(func=lambda c: c.data in ("whpost:yes", "whpost:no"))
def wh_post_action(call):
    global pending_wh_post
    if call.from_user.id != config.ADMIN_ID: return
    bot.answer_callback_query(call.id)
    if not pending_wh_post:
        return try_edit(call.message.chat.id, call.message.message_id, "⚠️ چیزی برای پست نیست!", None)
    if call.data == "whpost:no":
        pending_wh_post = None
        return try_edit(call.message.chat.id, call.message.message_id,
                        "❌ پست در چنل انبار لغو شد.", None)
    key, name, price, mn = pending_wh_post
    pending_wh_post = None
    ch = get_setting("warehouse_channel")
    url_kb = InlineKeyboardMarkup()
    url_kb.add(InlineKeyboardButton("🛍 خرید خدمات از ربات", url=f"https://t.me/{get_bot_username()}"))
    try:
        bot.send_message(ch, warehouse_post_text(key, name, price, mn),
                         parse_mode="HTML", disable_web_page_preview=True,
                         reply_markup=url_kb)
        try_edit(call.message.chat.id, call.message.message_id,
                 "✅ تو چنل انبار پست شد! 📦", None)
    except Exception as e:
        try_edit(call.message.chat.id, call.message.message_id,
                 f"❌ ارسال به چنل نشد!\n\n⚠️ خطا: {e}", None)

@bot.callback_query_handler(func=lambda c: c.data == "whtest")
def wh_test(call):
    if call.from_user.id != config.ADMIN_ID: return
    bot.answer_callback_query(call.id)
    ch = get_setting("warehouse_channel")
    if not ch:
        return bot.send_message(config.ADMIN_ID, "❌ اول چنل رو ثبت کن!")
    url_kb = InlineKeyboardMarkup()
    url_kb.add(InlineKeyboardButton("🛍 خرید خدمات از ربات", url=f"https://t.me/{get_bot_username()}"))
    try:
        bot.send_message(ch, warehouse_post_text("test", "محصول آزمایشی ✨", "۵,۰۰۰ تومان", "۵"),
                         parse_mode="HTML", disable_web_page_preview=True, reply_markup=url_kb)
        bot.send_message(config.ADMIN_ID,
            f"✅ پست آزمایشی ارسال شد به: {ch}\n👉 برو چنل رو چک کن!")
    except Exception as e:
        bot.send_message(config.ADMIN_ID, f"❌ ارسال نشد!\n\n⚠️ خطا: {e}")

# ==================== بکاپ خودکار دیتابیس ====================
import os
import glob
from datetime import datetime as dt

BACKUP_CHAT_ID = config.ADMIN_ID  # بکاپ‌ها به پیوی ادمین می‌رن
BACKUP_HOUR = 3                   # هر روز ساعت ۳ (به وقت سرور)

_last_backup_day = {"day": None}

def send_db_backup():
    """فایل دیتابیس رو به پیوی ادمین می‌فرسته"""
    try:
        if not os.path.exists(DB_NAME):
            return
        with open(DB_NAME, "rb") as f:
            bot.send_document(BACKUP_CHAT_ID, f,
                caption=f"📦 بکاپ خودکار دیتابیس\n📅 {now()}")
    except Exception as e:
        print(f"backup send error: {e}")

def _backup_loop():
    """حلقه‌ای که هر روز سر ساعت بکاپ می‌فرسته"""
    import threading as _th
    def runner():
        while True:
            today = dt.now().strftime("%Y-%m-%d")
            current_hour = dt.now().hour
            if _last_backup_day["day"] != today and current_hour >= BACKUP_HOUR:
                _last_backup_day["day"] = today
                send_db_backup()
            time.sleep(60 * 10)  # هر ۱۰ دقیقه چک می‌کنه
    t = _th.Thread(target=runner, daemon=True)
    t.start()

def restore_if_empty():
    """اگه دیتابیس خالی بود (رندر ری‌استارت شده)، آخرین بکاپ از تلگرام برمی‌گرده"""
    try:
        con = db()
        c = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        o = con.execute("SELECT COUNT(*) FROM orders").fetchone()[0]
        con.close()
        if c > 0 or o > 0:
            print("✅ دیتابیس سالمه — بکاپ لازم نیست")
            return

        # دنبال آخرین فایل بکاپ تو خود سرور بگرد (اگه از قبل دانلود شده)
        backups = sorted(glob.glob("restore_*.db"))
        if backups:
            import shutil
            shutil.copy(backups[-1], DB_NAME)
            print("♻️ دیتابیس از بکاپ لوکال بازیابی شد")
            return

        # از تلگرام بخواه بکاپو بفرسته
        bot.send_message(BACKUP_CHAT_ID,
            "⚠️ سرور ری‌استارت شده و دیتابیس خالیه!\n\n"
            "📤 آخرین فایل بکاپ (.db) که برات اومده رو **فوروارد کن همینجا** —\n"
            "ربات خودش برمی‌گردونه و سفارشا نجات پیدا می‌کنن.")
    except Exception as e:
        print(f"restore check error: {e}")

@bot.message_handler(content_types=['document'])
def restore_backup_doc(message):
    """اگه ادمین فایل .db فرستاد → بازیابی دیتابیس"""
    if message.from_user.id != config.ADMIN_ID: return
    doc = message.document
    if not (doc.file_name and doc.file_name.endswith(".db")):
        bot.reply_to(message, "⚠️ فقط فایل .db قبوله")
        return
    try:
        fi = bot.get_file(doc.file_id)
        downloaded = bot.download_file(fi.file_path)
        with open("restore_tmp.db", "wb") as f:
            f.write(downloaded)
        import shutil
        shutil.copy("restore_tmp.db", "restore_" + dt.now().strftime("%Y%m%d") + ".db")
        shutil.copy("restore_tmp.db", DB_NAME)
        bot.reply_to(message,
            "♻️ دیتابیس بازیابی شد!\n"
            "🔄 برای اعمال کامل، ربات چند ثانیه دیگه خودش رو تازه می‌کنه.\n"
            "(سفارشا و کاربرا برگشتن ✅)")
        # رستارت منطقی: polling قطع و وصل
        bot.stop_polling()
    except Exception as e:
        bot.reply_to(message, f"❌ بازیابی نشد: {e}")

# اجرای بکاپ و چک بازیابی موقع استارت
try:
    restore_if_empty()
except Exception as e:
    print(f"restore error: {e}")

_backup_loop()


if __name__ == "__main__":
    init_db()
    print("✅ ربات ONYX اجرا شد")
    bot.infinity_polling()