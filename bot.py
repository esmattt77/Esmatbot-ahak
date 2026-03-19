import telebot
from telebot import types
import logging
import os
import random
import time
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

# قاموس أسماء المشغلين (السيرفرات)
OPERATOR_NAMES = {
    'any': '🔄 أي مشغل',
    'mts': '📡 MTS',
    'beeline': '📡 Beeline',
    'megafon': '📡 Megafon',
    'tele2': '📡 Tele2',
    'vodafone': '📡 Vodafone',
    'kyivstar': '📡 Kyivstar',
    'lifecell': '📡 Lifecell',
    'orange': '📡 Orange',
    't-mobile': '📡 T-Mobile',
    'verizon': '📡 Verizon',
    'att': '📡 AT&T',
    'o2': '📡 O2',
    'three': '📡 Three',
    'etisalat': '📡 Etisalat',
    'du': '📡 Du',
    'zain': '📡 Zain',
    'stc': '📡 STC',
    'mobily': '📡 Mobily',
    'virgin': '📡 Virgin',
}

# قاموس رموز المشغلين (اختصاري)
OPERATOR_CODES = {
    'any': 'any',
    'mts': 'mts',
    'beeline': 'beeline',
    'megafon': 'megafon',
    'tele2': 'tele2',
    'vodafone': 'vodafone',
    'kyivstar': 'kyivstar',
    'lifecell': 'lifecell',
    'orange': 'orange',
    't-mobile': 't-mobile',
    'verizon': 'verizon',
    'att': 'att',
    'o2': 'o2',
    'three': 'three',
    'etisalat': 'etisalat',
    'du': 'du',
    'zain': 'zain',
    'stc': 'stc',
    'mobily': 'mobily',
    'virgin': 'virgin',
}

