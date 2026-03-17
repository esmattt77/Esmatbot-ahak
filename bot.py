import os
import sqlite3
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sms_activate_api import HeroSMSAPI

# --- جلب البيانات من متغيرات البيئة (Environment Variables) ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
API_KEY = os.getenv("SMS_ACTIVATE_API_KEY")
# تحويل سلسلة الآيديات من البيئة إلى قائمة أرقام
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]

# إعدادات العملة والربح
# 1 روبل ≈ 0.011 دولار. نستخدم 0.015 كمعامل تحويل شامل للربح.
EXCHANGE_RATE = 0.015 

bot = Bot(token=TOKEN)
dp = Dispatcher()
sms = HeroSMSAPI(API_KEY)

# --- قائمة الدول المترجمة ---
COUNTRIES = {
    "0": "روسيا 🇷🇺", "1": "أوكرانيا 🇺🇦", "2": "كازاخستان 🇰🇿", "12": "أمريكا 🇺🇸",
    "51": "مصر 🇪🇬", "95": "السعودية 🇸🇦", "48": "العراق 🇮🇶", "52": "المغرب 🇲🇦",
    "88": "فلسطين 🇵🇸", "21": "الجزائر 🇩🇿", "27": "تونس 🇹🇳", "91": "الأردن 🇯🇴",
    "107": "الإمارات 🇦🇪", "110": "الكويت 🇰🇼", "153": "عمان 🇴🇲", "22": "الهند 🇮🇳",
    "6": "إندونيسيا 🇮🇩", "10": "فيتنام 🇻🇳", "15": "بولندا 🇵🇱", "187": "جنوب أفريقيا 🇿🇦"
}

# --- إدارة قاعدة البيانات ---
def db_init():
    with sqlite3.connect("users.db") as conn:
        conn.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)")
        conn.commit()

def get_bal(uid):
    with sqlite3.connect("users.db") as conn:
        res = conn.execute("SELECT balance FROM users WHERE id = ?", (uid,)).fetchone()
        if res: return res[0]
        conn.execute("INSERT INTO users (id, balance) VALUES (?, 0.0)", (uid,))
        conn.commit()
        return 0.0

def add_bal(uid, amount):
    with sqlite3.connect("users.db") as conn:
        conn.execute("UPDATE users SET balance = balance + ? WHERE id = ?", (amount, uid))
        conn.commit()

# --- الأوامر الرئيسية ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    bal = get_bal(message.from_user.id)
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🛒 شراء رقم جديد", callback_data="all_srv"))
    kb.row(types.InlineKeyboardButton(text="💰 رصيدي", callback_data="my_acc"))
    if message.from_user.id in ADMIN_IDS:
        kb.row(types.InlineKeyboardButton(text="⚙️ لوحة الإدارة", callback_data="admin_panel"))
    
    await message.answer(f"🤖 **مرحباً بك في بوت أرقام الخفاش**\n\n💰 رصيدك الحالي: `${round(bal, 2)}`", 
                         reply_markup=kb.as_markup(), parse_mode="Markdown")

# --- عرض الخدمات المتاحة ---
@dp.callback_query(F.data == "all_srv")
async def show_services(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    srvs = {"wa": "WhatsApp ✅", "tg": "Telegram ✈️", "go": "Google 📧", "lf": "TikTok 📱", "ig": "Instagram 📸", "fb": "Facebook 👤"}
    for code, name in srvs.items():
        kb.add(types.InlineKeyboardButton(text=name, callback_data=f"list_{code}_0"))
    kb.adjust(2).row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="home"))
    await call.message.edit_text("إختر الخدمة المطلوبة:", reply_markup=kb.as_markup())

