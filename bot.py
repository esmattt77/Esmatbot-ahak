import os
import sqlite3
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sms_activate_api import HeroSMSAPI

logging.basicConfig(level=logging.INFO)

# --- الإعدادات ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]
API_KEY = os.getenv("SMS_ACTIVATE_API_KEY")

# الربح: نضرب سعر الموقع في 1.25 (ربح 25%) ثم نحول للدولار (0.011)
# يمكنك تعديل 0.015 للتحكم في السعر النهائي للمستخدم
PRICE_MULTIPLIER = 0.015 

bot = Bot(token=TOKEN)
dp = Dispatcher()
sms = HeroSMSAPI(API_KEY)

# ترجمة شاملة مرتبة
COUNTRIES = {
    "51": "مصر 🇪🇬", "95": "السعودية 🇸🇦", "48": "العراق 🇮🇶", "52": "المغرب 🇲🇦",
    "88": "فلسطين 🇵🇸", "21": "الجزائر 🇩🇿", "91": "الأردن 🇯🇴", "107": "الإمارات 🇦🇪",
    "0": "روسيا 🇷🇺", "12": "أمريكا 🇺🇸", "22": "الهند 🇮🇳", "15": "بولندا 🇵🇱"
}

# --- قاعدة البيانات ---
def db_query(query, params=(), fetch=False):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.execute(query, params)
        if fetch: return cursor.fetchone() if fetch == "one" else cursor.fetchall()
        conn.commit()

db_query("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)")

# --- الأوامر ---
@dp.message(Command("start"))
async def start(message: types.Message):
    user_id = message.from_user.id
    res = db_query("SELECT balance FROM users WHERE id = ?", (user_id,), "one")
    bal = res[0] if res else 0.0
    if not res: db_query("INSERT INTO users (id, balance) VALUES (?, 0.0)", (user_id,))
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🛒 شراء رقم", callback_data="services"))
    kb.row(types.InlineKeyboardButton(text="💰 رصيدي", callback_data="balance"))
    if user_id in ADMIN_IDS:
        kb.row(types.InlineKeyboardButton(text="⚙️ لوحة التحكم", callback_data="admin"))
    
    await message.answer(f"🚀 أهلاً بك في بوت الأرقام المتطور\n💰 رصيدك: **${round(bal, 2)}**", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "services")