# قائمة شاملة بجميع الدول المتاحة (مع رموزها ورموز الأعلام)
COUNTRIES = [
    {'code': '1', 'name': 'روسيا', 'flag': '🇷🇺', 'price': 0.50},
    {'code': '2', 'name': 'أوكرانيا', 'flag': '🇺🇦', 'price': 0.60},
    {'code': '3', 'name': 'كازاخستان', 'flag': '🇰🇿', 'price': 0.80},
    {'code': '4', 'name': 'بيلاروسيا', 'flag': '🇧🇾', 'price': 0.70},
    {'code': '6', 'name': 'إندونيسيا', 'flag': '🇮🇩', 'price': 1.10},
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
    {'code': '7', 'name': 'الولايات المتحدة', 'flag': '🇺🇸', 'price': 2.50},
    {'code': '8', 'name': 'كندا', 'flag': '🇨🇦', 'price': 2.40},
    {'code': '9', 'name': 'بريطانيا', 'flag': '🇬🇧', 'price': 2.30},
    {'code': '10', 'name': 'ألمانيا', 'flag': '🇩🇪', 'price': 2.20},
    {'code': '11', 'name': 'فرنسا', 'flag': '🇫🇷', 'price': 2.10},
    {'code': '12', 'name': 'إسبانيا', 'flag': '🇪🇸', 'price': 2.00},
    {'code': '13', 'name': 'إيطاليا', 'flag': '🇮🇹', 'price': 2.00},
    {'code': '14', 'name': 'هولندا', 'flag': '🇳🇱', 'price': 2.10},
    {'code': '15', 'name': 'بلجيكا', 'flag': '🇧🇪', 'price': 2.00},
    {'code': '16', 'name': 'السويد', 'flag': '🇸🇪', 'price': 2.20},
    {'code': '17', 'name': 'النرويج', 'flag': '🇳🇴', 'price': 2.30},
    {'code': '18', 'name': 'الدنمارك', 'flag': '🇩🇰', 'price': 2.20},
    {'code': '19', 'name': 'فنلندا', 'flag': '🇫🇮', 'price': 2.10},
    {'code': '20', 'name': 'بولندا', 'flag': '🇵🇱', 'price': 1.80},
    {'code': '21', 'name': 'التشيك', 'flag': '🇨🇿', 'price': 1.90},
    {'code': '22', 'name': 'سلوفاكيا', 'flag': '🇸🇰', 'price': 1.80},
    {'code': '23', 'name': 'المجر', 'flag': '🇭🇺', 'price': 1.80},
    {'code': '24', 'name': 'رومانيا', 'flag': '🇷🇴', 'price': 1.70},
    {'code': '25', 'name': 'بلغاريا', 'flag': '🇧🇬', 'price': 1.60},
    {'code': '26', 'name': 'اليونان', 'flag': '🇬🇷', 'price': 1.90},
    {'code': '27', 'name': 'البرتغال', 'flag': '🇵🇹', 'price': 1.90},
    {'code': '28', 'name': 'سويسرا', 'flag': '🇨🇭', 'price': 2.40},
    {'code': '29', 'name': 'النمسا', 'flag': '🇦🇹', 'price': 2.20},
    {'code': '30', 'name': 'اليابان', 'flag': '🇯🇵', 'price': 2.20},
    {'code': '31', 'name': 'كوريا الجنوبية', 'flag': '🇰🇷', 'price': 2.10},
    {'code': '32', 'name': 'الصين', 'flag': '🇨🇳', 'price': 1.40},
    {'code': '33', 'name': 'الهند', 'flag': '🇮🇳', 'price': 0.90},
    {'code': '34', 'name': 'باكستان', 'flag': '🇵🇰', 'price': 1.20},
    {'code': '35', 'name': 'بنغلاديش', 'flag': '🇧🇩', 'price': 1.10},
    {'code': '36', 'name': 'الفلبين', 'flag': '🇵🇭', 'price': 1.30},
    {'code': '37', 'name': 'ماليزيا', 'flag': '🇲🇾', 'price': 1.70},
    {'code': '38', 'name': 'سنغافورة', 'flag': '🇸🇬', 'price': 2.00},
    {'code': '39', 'name': 'تايلاند', 'flag': '🇹🇭', 'price': 1.60},
    {'code': '40', 'name': 'فيتنام', 'flag': '🇻🇳', 'price': 1.00},
    {'code': '41', 'name': 'أستراليا', 'flag': '🇦🇺', 'price': 2.40},
    {'code': '42', 'name': 'نيوزيلندا', 'flag': '🇳🇿', 'price': 2.30},
    {'code': '43', 'name': 'المكسيك', 'flag': '🇲🇽', 'price': 1.90},
    {'code': '44', 'name': 'البرازيل', 'flag': '🇧🇷', 'price': 2.00},
    {'code': '45', 'name': 'الأرجنتين', 'flag': '🇦🇷', 'price': 1.80},
    {'code': '46', 'name': 'كولومبيا', 'flag': '🇨🇴', 'price': 1.70},
    {'code': '47', 'name': 'بيرو', 'flag': '🇵🇪', 'price': 1.60},
    {'code': '48', 'name': 'تشيلي', 'flag': '🇨🇱', 'price': 1.80},
    {'code': '49', 'name': 'فنزويلا', 'flag': '🇻🇪', 'price': 1.50},
    {'code': '50', 'name': 'الإكوادور', 'flag': '🇪🇨', 'price': 1.50},
    {'code': '51', 'name': 'غواتيمالا', 'flag': '🇬🇹', 'price': 1.40},
    {'code': '52', 'name': 'كوبا', 'flag': '🇨🇺', 'price': 1.50},
    {'code': '53', 'name': 'هايتي', 'flag': '🇭🇹', 'price': 1.30},
    {'code': '54', 'name': 'جمهورية الدومينيكان', 'flag': '🇩🇴', 'price': 1.50},
    {'code': '55', 'name': 'هندوراس', 'flag': '🇭🇳', 'price': 1.30},
    {'code': '56', 'name': 'نيكاراغوا', 'flag': '🇳🇮', 'price': 1.30},
    {'code': '57', 'name': 'بنما', 'flag': '🇵🇦', 'price': 1.40},
    {'code': '58', 'name': 'السلفادور', 'flag': '🇸🇻', 'price': 1.30},
    {'code': '59', 'name': 'كوستاريكا', 'flag': '🇨🇷', 'price': 1.40},
    {'code': '60', 'name': 'باراغواي', 'flag': '🇵🇾', 'price': 1.40},
    {'code': '61', 'name': 'أوروغواي', 'flag': '🇺🇾', 'price': 1.60},
    {'code': '62', 'name': 'بوليفيا', 'flag': '🇧🇴', 'price': 1.40},
    {'code': '63', 'name': 'غيانا', 'flag': '🇬🇾', 'price': 1.30},
    {'code': '64', 'name': 'سورينام', 'flag': '🇸🇷', 'price': 1.30},
    {'code': '65', 'name': 'غويانا الفرنسية', 'flag': '🇬🇫', 'price': 1.40},
    {'code': '66', 'name': 'الجزائر', 'flag': '🇩🇿', 'price': 1.50},
    {'code': '67', 'name': 'المغرب', 'flag': '🇲🇦', 'price': 1.50},
    {'code': '68', 'name': 'تونس', 'flag': '🇹🇳', 'price': 1.40},
    {'code': '69', 'name': 'ليبيا', 'flag': '🇱🇾', 'price': 1.60},
    {'code': '70', 'name': 'السودان', 'flag': '🇸🇩', 'price': 1.30},
    {'code': '71', 'name': 'مصر', 'flag': '🇪🇬', 'price': 1.20},
    {'code': '72', 'name': 'الصومال', 'flag': '🇸🇴', 'price': 1.40},
    {'code': '73', 'name': 'جيبوتي', 'flag': '🇩🇯', 'price': 1.30},
    {'code': '74', 'name': 'كينيا', 'flag': '🇰🇪', 'price': 1.30},
    {'code': '75', 'name': 'تنزانيا', 'flag': '🇹🇿', 'price': 1.20},
    {'code': '76', 'name': 'أوغندا', 'flag': '🇺🇬', 'price': 1.20},
    {'code': '77', 'name': 'رواندا', 'flag': '🇷🇼', 'price': 1.10},
    {'code': '78', 'name': 'بوروندي', 'flag': '🇧🇮', 'price': 1.10},
    {'code': '79', 'name': 'إثيوبيا', 'flag': '🇪🇹', 'price': 1.20},
    {'code': '80', 'name': 'إريتريا', 'flag': '🇪🇷', 'price': 1.10},
    {'code': '81', 'name': 'جنوب السودان', 'flag': '🇸🇸', 'price': 1.10},
    {'code': '82', 'name': 'الكونغو الديمقراطية', 'flag': '🇨🇩', 'price': 1.10},
    {'code': '83', 'name': 'الكونغو', 'flag': '🇨🇬', 'price': 1.10},
    {'code': '84', 'name': 'الجابون', 'flag': '🇬🇦', 'price': 1.30},
    {'code': '85', 'name': 'غينيا الاستوائية', 'flag': '🇬🇶', 'price': 1.20},
    {'code': '86', 'name': 'الكاميرون', 'flag': '🇨🇲', 'price': 1.20},
    {'code': '87', 'name': 'نيجيريا', 'flag': '🇳🇬', 'price': 1.40},
    {'code': '88', 'name': 'غانا', 'flag': '🇬🇭', 'price': 1.20},
    {'code': '89', 'name': 'ساحل العاج', 'flag': '🇨🇮', 'price': 1.20},
    {'code': '90', 'name': 'بوركينا فاسو', 'flag': '🇧🇫', 'price': 1.10},
    {'code': '91', 'name': 'مالي', 'flag': '🇲🇱', 'price': 1.10},
    {'code': '92', 'name': 'النيجر', 'flag': '🇳🇪', 'price': 1.10},
    {'code': '93', 'name': 'تشاد', 'flag': '🇹🇩', 'price': 1.10},
    {'code': '94', 'name': 'موريتانيا', 'flag': '🇲🇷', 'price': 1.30},
    {'code': '95', 'name': 'السنغال', 'flag': '🇸🇳', 'price': 1.20},
    {'code': '96', 'name': 'غامبيا', 'flag': '🇬🇲', 'price': 1.10},
    {'code': '97', 'name': 'غينيا بيساو', 'flag': '🇬🇼', 'price': 1.10},
    {'code': '98', 'name': 'غينيا', 'flag': '🇬🇳', 'price': 1.10},
    {'code': '99', 'name': 'سيراليون', 'flag': '🇸🇱', 'price': 1.10},
    {'code': '100', 'name': 'ليبيريا', 'flag': '🇱🇷', 'price': 1.10}
]

