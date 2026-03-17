import os
import sqlite3
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sms_activate_api import HeroSMSAPI

# إعداد السجلات لمراقبة الأخطاء
logging.basicConfig(level=logging.INFO)

# --- الإعدادات وجلب متغيرات البيئة ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]
API_KEY = os.getenv("SMS_ACTIVATE_API_KEY")

# معدل التحويل (من روبل إلى دولار) - يمكنك تعديله لضبط ربحك
# مثال: إذا كان السعر 50 روبل، سيصبح بالدولار 50 * 0.015 = 0.75$
RUB_TO_USD = 0.015 

bot = Bot(token=TOKEN)
dp = Dispatcher()
sms = HeroSMSAPI(API_KEY)

# --- قائمة الدول المدعومة ---
COUNTRIES = {
    "0": "🇷🇺 روسيا", "1": "🇺🇦 أوكرانيا", "6": "🇮🇩 إندونيسيا", 
    "15": "🇵🇱 بولندا", "22": "🇮🇳 الهند", "123": "🇺🇸 أمريكا",
    "16": "🇵🇭 الفلبين", "13": "🇻🇳 فيتنام", "32": "🇹🇭 تايلاند"
}

# --- إدارة قاعدة البيانات المحلية ---
def db_query(query, params=(), fetch=False):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.execute(query, params)
        if fetch: return cursor.fetchone()
        conn.commit()

# إنشاء الجداول
db_query("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)")
db_query("CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, user_id INTEGER, service TEXT, number TEXT)")

def get_bal(uid):
    res = db_query("SELECT balance FROM users WHERE id = ?", (uid,), True)
    if res: return res[0]
    db_query("INSERT INTO users (id, balance) VALUES (?, 0.0)", (uid,))
    return 0.0

# --- الأوامر الرئيسية ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    bal = get_bal(user_id)
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🛒 شراء رقم جديد", callback_data="services"))
    kb.row(types.InlineKeyboardButton(text="💰 رصيدي", callback_data="my_balance"),
           types.InlineKeyboardButton(text="📱 أرقامي", callback_data="my_orders"))
    kb.row(types.InlineKeyboardButton(text="🛠 الدعم الفني", url="https://t.me/your_support"))
    
    if user_id in ADMIN_IDS:
        kb.row(types.InlineKeyboardButton(text="⚙️ لوحة الإدارة", callback_data="admin_panel"))

    await message.answer(
        f"👋 أهلاً بك في متجر الأرقام العالمي\n\n"
        f"💰 رصيدك: **{round(bal, 2)}$**\n"
        f"🆔 معرفك: `{user_id}`\n\n"
        "إختر من القائمة أدناه للبدء:",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

# --- قسم اختيار الخدمات ---
@dp.callback_query(F.data == "services")
async def show_services(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    # يمكنك إضافة أي اختصارات خدمات من موقع SMS-Activate هنا
    services = {
        "wa": "واتساب ✅",
        "tg": "تلجرام ✈️",
        "go": "جوجل/يوتيوب 📧",
        "lf": "تيك توك 📱",
        "ig": "إنستقرام 📸",
        "fb": "فيسبوك 👤"
    }
    for code, name in services.items():
        kb.add(types.InlineKeyboardButton(text=name, callback_data=f"set_svc_{code}"))
    
    kb.adjust(2).row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home"))
    await call.message.edit_text("إختر الخدمة المطلوبة:", reply_markup=kb.as_markup())

# --- قسم اختيار الدول والأسعار ---
@dp.callback_query(F.data.startswith("set_svc_"))
async def show_countries_with_prices(call: types.CallbackQuery):
    service = call.data.split("_")[2]
    await call.answer("⏳ جاري جلب الأسعار اللحظية من السيرفر...")
    
    try:
        prices_data = sms.get_prices(service)
        kb = InlineKeyboardBuilder()
        found = False

        if prices_data:
            # ترتيب الدول حسب القائمة المحددة فوق
            for c_id, c_name in COUNTRIES.items():
                if c_id in prices_data and service in prices_data[c_id]:
                    srv_info = prices_data[c_id][service]
                    raw_price_rub = float(list(srv_info.keys())[0])
                    count = list(srv_info.values())[0]
                    
                    # حساب السعر بالدولار
                    price_usd = round(raw_price_rub * RUB_TO_USD, 2)
                    
                    btn_text = f"{c_name} | {price_usd}$ ({count} رقم)"
                    kb.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"order_{service}_{c_id}_{price_usd}"))
                    found = True

        if not found:
            return await call.answer("⚠️ لا تتوفر أرقام حالياً لهذه الخدمة في الدول المختارة.", show_alert=True)

        kb.adjust(1).row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="services"))
        await call.message.edit_text(f"🌍 أرقام {service.upper()} المتاحة:\n(الدولة | السعر | التوفر)", reply_markup=kb.as_markup())
    
    except Exception as e:
        logging.error(f"Error fetching prices: {e}")
        await call.answer("❌ خطأ في الاتصال بالمورد، يرجى المحاولة لاحقاً.", show_alert=True)

