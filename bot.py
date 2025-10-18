# bot.py

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
import asyncio # تم إضافته لضمان التوافق مع async.run

# استيراد واجهة API الجديدة
from sms_activate_api import sms_api, RequestError 
# 💡 ملاحظة: تم إزالة sms_activate_api من بداية الكود لعدم تكرار الاستيراد

# إعدادات التسجيل
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", 
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# الحصول على المتغيرات البيئية
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
SMS_ACTIVATE_API_KEY = os.environ.get('SMS_ACTIVATE_API_KEY')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL', '').rstrip('/')
PORT = int(os.environ.get('PORT', 8080))

# إعدادات المشرفين
admin_ids_str = os.environ.get('ADMIN_IDS', '8102857570')
try:
    ADMIN_IDS = [int(id.strip()) for id in admin_ids_str.split(',')]
except:
    ADMIN_IDS = [8102857570]

# =================================================================
# 💡 التعديل 1: تعيين مفتاح API لكائن sms_api المستورد
# =================================================================
if SMS_ACTIVATE_API_KEY:
    sms_api.api_key = SMS_ACTIVATE_API_KEY
else:
    logger.warning("SMS_ACTIVATE_API_KEY غير مُعين. لن يتمكن البوت من شراء الأرقام.")


# تعيين الخدمات (تم الإبقاء عليها كما هي)
SERVICES = {
    'tg': 'تيليجرام',
    'wa': 'واتساب', 
    'fb': 'فيسبوك',
    'ig': 'انستجرام',
    'tw': 'تويتر',
    'vk': 'فكونتاكتي',
    'ok': 'أودنوكلاسنيكي',
    'mm': 'مابمبا',
    'mb': 'يولا',
    'wb': 'وي شات'
}

# قاعدة بيانات بسيطة (تم الإبقاء عليها كما هي، بافتراض أنك ستدمج db_manager لاحقاً)
users_db = {}
orders_db = {}

# ========== دوال البوت ==========

