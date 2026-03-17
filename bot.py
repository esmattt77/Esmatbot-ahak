import os
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sms_activate_api import HeroSMSAPI

logging.basicConfig(level=logging.INFO)

# --- الإعدادات ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]
API_KEY = os.getenv("SMS_ACTIVATE_API_KEY")
RUB_TO_USD = 0.012  # سعر تحويل الروبل للدولار (يمكنك تعديله)

bot = Bot(token=TOKEN)
dp = Dispatcher()
sms = HeroSMSAPI(API_KEY)

# --- قائمة الدول المدعومة ---
COUNTRIES = {
    "0": "🇷🇺 روسيا", "1": "🇺🇦 أوكرانيا", "6": "🇮🇩 إندونيسيا", 
    "15": "🇵🇱 بولندا", "22": "🇮🇳 الهند", "123": "🇺🇸 أمريكا", 
    "187": "🇿🇦 جنوب أفريقيا", "16": "🇵🇭 الفلبين"
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
    kb.row(types.InlineKeyboardButton(text="🛒 شراء رقم", callback_data="services"))
    kb.row(types.InlineKeyboardButton(text="💰 رصيدي", callback_data="my_balance"))
    if message.from_user.id in ADMIN_IDS:
        kb.row(types.InlineKeyboardButton(text="⚙️ لوحة الإدارة", callback_data="admin_panel"))

    await message.answer(f"أهلاً بك في بوت الأرقام 🤖\nرصيدك: **{round(bal, 2)}$**", 
                         reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "services")
async def show_services(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="واتساب ✅", callback_data="set_svc_wa"),
           types.InlineKeyboardButton(text="تلجرام ✈️", callback_data="set_svc_tg"),
           types.InlineKeyboardButton(text="تيك توك 📱", callback_data="set_svc_lf"))
    kb.adjust(2).row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home"))
    await call.message.edit_text("إختر الخدمة:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("set_svc_"))
async def show_countries_with_prices(call: types.CallbackQuery):
    service = call.data.split("_")[2]
    await call.answer("⏳ جاري جلب الأسعار اللحظية...")
    
    prices = sms.get_prices(service)
    kb = InlineKeyboardBuilder()
    
    for c_id, c_name in COUNTRIES.items():
        country_data = prices.get(c_id, {}).get(service, {})
        if country_data:
            # نأخذ أول سعر متاح من القائمة
            raw_price_rub = float(list(country_data.keys())[0])
            count = list(country_data.values())[0]
            price_usd = round(raw_price_rub * RUB_TO_USD, 2) # التحويل للدولار
            
            btn_text = f"{c_name} | {price_usd}$ ({count} رقم)"
            kb.add(types.InlineKeyboardButton(text=btn_text, callback_data=f"order_{service}_{c_id}_{price_usd}"))
    
    kb.adjust(1).row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="services"))
    await call.message.edit_text(f"🌍 دول {service.upper()} المتوفرة:\n(الدولة | السعر | التوفر)", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("order_"))
async def process_order(call: types.CallbackQuery):
    _, service, country_id, price = call.data.split("_")
    price = float(price)
    user_id = call.from_user.id
    
    if get_bal(user_id) < price:
        return await call.answer("❌ رصيدك غير كافٍ!", show_alert=True)

    res = sms.get_number(service, country_id)
    if isinstance(res, dict) and "id" in res:
        db_query("UPDATE users SET balance = balance - ? WHERE id = ?", (price, user_id))
        kb = InlineKeyboardBuilder()
        kb.add(types.InlineKeyboardButton(text="📩 جلب الكود", callback_data=f"get_sms_{res['id']}"))
        kb.add(types.InlineKeyboardButton(text="❌ إلغاء", callback_data=f"cancel_{res['id']}"))
        await call.message.edit_text(f"✅ تم الحجز!\nالرقم: `{res['number']}`\nالسعر: {price}$", 
                                     reply_markup=kb.as_markup(), parse_mode="Markdown")
    else:
        await call.answer(f"❌ المورد يقول: {res}", show_alert=True)

# --- لوحة الأدمن (مختصرة) ---
@dp.callback_query(F.data == "admin_panel")
async def admin_main(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ شحن مستخدم", callback_data="admin_add"))
    kb.row(types.InlineKeyboardButton(text="💳 رصيد الموقع (API)", callback_data="check_api"))
    kb.row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home"))
    await call.message.edit_text("⚙️ لوحة الإدارة", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "check_api")
async def check_api(call: types.CallbackQuery):
    await call.answer(f"💰 رصيد الموقع: {sms.get_balance()}₽", show_alert=True)

@dp.callback_query(F.data == "back_home")
async def go_back(call: types.CallbackQuery):
    await start_handler(call.message)
