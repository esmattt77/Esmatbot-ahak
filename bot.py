import os
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sms_activate_api import HeroSMSAPI

# إعداد السجلات لمراقبة أداء البوت
logging.basicConfig(level=logging.INFO)

# --- جلب الإعدادات من بيئة العمل (Render) ---
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]
API_KEY = os.getenv("SMS_ACTIVATE_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()
sms = HeroSMSAPI(API_KEY)

# --- قائمة الدول (يمكنك التوسع فيها) ---
COUNTRIES = {
    "0": "🇷🇺 روسيا",
    "1": "🇺🇦 أوكرانيا",
    "6": "🇮🇩 إندونيسيا",
    "15": "🇵🇱 بولندا",
    "22": "🇮🇳 الهند",
    "123": "🇺🇸 أمريكا",
    "187": "🇿🇦 جنوب أفريقيا"
}

# --- إدارة قاعدة البيانات ---
def db_query(query, params=(), fetch=False):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.execute(query, params)
        if fetch: return cursor.fetchone()
        conn.commit()

# إنشاء الجداول إذا لم تكن موجودة
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
    bal = get_bal(message.from_user.id)
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🛒 شراء رقم جديد", callback_data="services"))
    kb.row(types.InlineKeyboardButton(text="💰 رصيدي", callback_data="my_balance"))
    kb.row(types.InlineKeyboardButton(text="🛠 الدعم الفني", url="https://t.me/your_support"))
    
    if message.from_user.id in ADMIN_IDS:
        kb.row(types.InlineKeyboardButton(text="⚙️ لوحة الإدارة", callback_data="admin_panel"))

    await message.answer(
        f"👋 أهلاً بك في بوت خدمات الأرقام\n\n"
        f"💰 رصيدك الحالي: **{bal}$**\n"
        f"🆔 آيدي الحساب: `{message.from_user.id}`\n\n"
        "إختر ما تريد القيام به من الأسفل 👇",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "back_home")
async def back_home(call: types.CallbackQuery):
    await start_handler(call.message)

# --- نظام عرض الخدمات والدول ---
@dp.callback_query(F.data == "services")
async def show_services(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    kb.add(types.InlineKeyboardButton(text="واتساب ✅", callback_data="set_svc_wa"))
    kb.add(types.InlineKeyboardButton(text="تلجرام ✈️", callback_data="set_svc_tg"))
    kb.add(types.InlineKeyboardButton(text="تيك توك 📱", callback_data="set_svc_lf"))
    kb.adjust(2)
    kb.row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home"))
    await call.message.edit_text("اختر الخدمة المطلوبة:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("set_svc_"))
async def show_countries(call: types.CallbackQuery):
    service = call.data.split("_")[2]
    kb = InlineKeyboardBuilder()
    for c_id, c_name in COUNTRIES.items():
        kb.add(types.InlineKeyboardButton(text=c_name, callback_data=f"order_{service}_{c_id}"))
    kb.adjust(2)
    kb.row(types.InlineKeyboardButton(text="🔙 عودة للخدمات", callback_data="services"))
    await call.message.edit_text(f"🌍 اختر الدولة المطلوبة لخدمة {service.upper()}:", reply_markup=kb.as_markup())

# --- عملية شراء الرقم ---
@dp.callback_query(F.data.startswith("order_"))
async def process_order(call: types.CallbackQuery):
    _, service, country_id = call.data.split("_")
    user_id = call.from_user.id
    balance = get_bal(user_id)
    
    price = 0.5 # سعر افتراضي، يمكنك تعديله

    if balance < price:
        return await call.answer("❌ رصيدك في البوت غير كافٍ. يرجى شحن الرصيد أولاً.", show_alert=True)

    # طلب الرقم من الموقع
    res = sms.get_number(service, country_id)
    
    if isinstance(res, dict) and "id" in res:
        db_query("UPDATE users SET balance = balance - ? WHERE id = ?", (price, user_id))
        
        kb = InlineKeyboardBuilder()
        kb.row(types.InlineKeyboardButton(text="📩 جلب الكود", callback_data=f"get_sms_{res['id']}"))
        kb.row(types.InlineKeyboardButton(text="❌ إلغاء الطلب", callback_data=f"cancel_{res['id']}"))
        
        await call.message.edit_text(
            f"✅ تم حجز الرقم بنجاح!\n\n"
            f"📱 الرقم: `{res['number']}`\n"
            f"🌍 الدولة: {COUNTRIES.get(country_id, 'غير معروفة')}\n"
            f"💰 السعر: {price}$\n\n"
            "قم بطلب الكود الآن، وسيظهر هنا بمجرد وصوله.",
            reply_markup=kb.as_markup(),
            parse_mode="Markdown"
        )
    else:
        # إذا كان الموقع هو من لا يملك رصيد أو الرقم غير متوفر
        error_msg = str(res)
        if "NO_BALANCE" in error_msg:
            await call.message.answer("⚠️ عذراً، مخزن الأرقام فارغ حالياً (رصيد الموقع 0). يرجى إبلاغ الإدارة.")
        else:
            await call.answer(f"❌ خطأ من المزود: {error_msg}", show_alert=True)

# --- إدارة الأرصدة الشخصية ---
@dp.callback_query(F.data == "my_balance")
async def show_user_balance(call: types.CallbackQuery):
    balance = get_bal(call.from_user.id)
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home"))
    await call.message.edit_text(
        f"💰 **تفاصيل رصيدك**\n\n"
        f"• رصيدك المتوفر: {balance}$\n"
        f"• آيدي الحساب: `{call.from_user.id}`\n\n"
        "لشحن رصيدك، تواصل مع المطور.",
        reply_markup=kb.as_markup(),
        parse_mode="Markdown"
    )

# --- لوحة التحكم (للأدمن فقط) ---
@dp.callback_query(F.data == "admin_panel")
async def admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ شحن رصيد مستخدم", callback_data="admin_add_bal"))
    kb.row(types.InlineKeyboardButton(text="💳 رصيد الموقع (API)", callback_data="check_api_resid"))
    kb.row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="back_home"))
    
    await call.message.edit_text("⚙️ **لوحة التحكم للإدارة**\n\nتحكم بالأرصدة وراقب حالة الموقع من هنا:", 
                                 reply_markup=kb.as_markup(), parse_mode="Markdown")

@dp.callback_query(F.data == "check_api_resid")
async def check_api_balance(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    api_bal = sms.get_balance()
    await call.answer(f"💰 رصيد حسابك في HeroSMS هو: {api_bal}$", show_alert=True)

@dp.callback_query(F.data == "admin_add_bal")
async def admin_add_bal_instr(call: types.CallbackQuery):
    await call.message.answer("لشحن رصيد مستخدم، أرسل رسالة بالصيغة التالية:\n`الآيدي المبلغ`\n\nمثال:\n`8102857570 5.5`")

# معالج رسائل الشحن (للأدمن)
@dp.message(lambda msg: msg.from_user.id in ADMIN_IDS and len(msg.text.split()) == 2)
async def process_admin_deposit(message: types.Message):
    try:
        target_id, amount = message.text.split()
        # تحديث قاعدة البيانات
        db_query("UPDATE users SET balance = balance + ? WHERE id = ?", (float(amount), int(target_id)))
        await message.answer(f"✅ تم إضافة {amount}$ للحساب `{target_id}` بنجاح.", parse_mode="Markdown")
        # إشعار المستخدم
        try:
            await bot.send_message(int(target_id), f"💰 تم إضافة **{amount}$** لرصيدك في البوت بنجاح!")
        except: pass
    except:
        await message.answer("⚠️ خطأ! تأكد من إدخال الآيدي ثم المبلغ بشكل صحيح.")
