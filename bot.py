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

# قائمة شاملة بجميع الدول المتاحة (مع رموزها ورموز الأعلام)
COUNTRIES = [
    {'code': '6', 'name': 'روسيا', 'flag': '🇷🇺', 'price': 0.50},
    {'code': '2', 'name': 'كازاخستان', 'flag': '🇰🇿', 'price': 0.80},
    {'code': '1', 'name': 'أوكرانيا', 'flag': '🇺🇦', 'price': 0.60},
    {'code': '0', 'name': 'جميع الدول', 'flag': '🌍', 'price': 1.50},
    {'code': '187', 'name': 'مصر', 'flag': '🇪🇬', 'price': 1.20},
    {'code': '194', 'name': 'السعودية', 'flag': '🇸🇦', 'price': 1.80},
    {'code': '195', 'name': 'الإمارات', 'flag': '🇦🇪', 'price': 2.00},
    {'code': '193', 'name': 'الكويت', 'flag': '🇰🇼', 'price': 2.20},
    {'code': '196', 'name': 'قطر', 'flag': '🇶🇦', 'price': 2.10},
    {'code': '197', 'name': 'البحرين', 'flag': '🇧🇭', 'price': 2.00},
    {'code': '198', 'name': 'عمان', 'flag': '🇴🇲', 'price': 1.90},
    {'code': '192', 'name': 'اليمن', 'flag': '🇾🇪', 'price': 1.70},
    {'code': '191', 'name': 'العراق', 'flag': '🇮🇶', 'price': 1.80},
    {'code': '190', 'name': 'الأردن', 'flag': '🇯🇴', 'price': 1.60},
    {'code': '189', 'name': 'لبنان', 'flag': '🇱🇧', 'price': 1.70},
    {'code': '188', 'name': 'فلسطين', 'flag': '🇵🇸', 'price': 1.60},
    {'code': '199', 'name': 'سوريا', 'flag': '🇸🇾', 'price': 1.50},
    {'code': '200', 'name': 'ليبيا', 'flag': '🇱🇾', 'price': 1.60},
    {'code': '201', 'name': 'الجزائر', 'flag': '🇩🇿', 'price': 1.50},
    {'code': '202', 'name': 'المغرب', 'flag': '🇲🇦', 'price': 1.50},
    {'code': '203', 'name': 'تونس', 'flag': '🇹🇳', 'price': 1.40},
    {'code': '204', 'name': 'السودان', 'flag': '🇸🇩', 'price': 1.30},
    {'code': '205', 'name': 'الصومال', 'flag': '🇸🇴', 'price': 1.40},
    {'code': '206', 'name': 'جيبوتي', 'flag': '🇩🇯', 'price': 1.30},
    {'code': '207', 'name': 'موريتانيا', 'flag': '🇲🇷', 'price': 1.30},
    {'code': '3', 'name': 'إندونيسيا', 'flag': '🇮🇩', 'price': 1.10},
    {'code': '4', 'name': 'الهند', 'flag': '🇮🇳', 'price': 0.90},
    {'code': '5', 'name': 'الفلبين', 'flag': '🇵🇭', 'price': 1.30},
    {'code': '7', 'name': 'فيتنام', 'flag': '🇻🇳', 'price': 1.00},
    {'code': '8', 'name': 'الصين', 'flag': '🇨🇳', 'price': 1.40},
    {'code': '9', 'name': 'الولايات المتحدة', 'flag': '🇺🇸', 'price': 2.50},
    {'code': '10', 'name': 'بريطانيا', 'flag': '🇬🇧', 'price': 2.30},
    {'code': '11', 'name': 'ألمانيا', 'flag': '🇩🇪', 'price': 2.20},
    {'code': '12', 'name': 'فرنسا', 'flag': '🇫🇷', 'price': 2.10},
    {'code': '13', 'name': 'إسبانيا', 'flag': '🇪🇸', 'price': 2.00},
    {'code': '14', 'name': 'إيطاليا', 'flag': '🇮🇹', 'price': 2.00},
    {'code': '15', 'name': 'تركيا', 'flag': '🇹🇷', 'price': 1.70},
    {'code': '16', 'name': 'اليونان', 'flag': '🇬🇷', 'price': 1.90},
    {'code': '17', 'name': 'هولندا', 'flag': '🇳🇱', 'price': 2.10},
    {'code': '18', 'name': 'بلجيكا', 'flag': '🇧🇪', 'price': 2.00},
    {'code': '19', 'name': 'السويد', 'flag': '🇸🇪', 'price': 2.20},
    {'code': '20', 'name': 'النرويج', 'flag': '🇳🇴', 'price': 2.30},
    {'code': '21', 'name': 'الدنمارك', 'flag': '🇩🇰', 'price': 2.20},
    {'code': '22', 'name': 'فنلندا', 'flag': '🇫🇮', 'price': 2.10},
    {'code': '23', 'name': 'بولندا', 'flag': '🇵🇱', 'price': 1.80},
    {'code': '24', 'name': 'التشيك', 'flag': '🇨🇿', 'price': 1.90},
    {'code': '25', 'name': 'سلوفاكيا', 'flag': '🇸🇰', 'price': 1.80},
    {'code': '26', 'name': 'المجر', 'flag': '🇭🇺', 'price': 1.80},
    {'code': '27', 'name': 'رومانيا', 'flag': '🇷🇴', 'price': 1.70},
    {'code': '28', 'name': 'بلغاريا', 'flag': '🇧🇬', 'price': 1.60},
    {'code': '29', 'name': 'صربيا', 'flag': '🇷🇸', 'price': 1.60},
    {'code': '30', 'name': 'كرواتيا', 'flag': '🇭🇷', 'price': 1.70},
    {'code': '31', 'name': 'البوسنة', 'flag': '🇧🇦', 'price': 1.50},
    {'code': '32', 'name': 'ألبانيا', 'flag': '🇦🇱', 'price': 1.50},
    {'code': '33', 'name': 'مقدونيا', 'flag': '🇲🇰', 'price': 1.50},
    {'code': '34', 'name': 'الجبل الأسود', 'flag': '🇲🇪', 'price': 1.50},
    {'code': '35', 'name': 'البرتغال', 'flag': '🇵🇹', 'price': 1.90},
    {'code': '36', 'name': 'سويسرا', 'flag': '🇨🇭', 'price': 2.40},
    {'code': '37', 'name': 'النمسا', 'flag': '🇦🇹', 'price': 2.20},
    {'code': '38', 'name': 'البرازيل', 'flag': '🇧🇷', 'price': 2.00},
    {'code': '39', 'name': 'الأرجنتين', 'flag': '🇦🇷', 'price': 1.80},
    {'code': '40', 'name': 'المكسيك', 'flag': '🇲🇽', 'price': 1.90},
    {'code': '41', 'name': 'كولومبيا', 'flag': '🇨🇴', 'price': 1.70},
    {'code': '42', 'name': 'تشيلي', 'flag': '🇨🇱', 'price': 1.80},
    {'code': '43', 'name': 'بيرو', 'flag': '🇵🇪', 'price': 1.60},
    {'code': '44', 'name': 'فنزويلا', 'flag': '🇻🇪', 'price': 1.50},
    {'code': '45', 'name': 'الإكوادور', 'flag': '🇪🇨', 'price': 1.50},
    {'code': '46', 'name': 'بوليفيا', 'flag': '🇧🇴', 'price': 1.40},
    {'code': '47', 'name': 'باراغواي', 'flag': '🇵🇾', 'price': 1.40},
    {'code': '48', 'name': 'أوروغواي', 'flag': '🇺🇾', 'price': 1.60},
    {'code': '49', 'name': 'غيانا', 'flag': '🇬🇾', 'price': 1.30},
    {'code': '50', 'name': 'سورينام', 'flag': '🇸🇷', 'price': 1.30},
    {'code': '51', 'name': 'غويانا الفرنسية', 'flag': '🇬🇫', 'price': 1.40},
    {'code': '52', 'name': 'جنوب أفريقيا', 'flag': '🇿🇦', 'price': 1.80},
    {'code': '53', 'name': 'نيجيريا', 'flag': '🇳🇬', 'price': 1.40},
    {'code': '54', 'name': 'كينيا', 'flag': '🇰🇪', 'price': 1.30},
    {'code': '55', 'name': 'إثيوبيا', 'flag': '🇪🇹', 'price': 1.20},
    {'code': '56', 'name': 'تنزانيا', 'flag': '🇹🇿', 'price': 1.20},
    {'code': '57', 'name': 'أوغندا', 'flag': '🇺🇬', 'price': 1.20},
    {'code': '58', 'name': 'رواندا', 'flag': '🇷🇼', 'price': 1.10},
    {'code': '59', 'name': 'بوروندي', 'flag': '🇧🇮', 'price': 1.10},
    {'code': '60', 'name': 'الكونغو', 'flag': '🇨🇩', 'price': 1.10},
    {'code': '61', 'name': 'الكاميرون', 'flag': '🇨🇲', 'price': 1.20},
    {'code': '62', 'name': 'الغابون', 'flag': '🇬🇦', 'price': 1.30},
    {'code': '63', 'name': 'غينيا', 'flag': '🇬🇳', 'price': 1.10},
    {'code': '64', 'name': 'غانا', 'flag': '🇬🇭', 'price': 1.20},
    {'code': '65', 'name': 'كوت ديفوار', 'flag': '🇨🇮', 'price': 1.20},
    {'code': '66', 'name': 'بوركينا فاسو', 'flag': '🇧🇫', 'price': 1.10},
    {'code': '67', 'name': 'مالي', 'flag': '🇲🇱', 'price': 1.10},
    {'code': '68', 'name': 'النيجر', 'flag': '🇳🇪', 'price': 1.10},
    {'code': '69', 'name': 'السنغال', 'flag': '🇸🇳', 'price': 1.20},
    {'code': '70', 'name': 'بنين', 'flag': '🇧🇯', 'price': 1.10},
    {'code': '71', 'name': 'توغو', 'flag': '🇹🇬', 'price': 1.10},
    {'code': '72', 'name': 'أستراليا', 'flag': '🇦🇺', 'price': 2.40},
    {'code': '73', 'name': 'نيوزيلندا', 'flag': '🇳🇿', 'price': 2.30},
    {'code': '74', 'name': 'اليابان', 'flag': '🇯🇵', 'price': 2.20},
    {'code': '75', 'name': 'كوريا الجنوبية', 'flag': '🇰🇷', 'price': 2.10},
    {'code': '76', 'name': 'سنغافورة', 'flag': '🇸🇬', 'price': 2.00},
    {'code': '77', 'name': 'ماليزيا', 'flag': '🇲🇾', 'price': 1.70},
    {'code': '78', 'name': 'تايلاند', 'flag': '🇹🇭', 'price': 1.60},
    {'code': '79', 'name': 'ميانمار', 'flag': '🇲🇲', 'price': 1.30},
    {'code': '80', 'name': 'كمبوديا', 'flag': '🇰🇭', 'price': 1.30},
    {'code': '81', 'name': 'لاوس', 'flag': '🇱🇦', 'price': 1.20},
    {'code': '82', 'name': 'باكستان', 'flag': '🇵🇰', 'price': 1.20},
    {'code': '83', 'name': 'بنغلاديش', 'flag': '🇧🇩', 'price': 1.10},
    {'code': '84', 'name': 'سريلانكا', 'flag': '🇱🇰', 'price': 1.20},
    {'code': '85', 'name': 'نيبال', 'flag': '🇳🇵', 'price': 1.10},
    {'code': '86', 'name': 'أفغانستان', 'flag': '🇦🇫', 'price': 1.00},
    {'code': '87', 'name': 'إيران', 'flag': '🇮🇷', 'price': 1.30}
]