async def services(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    srvs = {"wa": "واتساب ✅", "tg": "تلجرام ✈️", "go": "جوجل 📧", "lf": "تيك توك 📱", "ig": "إنستقرام 📸"}
    for k, v in srvs.items(): kb.add(types.InlineKeyboardButton(text=v, callback_data=f"svc_{k}"))
    kb.adjust(2).row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="home"))
    await call.message.edit_text("إختر الخدمة:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("svc_") | F.data.startswith("p_"))
async def list_countries(call: types.CallbackQuery):
    data = call.data.split("_")
    service = data[1]
    page = int(data[2]) if len(data) > 2 else 0
    
    await call.answer("⏳ جاري جلب الأرقام المتاحة...")
    raw_prices = sms.get_prices(service)
    parsed = []

    # معالجة اختلاف رد الـ API (قاموس أو مصفوفة)
    items = raw_prices.items() if isinstance(raw_prices, dict) else enumerate(raw_prices)
    
    for c_id, srv_data in items:
        # فحص وجود الخدمة داخل بيانات الدولة
        if service in srv_data:
            s_info = srv_data[service]
            try:
                # جلب السعر (قد يكون في مفتاح 'cost' أو كأول مفتاح في القاموس)
                cost_rub = float(s_info.get('cost', list(s_info.keys())[0]))
                count = s_info.get('count', list(s_info.values())[0])
                if count > 0:
                    price_usd = max(0.01, round(cost_rub * PRICE_MULTIPLIER, 2))
                    parsed.append({"id": str(c_id), "name": COUNTRIES.get(str(c_id), f"دولة {c_id}"), "price": price_usd, "count": count})
            except: continue

    if not parsed:
        return await call.message.edit_text("❌ لا تتوفر أرقام حالياً لهذه الخدمة.", reply_markup=InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🔙", callback_data="services")).as_markup())

    # نظام الصفحات (10 لكل صفحة)
    start, end = page*10, (page+1)*10
    kb = InlineKeyboardBuilder()
    for item in parsed[start:end]:
        kb.row(types.InlineKeyboardButton(text=f"{item['name']} | ${item['price']} ({item['count']} ق)", callback_data=f"buy_{service}_{item['id']}_{item['price']}"))
    
    nav = []
    if page > 0: nav.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"p_{service}_{page-1}"))
    if end < len(parsed): nav.append(types.InlineKeyboardButton(text="➡️", callback_data=f"p_{service}_{page+1}"))
    if nav: kb.row(*nav)
    kb.row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="services"))
    
    await call.message.edit_text(f"🌍 اختر الدولة (صفحة {page+1}):", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def buy_num(call: types.CallbackQuery):
    _, svc, cid, price = call.data.split("_")
    user_id = call.from_user.id
    price = float(price)
    
    bal = db_query("SELECT balance FROM users WHERE id = ?", (user_id,), "one")[0]
    if bal < price: return await call.answer("❌ رصيدك غير كافٍ!", show_alert=True)

    res = sms.get_number(svc, cid)
    # التعامل مع رد JSON الجديد (getNumberV2)
    if isinstance(res, dict) and ("activationId" in res or "id" in res):
        act_id = res.get("activationId") or res.get("id")
        num = res.get("phoneNumber") or res.get("number")
        db_query("UPDATE users SET balance = balance - ? WHERE id = ?", (price, user_id))
        
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="📩 جلب الكود", callback_data=f"get_{act_id}"))
        kb.row(types.InlineKeyboardButton(text="❌ إلغاء واسترداد", callback_data=f"can_{act_id}_{price}"))
        await call.message.edit_text(f"✅ تم الحجز!\n📱 الرقم: `{num}`\n💰 السعر: ${price}", reply_markup=kb.as_markup(), parse_mode="Markdown")
    else:
        await call.answer(f"❌ خطأ من المصدر: {res}", show_alert=True)

@dp.callback_query(F.data.startswith("get_"))
async def get_sms(call: types.CallbackQuery):
    act_id = call.data.split("_")[1]
    status = sms.get_status(act_id)
    if "STATUS_OK" in status:
        code = status.split(":")[1]
        await call.message.answer(f"✅ كود التفعيل الخاص بك: `{code}`", parse_mode="Markdown")
    else:
        await call.answer("⏳ لم يصل الكود بعد، انتظر قليلاً ثم حاول مجدداً.", show_alert=True)

@dp.callback_query(F.data.startswith("can_"))
async def cancel(call: types.CallbackQuery):
    _, act_id, price = call.data.split("_")
    sms.set_status(act_id, 8)
    db_query("UPDATE users SET balance = balance + ? WHERE id = ?", (float(price), call.from_user.id))
    await call.message.edit_text("❌ تم إلغاء الطلب وإعادة الرصيد.")

# --- لوحة الإدارة (Admin) ---
@dp.callback_query(F.data == "admin")
async def admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="💳 رصيد Hero-SMS", callback_data="adm_bal"))
    kb.row(types.InlineKeyboardButton(text="👥 عدد المستخدمين", callback_data="adm_users"))
    kb.row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="home"))
    await call.message.edit_text("⚙️ لوحة التحكم للمسؤول:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "adm_bal")
async def adm_bal(call: types.CallbackQuery):
    await call.answer(f"💰 رصيد الموقع: {sms.get_balance()} RUB", show_alert=True)

@dp.callback_query(F.data == "home")
async def home(call: types.CallbackQuery):
    await start(call.message)

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
