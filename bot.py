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

# معامل التحويل (الروبل إلى دولار + عمولتك)
# إذا كان سعر الرقم 10 روبل، سيظهر في البوت 0.15 دولار
RUB_TO_USD = 0.015 

bot = Bot(token=TOKEN)
dp = Dispatcher()
sms = HeroSMSAPI(API_KEY)

# ترجمة الدول
COUNTRIES_NAMES = {
    "51": "مصر 🇪🇬", "95": "السعودية 🇸🇦", "48": "العراق 🇮🇶",
    "52": "المغرب 🇲🇦", "88": "فلسطين 🇵🇸", "21": "الجزائر 🇩🇿",
    "27": "تونس 🇹🇳", "91": "الأردن 🇯🇴", "107": "الإمارات 🇦🇪",
    "110": "الكويت 🇰🇼", "153": "عمان 🇴🇲", "0": "روسيا 🇷🇺",
    "12": "أمريكا 🇺🇸", "1": "أوكرانيا 🇺🇦", "22": "الهند 🇮🇳",
    "6": "إندونيسيا 🇮🇩", "10": "فيتنام 🇻🇳", "15": "بولندا 🇵🇱",
    "32": "تايلاند 🇹🇭", "4": "الفلبين 🇵🇭", "187": "جنوب أفريقيا 🇿🇦"
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
    kb.row(types.InlineKeyboardButton(text="💰 رصيدي", callback_data="my_balance"))
    if message.from_user.id in ADMIN_IDS:
        kb.row(types.InlineKeyboardButton(text="⚙️ لوحة الإدارة", callback_data="admin_panel"))
    await message.answer(f"👋 أهلاً بك في البوت\n💰 رصيدك الحالي: **{round(bal, 2)}$**", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "services")
async def show_services(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    services = {"wa": "واتساب ✅", "tg": "تلجرام ✈️", "go": "جوجل 📧", "lf": "تيك توك 📱", "ig": "إنستقرام 📸", "fb": "فيسبوك 👤"}
    for code, name in services.items():
        kb.add(types.InlineKeyboardButton(text=name, callback_data=f"set_svc_{code}"))
    kb.adjust(2).row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home"))
    await call.message.edit_text("إختر الخدمة المطلوبة:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("set_svc_") | F.data.startswith("page_"))
async def show_paged_countries(call: types.CallbackQuery):
    parts = call.data.split("_")
    service = parts[2] if parts[0] == "set" else parts[1]
    page = 0 if parts[0] == "set" else int(parts[2])
    await call.answer("⏳ جاري جلب الأسعار...")
    
    try:
        prices_data = sms.get_prices(service)
        available = []
        if isinstance(prices_data, dict):
            for c_id, srv_dict in prices_data.items():
                if service in srv_dict:
                    info = srv_dict[service]
                    keys = list(info.keys())
                    if not keys: continue
                    try:
                        # جلب السعر الخام من الموقع (بالروبل)
                        raw_p = float(keys[0]) if keys[0].replace('.','').isdigit() else float(info.get('cost', 0))
                        count = list(info.values())[0]
                        if count > 0:
                            # حساب السعر بالدولار بدقة (خانتين)
                            price_usd = round(raw_p * RUB_TO_USD, 2)
                            if price_usd < 0.01: price_usd = 0.01 # حد أدنى للسعر
                            
                            available.append({
                                "id": c_id,
                                "name": COUNTRIES_NAMES.get(str(c_id), f"دولة {c_id} 🚩"),
                                "price": "{:.2f}".format(price_usd), # تنسيق السعر كـ 0.00
                                "count": count
                            })
                    except: continue

        if not available:
            return await call.message.edit_text("⚠️ لا تتوفر أرقام حالياً.", reply_markup=InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="services")).as_markup())

        per_page = 10
        total_pages = (len(available) + per_page - 1) // per_page
        current_items = available[page*per_page : (page+1)*per_page]

        kb = InlineKeyboardBuilder()
        for item in current_items:
            kb.row(types.InlineKeyboardButton(text=f"{item['name']} | ${item['price']} ({item['count']} ق)", callback_data=f"order_{service}_{item['id']}_{item['price']}"))

        nav = []
        if page > 0: nav.append(types.InlineKeyboardButton(text="⬅️ السابق", callback_data=f"page_{service}_{page-1}"))
        if page < total_pages - 1: nav.append(types.InlineKeyboardButton(text="التالي ➡️", callback_data=f"page_{service}_{page+1}"))
        if nav: kb.row(*nav)
        kb.row(types.InlineKeyboardButton(text="🔙 قائمة الخدمات", callback_data="services"))
        await call.message.edit_text(f"🌍 أرقام {service.upper()} - صفحة {page+1}/{total_pages}:", reply_markup=kb.as_markup())
    except:
        await call.answer("❌ فشل في جلب البيانات")

@dp.callback_query(F.data.startswith("order_"))
async def process_order(call: types.CallbackQuery):
    _, svc, cid, price = call.data.split("_")
    price = float(price)
    uid = call.from_user.id
    if get_bal(uid) < price:
        return await call.answer("❌ رصيدك غير كافٍ!", show_alert=True)

    await call.answer("📡 جاري طلب الرقم...")
    res = sms.get_number(svc, cid)
    if isinstance(res, dict) and "id" in res:
        db_query("UPDATE users SET balance = balance - ? WHERE id = ?", (price, uid))
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="📩 جلب الكود", callback_data=f"get_sms_{res['id']}"))
        kb.row(types.InlineKeyboardButton(text="❌ إلغاء واسترداد", callback_data=f"cancel_{res['id']}_{price}"))
        await call.message.edit_text(f"✅ تم الحجز!\n📱 الرقم: `{res['number']}`\n💰 السعر: ${price}", reply_markup=kb.as_markup(), parse_mode="Markdown")
        
        # إلغاء تلقائي بعد 15 دقيقة
        await asyncio.sleep(900)
        status = sms.get_status(res['id'])
        if "STATUS_WAIT" in status:
            sms.set_status(res['id'], 8)
            db_query("UPDATE users SET balance = balance + ? WHERE id = ?", (price, uid))
    else:
        await call.answer(f"❌ فشل: {res}", show_alert=True)

