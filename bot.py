import telebot
from telebot import types
import logging
import os
from sms_activate_api import HeroSMSAPI

logger = logging.getLogger(__name__)

# متغيرات عامة
api_client = None
admin_ids = []

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

def setup_bot(bot):
    """إعداد جميع معالجات البوت"""
    global api_client, admin_ids
    
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

أهلاً بك في بوت شراء الأرقام الافتراضية.

🔹 **الخدمات المتاحة:**
• تلغرام - واتساب - Viber
• Gmail - Uber - Avito

🔹 **الأوامر:**
/buy - شراء رقم جديد
/balance - عرض الرصيد
/help - المساعدة
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
            # استدعاء غير متزامن - سنحتاج لمعالجته
            import asyncio
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
        
        bot.reply_to(message, "📋 اختر الخدمة:", reply_markup=keyboard)
    
    @bot.message_handler(commands=['help'])
    def help_command(message):
        """معالج أمر /help"""
        help_text = """
❓ **مساعدة البوت**

**الأوامر:**
/start - القائمة الرئيسية
/buy - شراء رقم
/balance - عرض الرصيد
/help - هذه المساعدة

**كيفية الشراء:**
1️⃣ اختر الخدمة
2️⃣ اختر الدولة
3️⃣ أكد الشراء
        """
        bot.reply_to(message, help_text, parse_mode='Markdown')
    
    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        """معالج جميع الأزرار"""
        try:
            data = call.data
            
            if data == "balance":
                # معالجة زر الرصيد
                if not api_client:
                    bot.edit_message_text("❌ API غير مهيأ", call.message.chat.id, call.message.message_id)
                    return
                
                try:
                    import asyncio
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
                help_text = "❓ استخدم /help للأوامر الكاملة"
                bot.edit_message_text(help_text, call.message.chat.id, call.message.message_id)
            
            elif data.startswith("service_"):
                service = data.replace("service_", "")
                service_name = AVAILABLE_SERVICES.get(service, service)
                
                # حفظ الخدمة في مؤقت
                import temp
                temp.user_data[call.from_user.id] = {'service': service, 'service_name': service_name}
                
                # عرض الدول
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                countries = [
                    ("🇷🇺 روسيا", "country_6"),
                    ("🇰🇿 كازاخستان", "country_2"),
                    ("🇺🇦 أوكرانيا", "country_1"),
                    ("🌍 جميع الدول", "country_0")
                ]
                
                for name, code in countries:
                    keyboard.add(types.InlineKeyboardButton(name, callback_data=code))
                
                keyboard.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="back"))
                
                bot.edit_message_text(
                    f"📱 الخدمة: **{service_name}**\n\n🌍 اختر الدولة:",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            
            elif data.startswith("country_"):
                country = data.replace("country_", "")
                user_data = temp.user_data.get(call.from_user.id, {})
                service = user_data.get('service', 'tg')
                service_name = user_data.get('service_name', 'تلغرام')
                
                country_names = {'6': 'روسيا', '2': 'كازاخستان', '1': 'أوكرانيا', '0': 'جميع الدول'}
                country_name = country_names.get(country, 'غير معروفة')
                
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                keyboard.add(
                    types.InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_{service}_{country}"),
                    types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel")
                )
                
                bot.edit_message_text(
                    f"📱 **تفاصيل الطلب**\n\n"
                    f"الخدمة: {service_name}\n"
                    f"الدولة: {country_name}\n\n"
                    f"⚠️ هل تريد تأكيد الشراء؟",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            
            elif data.startswith("confirm_"):
                parts = data.split('_')
                service = parts[1]
                country = parts[2]
                
                bot.edit_message_text(
                    "🔄 جاري طلب الرقم...",
                    call.message.chat.id,
                    call.message.message_id
                )
                
                # محاكاة طلب رقم
                import time
                time.sleep(2)
                
                bot.edit_message_text(
                    "✅ **تمت العملية بنجاح!**\n\n"
                    "📱 الرقم: +7 (999) 123-45-67\n"
                    "🔑 الرمز: 12345\n\n"
                    "⏱️ الرقم صالح لمدة 20 دقيقة",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
            
            elif data == "cancel":
                bot.edit_message_text(
                    "❌ تم إلغاء العملية",
                    call.message.chat.id,
                    call.message.message_id
                )
            
            elif data == "back":
                # العودة للقائمة الرئيسية
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                btn1 = types.InlineKeyboardButton("📱 شراء رقم", callback_data="buy")
                btn2 = types.InlineKeyboardButton("💰 رصيدي", callback_data="balance")
                btn3 = types.InlineKeyboardButton("❓ مساعدة", callback_data="help")
                keyboard.add(btn1, btn2, btn3)
                
                bot.edit_message_text(
                    "👫 **القائمة الرئيسية**",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            
            elif data == "buy":
                # شراء رقم
                buy_command(call.message)
            
            # الرد على الضغط
            bot.answer_callback_query(call.id)
            
        except Exception as e:
            logger.error(f"خطأ في معالج الأزرار: {e}")
            bot.answer_callback_query(call.id, "❌ حدث خطأ")
    
    logger.info("✅ تم إعداد معالجات البوت")