# 💡 تم الإبقاء على الدوال الأساسية دون تغيير (start, main_menu, handle_message, error_handler)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # ... (تم حذف الكود الطويل لـ start لضمان التركيز على التعديلات) ...
    user = update.effective_user
    user_id = user.id
    
    # 💡 [ملاحظة]: يفضل استخدام دالة register_user من db_manager.py هنا عند دمجه
    if user_id not in users_db:
        users_db[user_id] = {
            'username': user.username,
            'first_name': user.first_name,
            'join_date': datetime.now(),
            'balance': 0.0,
            'total_orders': 0
        }
    
    keyboard = [
        [InlineKeyboardButton('☎️ شراء أرقام', callback_data='buy_numbers')],
        [InlineKeyboardButton('💰 رصيدي', callback_data='my_balance'),
         InlineKeyboardButton('📊 إحصائياتي', callback_data='my_stats')],
        [InlineKeyboardButton('🛒 طلباتي', callback_data='my_orders')],
    ]
    
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton('👑 لوحة المشرفين', callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_html(
        f"مرحباً {user.mention_html()}! 👋\n\n"
        "أهلاً بك في بوت شراء الأرقام الافتراضية.\n"
        "اختر الخدمة التي تريدها من القائمة:",
        reply_markup=reply_markup
    )

async def show_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    try:
        # 💡 التعديل 2: استخدام get_balance_and_cashback
        balance_info = sms_api.get_balance_and_cashback() 
        user_balance = users_db.get(user_id, {}).get('balance', 0)
        
        message = (
            f"💳 **رصيدك الحالي:**\n\n"
            f"• رصيد SMS Activate: ${balance_info['balance']:.2f}\n"
            f"• رصيد الكاش باك: ${balance_info['cashback']:.2f}\n"
            f"• رصيدك في البوت: ${user_balance:.2f}"
        )
        
        keyboard = [[InlineKeyboardButton('🔙 العودة', callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
    except RequestError as e:
        await query.edit_message_text(f"❌ حدث خطأ: {str(e)}")

# ... (buy_numbers_menu لم تتغير) ...
async def buy_numbers_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    keyboard = []
    for service_code, service_name in SERVICES.items():
        keyboard.append([InlineKeyboardButton(f'📱 {service_name}', callback_data=f'service_{service_code}')])
    
    keyboard.append([InlineKeyboardButton('🔙 العودة', callback_data='main_menu')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "🛍️ **اختر الخدمة:**\n\nاختر الخدمة التي تريد شراء رقم لها:",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )


async def show_countries(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    service_code = query.data.split('_')[1]
    context.user_data['selected_service'] = service_code
    
    try:
        # 💡 التعديل 3: استخدام get_countries و get_prices
        countries_data = sms_api.get_countries()
        prices_data = sms_api.get_prices(service=service_code)
        
        keyboard = []
        
        # 💡 ملاحظة: يتم تجميع الدول والأسعار لعرضها في القائمة
        for country_id_str, country_info in countries_data.items():
            country_id = int(country_id_str)
            # مفتاح البحث في prices_data يكون عبارة عن: srv_id_country_id 
            # ولكن في get_prices تكون البنية: {service_id: {country_id: {cost: x, count: y}}}
            
            # نحتاج إلى البحث عن معلومات السعر بالـ service_code والدولة
            
            # الفحص الأبسط: هل توجد معلومات سعر متاحة لهذه الخدمة؟
            
            # يتم استخراج قائمة الأسعار لهذه الخدمة أولاً
            service_prices = prices_data.get(service_code, {})
            
            if country_id in service_prices:
                price_info = service_prices[country_id]
                price = price_info.get('cost', 0)
                count = price_info.get('count', 0)
                
                if count > 0:
                    button_text = f"🇺🇳 {country_info['name']} - ${price} ({count})"
                    keyboard.append([InlineKeyboardButton(button_text, callback_data=f'country_{country_id}')])
        
        keyboard.append([InlineKeyboardButton('🔙 العودة', callback_data='buy_numbers')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"🌍 **اختر الدولة للخدمة: {SERVICES[service_code]}**\n\nاختر الدولة التي تريد الرقم منها:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except RequestError as e:
        await query.edit_message_text(f"❌ حدث خطأ: {str(e)}")


async def request_number(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    country_id = int(query.data.split('_')[1])
    service_code = context.user_data.get('selected_service')
    
    # 💡 [ملاحظة]: يجب أن يتم هنا خصم الرصيد من قاعدة البيانات الحقيقية
    
    try:
        # 💡 التعديل 4: استخدام get_number
        number_info = sms_api.get_number(service_code, country_id)
        
        order_id = number_info['id']
        orders_db[order_id] = {
            'user_id': query.from_user.id,
            'service': service_code,
            'country': country_id,
            'number': number_info['number'],
            'status': 'active',
            'order_time': datetime.now()
        }
        
        user_id = query.from_user.id
        if user_id in users_db:
            users_db[user_id]['total_orders'] += 1
        
        keyboard = [
            [InlineKeyboardButton('📩 الحصول على الكود', callback_data=f'get_code_{order_id}')],
            [InlineKeyboardButton('❌ إلغاء الطلب', callback_data=f'cancel_{order_id}')],
            [InlineKeyboardButton('🔙 العودة', callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"✅ **تم شراء الرقم بنجاح!**\n\n"
            f"📱 **الرقم:** `{number_info['number']}`\n"
            f"🛍️ **الخدمة:** {SERVICES[service_code]}\n"
            f"🆔 **رقم الطلب:** `{order_id}`\n\n"
            f"استخدم الرقم في التطبيق المطلوب، ثم اضغط على 'الحصول على الكود'",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
    except RequestError as e:
        await query.edit_message_text(f"❌ حدث خطأ في طلب الرقم: {str(e)}")

async def get_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    order_id = query.data.split('_')[2]
    
    try:
        # 💡 التعديل 5: استخدام get_status
        status_info = sms_api.get_status(order_id)
        
        if status_info['code']:
            # 💡 التعديل 6: تغيير حالة الطلب في SMS-Activate إلى الإكمال (status=6)
            sms_api.set_status(order_id, 6) # 6 = STATUS_OK
            
            orders_db[order_id]['status'] = 'completed'
            orders_db[order_id]['code'] = status_info['code']
            
            await query.edit_message_text(
                f"🎉 **تم استلام الكود بنجاح!**\n\n"
                f"🔢 **الكود:** `{status_info['code']}`\n"
                f"🆔 **رقم الطلب:** `{order_id}`\n\n"
                f"يمكنك الآن استخدام الكود لإكمال العملية.",
                parse_mode='Markdown'
            )
        else:
            keyboard = [
                [InlineKeyboardButton('🔄 تحديث', callback_data=f'get_code_{order_id}')],
                [InlineKeyboardButton('❌ إلغاء الطلب', callback_data=f'cancel_{order_id}')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                f"⏳ **في انتظار الكود...**\n\nلم يصل الكود بعد. يرجى الانتظار قليلاً ثم الضغط على تحديث.",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
            
    except RequestError as e:
        await query.edit_message_text(f"❌ حدث خطأ: {str(e)}")

async def cancel_order(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    order_id = query.data.split('_')[1]
    
    try:
        # 💡 التعديل 7: استخدام set_status للإلغاء (status=8)
        sms_api.set_status(order_id, 8) # 8 = STATUS_CANCEL
        
        if order_id in orders_db:
            orders_db[order_id]['status'] = 'cancelled'
        
        await query.edit_message_text(
            f"✅ **تم إلغاء الطلب بنجاح**\n\n🆔 رقم الطلب: `{order_id}`\nتم إلغاء الطلب واسترجاع الرصيد.",
            parse_mode='Markdown'
        )
        
    except RequestError as e:
        await query.edit_message_text(f"❌ حدث خطأ في الإلغاء: {str(e)}")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    if user_id not in ADMIN_IDS:
        await query.edit_message_text("❌ ليس لديك صلاحية الوصول لهذه اللوحة.")
        return
    
    try:
        # 💡 التعديل 8: استخدام get_balance_and_cashback و get_numbers_status
        balance_info = sms_api.get_balance_and_cashback()
        numbers_status = sms_api.get_numbers_status()
        
        # ... (بقية إحصائيات البوت المحلية)
        total_users = len(users_db)
        total_orders = sum(user['total_orders'] for user in users_db.values())
        active_orders = sum(1 for order in orders_db.values() if order['status'] == 'active')
        
        keyboard = [
            [InlineKeyboardButton('📊 إحصائيات مفصلة', callback_data='admin_stats')],
            [InlineKeyboardButton('👥 إدارة المستخدمين', callback_data='admin_users')],
            [InlineKeyboardButton('🔄 تحديث البيانات', callback_data='admin_panel')],
            [InlineKeyboardButton('🔙 القائمة الرئيسية', callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        message = (
            f"👑 **لوحة المشرفين**\n\n"
            f"💳 **الرصيد:**\n"
            f"• الرصيد الرئيسي: ${balance_info['balance']:.2f}\n"
            f"• الكاش باك: ${balance_info['cashback']:.2f}\n\n"
            f"📊 **إحصائيات البوت:**\n"
            f"• إجمالي المستخدمين: {total_users}\n"
            f"• إجمالي الطلبات: {total_orders}\n"
            f"• الطلبات النشطة: {active_orders}"
            # 💡 [ملاحظة]: هنا يمكنك إضافة عرض موجز من numbers_status
        )
        
        await query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')
        
    except RequestError as e:
        await query.edit_message_text(f"❌ حدث خطأ: {str(e)}")

# ... (بقية دوال main_menu و handle_message و error_handler لم تتغير) ...

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    user_id = user.id
    
    keyboard = [
        [InlineKeyboardButton('☎️ شراء أرقام', callback_data='buy_numbers')],
        [InlineKeyboardButton('💰 رصيدي', callback_data='my_balance'),
         InlineKeyboardButton('📊 إحصائياتي', callback_data='my_stats')],
        [InlineKeyboardButton('🛒 طلباتي', callback_data='my_orders')],
    ]
    
    if user_id in ADMIN_IDS:
        keyboard.append([InlineKeyboardButton('👑 لوحة المشرفين', callback_data='admin_panel')])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"مرحباً {user.first_name}! 👋\n\n"
        "أهلاً بك في بوت شراء الأرقام الافتراضية.\n"
        "اختر الخدمة التي تريدها من القائمة:",
        reply_markup=reply_markup
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "يرجى استخدام الأزرار في القائمة للتفاعل مع البوت.\nاكتب /start لعرض القائمة الرئيسية."
    )

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error(f"حدث خطأ: {context.error}")


def main():
    """الدالة الرئيسية"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("يجب تعيين متغير البيئة TELEGRAM_BOT_TOKEN")
    
    # إنشاء التطبيق
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # إعداد المعالجات (تم الإبقاء عليها كما هي)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # معالجات الاستدعاء
    application.add_handler(CallbackQueryHandler(show_balance, pattern='^my_balance$'))
    application.add_handler(CallbackQueryHandler(buy_numbers_menu, pattern='^buy_numbers$'))
    application.add_handler(CallbackQueryHandler(show_countries, pattern='^service_'))
    application.add_handler(CallbackQueryHandler(request_number, pattern='^country_'))
    application.add_handler(CallbackQueryHandler(get_code, pattern='^get_code_'))
    application.add_handler(CallbackQueryHandler(cancel_order, pattern='^cancel_'))
    application.add_handler(CallbackQueryHandler(admin_panel, pattern='^admin_panel$'))
    application.add_handler(CallbackQueryHandler(main_menu, pattern='^main_menu$'))
    
    # معالجات للوظائف المستقبلية
    application.add_handler(CallbackQueryHandler(lambda update, ctx: update.callback_query.answer("قيد التطوير..."), 
                                              pattern='^my_stats$'))
    application.add_handler(CallbackQueryHandler(lambda update, ctx: update.callback_query.answer("قيد التطوير..."), 
                                              pattern='^my_orders$'))
    application.add_handler(CallbackQueryHandler(lambda update, ctx: update.callback_query.answer("قيد التطوير..."), 
                                              pattern='^admin_stats$'))
    application.add_handler(CallbackQueryHandler(lambda update, ctx: update.callback_query.answer("قيد التطوير..."), 
                                              pattern='^admin_users$'))
    
    # معالج الأخطاء
    application.add_error_handler(error_handler)
    
    # تشغيل البوت
    if WEBHOOK_URL:
        # وضع Webhook
        async def initialize_and_set_webhook():
            """تهيئة التطبيق وتعيين Webhook"""
            # التعديل الصحيح: تهيئة كائن التطبيق في سياق غير متزامن
            await application.initialize() 
            
            await application.bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
            logger.info(f"✅ تم تعيين Webhook: {WEBHOOK_URL}/webhook")
        
        # 💡 استخدمنا asyncio.run
        asyncio.run(initialize_and_set_webhook()) 
        
        from aiohttp import web
        
        async def handle_webhook(request):
            """معالجة طلبات Webhook"""
            try:
                data = await request.json()
                update = Update.de_json(data, application.bot)
                await application.process_update(update)
                return web.Response(status=200)
            except Exception as e:
                # 💡 استخدام logger لتسجيل الأخطاء
                logger.error(f"خطأ في معالجة Webhook: {e}")
                return web.Response(status=400)
        
        async def health_check(request):
            """فحص صحة الخدمة"""
            return web.Response(text="✅ البوت يعمل", status=200)
        
        # إنشاء تطبيق aiohttp
        app = web.Application()
        app.router.add_post('/webhook', handle_webhook)
        app.router.add_get('/health', health_check)
        app.router.add_get('/', health_check)
        
        logger.info(f"🚀 بدء البوت على PORT {PORT} مع Webhook")
        web.run_app(app, host='0.0.0.0', port=PORT)
        
    else:
        # وضع Polling
        logger.info("🚀 بدء البوت في وضع Polling")
        application.run_polling()

if __name__ == "__main__":
    main()