@dp.callback_query(F.data.startswith("get_sms_"))
async def check_sms(call: types.CallbackQuery):
    act_id = call.data.split("_")[2]
    status = sms.get_status(act_id)
    if "STATUS_OK" in status:
        code = status.split(":")[1]
        await call.message.answer(f"✅ كود التفعيل: `{code}`", parse_mode="Markdown")
        sms.set_status(act_id, 6)
    else:
        await call.answer("⏳ الكود لم يصل بعد.. تأكد من طلبه في التطبيق.", show_alert=True)

@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_order(call: types.CallbackQuery):
    _, act_id, price = call.data.split("_")
    sms.set_status(act_id, 8)
    db_query("UPDATE users SET balance = balance + ? WHERE id = ?", (float(price), call.from_user.id))
    await call.message.edit_text("❌ تم إلغاء الطلب بنجاح وإعادة الرصيد.")

@dp.callback_query(F.data == "my_balance")
async def show_balance(call: types.CallbackQuery):
    bal = get_bal(call.from_user.id)
    await call.message.edit_text(f"💰 رصيدك الحالي: **{round(bal, 2)}$**\nآيديك: `{call.from_user.id}`", reply_markup=InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home")).as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "admin_panel")
async def admin_p(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    kb = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="💳 رصيد المورد", callback_data="check_api"))
    kb.row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home"))
    await call.message.edit_text("⚙️ لوحة الإدارة:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "check_api")
async def check_api(call: types.CallbackQuery):
    await call.answer(f"💰 رصيد المورد: {sms.get_balance()} RUB", show_alert=True)

@dp.callback_query(F.data == "back_home")
async def go_back(call: types.CallbackQuery):
    await start_handler(call.message)

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
