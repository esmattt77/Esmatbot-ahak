import os
import sqlite3
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sms_activate_api import HeroSMSAPI

logging.basicConfig(level=logging.INFO)

# الإعدادات
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]
API_KEY = os.getenv("SMS_ACTIVATE_API_KEY")
RUB_TO_USD = 0.015 

bot = Bot(token=TOKEN)
dp = Dispatcher()
sms = HeroSMSAPI(API_KEY)

# قائمة الدول
COUNTRIES_NAMES = {
    "0": "🇷🇺 روسيا", "1": "🇺🇦 أوكرانيا", "6": "🇮🇩 إندونيسيا", 
    "15": "🇵🇱 بولندا", "22": "🇮🇳 الهند", "123": "🇺🇸 أمريكا",
    "16": "🇵🇭 الفلبين", "13": "🇻🇳 فيتنام", "187": "🇿🇦 جنوب أفريقيا"
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
    await message.answer(f"🤖 مرحباً بك في بوت الأرقام.\nرصيدك: **{round(bal, 2)}$**", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "services")
async def show_services(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    services = {"wa": "واتساب ✅", "tg": "تلجرام ✈️", "go": "جوجل 📧", "lf": "تيك توك 📱"}
    for code, name in services.items():
        kb.add(types.InlineKeyboardButton(text=name, callback_data=f"set_svc_{code}"))
    kb.adjust(2).row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home"))
    await call.message.edit_text("إختر الخدمة:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("set_svc_"))
async def show_countries_with_prices(call: types.CallbackQuery):
    service = call.data.split("_")[2]
    await call.answer("⏳ جاري فحص المخزن...")
    
    try:
        prices_data = sms.get_prices(service)
        print(f"DEBUG: Data for {service}: {prices_data}") # للمراقبة في Logs
        
        kb = InlineKeyboardBuilder()
        found = False

        if isinstance(prices_data, dict) and len(prices_data) > 0:
            for c_id, srv_dict in prices_data.items():
                if service in srv_dict:
                    srv_info = srv_dict[service]
                    keys = list(srv_info.keys())
                    if not keys: continue
                    
                    try:
                        # استخراج السعر سواء كان المفتاح رقمياً أو نصياً
                        raw_price = float(keys[0]) if keys[0].replace('.','').isdigit() else float(srv_info.get('cost', 0))
                        count = list(srv_info.values())[0]
                        if count == 0: continue
                        
                        price_usd = round(raw_price * RUB_TO_USD, 2)
                        c_name = COUNTRIES_NAMES.get(str(c_id), f"دولة رقم {c_id}")
                        
                        kb.add(types.InlineKeyboardButton(text=f"{c_name} | {price_usd}$ ({count} ق)", 
                                                         callback_data=f"order_{service}_{c_id}_{price_usd}"))
                        found = True
                    except: continue

        if not found:
            return await call.message.edit_text(f"⚠️ لا تتوفر أرقام لـ {service.upper()} حالياً في الدول المختارة.\nتأكد من شحن رصيد الموقع.", 
                                               reply_markup=InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="services")).as_markup())

        kb.adjust(1).row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="services"))
        await call.message.edit_text(f"🌍 الأرقام المتاحة لـ {service.upper()}:", reply_markup=kb.as_markup())
    
    except Exception as e:
        logging.error(f"Price Error: {e}")
        await call.answer("❌ خطأ في الاتصال بالمورد.", show_alert=True)

@dp.callback_query(F.data.startswith("order_"))
async def process_order(call: types.CallbackQuery):
    _, service, c_id, price = call.data.split("_")
    price = float(price)
    user_id = call.from_user.id

    if get_bal(user_id) < price:
        return await call.answer("❌ رصيدك غير كافٍ!", show_alert=True)

    await call.answer("📡 جاري طلب الرقم...")
    res = sms.get_number(service, c_id)
    
    if isinstance(res, dict) and "id" in res:
        db_query("UPDATE users SET balance = balance - ? WHERE id = ?", (price, user_id))
        
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="📩 جلب الكود", callback_data=f"get_sms_{res['id']}"))
        kb.row(types.InlineKeyboardButton(text="❌ إلغاء واسترداد", callback_data=f"cancel_{res['id']}_{price}"))
        
        await call.message.edit_text(f"✅ تم حجز الرقم!\n\n📱 الرقم: `{res['number']}`\n💰 السعر: {price}$\n\n⚠️ اطلب الكود في التطبيق ثم اضغط الزر بالأسفل:", 
                                     reply_markup=kb.as_markup(), parse_mode="Markdown")
        
        # نظام الإلغاء التلقائي بعد 15 دقيقة إذا لم يصل كود
        await asyncio.sleep(900) 
        status = sms.get_status(res['id'])
        if "STATUS_WAIT" in status:
            sms.set_status(res['id'], 8)
            db_query("UPDATE users SET balance = balance + ? WHERE id = ?", (price, user_id))
            try: await bot.send_message(user_id, f"ℹ️ تم إلغاء الطلب رقم {res['number']} تلقائياً واسترداد الرصيد لعدم وصول كود.")
            except: pass
    else:
        await call.answer(f"❌ المورد: {res}", show_alert=True)

@dp.callback_query(F.data.startswith("get_sms_"))
async def check_sms(call: types.CallbackQuery):
    act_id = call.data.split("_")[2]
    status = sms.get_status(act_id)
    if "STATUS_OK" in status:
        code = status.split(":")[1]
        await call.message.answer(f"✅ كود التفعيل: `{code}`", parse_mode="Markdown")
        sms.set_status(act_id, 6) # إنهاء العملية بنجاح
    elif "STATUS_WAIT" in status:
        await call.answer("⏳ الكود لم يصل بعد، اطلبه في التطبيق أولاً.", show_alert=True)
    else:
        await call.answer(f"⚠️ الحالة: {status}", show_alert=True)

@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_order(call: types.CallbackQuery):
    _, act_id, price = call.data.split("_")
    sms.set_status(act_id, 8)
    db_query("UPDATE users SET balance = balance + ? WHERE id = ?", (float(price), call.from_user.id))
    await call.message.edit_text("❌ تم إلغاء الطلب بنجاح وإعادة الرصيد.")

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    kb = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="💳 رصيد المورد", callback_data="check_api"))
    kb.row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home"))
    await call.message.edit_text("⚙️ لوحة الإدارة:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "check_api")
async def check_api(call: types.CallbackQuery):
    await call.answer(f"💰 رصيد حسابك في الموقع: {sms.get_balance()} روبل", show_alert=True)

@dp.callback_query(F.data == "back_home")
async def go_back(call: types.CallbackQuery):
    await start_handler(call.message)
