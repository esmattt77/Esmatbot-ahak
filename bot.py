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
RUB_TO_USD = 0.015 

bot = Bot(token=TOKEN)
dp = Dispatcher()
sms = HeroSMSAPI(API_KEY)

# --- قاموس ترجمة الدول (شامل) ---
COUNTRIES_NAMES = {
COUNTRIES_NAMES = {
    "0": "روسيا 🇷🇺",
    "1": "أوكرانيا 🇺🇦",
    "2": "كازاخستان 🇰🇿",
    "3": "الصين 🇨🇳",
    "4": "الفلبين 🇵🇭",
    "5": "ميانمار 🇲🇲",
    "6": "إندونيسيا 🇮🇩",
    "7": "ماليزيا 🇲🇾",
    "8": "كينيا 🇰🇪",
    "10": "فيتنام 🇻🇳",
    "12": "أمريكا 🇺🇸",
    "15": "بولندا 🇵🇱",
    "22": "الهند 🇮🇳",
    "32": "تايلاند 🇹🇭",
    "48": "العراق 🇮🇶",
    "51": "مصر 🇪🇬",
    "52": "المغرب 🇲🇦",
    "95": "السعودية 🇸🇦"
}

# --- قاعدة البيانات ---
def db_query(query, params=(), fetch=False):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.execute(query, params)
        if fetch: return cursor.fetchone() زد
        conn.commit()

db_query("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)")

def get_bal(uid):
    res = db_query("SELECT balance FROM users WHERE id = ?", (uid,), True)
    if res: return res[0]
    db_query("INSERT INTO users (id, balance) VALUES (?, 0.0)", (uid,))
    return 0.0

# --- الأوامر الرئيسية ---
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

# --- نظام الصفحات (Pagination) ---
@dp.callback_query(F.data.startswith("set_svc_") | F.data.startswith("page_"))
async def show_countries_paged(call: types.CallbackQuery):
    parts = call.data.split("_")
    
    # تحديد الخدمة والصفحة الحالية
    if parts[0] == "set":
        service = parts[2]
        page = 0
    else:
        service = parts[1]
        page = int(parts[2])

    await call.answer("⏳ جاري التحميل...")
    
    try:
        prices_data = sms.get_prices(service)
        all_available_countries = []

        if isinstance(prices_data, dict):
            for c_id, srv_dict in prices_data.items():
                if service in srv_dict:
                    srv_info = srv_dict[service]
                    keys = list(srv_info.keys())
                    if not keys: continue
                    try:
                        raw_price = float(keys[0]) if keys[0].replace('.','').isdigit() else float(srv_info.get('cost', 0))
                        count = list(srv_info.values())[0]
                        if count > 0:
                            price_usd = round(raw_price * RUB_TO_USD, 2)
                            all_available_countries.append({
                                "id": c_id,
                                "name": COUNTRIES_NAMES.get(str(c_id), f"دولة رقم {c_id} 🚩"),
                                "price": price_usd,
                                "count": count
                            })
                    except: continue

        if not all_available_countries:
            return await call.message.edit_text("⚠️ لا تتوفر أرقام حالياً.", 
                reply_markup=InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="services")).as_markup())

        # تقسيم القائمة إلى صفحات (10 دول لكل صفحة)
        page_size = 10
        total_pages = (len(all_available_countries) + page_size - 1) // page_size
        start_idx = page * page_size
        end_idx = start_idx + page_size
        current_page_items = all_available_countries[start_idx:end_idx]

        kb = InlineKeyboardBuilder()
        for item in current_page_items:
            btn_text = f"{item['name']} | {item['price']}$ ({item['count']} ق)"
            kb.row(types.InlineKeyboardButton(text=btn_text, callback_data=f"order_{service}_{item['id']}_{item['price']}"))

        # أزرار التنقل
        nav_btns = []
        if page > 0:
            nav_btns.append(types.InlineKeyboardButton(text="⬅️ السابق", callback_data=f"page_{service}_{page-1}"))
        if page < total_pages - 1:
            nav_btns.append(types.InlineKeyboardButton(text="التالي ➡️", callback_data=f"page_{service}_{page+1}"))
        
        if nav_btns:
            kb.row(*nav_btns)

        kb.row(types.InlineKeyboardButton(text="🔙 عودة للخدمات", callback_data="services"))
        
        await call.message.edit_text(f"🌍 الأرقام المتاحة لـ {service.upper()} (صفحة {page+1}/{total_pages}):", reply_markup=kb.as_markup())

    except Exception as e:
        logging.error(f"Pagination Error: {e}")
        await call.answer("❌ حدث خطأ أثناء عرض الصفحات.", show_alert=True)

