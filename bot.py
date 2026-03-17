import os
import sqlite3
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sms_activate_api import HeroSMSAPI

# إعداد السجلات
logging.basicConfig(level=logging.INFO)

# جلب الإعدادات
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]
API_KEY = os.getenv("SMS_ACTIVATE_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()
sms = HeroSMSAPI(API_KEY)

# --- قاعدة البيانات ---
def db_query(query, params=(), fetch=False):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.execute(query, params)
        if fetch: return cursor.fetchone()
        conn.commit()

db_query("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)")
db_query("CREATE TABLE IF NOT EXISTS orders (id TEXT PRIMARY KEY, user_id INTEGER, service TEXT, number TEXT)")

# --- دوال مساعدة ---
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
    kb.row(types.InlineKeyboardButton(text="📱 أرقامي النشطة", callback_data="my_numbers"))
    kb.row(types.InlineKeyboardButton(text="💰 رصيدي", callback_data="profile"),
           types.InlineKeyboardButton(text="🛠 الدعم", url="https://t.me/your_support"))
    
    if message.from_user.id in ADMIN_IDS:
        kb.row(types.InlineKeyboardButton(text="⚙️ لوحة التحكم (أدمن)", callback_data="admin_main"))

    await message.answer(f"مرحباً بك في بوت الأرقام الذكي 🤖\n\nرصيدك: **{bal}$**", 
                         reply_markup=kb.as_markup(), parse_mode="Markdown")

# --- متجر الأرقام ---
SERVICES = {"tg": "Telegram", "wa": "WhatsApp", "go": "Google", "vi": "Viber"}

@dp.callback_query(F.data == "services")
async def show_services(call: types.CallbackQuery):
    kb = InlineKeyboardBuilder()
    for code, name in SERVICES.items():
        kb.add(types.InlineKeyboardButton(text=name, callback_data=f"buy_{code}"))
    kb.adjust(2)
    kb.row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="start_back"))
    await call.message.edit_text("إختر الخدمة المطلوبة:", reply_markup=kb.as_markup())

@dp.callback_query(F.data.startswith("buy_"))
async def buy_number(call: types.CallbackQuery):
    service = call.data.split("_")[1]
    user_bal = get_bal(call.from_user.id)
    
    # طلب الرقم من الـ API
    res = sms.get_number(service) # هذه الدالة في ملف sms_activate_api.py
    if isinstance(res, dict):
        # هنا يجب خصم السعر (مثال: 0.5$)
        price = 0.5 
        if user_bal >= price:
            db_query("UPDATE users SET balance = balance - ? WHERE id = ?", (price, call.from_user.id))
            db_query("INSERT INTO orders (id, user_id, service, number) VALUES (?, ?, ?, ?)", 
                     (res['id'], call.from_user.id, service, res['number']))
            
            kb = InlineKeyboardBuilder()
            kb.row(types.InlineKeyboardButton(text="📩 جلب الكود", callback_data=f"get_sms_{res['id']}"))
            kb.row(types.InlineKeyboardButton(text="❌ إلغاء", callback_data=f"cancel_{res['id']}"))
            
            await call.message.edit_text(f"✅ تم حجز الرقم بنجاح!\n\nالرقم: `{res['number']}`\nالخدمة: {SERVICES[service]}\n\nانتظر وصول الكود ثم اضغط الزر بالأسفل.", 
                                         reply_markup=kb.as_markup(), parse_mode="Markdown")
        else:
            await call.answer("❌ رصيدك غير كافٍ!", show_alert=True)
    else:
        await call.answer(f"❌ عذراً: {res}", show_alert=True)

# --- إدارة الطلبات ---
@dp.callback_query(F.data.startswith("get_sms_"))
async def check_sms(call: types.CallbackQuery):
    act_id = call.data.split("_")[2]
    status = sms.get_status(act_id)
    
    if "STATUS_OK" in status:
        code = status.split(":")[1]
        await call.message.answer(f"✅ كود التفعيل الخاص بك هو: `{code}`", parse_mode="Markdown")
    elif "STATUS_WAIT" in status:
        await call.answer("⏳ لا يزال الانتظار جارياً لوصول الكود...", show_alert=True)
    else:
        await call.answer(f"⚠️ حالة الطلب: {status}", show_alert=True)

@dp.callback_query(F.data.startswith("cancel_"))
async def cancel_order(call: types.CallbackQuery):
    act_id = call.data.split("_")[1]
    sms.set_status(act_id, 8) # 8 تعني إلغاء
    # استرجاع المبلغ (مثال)
    db_query("UPDATE users SET balance = balance + 0.5 WHERE id = ?", (call.from_user.id,))
    await call.message.edit_text("❌ تم إلغاء الطلب واسترجاع المبلغ لرصيدك.")

# --- لوحة التحكم للأدمن ---
@dp.callback_query(F.data == "admin_main")
async def admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    api_bal = sms.get_balance()
    total_users = db_query("SELECT COUNT(*) FROM users", fetch=True)[0]
    
    kb = InlineKeyboardBuilder()
    kb.row(types.InlineKeyboardButton(text="➕ إضافة رصيد لمستخدم", callback_data="admin_add"))
    kb.row(types.InlineKeyboardButton(text="🔙 عودة", callback_data="start_back"))
    
    await call.message.edit_text(f"⚙️ لوحة تحكم الإدارة\n\n👥 عدد المستخدمين: {total_users}\n💰 رصيدك في HeroSMS: {api_bal}$", 
                                 reply_markup=kb.as_markup())

@dp.callback_query(F.data == "start_back")
async def back_home(call: types.CallbackQuery):
    await start_handler(call.message)
