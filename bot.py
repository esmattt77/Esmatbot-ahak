import telebot
from telebot import types
import logging
import os
import asyncio
import random
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
        logger.info("✅ تم تهيئة API client")
    else:
        logger.warning("⚠️ SMS_ACTIVATE_API_KEY غير موجودة - سيتم استخدام وضع التجربة")
    
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
            bot.reply_to(message, "❌ API غير مهيأ - وضع التجربة نشط")
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
2️⃣ اختر الدولة (مع عرض السعر)
3️⃣ قم بتأكيد الشراء
4️⃣ استلم الرقم ورمز التفعيل

**ملاحظات مهمة:**
• يتم خصم المبلغ من رصيدك عند التأكيد
• صلاحية الرقم 20 دقيقة
• يمكنك إلغاء العملية في أي وقت
        """
        bot.reply_to(message, help_text, parse_mode='Markdown')
    
    @bot.message_handler(commands=['admin'])
    def admin_command(message):
        """معالج أوامر المشرفين"""
        user_id = message.from_user.id
        
        if user_id not in admin_ids:
            bot.reply_to(message, "❌ هذا الأمر مخصص للمشرفين فقط")
            return
        
        text = message.text.lower()
        
        if text == '/admin balance' and api_client:
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                balance = loop.run_until_complete(api_client.get_balance())
                loop.close()
                bot.reply_to(message, f"💰 رصيد API: {balance} دولار")
            except Exception as e:
                bot.reply_to(message, f"❌ خطأ: {e}")
        
        elif text == '/admin stats':
            bot.reply_to(message, f"📊 إحصائيات:\nالمستخدمين النشطين: {len(user_data)}")
        
        else:
            bot.reply_to(message, "🔧 أوامر المشرفين:\n/admin balance - عرض رصيد API\n/admin stats - عرض إحصائيات")
    
    @bot.callback_query_handler(func=lambda call: True)
    def callback_handler(call):
        """معالج جميع الأزرار"""
        try:
            data = call.data
            user_id = call.from_user.id
            
            logger.info(f"🔘 زر مضغوط: {data} من المستخدم {user_id}")
            
            if data == "balance":
                # معالجة زر الرصيد
                if not api_client:
                    bot.edit_message_text("❌ API غير مهيأ - وضع التجربة", call.message.chat.id, call.message.message_id)
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
                    bot.edit_message_text("❌ حدث خطأ في جلب الرصيد", call.message.chat.id, call.message.message_id)
            
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
                
                # رسالة تحميل
                bot.edit_message_text(
                    "🔄 **جاري تحميل الأسعار...**",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
                
                # محاولة جلب الأسعار من API
                prices = {}
                if api_client:
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        prices_data = loop.run_until_complete(api_client.get_prices(service))
                        loop.close()
                        
                        if prices_data and isinstance(prices_data, dict):
                            prices = prices_data
                            logger.info(f"✅ تم جلب الأسعار الحقيقية للخدمة {service}: {len(prices)} دولة")
                    except Exception as e:
                        logger.error(f"❌ خطأ في جلب الأسعار: {e}")
                        prices = {}
                
                # قائمة موسعة من الدول مع رموزها وأسعارها
                countries = [
                    {'code': '6', 'name': 'روسيا', 'flag': '🇷🇺', 
                     'price': prices.get('6', {}).get(service, {}).get('cost', 0.50) if prices and isinstance(prices.get('6'), dict) and service in prices.get('6', {}) else 0.50},
                    {'code': '2', 'name': 'كازاخستان', 'flag': '🇰🇿', 
                     'price': prices.get('2', {}).get(service, {}).get('cost', 0.80) if prices and isinstance(prices.get('2'), dict) and service in prices.get('2', {}) else 0.80},
                    {'code': '1', 'name': 'أوكرانيا', 'flag': '🇺🇦', 
                     'price': prices.get('1', {}).get(service, {}).get('cost', 0.60) if prices and isinstance(prices.get('1'), dict) and service in prices.get('1', {}) else 0.60},
                    {'code': '0', 'name': 'جميع الدول', 'flag': '🌍', 
                     'price': prices.get('0', {}).get(service, {}).get('cost', 1.50) if prices and isinstance(prices.get('0'), dict) and service in prices.get('0', {}) else 1.50},
                    {'code': '187', 'name': 'مصر', 'flag': '🇪🇬', 
                     'price': prices.get('187', {}).get(service, {}).get('cost', 1.20) if prices and isinstance(prices.get('187'), dict) and service in prices.get('187', {}) else 1.20},
                    {'code': '194', 'name': 'السعودية', 'flag': '🇸🇦', 
                     'price': prices.get('194', {}).get(service, {}).get('cost', 1.80) if prices and isinstance(prices.get('194'), dict) and service in prices.get('194', {}) else 1.80},
                    {'code': '195', 'name': 'الإمارات', 'flag': '🇦🇪', 
                     'price': prices.get('195', {}).get(service, {}).get('cost', 2.00) if prices and isinstance(prices.get('195'), dict) and service in prices.get('195', {}) else 2.00},
                    {'code': '193', 'name': 'الكويت', 'flag': '🇰🇼', 
                     'price': prices.get('193', {}).get(service, {}).get('cost', 2.20) if prices and isinstance(prices.get('193'), dict) and service in prices.get('193', {}) else 2.20},
                    {'code': '196', 'name': 'قطر', 'flag': '🇶🇦', 
                     'price': prices.get('196', {}).get(service, {}).get('cost', 2.10) if prices and isinstance(prices.get('196'), dict) and service in prices.get('196', {}) else 2.10},
                    {'code': '197', 'name': 'البحرين', 'flag': '🇧🇭', 
                     'price': prices.get('197', {}).get(service, {}).get('cost', 2.00) if prices and isinstance(prices.get('197'), dict) and service in prices.get('197', {}) else 2.00},
                    {'code': '198', 'name': 'عمان', 'flag': '🇴🇲', 
                     'price': prices.get('198', {}).get(service, {}).get('cost', 1.90) if prices and isinstance(prices.get('198'), dict) and service in prices.get('198', {}) else 1.90},
                    {'code': '3', 'name': 'إندونيسيا', 'flag': '🇮🇩', 
                     'price': prices.get('3', {}).get(service, {}).get('cost', 1.10) if prices and isinstance(prices.get('3'), dict) and service in prices.get('3', {}) else 1.10},
                    {'code': '4', 'name': 'الهند', 'flag': '🇮🇳', 
                     'price': prices.get('4', {}).get(service, {}).get('cost', 0.90) if prices and isinstance(prices.get('4'), dict) and service in prices.get('4', {}) else 0.90},
                    {'code': '5', 'name': 'الفلبين', 'flag': '🇵🇭', 
                     'price': prices.get('5', {}).get(service, {}).get('cost', 1.30) if prices and isinstance(prices.get('5'), dict) and service in prices.get('5', {}) else 1.30},
                    {'code': '7', 'name': 'فيتنام', 'flag': '🇻🇳', 
                     'price': prices.get('7', {}).get(service, {}).get('cost', 1.00) if prices and isinstance(prices.get('7'), dict) and service in prices.get('7', {}) else 1.00},
                    {'code': '8', 'name': 'الصين', 'flag': '🇨🇳', 
                     'price': prices.get('8', {}).get(service, {}).get('cost', 1.40) if prices and isinstance(prices.get('8'), dict) and service in prices.get('8', {}) else 1.40},
                    {'code': '9', 'name': 'الولايات المتحدة', 'flag': '🇺🇸', 
                     'price': prices.get('9', {}).get(service, {}).get('cost', 2.50) if prices and isinstance(prices.get('9'), dict) and service in prices.get('9', {}) else 2.50},
                    {'code': '10', 'name': 'بريطانيا', 'flag': '🇬🇧', 
                     'price': prices.get('10', {}).get(service, {}).get('cost', 2.30) if prices and isinstance(prices.get('10'), dict) and service in prices.get('10', {}) else 2.30},
                    {'code': '11', 'name': 'ألمانيا', 'flag': '🇩🇪', 
                     'price': prices.get('11', {}).get(service, {}).get('cost', 2.20) if prices and isinstance(prices.get('11'), dict) and service in prices.get('11', {}) else 2.20},
                    {'code': '12', 'name': 'فرنسا', 'flag': '🇫🇷', 
                     'price': prices.get('12', {}).get(service, {}).get('cost', 2.10) if prices and isinstance(prices.get('12'), dict) and service in prices.get('12', {}) else 2.10},
                    {'code': '13', 'name': 'إسبانيا', 'flag': '🇪🇸', 
                     'price': prices.get('13', {}).get(service, {}).get('cost', 2.00) if prices and isinstance(prices.get('13'), dict) and service in prices.get('13', {}) else 2.00},
                    {'code': '14', 'name': 'إيطاليا', 'flag': '🇮🇹', 
                     'price': prices.get('14', {}).get(service, {}).get('cost', 2.00) if prices and isinstance(prices.get('14'), dict) and service in prices.get('14', {}) else 2.00},
                    {'code': '15', 'name': 'تركيا', 'flag': '🇹🇷', 
                     'price': prices.get('15', {}).get(service, {}).get('cost', 1.70) if prices and isinstance(prices.get('15'), dict) and service in prices.get('15', {}) else 1.70}
                ]
                
                # عرض الدول مع الأسعار
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                
                for country in countries:
                    button_text = f"{country['flag']} {country['name']} - ${country['price']:.2f}"
                    keyboard.add(types.InlineKeyboardButton(
                        button_text, 
                        callback_data=f"country_{country['code']}"
                    ))
                
                keyboard.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="buy"))
                
                bot.edit_message_text(
                    f"📱 **الخدمة:** {service_name}\n\n"
                    f"🌍 **اختر الدولة (مع السعر):**",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            
            elif data.startswith("country_"):
                country = data.replace("country_", "")
                
                # استرجاع بيانات المستخدم
                user_info = user_data.get(user_id, {})
                service = user_info.get('service', 'tg')
                service_name = user_info.get('service_name', 'تلغرام')
                
                # أسعار الدول
                country_prices = {
                    '6': 0.50, '2': 0.80, '1': 0.60, '0': 1.50,
                    '187': 1.20, '194': 1.80, '195': 2.00, '193': 2.20,
                    '196': 2.10, '197': 2.00, '198': 1.90, '3': 1.10,
                    '4': 0.90, '5': 1.30, '7': 1.00, '8': 1.40,
                    '9': 2.50, '10': 2.30, '11': 2.20, '12': 2.10,
                    '13': 2.00, '14': 2.00, '15': 1.70
                }
                
                country_names = {
                    '6': 'روسيا', '2': 'كازاخستان', '1': 'أوكرانيا', '0': 'جميع الدول',
                    '187': 'مصر', '194': 'السعودية', '195': 'الإمارات', '193': 'الكويت',
                    '196': 'قطر', '197': 'البحرين', '198': 'عمان', '3': 'إندونيسيا',
                    '4': 'الهند', '5': 'الفلبين', '7': 'فيتنام', '8': 'الصين',
                    '9': 'الولايات المتحدة', '10': 'بريطانيا', '11': 'ألمانيا', '12': 'فرنسا',
                    '13': 'إسبانيا', '14': 'إيطاليا', '15': 'تركيا'
                }
                
                country_flags = {
                    '6': '🇷🇺', '2': '🇰🇿', '1': '🇺🇦', '0': '🌍',
                    '187': '🇪🇬', '194': '🇸🇦', '195': '🇦🇪', '193': '🇰🇼',
                    '196': '🇶🇦', '197': '🇧🇭', '198': '🇴🇲', '3': '🇮🇩',
                    '4': '🇮🇳', '5': '🇵🇭', '7': '🇻🇳', '8': '🇨🇳',
                    '9': '🇺🇸', '10': '🇬🇧', '11': '🇩🇪', '12': '🇫🇷',
                    '13': '🇪🇸', '14': '🇮🇹', '15': '🇹🇷'
                }
                
                country_name = country_names.get(country, 'غير معروفة')
                country_flag = country_flags.get(country, '🏳️')
                price = country_prices.get(country, 1.0)
                
                # حفظ الدولة
                if user_id not in user_data:
                    user_data[user_id] = {}
                user_data[user_id]['country'] = country
                user_data[user_id]['country_name'] = country_name
                user_data[user_id]['country_flag'] = country_flag
                user_data[user_id]['price'] = price
                
                # عرض تأكيد الشراء مع السعر
                keyboard = types.InlineKeyboardMarkup(row_width=2)
                keyboard.add(
                    types.InlineKeyboardButton("✅ تأكيد الشراء", callback_data="confirm"),
                    types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel")
                )
                
                bot.edit_message_text(
                    f"📱 **تفاصيل الطلب**\n\n"
                    f"الخدمة: {service_name}\n"
                    f"الدولة: {country_flag} {country_name}\n"
                    f"السعر: **${price:.2f}**\n\n"
                    f"⚠️ هل تريد تأكيد الشراء؟",
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            
            elif data == "confirm":
                # تأكيد الشراء
                user_info = user_data.get(user_id, {})
                service = user_info.get('service', 'tg')
                service_name = user_info.get('service_name', 'تلغرام')
                country = user_info.get('country', '6')
                country_name = user_info.get('country_name', 'روسيا')
                country_flag = user_info.get('country_flag', '🇷🇺')
                price = user_info.get('price', 0.5)
                
                bot.edit_message_text(
                    "🔄 **جاري طلب الرقم...**\n\nالرجاء الانتظار",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
                
                # محاولة طلب رقم حقيقي من API
                if api_client:
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        # تحويل رمز الدولة إلى رقم صحيح
                        country_int = int(country) if country.isdigit() else 6
                        
                        number_data = loop.run_until_complete(
                            api_client.get_number(service, country_int)
                        )
                        loop.close()
                        
                        if number_data and number_data.get('phoneNumber'):
                            phone = number_data.get('phoneNumber')
                            activation_id = number_data.get('activationId')
                            
                            bot.edit_message_text(
                                f"✅ **تم شراء الرقم بنجاح!**\n\n"
                                f"📱 **الرقم:** `{phone}`\n"
                                f"🆔 **معرف التفعيل:** `{activation_id}`\n"
                                f"💰 **السعر:** ${price:.2f}\n"
                                f"🌍 **الدولة:** {country_flag} {country_name}\n"
                                f"📱 **الخدمة:** {service_name}\n\n"
                                f"⏱️ الرقم صالح لمدة 20 دقيقة\n"
                                f"📨 سيتم إعلامك عند وصول رسالة جديدة",
                                call.message.chat.id,
                                call.message.message_id,
                                parse_mode='Markdown'
                            )
                        else:
                            # إذا فشل API، استخدم رقماً وهمياً
                            phone = f"+7 (9{random.randint(10, 99)}) {random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10, 99)}"
                            
                            bot.edit_message_text(
                                f"✅ **تمت العملية بنجاح! (تجريبي)**\n\n"
                                f"📱 **الرقم:** `{phone}`\n"
                                f"💰 **السعر:** ${price:.2f}\n"
                                f"🌍 **الدولة:** {country_flag} {country_name}\n"
                                f"📱 **الخدمة:** {service_name}\n\n"
                                f"⚠️ هذا رقم تجريبي (فشل الاتصال بـ API)",
                                call.message.chat.id,
                                call.message.message_id,
                                parse_mode='Markdown'
                            )
                            
                    except Exception as e:
                        logger.error(f"خطأ في طلب الرقم من API: {e}")
                        
                        # استخدام رقم وهمي في حالة الخطأ
                        phone = f"+7 (9{random.randint(10, 99)}) {random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10, 99)}"
                        
                        bot.edit_message_text(
                            f"✅ **تمت العملية بنجاح! (تجريبي)**\n\n"
                            f"📱 **الرقم:** `{phone}`\n"
                            f"💰 **السعر:** ${price:.2f}\n"
                            f"🌍 **الدولة:** {country_flag} {country_name}\n"
                            f"📱 **الخدمة:** {service_name}\n\n"
                            f"⚠️ هذا رقم تجريبي (خطأ: {str(e)[:50]}...)",
                            call.message.chat.id,
                            call.message.message_id,
                            parse_mode='Markdown'
                        )
                else:
                    # API غير مهيأ - استخدام أرقام وهمية
                    phone = f"+7 (9{random.randint(10, 99)}) {random.randint(100, 999)}-{random.randint(10, 99)}-{random.randint(10, 99)}"
                    
                    bot.edit_message_text(
                        f"✅ **تمت العملية بنجاح! (تجريبي)**\n\n"
                        f"📱 **الرقم:** `{phone}`\n"
                        f"💰 **السعر:** ${price:.2f}\n"
                        f"🌍 **الدولة:** {country_flag} {country_name}\n"
                        f"📱 **الخدمة:** {service_name}\n\n"
                        f"⚠️ هذا رقم تجريبي (API غير مهيأ)",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='Markdown'
                    )
                
                # مسح بيانات المستخدم بعد الشراء
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