# --- استكمال الدوال (شراء، إلغاء، جلب كود) بنفس المنطق السابق ---
@dp.callback_query(F.data.startswith("order_"))
async def process_order(call: types.CallbackQuery):
    _, service, c_id, price = call.data.split("_")
    price = float(price)
    user_id = call.from_user.id
    if get_bal(user_id) < price:
        return await call.answer("❌ رصيدك غير كافٍ!", show_alert=True)

    res = sms.get_number(service, c_id)
    if isinstance(res, dict) and "id" in res:
        db_query("UPDATE users SET balance = balance - ? WHERE id = ?", (price, user_id))
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="📩 جلب الكود", callback_data=f"get_sms_{res['id']}"))
        kb.row(types.InlineKeyboardButton(text="❌ إلغاء واسترداد", callback_data=f"cancel_{res['id']}_{price}"))
        await call.message.edit_text(f"✅ تم حجز الرقم!\n📱 الرقم: `{res['number']}`\n💰 السعر: {price}$", 
                                     reply_markup=kb.as_markup(), parse_mode="Markdown")
        # إلغاء تلقائي بعد 15 دقيقة
        await asyncio.sleep(900)
        status = sms.get_status(res['id'])
        if "STATUS_WAIT" in status:
            sms.set_status(res['id'], 8)
            db_query("UPDATE users SET balance = balance + ? WHERE id = ?", (price, user_id))
    else:
        await call.answer(f"❌ المورد: {res}", show_alert=True)

@dp.callback_query(F.data.startswith("get_sms_"))
async def check_sms(call: types.CallbackQuery):
    act_id = call.data.split("_")[2]
    status = sms.get_status(act_id)
    if "STATUS_OK" in status:
        code = status.split(":")[1]
        await call.message.answer(f"✅ كود التفعيل: `{code}`", parse_mode="Markdown")
        sms.set_status(act_id, 6)
    else:
        await call.answer("⏳ لم يصل الكود بعد..", show_alert=True)

@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_order(call: types.CallbackQuery):
    _, act_id, price = call.data.split("_")
    sms.set_status(act_id, 8)
    db_query("UPDATE users SET balance = balance + ? WHERE id = ?", (float(price), call.from_user.id))
    await call.message.edit_text("❌ تم الإلغاء واسترداد الرصيد.")

@dp.callback_query(F.data == "my_balance")
async def show_balance(call: types.CallbackQuery):
    bal = get_bal(call.from_user.id)
    await call.message.edit_text(f"💰 رصيدك الحالي: **{round(bal, 2)}$**", 
        reply_markup=InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home")).as_markup())

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    kb = InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="💳 رصيد المورد", callback_data="check_api"))
    kb.row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home"))
    await call.message.edit_text("⚙️ لوحة الإدارة:", reply_markup=kb.as_markup())

@dp.callback_query(F.data == "check_api")
async def check_api(call: types.CallbackQuery):
    await call.answer(f"💰 رصيد المورد: {sms.get_balance()} روبل", show_alert=True)

@dp.callback_query(F.data == "back_home")
async def go_back(call: types.CallbackQuery):
    await start_handler(call.message)