# --- عرض الدول والأسعار (تم إصلاح ظهور السعر الصفر) ---
@dp.callback_query(F.data.startswith("list_"))
async def list_countries(call: types.CallbackQuery):
    _, svc, page = call.data.split("_")
    page = int(page)
    await call.answer("⏳ جاري جلب أفضل الأسعار...")
    
    raw_data = sms.get_prices(service=svc)
    available = []

    # معالجة بيانات الـ API لضمان استخراج السعر الصحيح
    items = raw_data.items() if isinstance(raw_data, dict) else enumerate(raw_data)
    for cid, srv_info in items:
        if svc in srv_info:
            data = srv_info[svc]
            try:
                # جلب السعر الخام بالروبل
                rub_price = float(data.get('cost', list(data.keys())[0]))
                count = data.get('count', list(data.values())[0])
                if count > 0:
                    # تحويل للدولار وتنسيقه
                    usd_price = round(rub_price * EXCHANGE_RATE, 2)
                    if usd_price < 0.01: usd_price = 0.05 # حماية من السعر الصفر
                    available.append({"id": str(cid), "name": COUNTRIES.get(str(cid), f"دولة {cid}"), "price": usd_price, "count": count})
            except: continue

    if not available:
        return await call.message.edit_text("❌ لا تتوفر أرقام حالياً.", reply_markup=InlineKeyboardBuilder().row(types.InlineKeyboardButton(text="🔙", callback_data="all_srv")).as_markup())

    # عرض 10 دول فقط لكل صفحة
    start, end = page*10, (page+1)*10
    kb = InlineKeyboardBuilder()
    for item in available[start:end]:
        kb.row(types.InlineKeyboardButton(text=f"{item['name']} | ${item['price']} ({item['count']} ق)", 
                                          callback_data=f"buy_{svc}_{item['id']}_{item['price']}"))
    
    nav = []
    if page > 0: nav.append(types.InlineKeyboardButton(text="⬅️", callback_data=f"list_{svc}_{page-1}"))
    if end < len(available): nav.append(types.InlineKeyboardButton(text="➡️", callback_data=f"list_{svc}_{page+1}"))
    if nav: kb.row(*nav)
    kb.row(types.InlineKeyboardButton(text="🔙 الخدمات", callback_data="all_srv"))
    
    await call.message.edit_text(f"🌍 أرقام {svc.upper()} المتاحة:", reply_markup=kb.as_markup())

# --- تنفيذ عملية الشراء (getNumberV2) ---
@dp.callback_query(F.data.startswith("buy_"))
async def buy_process(call: types.CallbackQuery):
    _, svc, cid, price = call.data.split("_")
    price = float(price)
    uid = call.from_user.id
    
    if get_bal(uid) < price:
        return await call.answer("❌ رصيدك غير كافٍ!", show_alert=True)

    res = sms.get_number(svc, cid)
    if isinstance(res, dict) and ("activationId" in res or "id" in res):
        aid = res.get("activationId") or res.get("id")
        num = res.get("phoneNumber") or res.get("number")
        add_bal(uid, -price) # خصم الرصيد
        
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="📩 جلب الكود", callback_data=f"otp_{aid}"))
        kb.row(types.InlineKeyboardButton(text="❌ إلغاء واسترداد", callback_data=f"can_{aid}_{price}"))
        
        await call.message.edit_text(f"✅ تم شراء الرقم!\n📱 الرقم: `{num}`\n💰 السعر: `${price}`", 
                                     reply_markup=kb.as_markup(), parse_mode="Markdown")
    else:
        await call.answer(f"❌ فشل من الموقع: {res}", show_alert=True)

# --- لوحة التحكم الشاملة للمسؤول ---
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="💳 رصيد الموقع", callback_data="adm_bal"),
           types.InlineKeyboardButton(text="📜 السجل العام", callback_data="adm_hist"))
    kb.row(types.InlineKeyboardButton(text="🛠 قائمة الخدمات", callback_data="adm_srvs"),
           types.InlineKeyboardButton(text="🌍 أفضل الدول", callback_data="adm_top"))
    kb.row(types.InlineKeyboardButton(text="🔙 الرئيسية", callback_data="home"))
    kb.adjust(2)
    await call.message.edit_text("⚙️ **لوحة تحكم المسؤول الشاملة**", reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "adm_bal")
async def adm_bal(call: types.CallbackQuery):
    await call.answer(f"💰 رصيد المورد: {sms.get_balance()} RUB", show_alert=True)

@dp.callback_query(F.data == "home")
async def go_home(call: types.CallbackQuery):
    await cmd_start(call.message)

# --- تشغيل ---
async def main():
    db_init()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
