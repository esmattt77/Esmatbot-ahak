import os
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sms_activate_api import HeroSMSAPI

# إعداد السجلات
logging.basicConfig(level=logging.INFO)

# الإعدادات
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]
API_KEY = os.getenv("SMS_ACTIVATE_API_KEY")
RUB_TO_USD = 0.015  # يمكنك تعديل نسبة الربح هنا

bot = Bot(token=TOKEN)
dp = Dispatcher()
sms = HeroSMSAPI(API_KEY)

# قائمة الدول الأساسية
COUNTRIES = {
    "0": "🇷🇺 روسيا", "1": "🇺🇦 أوكرانيا", "6": "🇮🇩 إندونيسيا", 
    "15": "🇵🇱 بولندا", "22": "🇮🇳 الهند", "123": "🇺🇸 أمريكا",
    "16": "🇵🇭 الفلبين", "13": "🇻🇳 فيتنام", "32": "🇹🇭 تايلاند"
}

# --- قاعدة البيانات ---
def db_query(query, params=(), fetch=False):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.execute(query, params)
        if fetch: return cursor.fetchone()
        conn.commit()

db_query("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)")

def get_bal(uid):
    res = db_query("SELECT balance FROM users WHERE id = ?", (uid,), True)
    if res: return res[0]
    db_query("INSERT INTO users (id, balance) VALUES (?, 0.0)", (uid,))
    return 0.0

# --- الأوامر ---
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    bal = get_bal(message.from_user.id)
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🛒 شراء رقم جديد", callback_data="services"))
    kb.row(types.InlineKeyboardButton(text="💰 رصيدي", callback_data="my_balance"),
           types.InlineKeyboardButton(text="🛠 الدعم", url="https://t.me/your_support"))
    if message.from_user.id in ADMIN_IDS:
        kb.row(types.InlineKeyboardButton(text="⚙️ لوحة الإدارة", callback_data="admin_panel"))

    await message.answer(f"أهلاً بك في بوت الأرقام المتطور 🤖\nرصيدك الحالي: **{round(bal, 2)}$**", 
                         reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "services")
async def show_services(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    services = {"wa": "واتساب ✅", "tg": "تلجرام ✈️", "go": "جوجل 📧", "lf": "تيك توك 📱"}
    for code, name in services.items():
        kb.add(types.InlineKeyboardButton(text=name, callback_data=f"set_svc_{code}"))
    kb.adjust(2).row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home"))
    await call.message.edit_text("إختر الخدمة المطلوبة:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("set_svc_"))
async def show_countries_with_prices(call: types.CallbackQuery):
    service = call.data.split("_")[2]
    # حل مشكلة الـ Timeout: الرد فوراً على تلجرام
    await call.answer("⏳ جاري التحميل...")
    
    try:
        prices_data = sms.get_prices(service)
        kb = InlineKeyboardBuilder()
        found = False

        if isinstance(prices_data, dict):
            for c_id, c_name in COUNTRIES.items():
                if c_id in prices_data and service in prices_data[c_id]:
                    srv_info = prices_data[c_id][service]
                    # معالجة آمنة لجلب السعر
                    prices_list = list(srv_info.keys())
                    if prices_list and prices_list[0].isdigit() or "." in prices_list[0]:
                        raw_price_rub = float(prices_list[0])
                        count = list(srv_info.values())[0]
                        price_usd = round(raw_price_rub * RUB_TO_USD, 2)
                        
                        btn_text = f"{c_name} | {price_usd}$ ({count} ق)"
                        kb.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"order_{service}_{c_id}_{price_usd}"))
                        found = True

        if not found:
            return await call.message.edit_text("⚠️ نعتذر، لا تتوفر أرقام لهذه الخدمة حالياً.", 
                                               reply_markup=InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="services")).as_markup())

        kb.adjust(1).row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="services"))
        await call.message.edit_text(f"🌍 أرقام {service.upper()} المتاحة:", reply_markup=kb.as_markup())
    
    except Exception as e:
        logging.error(f"Error: {e}")
        await call.answer("❌ خطأ فني في جلب البيانات.", show_alert=True)

@dp.callback_query(F.data.startswith("order_"))
async def process_order(call: types.CallbackQuery):
    _, service, country_id, price = call.data.split("_")
    price = float(price)
    user_id = call.from_user.id
    
    if get_bal(user_id) < price:
        return await call.answer("❌ رصيدك غير كافٍ!", show_alert=True)

    await call.answer("📡 جاري طلب الرقم...")
    res = sms.get_number(service, country_id)
    if isinstance(res, dict) and "id" in res:
        db_query("UPDATE users SET balance = balance - ? WHERE id = ?", (price, user_id))
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="📩 جلب الكود", callback_data=f"get_sms_{res['id']}"))
        kb.row(types.InlineKeyboardButton(text="❌ إلغاء", callback_data=f"cancel_{res['id']}_{price}"))
        await call.message.edit_text(f"✅ تم الحجز!\nالرقم: `{res['number']}`\nالسعر: {price}$", 
                                     reply_markup=kb.as_markup(), parse_mode="Markdown")
    else:
        await call.answer(f"❌ المورد: {res}", show_alert=True)

@dp.callback_query(F.data.startswith("get_sms_"))
async def check_sms(call: types.CallbackQuery):
    act_id = call.data.split("_")[2]
    status = sms.get_status(act_id)
    if "STATUS_OK" in status:
        code = status.split(":")[1]
        await call.message.answer(f"✅ كود التفعيل: `{code}`", parse_mode="Markdown")
    else:
        await call.answer("⏳ لم يصل الكود بعد، حاول مجدداً بعد ثوانٍ.", show_alert=True)

@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_order(call: types.CallbackQuery):
    _, act_id, price = call.data.split("_")
    sms.set_status(act_id, 8)
    db_query("UPDATE users SET balance = balance + ? WHERE id = ?", (float(price), call.from_user.id))
    await call.message.edit_text("❌ تم الإلغاء واسترداد الرصيد.")

@dp.callback_query(F.data == "admin_panel")
async def admin_main(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="💳 رصيد الموقع", callback_data="check_api"))
    kb.row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home"))
    await call.message.edit_text("⚙️ لوحة الإدارة:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "check_api")
async def check_api(call: types.CallbackQuery):
    await call.answer(f"💰 رصيد المورد: {sms.get_balance()} روبل", show_alert=True)

@dp.callback_query(F.data == "back_home")
async def go_back(call: types.CallbackQuery):
    await start_handler(call.message)