# عدد الدول في كل صفحة
COUNTRIES_PER_PAGE = 8

# قاموس مؤقت لتخزين بيانات المستخدمين
user_data = {}

# قواميس مساعدة للدول
country_names = {str(c['code']): c['name'] for c in COUNTRIES}
country_flags = {str(c['code']): c['flag'] for c in COUNTRIES}

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
• وأكثر من 100 دولة حول العالم

🔹 **المميزات:**
• اختيار السيرفر (المشغل) المناسب
• إلغاء الرقم واسترداد الرصيد
• إعادة إرسال رمز التفعيل

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
            balance = api_client.get_balance()
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
3️⃣ اختر السيرفر (المشغل) المناسب
4️⃣ قم بتأكيد الشراء

**بعد الشراء:**
• يمكنك إعادة إرسال رمز التفعيل
• يمكنك إلغاء الرقم واسترداد الرصيد
• يمكنك الاستعلام عن حالة الرقم

**ملاحظات مهمة:**
• يتم خصم المبلغ من رصيدك عند التأكيد
• صلاحية الرقم 20 دقيقة
• يمكنك إلغاء العملية في أي وقت
• تتوفر أكثر من 100 دولة للاختيار من بينها
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
                balance = api_client.get_balance()
                bot.reply_to(message, f"💰 رصيد API: {balance} دولار")
            except Exception as e:
                bot.reply_to(message, f"❌ خطأ: {e}")
        
        elif text == '/admin stats':
            bot.reply_to(message, f"📊 إحصائيات:\nالمستخدمين النشطين: {len(user_data)}")
        
        else:
            bot.reply_to(message, "🔧 أوامر المشرفين:\n/admin balance - عرض رصيد API\n/admin stats - عرض إحصائيات")
    
    def show_countries_page(call, service, service_name, page=0, prices_data=None):
        """عرض صفحة من الدول مع أزرار التنقل"""
        user_id = call.from_user.id
        
        # حساب مؤشرات الصفحة
        start_idx = page * COUNTRIES_PER_PAGE
        end_idx = min(start_idx + COUNTRIES_PER_PAGE, len(COUNTRIES))
        total_pages = (len(COUNTRIES) + COUNTRIES_PER_PAGE - 1) // COUNTRIES_PER_PAGE
        
        # الحصول على الدول للصفحة الحالية
        current_countries = COUNTRIES[start_idx:end_idx]
        
        # إنشاء نسخة من الدول مع تحديث الأسعار من API إذا كانت متوفرة
        displayed_countries = []
        for country in current_countries:
            country_copy = country.copy()
            # تحديث السعر من بيانات API إذا كانت متوفرة
            if prices_data and country['code'] in prices_data and service in prices_data[country['code']]:
                country_copy['price'] = prices_data[country['code']][service].get('cost', country['price'])
            displayed_countries.append(country_copy)
        
        # إنشاء لوحة المفاتيح
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        
        # إضافة أزرار الدول
        for country in displayed_countries:
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
        keyboard.add(types.InlineKeyboardButton("🔙 رجوع للخدمات", callback_data="buy"))
        
        # حفظ الصفحة الحالية في بيانات المستخدم
        if user_id not in user_data:
            user_data[user_id] = {}
        user_data[user_id]['current_page'] = page
        user_data[user_id]['service'] = service
        user_data[user_id]['service_name'] = service_name
        
        # تحديث الرسالة
        bot.edit_message_text(
            f"📱 **الخدمة:** {service_name}\n\n"
            f"🌍 **اختر الدولة (الأسعار من الموقع):**\n"
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
                    balance = api_client.get_balance()
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
                    "🔄 **جاري تحميل الأسعار من الموقع...**",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
                
                # جلب الأسعار الحقيقية من API
                prices_data = None
                if api_client:
                    try:
                        prices_data = api_client.get_prices(service)
                        if prices_data and isinstance(prices_data, dict):
                            logger.info(f"✅ تم جلب الأسعار للخدمة {service}: {len(prices_data)} دولة")
                    except Exception as e:
                        logger.error(f"❌ خطأ في جلب الأسعار: {e}")
                
                # عرض الصفحة الأولى من الدول مع الأسعار المحدثة
                show_countries_page(call, service, service_name, 0, prices_data)
            
            elif data.startswith("page_"):
                # معالجة التنقل بين الصفحات
                parts = data.split('_')
                if len(parts) >= 3:
                    service = parts[1]
                    page = int(parts[2])
                    service_name = user_data.get(user_id, {}).get('service_name', AVAILABLE_SERVICES.get(service, service))
                    
                    # جلب الأسعار مرة أخرى للتأكد من تحديثها
                    prices_data = None
                    if api_client:
                        try:
                            prices_data = api_client.get_prices(service)
                        except:
                            pass
                    
                    show_countries_page(call, service, service_name, page, prices_data)
            
            elif data == "noop":
                # زر غير فعال (للعداد فقط)
                bot.answer_callback_query(call.id, f"الصفحة {user_data.get(user_id, {}).get('current_page', 0)+1}")
            
            elif data.startswith("country_"):
                country = data.replace("country_", "")
                
                # استرجاع بيانات المستخدم
                user_info = user_data.get(user_id, {})
                service = user_info.get('service', 'tg')
                service_name = user_info.get('service_name', 'تلغرام')
                
                # التحقق من وجود رقم صفحة
                page = 1
                if '_page_' in country:
                    parts = country.split('_page_')
                    country = parts[0]
                    page = int(parts[1])
                
                # جلب بيانات السيرفرات من API
                bot.edit_message_text(
                    "🔄 **جاري تحميل خيارات السيرفرات...**",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
                
                operators_data = {}
                if api_client:
                    try:
                        # جلب بيانات السيرفرات للدولة والخدمة المحددة
                        prices_data = api_client.get_services_with_operators(service, int(country))
                        if prices_data and country in prices_data:
                            country_data = prices_data[country]
                            if service in country_data:
                                operators_data = country_data[service]
                                logger.info(f"✅ تم جلب {len(operators_data)} سيرفر للدولة {country}")
                    except Exception as e:
                        logger.error(f"❌ خطأ في جلب السيرفرات: {e}")
                
                # تجهيز قائمة السيرفرات
                operators_list = []
                if operators_data and isinstance(operators_data, dict):
                    # تحويل القاموس إلى قائمة للترتيب
                    for operator, data in operators_data.items():
                        if isinstance(data, dict) and 'cost' in data:
                            operators_list.append((operator, data))
                    
                    # ترتيب السيرفرات حسب السعر (الأقل أولاً)
                    operators_list.sort(key=lambda x: x[1].get('cost', 0))
                    
                    logger.info(f"📊 تم تحويل {len(operators_list)} سيرفر إلى قائمة مرتبة")
                else:
                    # سيرفرات افتراضية (احتياطي)
                    logger.warning("⚠️ استخدام السيرفرات الافتراضية")
                    default_operators = [
                        ('any', {'cost': 0.5, 'count': 100}),
                        ('mts', {'cost': 0.6, 'count': 50}),
                        ('beeline', {'cost': 0.55, 'count': 75}),
                        ('megafon', {'cost': 0.58, 'count': 60}),
                        ('tele2', {'cost': 0.52, 'count': 80}),
                        ('vodafone', {'cost': 0.65, 'count': 40}),
                        ('kyivstar', {'cost': 0.62, 'count': 45}),
                        ('lifecell', {'cost': 0.59, 'count': 55}),
                        ('orange', {'cost': 0.70, 'count': 30}),
                        ('t-mobile', {'cost': 0.75, 'count': 25}),
                        ('verizon', {'cost': 0.80, 'count': 20}),
                        ('att', {'cost': 0.78, 'count': 22}),
                    ]
                    operators_list = default_operators
                
                # إعداد الترقيم
                items_per_page = 8  # عدد السيرفرات في كل صفحة
                total_pages = (len(operators_list) + items_per_page - 1) // items_per_page
                
                # التأكد أن رقم الصفحة ضمن النطاق الصحيح
                if page < 1:
                    page = 1
                elif page > total_pages:
                    page = total_pages
                
                start_idx = (page - 1) * items_per_page
                end_idx = min(start_idx + items_per_page, len(operators_list))
                
                # عرض السيرفرات للصفحة الحالية
                keyboard = types.InlineKeyboardMarkup(row_width=1)
                
                # رسالة إذا لم توجد سيرفرات
                if len(operators_list) == 0:
                    keyboard.add(types.InlineKeyboardButton(
                        "❌ لا توجد سيرفرات متاحة", 
                        callback_data="noop"
                    ))
                else:
                    # إضافة أزرار السيرفرات للصفحة الحالية
                    for i in range(start_idx, end_idx):
                        operator, data = operators_list[i]
                        price = data.get('cost', 0.5)
                        count = data.get('count', 0)
                        
                        # الحصول على اسم السيرفر
                        if operator in OPERATOR_NAMES:
                            operator_name = OPERATOR_NAMES[operator]
                        else:
                            # إذا كان اسم السيرفر غير معروف، استخدم صيغة مناسبة
                            operator_name = f"📡 {operator}"
                        
                        # إضافة عدد الأرقام المتاحة
                        if count > 0:
                            button_text = f"{operator_name} - ${price:.2f} (📊 {count})"
                        else:
                            button_text = f"{operator_name} - ${price:.2f}"
                        
                        keyboard.add(types.InlineKeyboardButton(
                            button_text,
                            callback_data=f"operator_{country}_{operator}"
                        ))
                
                # إضافة أزرار التنقل بين الصفحات
                nav_buttons = []
                
                if page > 1:
                    nav_buttons.append(types.InlineKeyboardButton(
                        "◀️ السابق", 
                        callback_data=f"country_{country}_page_{page-1}"
                    ))
                
                # عرض معلومات الصفحة (كزر غير قابل للنقر)
                if total_pages > 1:
                    nav_buttons.append(types.InlineKeyboardButton(
                        f"📄 {page}/{total_pages}", 
                        callback_data="noop"
                    ))
                
                if page < total_pages:
                    nav_buttons.append(types.InlineKeyboardButton(
                        "التالي ▶️", 
                        callback_data=f"country_{country}_page_{page+1}"
                    ))
                
                if nav_buttons:
                    keyboard.row(*nav_buttons)
                
                # إضافة زر الرجوع للدول
                keyboard.add(types.InlineKeyboardButton(
                    "🔙 رجوع للدول", 
                    callback_data=f"service_{service}"
                ))
                
                # ترجمة اسم الدولة
                country_name = country_names.get(country, f'دولة {country}')
                country_flag = country_flags.get(country, '🏳️')
                
                # حفظ معلومات الدولة في بيانات المستخدم
                if user_id not in user_data:
                    user_data[user_id] = {}
                user_data[user_id]['country'] = country
                user_data[user_id]['country_name'] = country_name
                user_data[user_id]['country_flag'] = country_flag
                
                # بناء رسالة الحالة
                message_lines = [
                    f"📱 **الخدمة:** {service_name}",
                    f"🌍 **الدولة:** {country_flag} {country_name}",
                    f"📊 **إجمالي السيرفرات:** {len(operators_list)}"
                ]
                
                if total_pages > 1:
                    message_lines.append(f"📄 **الصفحة:** {page} من {total_pages}")
                
                message_lines.append("")  # سطر فارغ
                message_lines.append("🔽 **اختر السيرفر المناسب:**")
                
                bot.edit_message_text(
                    "\n".join(message_lines),
                    call.message.chat.id,
                    call.message.message_id,
                    reply_markup=keyboard,
                    parse_mode='Markdown'
                )
            
            elif data.startswith("operator_"):
                parts = data.split('_')
                if len(parts) >= 3:
                    country = parts[1]
                    operator = parts[2]
                    
                    # استرجاع بيانات المستخدم
                    user_info = user_data.get(user_id, {})
                    service = user_info.get('service', 'tg')
                    service_name = user_info.get('service_name', 'تلغرام')
                    country_name = user_info.get('country_name', country_names.get(country, 'غير معروفة'))
                    country_flag = user_info.get('country_flag', country_flags.get(country, '🏳️'))
                    
                    # جلب السعر الحقيقي للسيرفر
                    price = 0.5  # قيمة افتراضية
                    if api_client:
                        try:
                            prices_data = api_client.get_services_with_operators(service, int(country))
                            if prices_data and country in prices_data:
                                country_data = prices_data[country]
                                if service in country_data and operator in country_data[service]:
                                    price = country_data[service][operator].get('cost', 0.5)
                        except:
                            pass
                    
                    # حفظ بيانات السيرفر
                    if user_id not in user_data:
                        user_data[user_id] = {}
                    user_data[user_id]['operator'] = operator
                    user_data[user_id]['operator_name'] = OPERATOR_NAMES.get(operator, f'سيرفر {operator}')
                    user_data[user_id]['price'] = price
                    
                    # عرض تأكيد الشراء مع السيرفر
                    operator_name = OPERATOR_NAMES.get(operator, f'سيرفر {operator}')
                    
                    keyboard = types.InlineKeyboardMarkup(row_width=2)
                    keyboard.add(
                        types.InlineKeyboardButton("✅ تأكيد الشراء", callback_data="confirm_purchase"),
                        types.InlineKeyboardButton("❌ إلغاء", callback_data="cancel")
                    )
                    
                    # إضافة زر العودة للسيرفرات مع الحفاظ على الصفحة الحالية
                    # نحتاج لاستخراج رقم الصفحة الحالية من بيانات المستخدم أو استخدام قيمة افتراضية
                    current_page = user_info.get('current_operators_page', 1)
                    keyboard.add(types.InlineKeyboardButton(
                        "🔙 اختيار سيرفر آخر", 
                        callback_data=f"country_{country}_page_{current_page}"
                    ))
                    
                    bot.edit_message_text(
                        f"📱 **تأكيد الطلب**\n\n"
                        f"الخدمة: {service_name}\n"
                        f"الدولة: {country_flag} {country_name}\n"
                        f"السيرفر: {operator_name}\n"
                        f"السعر: **${price:.2f}**\n\n"
                        f"⚠️ هل تريد تأكيد الشراء؟",
                        call.message.chat.id,
                        call.message.message_id,
                        reply_markup=keyboard,
                        parse_mode='Markdown'
                    )
            
            elif data == "confirm_purchase":
                user_info = user_data.get(user_id, {})
                service = user_info.get('service', 'tg')
                service_name = user_info.get('service_name', 'تلغرام')
                country = user_info.get('country', '1')
                operator = user_info.get('operator', 'any')
                country_name = user_info.get('country_name', country_names.get(country, 'روسيا'))
                country_flag = user_info.get('country_flag', country_flags.get(country, '🇷🇺'))
                operator_name = user_info.get('operator_name', 'أي مشغل')
                price = user_info.get('price', 0.5)
                
                bot.edit_message_text(
                    "🔄 **جاري طلب الرقم...**\n\nالرجاء الانتظار",
                    call.message.chat.id,
                    call.message.message_id,
                    parse_mode='Markdown'
                )
                
                if api_client:
                    try:
                        country_int = int(country) if country.isdigit() else 1
                        
                        # استخدام المعاملات مع السيرفر
                        number_data = api_client.get_number_with_operator(service, country_int, operator)
                        
                        logger.info(f"📞 استجابة get_number_with_operator: {number_data}")
                        
                        if number_data and number_data.get('success', False):
                            phone = number_data.get('phoneNumber')
                            activation_id = number_data.get('activationId')
                            
                            # أزرار التحكم
                            control_keyboard = types.InlineKeyboardMarkup(row_width=2)
                            control_keyboard.add(
                                types.InlineKeyboardButton("🔄 إعادة إرسال الرمز", callback_data=f"resend_{activation_id}"),
                                types.InlineKeyboardButton("❌ إلغاء الرقم", callback_data=f"cancel_{activation_id}")
                            )
                            control_keyboard.add(
                                types.InlineKeyboardButton("📋 حالة الرقم", callback_data=f"status_{activation_id}"),
                                types.InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="back")
                            )
                            
                            bot.edit_message_text(
                                f"✅ **تم شراء الرقم بنجاح!**\n\n"
                                f"📱 **الرقم:** `{phone}`\n"
                                f"🆔 **معرف التفعيل:** `{activation_id}`\n"
                                f"💰 **السعر:** ${price:.2f}\n"
                                f"🌍 **الدولة:** {country_flag} {country_name}\n"
                                f"📡 **السيرفر:** {operator_name}\n"
                                f"📱 **الخدمة:** {service_name}\n\n"
                                f"⏱️ الرقم صالح لمدة 20 دقيقة",
                                call.message.chat.id,
                                call.message.message_id,
                                reply_markup=control_keyboard,
                                parse_mode='Markdown'
                            )
                        else:
                            error_msg = "فشل الاتصال بـ API"
                            if number_data and number_data.get('message'):
                                error_msg = number_data.get('message')
                            
                            bot.edit_message_text(
                                f"❌ **فشل شراء الرقم**\n\n"
                                f"السبب: {error_msg}\n\n"
                                f"💰 السعر: ${price:.2f}\n"
                                f"🌍 الدولة: {country_flag} {country_name}\n"
                                f"📡 السيرفر: {operator_name}\n"
                                f"📱 الخدمة: {service_name}\n\n"
                                f"⚠️ يرجى المحاولة لاحقاً",
                                call.message.chat.id,
                                call.message.message_id,
                                parse_mode='Markdown'
                            )
                    except Exception as e:
                        logger.error(f"خطأ في طلب الرقم: {e}")
                        bot.edit_message_text(
                            f"❌ **فشل شراء الرقم**\n\n"
                            f"السبب: خطأ تقني\n\n"
                            f"💰 السعر: ${price:.2f}\n"
                            f"🌍 الدولة: {country_flag} {country_name}\n"
                            f"📡 السيرفر: {operator_name}\n"
                            f"📱 الخدمة: {service_name}",
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
                        f"📡 **السيرفر:** {operator_name}\n"
                        f"📱 **الخدمة:** {service_name}\n\n"
                        f"⚠️ هذا رقم تجريبي (API غير مهيأ)",
                        call.message.chat.id,
                        call.message.message_id,
                        parse_mode='Markdown'
                    )
                
                # مسح بيانات المستخدم بعد الشراء
                if user_id in user_data:
                    del user_data[user_id]
            
            elif data.startswith("resend_"):
                activation_id = data.replace("resend_", "")
                # طلب إعادة إرسال الرمز
                if api_client:
                    try:
                        result = api_client.set_status(int(activation_id), 3)  # 3 = طلب إعادة SMS
                        if result:
                            bot.answer_callback_query(call.id, "✅ تم طلب إعادة إرسال الرمز")
                        else:
                            bot.answer_callback_query(call.id, "❌ فشل طلب إعادة الإرسال")
                    except Exception as e:
                        logger.error(f"خطأ في إعادة الإرسال: {e}")
                        bot.answer_callback_query(call.id, "❌ حدث خطأ")
                else:
                    bot.answer_callback_query(call.id, "❌ API غير متاح")
            
            elif data.startswith("cancel_"):
                activation_id = data.replace("cancel_", "")
                # إلغاء الرقم واسترداد الرصيد
                if api_client:
                    try:
                        result = api_client.set_status(int(activation_id), 8)  # 8 = إلغاء واسترداد
                        if result:
                            bot.edit_message_text(
                                f"✅ **تم إلغاء الرقم بنجاح!**\n\n"
                                f"🆔 معرف التفعيل: {activation_id}\n"
                                f"💰 تم استرداد الرصيد إلى حسابك",
                                call.message.chat.id,
                                call.message.message_id,
                                parse_mode='Markdown'
                            )
                        else:
                            bot.answer_callback_query(call.id, "❌ فشل إلغاء الرقم")
                    except Exception as e:
                        logger.error(f"خطأ في إلغاء الرقم: {e}")
                        bot.answer_callback_query(call.id, "❌ حدث خطأ")
                else:
                    bot.answer_callback_query(call.id, "❌ API غير متاح")
            
            elif data.startswith("status_"):
                activation_id = data.replace("status_", "")
                # الاستعلام عن حالة الرقم
                if api_client:
                    try:
                        status = api_client.get_status(int(activation_id))
                        status_messages = {
                            'STATUS_WAIT_CODE': '⏳ في انتظار الرمز',
                            'STATUS_OK': '✅ تم استلام الرمز',
                            'STATUS_CANCEL': '❌ ملغي'
                        }
                        status_text = status_messages.get(status, f'حالة غير معروفة: {status}')
                        bot.answer_callback_query(call.id, f"حالة الرقم: {status_text}")
                    except Exception as e:
                        logger.error(f"خطأ في الاستعلام عن الحالة: {e}")
                        bot.answer_callback_query(call.id, "❌ حدث خطأ")
                else:
                    bot.answer_callback_query(call.id, "❌ API غير متاح")
            
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
