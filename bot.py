import telebot
from telebot import types
import logging
import os
import asyncio
from sms_activate_api import HeroSMSAPI

logger = logging.getLogger(__name__)

# متغيرات عامة
api_client = None
admin_ids = []
bot_instance = None

# الخدمات المتاحة
AVAILABLE_SERVICES = {
    'tg': '📱 تلغرام',
    'wa': '💬 واتساب',
    'vb': '📞 Viber',
    'ok': '👥 Odnoklassniki',
    'go': '📧 Gmail',
    'ub': '🚗 Uber',
    'av': '🏠 Avito',
}

# قاموس مؤقت لتخزين بيانات المستخدمين
user_data = {}

def setup_bot(bot):
    """إعداد جميع معالجات البوت"""
    global api_client, admin_ids, bot_instance
    
    # حفظ مرجع البوت
    bot_instance = bot
    
    # تهيئة API client
    api_key = os.environ.get('SMS_ACTIVATE_API_KEY')
    if api_key:
        api_client = HeroSMSAPI(api_key)
    
    # قراءة معرفات المشرفين
    admin_ids_str = os.environ.get('ADMIN_IDS', '')
    admin_ids = [int(id.strip()) for id in admin_ids_str.split(',') if id.strip().isdigit()]
    
    @bot.message_handler(commands=['start'])
    def start_command(message):
        """معالج أمر /start"""
        user = message.from_user
        welcome_text = f"""
👋 مرحباً {user.first_name}!

أهلاً بك في **بوت شراء الأرقام الافتراضية**

🔹 **الخدمات المتاحة:**
• تلغرام - واتساب - Viber
• Gmail - Uber - Avito

🔹 **الأوامر:**
/buy - شراء رقم جديد
/balance - عرض الرصيد
/help - المساعدة

🔹 **لبدء الشراء، اختر من الأزرار أدناه:**
        """
        
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        btn1 = types.InlineKeyboardButton("📱 شراء رقم", callback_data="buy")
        btn2 = types.InlineKeyboardButton("💰 رصيدي", callback_data="balance")
        btn3 = types.InlineKeyboardButton("❓ مساعدة", callback_data="help")
        keyboard.add(btn1, btn2, btn3)
        
        bot.reply_to(message, welcome_text, reply_markup=keyboard, parse_mode='Markdown')
    
    @bot.message_handler(commands=['balance'])
    def balance_command(message):
        """معالج أمر /balance"""
        if not api_client:
            bot.reply_to(message, "❌ API غير مهيأ")
            return
        
        try:
            # استدعاء غير متزامن
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            balance = loop.run_until_complete(api_client.get_balance())
            loop.close()
            
            bot.reply_to(message, f"💰 رصيدك الحالي: **{balance}** دولار", parse_mode='Markdown')
        except Exception as e:
            logger.error(f"خطأ في جلب الرصيد: {e}")
            bot.reply_to(message, "❌ حدث خطأ في جلب الرصيد")
    
    @bot.message_handler(commands=['buy'])
    def buy_command(message):
        """معالج أمر /buy"""
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        buttons = []
        for code, name in AVAILABLE_SERVICES.items():
            buttons.append(types.InlineKeyboardButton(name, callback_data=f"service_{code}"))
        
        keyboard.add(*buttons)
        keyboard.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back"))
        
        bot.reply_to(message, "📋 **اختر الخدمة المطلوبة:**", reply_markup=keyboard, parse_mode='Markdown')
    
    @bot.message_handler(commands=['help'])
    def help_command(message):
        """معالج أمر /help"""
        help_text = """
❓ **مساعدة البوت**

**الأوامر المتاحة:**
/start - القائمة الرئيسية
/buy - شراء رقم جديد
/balance - عرض الرصيد
/help - عرض هذه المساعدة

**كيفية الشراء:**
1️⃣ اختر الخدمة المطلوبة
2️⃣ اختر الدولة
3️⃣ قم بتأكيد الشراء
4️⃣ استلم الرقم ورمز التفعيل

**ملاحظات مهمة:**
• يتم خصم المبلغ من رصيدك عند التأكيد
• صلاحية الرقم 20 دقيقة
• يمكنك إلغاء العملية في أي وقت
        """
        bot.reply_to(message, help_text, parse_mode='Markdown')
    
    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        """معالج جميع الأزرار"""
        try:
            data = call.data
            user_id = call.from_user.id
            
            logger.info(f"زر مضغوط: {data} من المستخدم {user_id}")
            
            if data == "balance":
                # معالجة زر الرصيد
                if not api_client:
                    bot.edit_message_text("❌ API غير مهيأ", call.message.chat.id, call.message.message_id)
                    bot.answer_callback_query(call.id)
                    return
                
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    balance = loop.run_until_complete(api_client.get_balance())
                    loop.close()
                    
                    bot.edit_message_text(
                        f"💰 رصيدك الحالي: **{balance}** دولار",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.error(f"خطأ في جلب الرصيد: {e}")
                    bot.edit_message_text("❌ حدث خطأ", call.message.chat.id, call.message.message_id)
            
            elif data == "help":
                help_text = "❓ للمساعدة، أرسل الأمر /help"
                bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id)
            
            elif data == "back":
                # العودة للقائمة الرئيسية
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                btn1 = types.InlineKeyboardButton("📱 شراء رقم", callback_data="buy")
                btn2 = types.InlineKeyboardButton("💰 رصيدي", callback_data="balance")
                btn3 = types.InlineKeyboardButton("❓ مساعدة", callback_data="help")
                keyboard.add(btn1, btn2, btn3)
                
                bot.edit_message_text(
                    "👫 **القائمة الرئيسية**\n\nاختر ما تريد:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            
            elif data == "buy":
                # عرض الخدمات
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                buttons = []
                for code, name in AVAILABLE_SERVICES.items():
                    buttons.append(types.InlineKeyboardButton(name, callback_data=f"service_{code}"))
                keyboard.add(*buttons)
                keyboard.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back"))
                
                bot.edit_message_text(
                    "📋 **اختر الخدمة المطلوبة:**",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            
            elif data.startswith("service_"):
                service = data.replace("service_", "")
                service_name = AVAILABLE_SERVICES.get(service, service)
                
                # حفظ الخدمة في البيانات المؤقتة
                if user_id not in user_data:
                    user_data[user_id] = {}
                user_data[user_id]['service'] = service
                user_data[user_id]['service_name'] = service_name
                
                # عرض الدول
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                countries = [
                    ("🇷🇺 روسيا", "country_6"),
                    ("🇰🇿 كازاخستان", "country_2"),
                    ("🇺🇦 أوكرانيا", "country_1"),
                    ("🌍 جميع الدول", "country_0")
                ]
                
                buttons = []
                for name, code in countries:
                    buttons.append(types.InlineKeyboardButton(name, callback_data=code))
                keyboard.add(*buttons)
                keyboard.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="buy"))
                
                bot.edit_message_text(
                    f"📱 **الخدمة:** {service_name}\n\n🌍 **اختر الدولة:**",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            
            elif data.startswith("country_"):
                country = data.replace("country_", "")
                
                # استرجاع بيانات المستخدم
                service = user_data.get(user_id, {}).get('service', 'tg')
                service_name = user_data.get(user_id, {}).get('service_name', 'تلغرام')
                
                country_names = {'6': 'روسيا', '2': 'كازاخستان', '1': 'أوكرانيا', '0': 'جميع الدول'}
                country_name = country_names.get(country, 'غير معروفة')
                
                # حفظ الدولة
                if user_id not in user_data:
                    user_data[user_id] = {}
                user_data[user_id]['country'] = country
                user_data[user_id]['country_name'] = country_name
                
                # عرض تأكيد الشراء
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                keyboard.add(
                    types.InlineKeyboardButton("✅ تأكيد الشراء", callback_data="confirm"),
                    types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel")
                )
                
                bot.edit_message_text(
                    f"📱 **تفاصيل الطلب**\n\n"
                    f"الخدمة: {service_name}\n"
                    f"الدولة: {country_name}\n"
                    f"السعر التقريبي: 0.5 - 2 دولار\n\n"
                    f"⚠️ هل تريد تأكيد الشراء؟",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            
            elif data == "confirm":
                # تأكيد الشراء
                service = user_data.get(user_id, {}).get('service', 'tg')
                service_name = user_data.get(user_id, {}).get('service_name', 'تلغرام')
                country = user_data.get(user_id, {}).get('country', '6')
                
                bot.edit_message_text(
                    "🔄 **جاري طلب الرقم...**\n\nالرجاء الانتظار",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
                
                # محاكاة طلب رقم (سيتم استبداله بطلب API حقيقي)
                import time
                time.sleep(2)
                
                # إنشاء رقم وهمي
                import random
                phone = f"+7 (9{random.randint(10, 99)}) {random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10, 99)}"
                code = random.randint(10000, 99999)
                
                bot.edit_message_text(
                    f"✅ **تمت العملية بنجاح!**\n\n"
                    f"📱 **الرقم:** `{phone}`\n"
                    f"🔑 **رمز التفعيل:** `{code}`\n\n"
                    f"⏱️ الرقم صالح لمدة 20 دقيقة\n"
                    f"📨 سيتم إعلامك عند وصول رسالة جديدة",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
                
                # مسح بيانات المستخدم
                if user_id in user_data:
                    del user_data[user_id]
            
            elif data == "cancel":
                # إلغاء العملية
                bot.edit_message_text(
                    "❌ **تم إلغاء العملية**",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
                
                # مسح بيانات المستخدم
                if user_id in user_data:
                    del user_data[user_id]
            
            # الرد على الضغط
            bot.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"خطأ في معالج الأزرار: {e}")
            try:
                bot.answer_callback_query(call.id, "❌ حدث خطأ")
            except:
                pass
    
    @bot.message_handler(func=lambda message: True)
    def echo_all(message):
        """معالج الرسائل النصية العامة"""
        bot.reply_to(message, "❓ أمر غير معروف. أرسل /start للبدء")
    
    logger.info("✅ تم إعداد معالجات البوت بنجاح")
