import os
import logging
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
)
from sms_activate_api import sms_api, RequestError

# -----------------
# 1. الإعدادات الأساسية
# -----------------

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# متغيرات البيئة
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL') 
ADMIN_IDS_STR = os.environ.get('ADMIN_IDS', '8102857570') 
SMS_ACTIVATE_API_KEY = os.environ.get('SMS_ACTIVATE_API_KEY')
PORT = int(os.environ.get('PORT', 10000))

try:
    ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(',')]
except:
    ADMIN_IDS = [81028557570] 

if SMS_ACTIVATE_API_KEY:
    sms_api.api_key = SMS_ACTIVATE_API_KEY

# قاموس الخدمات
SERVICES = {
    'tg': 'تيليجرام 🔵',
    'wa': 'واتساب 🟢', 
    'fb': 'فيسبوك 🟦',
    'ig': 'انستجرام',
    'tw': 'تويتر',
}

# 💡 قاموس ترجمة إنجليزي-عربي شامل مع الأعلام
# (يعتمد على الأسماء الإنجليزية الرسمية في القائمة التي قدمتها)
COUNTRY_TRANSLATIONS = {
    "Ukraine": ('🇺🇦', 'أوكرانيا'),
    "Kazakhstan": ('🇰🇿', 'كازاخستان'),
    "China": ('🇨🇳', 'الصين'),
    "Philippines": ('🇵🇭', 'الفلبين'),
    "Myanmar": ('🇲🇲', 'ميانمار'),
    "Indonesia": ('🇮🇩', 'إندونيسيا'),
    "Malaysia": ('🇲🇾', 'ماليزيا'),
    "Kenya": ('🇰🇪', 'كينيا'),
    "Tanzania": ('🇹🇿', 'تنزانيا'),
    "Vietnam": ('🇻🇳', 'فيتنام'),
    "Kyrgyzstan": ('🇰🇬', 'قيرغيزستان'),
    "Israel": ('🇮🇱', 'إسرائيل'),
    "Hong Kong": ('🇭🇰', 'هونج كونج'),
    "Poland": ('🇵🇱', 'بولندا'),
    "United Kingdom": ('🇬🇧', 'المملكة المتحدة'),
    "Madagascar": ('🇲🇬', 'مدغشقر'),
    "DR Congo": ('🇨🇩', 'الكونغو الديمقراطية'),
    "Nigeria": ('🇳🇬', 'نيجيريا'),
    "Macao": ('🇲🇴', 'ماكاو'),
    "Egypt": ('🇪🇬', 'مصر'),
    "India": ('🇮🇳', 'الهند'),
    "Ireland": ('🇮🇪', 'أيرلندا'),
    "Cambodia": ('🇰🇭', 'كمبوديا'),
    "Laos": ('🇱🇦', 'لاوس'),
    "Haiti": ('🇭🇹', 'هايتي'),
    "Ivory Coast": ('🇨🇮', 'ساحل العاج'),
    "Gambia": ('🇬🇲', 'غامبيا'),
    "Serbia": ('🇷🇸', 'صربيا'),
    "Yemen": ('🇾🇪', 'اليمن'),
    "South Africa": ('🇿🇦', 'جنوب أفريقيا'),
    "Romania": ('🇷🇴', 'رومانيا'),
    "Colombia": ('🇨🇴', 'كولومبيا'),
    "Estonia": ('🇪🇪', 'إستونيا'),
    "Azerbaijan": ('🇦🇿', 'أذربيجان'),
    "Canada": ('🇨🇦', 'كندا'),
    "Morocco": ('🇲🇦', 'المغرب'),
    "Ghana": ('🇬🇭', 'غانا'),
    "Argentina": ('🇦🇷', 'الأرجنتين'),
    "Uzbekistan": ('🇺🇿', 'أوزبكستان'),
    "Cameroon": ('🇨🇲', 'الكاميرون'),
    "Chad": ('🇹🇩', 'تشاد'),
    "Germany": ('🇩🇪', 'ألمانيا'),
    "Lithuania": ('🇱🇹', 'ليتوانيا'),
    "Croatia": ('🇭🇷', 'كرواتيا'),
    "Sweden": ('🇸🇪', 'السويد'),
    "Iraq": ('🇮🇶', 'العراق'),
    "Netherlands": ('🇳🇱', 'هولندا'),
    "Latvia": ('🇱🇻', 'لاتفيا'),
    "Austria": ('🇦🇹', 'النمسا'),
    "Belarus": ('🇧🇾', 'بيلاروسيا'),
    "Thailand": ('🇹🇭', 'تايلاند'),
    "Saudi Arabia": ('🇸🇦', 'المملكة العربية السعودية'),
    "Mexico": ('🇲🇽', 'المكسيك'),
    "Taiwan": ('🇹🇼', 'تايوان'),
    "Spain": ('🇪🇸', 'إسبانيا'),
    "Iran": ('🇮🇷', 'إيران'),
    "Algeria": ('🇩🇿', 'الجزائر'),
    "Slovenia": ('🇸🇮', 'سلوفينيا'),
    "Bangladesh": ('🇧🇩', 'بنجلاديش'),
    "Senegal": ('🇸🇳', 'السنغال'),
    "Turkey": ('🇹🇷', 'تركيا'),
    "Czech": ('🇨🇿', 'التشيك'),
    "Sri Lanka": ('🇱🇰', 'سريلانكا'),
    "Peru": ('🇵🇪', 'بيرو'),
    "Pakistan": ('🇵🇰', 'باكستان'),
    "New Zealand": ('🇳🇿', 'نيوزيلندا'),
    "Guinea": ('🇬🇳', 'غينيا'),
    "Mali": ('🇲🇱', 'مالي'),
    "Venezuela": ('🇻🇪', 'فنزويلا'),
    "Ethiopia": ('🇪🇹', 'إثيوبيا'),
    "Mongolia": ('🇲🇳', 'منغوليا'),
    "Brazil": ('🇧🇷', 'البرازيل'),
    "Afghanistan": ('🇦🇫', 'أفغانستان'),
    "Uganda": ('🇺🇬', 'أوغندا'),
    "Angola": ('🇦🇴', 'أنجولا'),
    "Cyprus": ('🇨🇾', 'قبرص'),
    "France": ('🇫🇷', 'فرنسا'),
    "Papua": ('🇵🇬', 'بابوا غينيا الجديدة'),
    "Mozambique": ('🇲🇿', 'موزمبيق'),
    "Nepal": ('🇳🇵', 'نيبال'),
    "Belgium": ('🇧🇪', 'بلجيكا'),
    "Bulgaria": ('🇧🇬', 'بلغاريا'),
    "Hungary": ('🇭🇺', 'المجر'),
    "Moldova": ('🇲🇩', 'مولدوفا'),
    "Italy": ('🇮🇹', 'إيطاليا'),
    "Paraguay": ('🇵🇾', 'باراجواي'),
    "Honduras": ('🇭🇳', 'هندوراس'),
    "Tunisia": ('🇹🇳', 'تونس'),
    "Nicaragua": ('🇳🇮', 'نيكاراغوا'),
    "Timor-Leste": ('🇹🇱', 'تيمور الشرقية'),
    "Bolivia": ('🇧🇴', 'بوليفيا'),
    "Costa Rica": ('🇨🇷', 'كوستاريكا'),
    "Guatemala": ('🇬🇹', 'غواتيمالا'),
    "UAE": ('🇦🇪', 'الإمارات العربية المتحدة'),
    "Zimbabwe": ('🇿🇼', 'زيمبابوي'),
    "Puerto Rico": ('🇵🇷', 'بورتوريكو'),
    "Sudan": ('🇸🇩', 'السودان'),
    "Togo": ('🇹🇬', 'توجو'),
    "Kuwait": ('🇰🇼', 'الكويت'),
    "Salvador": ('🇸🇻', 'السلفادور'),
    "Libya": ('🇱🇾', 'ليبيا'),
    "Jamaica": ('🇯🇲', 'جامايكا'),
    "Trinidad and Tobago": ('🇹🇹', 'ترينيداد وتوباغو'),
    "Ecuador": ('🇪🇨', 'الإكوادور'),
    "Swaziland": ('🇸🇿', 'إي سواتيني (سوازيلاند)'),
    "Oman": ('🇴🇲', 'عمان'),
    "Bosnia": ('🇧🇦', 'البوسنة والهرسك'),
    "Dominican Republic": ('🇩🇴', 'جمهورية الدومينيكان'),
    "Syria": ('🇸🇾', 'سوريا'),
    "Qatar": ('🇶🇦', 'قطر'),
    "Panama": ('🇵🇦', 'بنما'),
    "Cuba": ('🇨🇺', 'كوبا'),
    "Mauritania": ('🇲🇷', 'موريتانيا'),
    "Sierra Leone": ('🇸🇱', 'سيراليون'),
    "Jordan": ('🇯🇴', 'الأردن'),
    "Portugal": ('🇵🇹', 'البرتغال'),
    "Barbados": ('🇧🇧', 'بربادوس'),
    "Burundi": ('🇧🇮', 'بوروندي'),
    "Benin": ('🇧🇯', 'بنين'),
    "Brunei": ('🇧🇳', 'بروناي'),
    "Bahamas": ('🇧🇸', 'جزر البهاما'),
    "Botswana": ('🇧🇼', 'بوتسوانا'),
    "Belize": ('🇧🇿', 'بليز'),
    "Central African Republic": ('🇨🇫', 'جمهورية أفريقيا الوسطى'),
    "Dominica": ('🇩🇲', 'دومينيكا'),
    "Grenada": ('🇬🇩', 'غرينادا'),
    "Georgia": ('🇬🇪', 'جورجيا'),
    "Greece": ('🇬🇷', 'اليونان'),
    "Guinea-Bissau": ('🇬🇼', 'غينيا بيساو'),
    "Guyana": ('🇬🇾', 'غيانا'),
    "Iceland": ('🇮🇸', 'آيسلندا'),
    "Comoros": ('🇰🇲', 'جزر القمر'),
    "Saint Kitts and Nevis": ('🇰🇳', 'سانت كيتس ونيفيس'),
    "Liberia": ('🇱🇷', 'ليبيريا'),
    "Lesotho": ('🇱🇸', 'ليسوتو'),
    "Malawi": ('🇲🇼', 'مالاوي'),
    "Namibia": ('🇳🇦', 'ناميبيا'),
    "Niger": ('🇳🇪', 'النيجر'),
    "Rwanda": ('🇷🇼', 'رواندا'),
    "Slovakia": ('🇸🇰', 'سلوفاكيا'),
    "Suriname": ('🇸🇷', 'سورينام'),
    "Tajikistan": ('🇹🇯', 'طاجيكستان'),
    "Monaco": ('🇲🇨', 'موناكو'),
    "Bahrain": ('🇧🇭', 'البحرين'),
    "Reunion": ('🇷🇪', 'ريونيون'),
    "Zambia": ('🇿🇲', 'زامبيا'),
    "Armenia": ('🇦🇲', 'أرمينيا'),
    "Somalia": ('🇸🇴', 'الصومال'),
    "Congo": ('🇨🇬', 'الكونغو (برازافيل)'),
    "Chile": ('🇨🇱', 'تشيلي'),
    "Burkina Faso": ('🇧🇫', 'بوركينا فاسو'),
    "Lebanon": ('🇱🇧', 'لبنان'),
    "Gabon": ('🇬🇦', 'الجابون'),
    "Albania": ('🇦🇱', 'ألبانيا'),
    "Uruguay": ('🇺🇾', 'أوروغواي'),
    "Mauritius": ('🇲🇺', 'موريشيوس'),
    "Bhutan": ('🇧🇹', 'بوتان'),
    "Maldives": ('🇲🇻', 'جزر المالديف'),
    "Guadeloupe": ('🇬🇵', 'جوادلوب'),
    "Turkmenistan": ('🇹🇲', 'تركمانستان'),
    "French Guiana": ('🇬🇫', 'غويانا الفرنسية'),
    "Finland": ('🇫🇮', 'فنلندا'),
    "Saint Lucia": ('🇱🇨', 'سانت لوسيا'),
    "Luxembourg": ('🇱🇺', 'لوكسمبورغ'),
    "Saint Vincent and the Grenadines": ('🇻🇨', 'سانت فنسنت والغرينادين'),
    "Equatorial Guinea": ('🇬🇶', 'غينيا الاستوائية'),
    "Djibouti": ('🇩🇯', 'جيبوتي'),
    "Antigua and Barbuda": ('🇦🇬', 'أنتيغوا وباربودا'),
    "Cayman Islands": ('🇰🇾', 'جزر كايمان'),
    "Montenegro": ('🇲🇪', 'الجبل الأسود'),
    "Denmark": ('🇩🇰', 'الدنمارك'),
    "Switzerland": ('🇨🇭', 'سويسرا'),
    "Norway": ('🇳🇴', 'النرويج'),
    "Australia": ('🇦🇺', 'أستراليا'),
    "Eritrea": ('🇪🇷', 'إريتريا'),
    "South Sudan": ('🇸🇸', 'جنوب السودان'),
    "Sao Tome and Principe": ('🇸🇹', 'ساو تومي وبرينسيب'),
    "Aruba": ('🇦🇼', 'أروبا'),
    "Montserrat": ('🇲🇸', 'مونتسيرات'),
    "Anguilla": ('🇦🇮', 'أنغويلا'),
    "Japan": ('🇯🇵', 'اليابان'),
    "North Macedonia": ('🇲🇰', 'مقدونيا الشمالية'),
    "Seychelles": ('🇸🇨', 'سيشل'),
    "New Caledonia": ('🇳🇨', 'كاليدونيا الجديدة'),
    "Cape Verde": ('🇨🇻', 'الرأس الأخضر'),
    "USA": ('🇺🇸', 'الولايات المتحدة الأمريكية'),
    "Palestine": ('🇵🇸', 'فلسطين'),
    "Fiji": ('🇫🇯', 'فيجي'),
    "Singapore": ('🇸🇬', 'سنغافورة'),
    "Malta": ('🇲🇹', 'مالطا'),
    "Gibraltar": ('🇬🇮', 'جبل طارق'),
    "Kosovo": ('🇽🇰', 'كوسوفو'),
    "Niue": ('🇳🇺', 'نيوي')
}