# عدد الدول في كل صفحة
COUNTRIES_PER_PAGE = 10

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
• وأكثر من 80 دولة حول العالم

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
• تتوفر أكثر من 80 دولة للاختيار من بينها
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
    
    def show_countries_page(call, service, service_name, page=0):
        """عرض صفحة من الدول مع أزرار التنقل"""
        user_id = call.from_user.id
        
        # حساب مؤشرات الصفحة
        start_idx = page * COUNTRIES_PER_PAGE
        end_idx = min(start_idx + COUNTRIES_PER_PAGE, len(COUNTRIES))
        total_pages = (len(COUNTRIES) + COUNTRIES_PER_PAGE - 1) // COUNTRIES_PER_PAGE
        
        # الحصول على الدول للصفحة الحالية
        current_countries = COUNTRIES[start_idx:end_idx]
        
        # إنشاء لوحة المفاتيح
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # إضافة أزرار الدول
        for country in current_countries:
            button_text = f"{country['flag']} {country['name']} - ${country['price']:.2f}"
            keyboard.add(types.InlineKeyboardButton(
                button_text, 
                callback_data=f"country_{country['code']}"
            ))
        
        # إضافة أزرار التنقل
        nav_buttons = []
        
        if page > 0:
            nav_buttons.append(types.InlineKeyboardButton(
                "◀️ السابق", 
                callback_data=f"page_{service}_{page-1}"
            ))
        
        nav_buttons.append(types.InlineKeyboardButton(
            f"📄 {page+1}/{total_pages}", 
            callback_data="noop"
        ))
        
        if page < total_pages - 1:
            nav_buttons.append(types.InlineKeyboardButton(
                "التالي ▶️", 
                callback_data=f"page_{service}_{page+1}"
            ))
        
        keyboard.row(*nav_buttons)
        
        # إضافة زر الرجوع
        keyboard.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="buy"))
        
        # حفظ الصفحة الحالية في بيانات المستخدم
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['current_page'] = page
        user_data[user_id]['service'] = service
        user_data[user_id]['service_name'] = service_name
        
        # تحديث الرسالة
        bot.edit_message_text(
            f"📱 **الخدمة:** {service_name}\n\n"
            f"🌍 **اختر الدولة (مع السعر):**\n"
            f"عرض {start_idx+1}-{end_idx} من {len(COUNTRIES)} دولة",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=keyboard,
            parse_mode='Markdown'
        )
    
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
                
                # رسالة تحميل
                bot.edit_message_text(
                    "🔄 **جاري تحميل الأسعار...**",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
                
                # محاولة جلب الأسعار من API
                if api_client:
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        prices_data = loop.run_until_complete(api_client.get_prices(service))
                        loop.close()
                        
                        # تحديث الأسعار إذا توفرت
                        if prices_data and isinstance(prices_data, dict):
                            for country in COUNTRIES:
                                code = country['code']
                                if code in prices_data and isinstance(prices_data[code], dict) and service in prices_data[code]:
                                    country['price'] = prices_data[code][service].get('cost', country['price'])
                            logger.info(f"✅ تم تحديث الأسعار للخدمة {service}")
                    except Exception as e:
                        logger.error(f"❌ خطأ في جلب الأسعار: {e}")
                
                # عرض الصفحة الأولى من الدول
                show_countries_page(call, service, service_name, 0)
            
            elif data.startswith("page_"):
                # معالجة التنقل بين الصفحات
                parts = data.split('_')
                if len(parts) >= 3:
                    service = parts[1]
                    page = int(parts[2])
                    service_name = AVAILABLE_SERVICES.get(service, service)
                    show_countries_page(call, service, service_name, page)
            
            elif data == "noop":
                # زر غير فعال (للعداد فقط)
                bot.answer_callback_query(call.id, f"الصفحة {user_data.get(user_id, {}).get('current_page', 0)+1}")
            
            elif data.startswith("country_"):
                country = data.replace("country_", "")
                
                # استرجاع بيانات المستخدم
                user_info = user_data.get(user_id, {})
                service = user_info.get('service', 'tg')
                service_name = user_info.get('service_name', 'تلغرام')
                
                # البحث عن معلومات الدولة
                selected_country = None
                for c in COUNTRIES:
                    if c['code'] == country:
                        selected_country = c
                        break
                
                if not selected_country:
                    selected_country = {'code': country, 'name': 'غير معروفة', 'flag': '🏳️', 'price': 1.0}
                
                country_name = selected_country['name']
                country_flag = selected_country['flag']
                price = selected_country['price']
                
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
                
                # إضافة زر الرجوع للدول مع حفظ الصفحة
                back_page = user_info.get('current_page', 0)
                keyboard.add(types.InlineKeyboardButton("🔙 رجوع للدول", callback_data=f"page_{service}_{back_page}"))
                
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
                        
                        # تسجيل الاستجابة للتصحيح
                        logger.info(f"📞 استجابة get_number: {number_data}")
                        
                        # تحقق من نجاح العملية
                        if number_data and number_data.get('success', False):
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
                            # عرض رسالة خطأ واضحة
                            error_msg = "فشل الاتصال بـ API"
                            if number_data and number_data.get('error') == 'no_numbers':
                                error_msg = "لا توجد أرقام متاحة حالياً"
                            elif number_data and number_data.get('error') == 'no_balance':
                                error_msg = "رصيد API غير كافٍ"
                            
                            bot.edit_message_text(
                                f"❌ **فشل شراء الرقم**\n\n"
                                f"السبب: {error_msg}\n\n"
                                f"💰 السعر: ${price:.2f}\n"
                                f"🌍 الدولة: {country_flag} {country_name}\n"
                                f"📱 الخدمة: {service_name}\n\n"
                                f"⚠️ يرجى المحاولة لاحقاً أو اختيار دولة أخرى",
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
