🤖 ONYX Store Bot
فارسی | English

PythonpyTelegramBotAPISQLiteFlaskRenderLicense

🇮🇷 فارسی
📖 درباره پروژه
ربات ONYX Store یک پلتفرم کامل فروش خدمات مجازی تلگرام است که با هدف ساده‌سازی فرآیند فروش، مدیریت سفارشات و ارتباط با مشتری طراحی شده است. این ربات به‌صورت end-to-end از ثبت سفارش تا تحویل، تمام نیازهای یک کسب‌وکار آنلاین خدمات مجازی را پوشش می‌دهد.

این پروژه به‌عنوان نمونه‌کار پیاده‌سازی شده و توانایی‌های معماری چند‌تردی، دیپلوی ابری، مکانیزم بکاپ/بازیابی توزیع‌شده و طراحی سیستم کسب‌وکار کامل را نمایش می‌دهد.

✨ امکانات کلیدی
👤 بخش کاربر
امکان	توضیح
🛍 مرور محصولات	دسته‌بندی شده با زیرمحصولات و قیمت‌گذاری منعطف
🛒 ثبت سفارش چندمرحله‌ای	فرم پویا با آپلود فیش واریز
💰 کیف پول پوینتی	۵ پوینت هر سفارش، ۱۰ پوینت هر دعوت موفق
🎭 سیستم دعوت	لینک اختصاصی + آمار لحظه‌ای دعوت‌ها
❓ سوالات متداول	قابل مدیریت از پنل ادمین
👤 پشتیبانی آنلاین	ارسال متن/عکس/ویدیو/ویس مستقیم به ادمین
📢 عضویت اجباری	چنل‌های اجباری قابل تنظیم
💻 پنل مدیریت
امکان	توضیح
📊 داشبورد آماری	کاربران، سفارشات امروز، محصولات فعال
📦 مدیریت سفارشات	تأیید/رد + اطلاع‌رسانی خودکار به مشتری
📢 پیام همگانی	ارسال به همه کاربران با گزارش موفق/ناموفق
🛍 مدیریت محصولات	افزودن/ویرایش/حذف/فعال‌سازی محصولات و زیرمحصولات
❓ مدیریت FAQ	افزودن/حذف سوالات متداول
💬 مکالمات پشتیبانی	پاسخ مستقیم به کاربر با یک کلیک
💰 کیف پول کاربران	مشاهده کاربران ۵۰+ پوینت
📦 چنل انبار	پست خودکار محصولات جدید با قالب تبلیغاتی
📢 چنل‌های اجباری	افزودن/حذف با بررسی خودکار ادمین بودن ربات
🔄 بکاپ خودکار	ارسال روزانه دیتابیس به PV ادمین (هر شب ۳ صبح)
♻️ بازیابی خودکار	restore از فایل .db فوروارد شده توسط ادمین
🛠 تکنولوژی‌ها
دسته	تکنولوژی
زبان برنامه‌نویسی	Python 3.11
فریمورک ربات	pyTelegramBotAPI (telebot) 4.26
دیتابیس	SQLite 3
Web Framework	Flask 3.0
WSGI Server	Gunicorn / Werkzeug
Cloud Platform	Render (Free Tier)
CI/CD	Render Blueprint (auto-deploy از GitHub)
Uptime Monitoring	UptimeRobot
🏗 معماری سیستم
┌────────────────────────────────────────────────┐│                Telegram Bot API                │└─────────────────────┬──────────────────────────┘                      │                      ▼┌────────────────────────────────────────────────┐│              ONYX Bot Process                  ││  ┌──────────────────────────────────────────┐ ││  │   Thread 1: Bot Polling                 │ ││  │   (infinity_polling + auto-reconnect)   │ ││  └──────────────────────────────────────────┘ ││  ┌──────────────────────────────────────────┐ ││  │   Thread 2: Flask Health Endpoint       │ ││  │   GET /health → JSON status             │ ││  └──────────────────────────────────────────┘ ││  ┌──────────────────────────────────────────┐ ││  │   Thread 3: Backup Loop                 │ ││  │   (هر شب ساعت ۳:۰۰)                     │ ││  └──────────────────────────────────────────┘ │└─────────────────────┬──────────────────────────┘                      │                      ▼┌────────────────────────────────────────────────┐│              SQLite Database                   ││  ┌─────────┬─────────┬──────────┬───────────┐ ││  │ users   │ orders  │ products │  support  │ ││  ├─────────┼─────────┼──────────┼───────────┤ ││  │  faq    │channels │settings  │sub_product│ ││  └─────────┴─────────┴──────────┴───────────┘ │└────────────────────────────────────────────────┘
📁 ساختار پروژه
onyx-bot/├── main.py              # کد اصلی ربات (~۱۹۰۰ خط)├── config.py            # تنظیمات (توکن، ادمین، کارت)├── requirements.txt     # وابستگی‌های پایتون├── Procfile             # دستور اجرای gunicorn برای Render├── render.yaml          # Blueprint دیپلوی روی Render├── .env.example         # نمونه env vars├── .gitignore           # استثنائات git└── README.md            # همین فایل
📊 مدل داده (Database Schema)
users(user_id, name, username, referrer_id, joined_at, points, wallet_notified)orders(order_id, user_id, product_name, details, price, status, created_at)products(key, name, price, description, extra, available)sub_products(id, device_key, name, price, available, min_qty, max_qty)faq(id, question, answer)support(user_id, name, username, last_time)channels(id, ch)settings(k, value)
روابط کلیدی
users.referrer_id → users.user_id (سیستم دعوت)
orders.user_id → users.user_id (سفارشات کاربر)
sub_products.device_key → products.key (زیرمحصولات هر دسته)
🚀 راه‌اندازی محلی
پیش‌نیازها
Python 3.11+
توکن ربات از @BotFather
آیدی عددی خود از @userinfobot
نصب
# کلون کردن repogit clone https://github.com/USERNAME/onyx-bot.gitcd onyx-bot# ساخت محیط مجازیpython -m venv .venvsource .venv/bin/activate        # Linux/Mac# .venv\Scripts\activate          # Windows# نصب وابستگی‌هاpip install -r requirements.txt# پیکربندیcp .env.example .env# فایل .env را با مقادیر واقعی پر کنید# اجرای رباتpython main.py
☁️ دیپلوی روی Render (پلن رایگان)
این ربات برای دیپلوی روی Render آماده شده و شامل:

✅ Health endpoint (/health) برای جلوگیری از sleep
✅ Multi-threading با reconnect خودکار
✅ Configurable DB path (پشتیبانی از Render Disk)
✅ Auto-deploy از GitHub
مراحل دیپلوی
۱. Push به GitHub (repo باید Private باشد)

۲. در Render Dashboard:

New + → Blueprint
انتخاب repo → render.yaml خودکار پیدا می‌شود
Plan: Free
۳. در بخش Environment، متغیرهای زیر را وارد کنید:

کلید	مقدار
BOT_TOKEN	توکن از @BotFather
ADMIN_ID	آیدی عددی خودتان
ADMIN_USERNAME	یوزرنیم با @
CARD_NUMBER	شماره کارت دریافت
CARD_OWNER	نام صاحب کارت
۴. Apply → منتظر Build (~۱-۲ دقیقه)

۵. URL نهایی: https://services-xxxx.onrender.com

روشن نگه‌داشتن ۲۴/۷ (پلن رایگان)
روی Render Free، سرویس بعد از ۱۵ دقیقه بدون ترافیک sleep می‌شود. راه‌حل رایگان:

۱. در UptimeRobot ثبت‌نام کنید۲. یک Monitor از نوع HTTP(s) با URL زیر بسازید:

https://services-xxxx.onrender.com/health
۳. بازه را ۱۰ دقیقه تنظیم کنید

✅ ربات ۲۴/۷ تا یک ماه (۷۴۴ ساعت از ۷۵۰ سقف رایگان) اجرا می‌شود.

🔐 امنیت
توکن و اطلاعات حساس از environment variables خوانده می‌شوند (در production)
.gitignore فایل‌های حساس را از commit مستثنی می‌کند
پنل مدیریت فقط به ADMIN_ID پاسخ می‌دهد
بکاپ روزانه دیتابیس به PV ادمین ارسال می‌شود
مکانیزم بازیابی خودکار در صورت restart سرور
💾 استراتژی حفظ دیتابیس
روی پلن رایگان Render، فایل‌سیستم ephemeral است. این ربات از مکانیزم دوگانه برای حفظ داده استفاده می‌کند:

۱) بکاپ خودکار
هر شب ساعت ۳:۰۰ → فایل onyx.db → PV ادمین در تلگرام
۲) بازیابی خودکار
ربات restart می‌شود → دیتابیس خالی است            ↓ربات به ادمین پیام می‌دهد: "فایل .db را فوروارد کن"            ↓ادمین فایل را forward می‌کند            ↓ربات فایل را دانلود و دیتابیس را restore می‌کند            ↓✅ کاربران و سفارشات برمی‌گردن
۳) گزینه پایدارتر (اختیاری)
اضافه کردن یک Render Disk 1GB (حدود $0.25/mo) و تنظیم DB_PATH=/data/onyx.db برای حفظ دیتابیس بین restart‌ها.

📸 اسکرین‌شات‌ها
منوی اصلی	پنل ادمین
Main Menu	Admin Panel
ثبت سفارش	چنل انبار
Order Flow	Warehouse
📜 مجوز
MIT License - 2026

👨‍💻 درباره توسعه‌دهنده
این پروژه نمونه‌ای از توانایی‌های زیر است:

✅ طراحی end-to-end یک کسب‌وکار آنلاین کامل
✅ معماری multi-threading با auto-reconnect
✅ پیاده‌سازی مکانیزم backup/restore توزیع‌شده
✅ دیپلوی ابری با CI/CD و zero-downtime
✅ مدیریت SQLite با schema migration داخلی
✅ طراحی سیستم پوینت و دعوت کاربران
✅ رابط کاربری غنی با inline keyboards
✅ پیاده‌سازی middleware با decorators
✅ مدیریت استثنا و resilient design
📞 تماس
Telegram: @YOUR_USERNAME
Email: your.email@example.com
GitHub: github.com/USERNAME
🇬🇧 English
📖 About
ONYX Store is a comprehensive Telegram bot platform for selling virtual services (stars, gifts, fake members, etc.) designed to streamline the sales process, order management, and customer communication. This bot handles end-to-end operations from order placement to delivery, covering all the needs of an online virtual services business.

This project is implemented as a portfolio piece demonstrating capabilities in multi-threaded architecture, cloud deployment, distributed backup/restore mechanisms, and complete business system design.

✨ Key Features
👤 User Section
Feature	Description
🛍 Product browsing	Categorized with sub-products and flexible pricing
🛒 Multi-step ordering	Dynamic form with payment receipt upload
💰 Points wallet	5 points per order, 10 per successful referral
🎭 Referral system	Personal link + real-time referral stats
❓ FAQ	Manageable from admin panel
👤 Online support	Send text/photo/video/voice directly to admin
📢 Required membership	Configurable required channel subscriptions
💻 Admin Panel
Feature	Description
📊 Statistics dashboard	Users, today's orders, active products
📦 Order management	Approve/reject + auto-notify customer
📢 Broadcast messages	Send to all users with success/fail report
🛍 Product management	Add/edit/delete/activate products & sub-products
❓ FAQ management	Add/remove FAQ entries
💬 Support conversations	Direct reply to user with one click
💰 User wallets	View users with 50+ points
📦 Warehouse channel	Auto-post new products with ad template
📢 Required channels	Add/remove with bot-admin check
🔄 Auto backup	Daily DB backup to admin's PM (3 AM)
♻️ Auto restore	Restore from .db file forwarded by admin
🛠 Tech Stack
Category	Technology
Programming Language	Python 3.11
Bot Framework	pyTelegramBotAPI (telebot) 4.26
Database	SQLite 3
Web Framework	Flask 3.0
WSGI Server	Gunicorn / Werkzeug
Cloud Platform	Render (Free Tier)
CI/CD	Render Blueprint (auto-deploy from GitHub)
Uptime Monitoring	UptimeRobot
🏗 System Architecture
┌────────────────────────────────────────────────┐│                Telegram Bot API                │└─────────────────────┬──────────────────────────┘                      │                      ▼┌────────────────────────────────────────────────┐│              ONYX Bot Process                  ││  ┌──────────────────────────────────────────┐ ││  │   Thread 1: Bot Polling                 │ ││  │   (infinity_polling + auto-reconnect)   │ ││  └──────────────────────────────────────────┘ ││  ┌──────────────────────────────────────────┐ ││  │   Thread 2: Flask Health Endpoint       │ ││  │   GET /health → JSON status             │ ││  └──────────────────────────────────────────┘ ││  ┌──────────────────────────────────────────┐ ││  │   Thread 3: Backup Loop                 │ ││  │   (daily at 3:00 AM)                    │ ││  └──────────────────────────────────────────┘ │└─────────────────────┬──────────────────────────┘                      │                      ▼┌────────────────────────────────────────────────┐│              SQLite Database                   ││  ┌─────────┬─────────┬──────────┬───────────┐ ││  │ users   │ orders  │ products │  support  │ ││  ├─────────┼─────────┼──────────┼───────────┤ ││  │  faq    │channels │settings  │sub_product│ ││  └─────────┴─────────┴──────────┴───────────┘ │└────────────────────────────────────────────────┘
📁 Project Structure
onyx-bot/├── main.py              # Main bot code (~1900 lines)├── config.py            # Configuration (token, admin, card)├── requirements.txt     # Python dependencies├── Procfile             # Gunicorn start command for Render├── render.yaml          # Render Blueprint deployment├── .env.example         # Sample env vars├── .gitignore           # Git exceptions└── README.md            # This file
📊 Database Schema
users(user_id, name, username, referrer_id, joined_at, points, wallet_notified)orders(order_id, user_id, product_name, details, price, status, created_at)products(key, name, price, description, extra, available)sub_products(id, device_key, name, price, available, min_qty, max_qty)faq(id, question, answer)support(user_id, name, username, last_time)channels(id, ch)settings(k, value)
Key Relationships
users.referrer_id → users.user_id (referral system)
orders.user_id → users.user_id (user orders)
sub_products.device_key → products.key (sub-products per category)
🚀 Local Setup
Prerequisites
Python 3.11+
Bot token from @BotFather
Your numeric ID from @userinfobot
Installation
# Clone repositorygit clone https://github.com/USERNAME/onyx-bot.gitcd onyx-bot# Create virtual environmentpython -m venv .venvsource .venv/bin/activate        # Linux/Mac# .venv\Scripts\activate          # Windows# Install dependenciespip install -r requirements.txt# Configurationcp .env.example .env# Fill .env with real values# Run the botpython main.py
☁️ Deploy on Render (Free Tier)
This bot is ready for Render deployment and includes:

✅ Health endpoint (/health) to prevent sleep
✅ Multi-threading with auto-reconnect
✅ Configurable DB path (supports Render Disk)
✅ Auto-deploy from GitHub
Deployment Steps
Push to GitHub (repo must be Private)
In Render Dashboard:
New + → Blueprint
Select repo → render.yaml is auto-detected
Plan: Free
In the Environment section, set these variables:
Key	Value
BOT_TOKEN	Token from @BotFather
ADMIN_ID	Your numeric ID
ADMIN_USERNAME	Your username with @
CARD_NUMBER	Payment card number
CARD_OWNER	Card owner name
Apply → Wait for build (~1-2 minutes)
Final URL: https://services-xxxx.onrender.com
Keep it Running 24/7 (Free Tier)
On Render Free, the service sleeps after 15 minutes of inactivity. Free solution:

Sign up at UptimeRobot
Create an HTTP(s) Monitor with URL:
https://services-xxxx.onrender.com/health
Set interval to 10 minutes
✅ The bot runs 24/7 for a month (744 hours out of 750 free limit).

🔐 Security
Tokens and sensitive info are read from environment variables (in production)
.gitignore excludes sensitive files from commits
Admin panel only responds to ADMIN_ID
Daily database backup sent to admin's PM
Auto-restore mechanism on server restart
💾 Database Persistence Strategy
On Render Free tier, the filesystem is ephemeral. This bot uses a dual mechanism to preserve data:

1) Automatic Backup
Every night at 3:00 AM → onyx.db file → admin's PM in Telegram
2) Automatic Restore
Bot restarts → database is empty        ↓Bot messages admin: "Forward the .db file"        ↓Admin forwards the file        ↓Bot downloads and restores the database        ↓✅ Users and orders are back
3) More Stable Option (Optional)
Add a Render Disk 1GB (~$0.25/mo) and set DB_PATH=/data/onyx.db to persist the database across restarts.

📸 Screenshots
Main Menu	Admin Panel
Main Menu	Admin Panel
Order Flow	Warehouse
Order Flow	Warehouse
📜 License
MIT License - 2026

👨‍💻 About the Developer
This project demonstrates the following capabilities:

✅ End-to-end design of a complete online business
✅ Multi-threaded architecture with auto-reconnect
✅ Distributed backup/restore mechanism
✅ Cloud deployment with CI/CD and zero-downtime
✅ SQLite management with internal schema migration
✅ Points and referral system design
✅ Rich UI with inline keyboards
✅ Middleware implementation with decorators
✅ Exception handling and resilient design
📞 Contact
Telegram: @YOUR_USERNAME
Email: your.email@example.com
GitHub: github.com/USERNAME
⭐ If you found this project helpful, please give it a Star!