# --- تنفيذ عملية الشراء ---
@dp.callback_query(F.data.startswith("order_"))
async def process_order(call: types.CallbackQuery):
    _, service, country_id, price_usd = call.data.split("_")
    price_usd = float(price_usd)
    user_id = call.from_user.id
    
    if get_bal(user_id) < price_usd:
        return await call.answer("❌ رصيدك غير كافٍ لشراء هذا الرقم.", show_alert=True)

    await call.answer("📡 جاري طلب الرقم...")
    res = sms.get_number(service, country_id)
    
    if isinstance(res, dict) and "id" in res:
        # خصم الرصيد
        db_query("UPDATE users SET balance = balance - ? WHERE id = ?", (price_usd, user_id))
        
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="📩 جلب الكود", callback_data=f"get_sms_{res['id']}"))
        kb.row(types.InlineKeyboardButton(text="❌ إلغاء واسترداد", callback_data=f"cancel_{res['id']}_{price_usd}"))
        
        await call.message.edit_text(
            f"✅ تم حجز الرقم!\n\n"
            f"📱 الرقم: `{res['number']}`\n"
            f"💰 السعر: {price_usd}$\n\n"
            "⚠️ اطلب الكود في التطبيق ثم اضغط الزر بالأسفل:",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    else:
        await call.message.answer(f"❌ فشل المورد في توفير رقم: {res}")

# --- معالجة الكود والإلغاء ---
@dp.callback_query(F.data.startswith("get_sms_"))
async def get_activation_code(call: types.CallbackQuery):
    act_id = call.data.split("_")[2]
    status = sms.get_status(act_id)
    
    if "STATUS_OK" in status:
        code = status.split(":")[1]
        await call.message.answer(f"✅ كود التفعيل الخاص بك هو: `{code}`", parse_mode="Markdown")
    elif "STATUS_WAIT" in status:
        await call.answer("⏳ لم يصل الكود بعد، انتظر قليلاً ثم حاول مجدداً.", show_alert=True)
    else:
        await call.answer(f"⚠️ الحالة: {status}", show_alert=True)

@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_order(call: types.CallbackQuery):
    _, act_id, price = call.data.split("_")
    # إبلاغ الموقع بالإلغاء (الحالة 8 تعني إلغاء)
    sms.set_status(act_id, 8)
    # استرداد المبلغ للمستخدم
    db_query("UPDATE users SET balance = balance + ? WHERE id = ?", (float(price), call.from_user.id))
    await call.message.edit_text("❌ تم إلغاء الطلب بنجاح وإرجاع الرصيد لحسابك.")

# --- لوحة التحكم والبيانات الشخصية ---
@dp.callback_query(F.data == "my_balance")
async def my_balance(call: types.CallbackQuery):
    bal = get_bal(call.from_user.id)
    kb = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home"))
    await call.message.edit_text(f"💰 رصيدك الحالي: **{round(bal, 2)}$**", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ شحن رصيد مستخدم", callback_data="admin_add_bal"))
    kb.row(types.InlineKeyboardButton(text="💳 رصيد الموقع (API)", callback_data="check_api"))
    kb.row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home"))
    await call.message.edit_text("⚙️ لوحة إدارة البوت:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "check_api")
async def check_api(call: types.CallbackQuery):
    api_bal = sms.get_balance()
    await call.answer(f"💰 رصيد حسابك الأصلي في الموقع: {api_bal} روبل", show_alert=True)

@dp.callback_query(F.data == "admin_add_bal")
async def instr_add(call: types.CallbackQuery):
    await call.message.answer("لشحن رصيد مستخدم، أرسل: `الآيدي المبلغ`\nمثال: `12345678 10.5`")

@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and len(msg.text.split()) == 2)
async def admin_deposit(message: types.Message):
    try:
        uid, amt = message.text.split()
        db_query("UPDATE users SET balance = balance + ? WHERE id = ?", (float(amt), int(uid)))
        await message.answer(f"✅ تم شحن {amt}$ للآيدي {uid}")
        await bot.send_message(int(uid), f"💰 تم إضافة {amt}$ إلى رصيدك بنجاح!")
    except:
        await message.answer("❌ خطأ! الصيغة: الآيدي ثم المسافة ثم المبلغ.")

@dp.callback_query(F.data == "back_home")
async def back_home_btn(call: types.CallbackQuery):
    await start_handler(call.message)

if __name__ == "__main__":
    # هذا السطر للتشغيل المحلي فقط، Render يستخدم app.py
    pass