# قواعد بيانات بسيطة (مؤقتة)
users_db = {}
orders_db = {} 

def is_admin(user_id):
    return user_id in ADMIN_IDS

# -----------------
# 2. دوال المُسْتَخْدِم
# -----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    
    if user_id not in users_db:
        users_db[user_id] = {'balance': 0.0, 'orders': []}

    keyboard = [
        [InlineKeyboardButton('☎️︙شراء ارقـام وهمية', callback_data='Buynum')],
        [InlineKeyboardButton('💰︙رصيدي الحالي', callback_data='my_balance'), InlineKeyboardButton('🅿️︙سجل طلباتي', callback_data='Record')],
        [InlineKeyboardButton('👤︙قسم الرشق', callback_data='sh'), InlineKeyboardButton('🛍︙قسم العروض', callback_data='Wo')],
        [InlineKeyboardButton('☑️︙قسم العشوائي', callback_data='worldwide'), InlineKeyboardButton('👑︙قسم الملكي', callback_data='saavmotamy')],
        [InlineKeyboardButton('💰︙ربح روبل مجاني 🤑', callback_data='assignment')],
        [InlineKeyboardButton('💳︙متجر الكروت', callback_data='readycard-10'), InlineKeyboardButton('🔰︙الارقام الجاهزة', callback_data='ready')]
    ]
    
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton('⚙️ لوحة المشرفين', callback_data='admin_panel')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if update.callback_query:
         await update.callback_query.edit_message_text(
            f"مرحباً بك يا {user.mention_html()}! تفضل لوحة التحكم الرئيسية للبوت:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:
        await update.message.reply_html(
            f"مرحباً بك يا {user.mention_html()}! تفضل لوحة التحكم الرئيسية للبوت:",
            reply_markup=reply_markup,
        )


async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    user_balance = users_db.get(user_id, {}).get('balance', 0.0)
    api_balance_text = ""
    
    if is_admin(user_id):
        try:
            balance_info = sms_api.get_balance_and_cashback() 
            api_balance_text = f"• رصيد SMS-Activate: ${balance_info['balance']:.2f}\n"
        except RequestError as e:
            api_balance_text = f"• خطأ في جلب رصيد API: {e.get_api_error_message()}\n"
        except Exception:
            api_balance_text = "• خطأ غير متوقع في الاتصال بـ API.\n"

    message = (
        f"💳 **رصيدك الحالي:**\n"
        f"• رصيدك في البوت: ${user_balance:.2f}\n"
        f"{api_balance_text}" 
        f"\nلشحن رصيد البوت، يرجى التواصل مع المالك."
    )
    
    keyboard = [[InlineKeyboardButton('🔙 العودة', callback_data='back_to_main')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def buy_number_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    keyboard = []
    service_codes = list(SERVICES.keys())
    
    for i in range(0, len(service_codes), 2):
        row = []
        for j in range(2):
            if i + j < len(service_codes):
                service_code = service_codes[i + j]
                service_name = SERVICES[service_code]
                row.append(InlineKeyboardButton(service_name, callback_data=f'service_{service_code}_0'))
        if row:
            keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton('عودة', callback_data='back_to_main')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        text="🛍️ **اختر الخدمة:**\n\nاختر الخدمة التي تريد شراء رقم لها:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def get_countries_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("جاري تحميل قائمة الدول...", show_alert=False)
    
    data = query.data.split('_')
    service_code = data[1]
    current_page = int(data[2]) if len(data) > 2 else 0
    
    context.user_data['selected_service'] = service_code
    service_name = SERVICES.get(service_code, service_code)
    
    try:
        prices_data_all_countries = sms_api.get_prices(service=service_code)
        countries_names_data = sms_api.get_countries() 
        
        available_countries = []
        
        for country_id_str, services_info in prices_data_all_countries.items():
            
            if service_code in services_info:
                price_info = services_info[service_code]
                
                try:
                    count = int(price_info.get('count', 0))
                    cost = float(price_info.get('cost', 0.0))
                except (ValueError, TypeError):
                    continue 
                
                if count > 0:
                    
                    country_info = countries_names_data.get(country_id_str, {})
                    
                    # 💡 المنطق الجديد: الاعتماد على الاسم الإنجليزي (eng) لضمان الترجمة
                    country_name_eng = country_info.get('eng')
                    
                    # 1. محاولة الترجمة عبر القاموس الإنجليزي-العربي
                    translation_info = COUNTRY_TRANSLATIONS.get(country_name_eng)
                    
                    if translation_info:
                        # استخدام الاسم المترجم والعلم من القاموس
                        flag, country_name_display = translation_info
                    else:
                        # في حالة الفشل، نعود للاسم العربي أو الإنجليزي أو الروسي كبديل
                        country_name_display = country_info.get('arab') or country_name_eng or country_info.get('rus') or f"دولة-{country_id_str}"
                        flag = '❓'
                    
                    available_countries.append({
                        'id': country_id_str,
                        'name': country_name_display,
                        'price': cost,
                        'count': count,
                        'flag': flag
                    })

        sorted_countries = sorted(available_countries, key=lambda c: c['price'])
        
    except RequestError as e:
        await query.edit_message_text(f"❌ حدث خطأ في جلب الدول: {e.get_api_error_message()}")
        return
    except Exception as e:
         logger.error(f"Error in get_countries_menu: {e}")
         await query.edit_message_text(f"❌ حدث خطأ غير متوقع أثناء جلب الدول.")
         return
    
    countries_per_page = 24
    start_index = current_page * countries_per_page
    end_index = start_index + countries_per_page
    countries_to_display = sorted_countries[start_index:end_index]
    
    keyboard = []
    
    for i in range(0, len(countries_to_display), 2):
        row = []
        for j in range(2):
            if i + j < len(countries_to_display):
                country_data = countries_to_display[i + j]
                country_id_str = country_data['id']
                
                button_text = f"{country_data['flag']} {country_data['name']} | ${country_data['price']:.2f} ({country_data['count']})"
                callback_data = f"request_{service_code}_{country_id_str}"
                row.append(InlineKeyboardButton(button_text, callback_data=callback_data))
        
        if row:
            keyboard.append(row)
    
    nav_buttons = []
    if current_page > 0:
        nav_buttons.append(InlineKeyboardButton("⬅️ السابق", callback_data=f"service_{service_code}_{current_page - 1}"))
    if end_index < len(sorted_countries):
        nav_buttons.append(InlineKeyboardButton("التالي ➡️", callback_data=f"service_{service_code}_{current_page + 1}"))
    
    if nav_buttons:
        keyboard.append(nav_buttons)

    keyboard.append([InlineKeyboardButton("عودة", callback_data='Buynum')])
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(
        text=f"🌍 **اختر الدولة لخدمة: {service_name}**\n\nتم العثور على {len(sorted_countries)} دولة. اختر الدولة والسعر:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def request_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("جاري طلب رقمك...", show_alert=True)
    
    user_id = query.from_user.id
    data = query.data.split('_')
    service_code = data[1]
    country_id = int(data[2])
    
    try:
        number_info = sms_api.get_number(service_code, country_id)
        
        request_id = number_info['id']
        phone_number = number_info['number']
        
        orders_db[request_id] = {
            'user_id': user_id,
            'phone_number': phone_number,
            'service_code': service_code,
            'status': 'STATUS_WAIT_CODE', 
            'order_time': datetime.now()
        }
        
        context.user_data['active_request_id'] = request_id
        
        keyboard = [
            [InlineKeyboardButton('📩 الحصول على الكود', callback_data=f'get_code_{request_id}')],
            [InlineKeyboardButton('❌ إلغاء الطلب', callback_data=f'cancel_request_{request_id}')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(
            f"✅ **تم شراء الرقم بنجاح!**\n\n"
            f"📱 **الرقم:** `{phone_number}`\n"
            f"🛍️ **الخدمة:** {SERVICES.get(service_code)}\n"
            f"🆔 **رقم التفعيل:** `{request_id}`\n\n"
            f"استخدم الرقم في التطبيق واضغط 'الحصول على الكود'.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    except RequestError as e:
        await query.edit_message_text(f"❌ حدث خطأ في طلب الرقم: {e.get_api_error_message()}")


async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("جاري التحقق من الكود...", show_alert=False)
    
    request_id = query.data.split('_')[2]
    
    if request_id not in orders_db:
        await query.edit_message_text("❌ لم يتم العثور على هذا الطلب النشط.")
        return

    try:
        status_info = sms_api.get_status(request_id)
        status = status_info['status']
        code = status_info.get('code')
        
        if status == 'STATUS_OK' and code:
            sms_api.set_status(request_id, 6) 
            
            orders_db[request_id]['status'] = 'completed'
            orders_db[request_id]['code'] = code
            
            await query.edit_message_text(
                f"🎉 **تم استلام الكود بنجاح!**\n\n"
                f"🔢 **الكود:** `{code}`\n"
                f"🆔 **رقم التفعيل:** `{request_id}`",
                parse_mode='Markdown'
            )
        elif status in ['STATUS_WAIT_CODE', 'STATUS_WAIT_RETRY']:
            sms_api.set_status(request_id, 3) 
            
            keyboard = [
                [InlineKeyboardButton('🔄 تحديث ومحاولة', callback_data=f'get_code_{request_id}')],
                [InlineKeyboardButton('❌ إلغاء الطلب', callback_data=f'cancel_request_{request_id}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"⏳ **في انتظار الكود...**\n\nلم يصل الكود بعد. الحالة: `{status}`\nاضغط تحديث للمحاولة مرة أخرى. يمكنك استخدام الرقم الآن.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(f"⚠️ حالة الطلب غير متوقعة: `{status}`")
            
    except RequestError as e:
        await query.edit_message_text(f"❌ حدث خطأ في جلب الكود: {e.get_api_error_message()}")

async def cancel_request(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("جاري إلغاء الطلب...", show_alert=True)
    
    request_id = query.data.split('_')[2]
    
    if request_id not in orders_db:
        await query.edit_message_text("❌ لا يوجد طلب نشط بهذا المعرف لإلغائه.")
        return

    try:
        sms_api.set_status(request_id, 8) 
        
        orders_db[request_id]['status'] = 'cancelled'
        
        await query.edit_message_text(
            f"✅ **تم إلغاء الطلب بنجاح**\n\n🆔 رقم التفعيل: `{request_id}`\nتم إلغاء الطلب واسترجاع الرصيد (افتراضياً).",
            parse_mode='Markdown'
        )
    except RequestError as e:
        await query.edit_message_text(f"❌ حدث خطأ في الإلغاء: {e.get_api_error_message()}")


async def show_account_record(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user_orders = [order for order in orders_db.values() if order['user_id'] == user_id]
    
    if user_orders:
        message = "**سجل طلباتك الأخيرة:**\n\n"
        for i, order in enumerate(user_orders[-5:]): 
            message += (
                f"**{i+1}.** **الرقم:** `{order['phone_number']}`\n"
                f"   **الخدمة:** {SERVICES.get(order.get('service_code'), 'غير معروف')}\n"
                f"   **الحالة:** {order['status']}\n"
                f"   **الكود:** {order.get('code', 'لم يصل')}\n\n"
            )
        keyboard = [[InlineKeyboardButton('🔙 العودة', callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        keyboard = [[InlineKeyboardButton('🔙 العودة', callback_data='back_to_main')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("لا توجد سجلات لعمليات شراء سابقة في حسابك.", reply_markup=reply_markup)

# -----------------
# 3. دوال التنقل والمشرفين
# -----------------

async def back_to_main(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    await start(update, context)

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    if not is_admin(query.from_user.id):
        await query.edit_message_text("❌ ليس لديك صلاحية الوصول لهذه اللوحة.")
        return

    try:
        balance_info = sms_api.get_balance_and_cashback()
        api_balance = f"${balance_info['balance']:.2f}"
    except RequestError as e:
        api_balance = f"خطأ: {e.get_api_error_message()}"
    
    total_users = len(users_db)
    total_orders = len(orders_db)
    active_orders = sum(1 for order in orders_db.values() if order['status'] in ['STATUS_WAIT_CODE', 'STATUS_WAIT_RETRY'])

    message = (
        f"👑 **لوحة المشرفين**\n\n"
        f"💳 **رصيد SMS-Activate:** {api_balance}\n\n"
        f"📊 **إحصائيات البوت:**\n"
        f"• إجمالي المستخدمين: {total_users}\n"
        f"• إجمالي الطلبات: {total_orders}\n"
        f"• الطلبات النشطة: {active_orders}\n"
    )

    keyboard = [
        [InlineKeyboardButton('💰 شحن رصيد لمستخدم', callback_data='admin_charge')],
        [InlineKeyboardButton('📃 عرض سجل الطلبات', callback_data='admin_orders_log')],
        [InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='back_to_main')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

async def handle_static_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer("هذه الميزة قيد التطوير.")
    
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_user.id in ADMIN_IDS and update.message.text.lower().startswith('شحن'):
        pass 
    else:
        await update.message.reply_text(
            "يرجى استخدام الأزرار في القائمة للتفاعل مع البوت.\nاكتب /start لعرض القائمة الرئيسية."
        )

# -----------------
# 4. الدالة الرئيسية (Main)
# -----------------

def main() -> None:
    if not TELEGRAM_BOT_TOKEN or not WEBHOOK_URL:
        logger.error("TELEGRAM_BOT_TOKEN أو WEBHOOK_URL غير مُعينين بشكل صحيح.")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # === Handlers ===
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # المستخدم
    application.add_handler(CallbackQueryHandler(show_balance, pattern='^my_balance$'))
    application.add_handler(CallbackQueryHandler(show_account_record, pattern='^Record$'))
    application.add_handler(CallbackQueryHandler(buy_number_menu, pattern='^Buynum$'))
    application.add_handler(CallbackQueryHandler(get_countries_menu, pattern=r'^service_[a-z]{2}(_\d+)?$')) 
    application.add_handler(CallbackQueryHandler(request_number, pattern=r'^request_[a-z]{2}_\d+$'))
    application.add_handler(CallbackQueryHandler(get_code, pattern=r'^get_code_\d+$'))
    application.add_handler(CallbackQueryHandler(cancel_request, pattern=r'^cancel_request_\d+$'))
    
    # المشرفين والتنقل
    application.add_handler(CallbackQueryHandler(back_to_main, pattern='^back_to_main$'))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(handle_static_buttons, pattern='^sh$|^Wo$|^worldwide$|^saavmotamy$|^assignment$|^readycard-10$|^ready$|^admin_charge$|^admin_orders_log$'))
    
    # 💡 تشغيل الـ Webhook
    webhook_path = f"/{TELEGRAM_BOT_TOKEN}" 
    
    application.run_webhook(
        listen="0.0.0.0", 
        port=PORT,
        url_path=TELEGRAM_BOT_TOKEN, 
        webhook_url=f"{WEBHOOK_URL}{webhook_path}"
    )


if __name__ == "__main__":
    main()
