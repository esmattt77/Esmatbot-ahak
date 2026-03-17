import os
import sqlite3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sms_activate_api import HeroSMSAPI

# جلب الإعدادات من البيئة
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i]
API_KEY = os.getenv("SMS_ACTIVATE_API_KEY")

bot = Bot(token=TOKEN)
dp = Dispatcher()
sms = HeroSMSAPI(API_KEY)

# قاعدة بيانات بسيطة (ملاحظة: Render يمسح البيانات عند إعادة التشغيل إلا لو استخدمت قرص خارجي)
db = sqlite3.connect("users.db")
db.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, balance REAL DEFAULT 0.0)")
db.commit()

def get_user_balance(user_id):
    with sqlite3.connect("users.db") as conn:
        cursor = conn.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        row = cursor.fetchone()
        if row: return row[0]
        conn.execute("INSERT INTO users (id, balance) VALUES (?, 0.0)", (user_id,))
        conn.commit()
        return 0.0

@dp.message(Command("start"))
async def start_cmd(message: types.Message):
    balance = get_user_balance(message.from_user.id)
    builder = InlineKeyboardBuilder()
    builder.row(types.InlineKeyboardButton(text="🛒 شراء رقم", callback_data="buy_menu"))
    builder.row(types.InlineKeyboardButton(text="👤 حسابي", callback_data="profile"))
    
    if message.from_user.id in ADMIN_IDS:
        builder.row(types.InlineKeyboardButton(text="⚙️ لوحة الإدارة", callback_data="admin_panel"))

    await message.answer(f"مرحباً بك في متجر الأرقام 🤖\n\nرصيدك: {balance}$", reply_markup=builder.as_markup())

@dp.callback_query(F.data == "admin_panel")
async def admin_panel(call: types.CallbackQuery):
    if call.from_user.id not in ADMIN_IDS: return
    api_bal = sms.get_balance()
    await call.message.edit_text(f"⚙️ لوحة الإدارة\n\nرصيد المورد الأساسي: {api_bal}$", 
                                 reply_markup=InlineKeyboardBuilder().button(text="🔙 عودة", callback_data="start").as_markup())

# يمكنك إضافة المزيد من المعالجات (Handlers) هنا لشراء الأرقام
