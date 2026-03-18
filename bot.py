import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
    ContextTypes
)
from sms_activate_api import HeroSMSAPI
import os
from typing import Dict, Any
import json

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# حالات المحادثة
SERVICE_SELECTION, COUNTRY_SELECTION, CONFIRM_PURCHASE = range(3)

# الخدمات المتاحة (يمكن تحديثها من API)
AVAILABLE_SERVICES = {
    'tg': 'تلغرام',
    'wa': 'واتساب',
    'vb': 'Viber',
    'ok': 'Odnoklassniki',
    'go': 'Gmail',
    'ub': 'Uber',
    'av': 'Avito',
}

class NumberSellingBot:
    def __init__(self, token: str, api_key: str, admin_ids: list):
        self.token = token
        self.api = HeroSMSAPI(api_key)
        self.admin_ids = admin_ids
        self.application = Application.builder().token(token).build()
        self._setup_handlers()
        
    def _setup_handlers(self):
        """إعداد معالجات الأوامر"""
        
        # معالج الأزرار العام - ضعه في الأعلى لالتقاط جميع الأزرار
        self.application.add_handler(CallbackQueryHandler(self.button_handler))
        
        # أمر البدء
        self.application.add_handler(CommandHandler("start", self.start_command))
        
        # أمر الرصيد
        self.application.add_handler(CommandHandler("balance", self.balance_command))
        
        # أمر شراء رقم
        self.application.add_handler(CommandHandler("buy", self.buy_command))
        
        # أمر المساعدة
        self.application.add_handler(CommandHandler("help", self.help_command))
        
        # أوامر المشرفين
        self.application.add_handler(CommandHandler("admin", self.admin_command, filters=filters.User(user_id=self.admin_ids)))
        
        # محادثة شراء رقم - مع تحسين الإعدادات
        conv_handler = ConversationHandler(
            entry_points=[
                CommandHandler("buy", self.buy_command),
                CallbackQueryHandler(self.service_selection, pattern="^buy_number$")
            ],
            states={
                SERVICE_SELECTION: [CallbackQueryHandler(self.country_selection, pattern="^service_")],
                COUNTRY_SELECTION: [CallbackQueryHandler(self.confirm_purchase, pattern="^country_")],
                CONFIRM_PURCHASE: [CallbackQueryHandler(self.process_purchase, pattern="^(confirm|cancel)_")]
            },
            fallbacks=[
                CommandHandler("cancel", self.cancel),
                CallbackQueryHandler(self.fallback_handler, pattern="^back_to_main$")
            ],
            name="buy_number_conversation",
            persistent=False,
            per_user=True,
            per_chat=True,
            per_message=False  # مهم: per_message=False للسماح بمعالجة الأزرار بشكل صحيح
        )
        self.application.add_handler(conv_handler)
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /start"""
        user = update.effective_user
        welcome_message = f"""
👋 مرحباً {user.first_name}!

أهلاً بك في بوت شراء الأرقام الافتراضية.
يمكنك من خلال هذا البوت شراء أرقام مؤقتة لتفعيل حساباتك على مختلف المنصات.

🔹 **الخدمات المتاحة**:
• تلغرام - واتساب - Viber
• Gmail - Uber - Avito
• والمزيد...

🔹 **المميزات**:
• أسعار تنافسية
• أرقام من عدة دول
• استلام الرسائل فور وصولها

استخدم الأوامر التالية:
/buy - لشراء رقم جديد
/balance - لعرض رصيدك
/help - للمساعدة

📍 للبدء، اضغط على الزر أدناه:
        """
        
        keyboard = [
            [InlineKeyboardButton("📱 شراء رقم", callback_data="buy_number")],
            [InlineKeyboardButton("💰 رصيدي", callback_data="check_balance")],
            [InlineKeyboardButton("❓ مساعدة", callback_data="show_help")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    
    async def buy_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /buy"""
        # عرض الخدمات المتاحة
        keyboard = []
        for service_code, service_name in AVAILABLE_SERVICES.items():
            keyboard.append([InlineKeyboardButton(
                f"📱 {service_name}",
                callback_data=f"service_{service_code}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            "📋 اختر الخدمة التي تريد رقمًا لها:",
            reply_markup=reply_markup
        )
        
        return SERVICE_SELECTION
    
    async def balance_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /balance - عرض الرصيد"""
        try:
            balance = await self.api.get_balance()
            await update.message.reply_text(
                f"💰 رصيدك الحالي: **{balance}** دولار",
                parse_mode='Markdown'
            )
        except Exception as e:
            logger.error(f"خطأ في جلب الرصيد: {e}")
            await update.message.reply_text("❌ حدث خطأ في جلب الرصيد. الرجاء المحاولة لاحقاً.")
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أمر /help"""
        help_text = """
❓ **مساعدة البوت**

**الأوامر المتاحة:**
/start - بدء البوت وعرض القائمة الرئيسية
/buy - شراء رقم جديد
/balance - عرض رصيدك
/help - عرض هذه المساعدة

**كيفية الشراء:**
1️⃣ اختر الخدمة المطلوبة
2️⃣ اختر الدولة
3️⃣ قم بتأكيد عملية الشراء
4️⃣ استلم الرقم وانتظر وصول الرسالة

**ملاحظات مهمة:**
• يتم خصم المبلغ من رصيدك عند تأكيد الشراء
• صلاحية الرقم 20 دقيقة لاستلام الرسالة
• يمكنك إلغاء العملية في أي وقت

للمساعدة الإضافية، تواصل مع المشرفين.
        """
        await update.message.reply_text(help_text, parse_mode='Markdown')
    
    async def admin_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج أوامر المشرفين"""
        if len(context.args) == 0:
            await update.message.reply_text(
                "🔧 **أوامر المشرفين**\n\n"
                "/admin balance - عرض رصيد API\n"
                "/admin services - تحديث قائمة الخدمات\n"
                "/admin stats - عرض إحصائيات البوت",
                parse_mode='Markdown'
            )
            return
        
        command = context.args[0]
        
        if command == "balance":
            balance = await self.api.get_balance()
            await update.message.reply_text(f"💰 رصيد API: {balance} دولار")
        
        elif command == "services":
            services = await self.api.get_services()
            if services:
                services_text = "📋 **الخدمات المتاحة:**\n\n"
                for service in services[:20]:  # عرض أول 20 خدمة فقط
                    services_text += f"• {service.get('name', 'N/A')} (رمز: {service.get('code', 'N/A')})\n"
                await update.message.reply_text(services_text, parse_mode='Markdown')
            else:
                await update.message.reply_text("❌ لا توجد خدمات متاحة")
    
    async def button_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج الضغط على الأزرار العامة (خارج المحادثة)"""
        query = update.callback_query
        await query.answer()  # مهم جداً: استخدم await
        
        logger.info(f"تم الضغط على زر: {query.data} من المستخدم {update.effective_user.id}")
        
        if query.data == "check_balance":
            try:
                balance = await self.api.get_balance()
                await query.edit_message_text(
                    f"💰 رصيدك الحالي: **{balance}** دولار",
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"خطأ في جلب الرصيد: {e}")
                await query.edit_message_text("❌ حدث خطأ في جلب الرصيد")
        
        elif query.data == "show_help":
            # إنشاء رسالة مساعدة مبسطة
            help_text = """
❓ **مساعدة سريعة**

• /buy - لشراء رقم جديد
• /balance - لعرض الرصيد
• /start - القائمة الرئيسية

للمساعدة التفصيلية، أرسل /help
            """
            await query.edit_message_text(help_text, parse_mode='Markdown')
        
        elif query.data == "back_to_main":
            # العودة للقائمة الرئيسية
            keyboard = [
                [InlineKeyboardButton("📱 شراء رقم", callback_data="buy_number")],
                [InlineKeyboardButton("💰 رصيدي", callback_data="check_balance")],
                [InlineKeyboardButton("❓ مساعدة", callback_data="show_help")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "👫 **القائمة الرئيسية**\n\nاختر ما تريد:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        
        elif query.data == "buy_number":
            # بدء محادثة الشراء
            await self.service_selection(update, context)
        
        else:
            await query.edit_message_text("❓ زر غير معروف. الرجاء استخدام الأزرار المتاحة.")
    
    async def service_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """اختيار الخدمة"""
        query = update.callback_query
        await query.answer()  # مهم جداً!
        
        service_code = query.data.replace("service_", "")
        context.user_data['selected_service'] = service_code
        context.user_data['service_name'] = AVAILABLE_SERVICES.get(service_code, service_code)
        
        # عرض الدول المتاحة (مبسطة)
        countries = {
            '6': 'روسيا',
            '2': 'كازاخستان',
            '1': 'أوكرانيا',
            '0': 'جميع الدول'
        }
        
        keyboard = []
        for country_code, country_name in countries.items():
            # إضافة الأعلام التوضيحية
            flag = "🇷🇺" if country_code == '6' else "🇰🇿" if country_code == '2' else "🇺🇦" if country_code == '1' else "🌍"
            keyboard.append([InlineKeyboardButton(
                f"{flag} {country_name}",
                callback_data=f"country_{country_code}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📱 الخدمة المختارة: **{context.user_data['service_name']}**\n\n"
            "🌍 اختر الدولة:",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return COUNTRY_SELECTION
    
    async def country_selection(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """اختيار الدولة"""
        query = update.callback_query
        await query.answer()  # مهم جداً!
        
        country_code = query.data.replace("country_", "")
        context.user_data['selected_country'] = int(country_code)
        
        # تحديد اسم الدولة للعرض
        country_name = "روسيا" if context.user_data['selected_country'] == 6 else "كازاخستان" if context.user_data['selected_country'] == 2 else "أوكرانيا" if context.user_data['selected_country'] == 1 else "جميع الدول"
        
        # عرض تأكيد الشراء مع السعر التقريبي
        keyboard = [
            [
                InlineKeyboardButton("✅ تأكيد الشراء", callback_data="confirm_purchase"),
                InlineKeyboardButton("❌ إلغاء", callback_data="cancel_purchase")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📱 **تفاصيل الطلب**\n\n"
            f"الخدمة: {context.user_data['service_name']}\n"
            f"الدولة: {country_name}\n"
            f"السعر التقريبي: 0.5 - 2 دولار\n\n"
            f"⚠️ هل تريد تأكيد الشراء؟",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
        
        return CONFIRM_PURCHASE
    
    async def confirm_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """تأكيد الشراء - placeholder"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "confirm_purchase":
            # هنا سيتم تنفيذ عملية الشراء الفعلية
            await query.edit_message_text(
                "🔄 جاري طلب الرقم...",
                parse_mode='Markdown'
            )
            
            # محاكاة طلب رقم (سيتم استبداله بالطلب الفعلي)
            import asyncio
            await asyncio.sleep(2)
            
            await query.edit_message_text(
                "✅ **تمت العملية بنجاح!**\n\n"
                "الرقم: +7 (999) 123-45-67\n"
                "رمز التفعيل: 12345\n\n"
                "⏱️ الرقم صالح لمدة 20 دقيقة.\n"
                "سيتم إعلامك عند وصول رسالة جديدة.",
                parse_mode='Markdown'
            )
        
        elif query.data == "cancel_purchase":
            await query.edit_message_text(
                "❌ تم إلغاء عملية الشراء.",
                parse_mode='Markdown'
            )
            return ConversationHandler.END
        
        return ConversationHandler.END
    
    async def process_purchase(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالجة الشراء الفعلية"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "confirm_yes":
            # تنفيذ الشراء الفعلي عبر API
            service = context.user_data['selected_service']
            country = context.user_data['selected_country']
            
            try:
                # طلب رقم من API
                number_data = await self.api.get_number(service, country)
                
                if number_data:
                    activation_id = number_data.get('activationId')
                    phone_number = number_data.get('phoneNumber')
                    
                    # حفظ بيانات التفعيل في context
                    context.user_data['current_activation'] = {
                        'id': activation_id,
                        'phone': phone_number,
                        'service': service
                    }
                    
                    await query.edit_message_text(
                        f"✅ **تم شراء الرقم بنجاح!**\n\n"
                        f"📱 الرقم: `{phone_number}`\n"
                        f"🆔 معرف التفعيل: {activation_id}\n"
                        f"⏱️ صالح لمدة: 20 دقيقة\n\n"
                        f"سيتم إعلامك عند وصول الرسالة.",
                        parse_mode='Markdown'
                    )
                    
                    # هنا يمكن إضافة مراقبة وصول الرسالة
                    
                else:
                    await query.edit_message_text(
                        "❌ فشل في الحصول على رقم. الرجاء المحاولة مرة أخرى.",
                        parse_mode='Markdown'
                    )
            
            except Exception as e:
                logger.error(f"خطأ في عملية الشراء: {e}")
                await query.edit_message_text(
                    "❌ حدث خطأ أثناء الشراء. الرجاء المحاولة لاحقاً.",
                    parse_mode='Markdown'
                )
        
        elif query.data == "confirm_no":
            await query.edit_message_text(
                "❌ تم إلغاء عملية الشراء.",
                parse_mode='Markdown'
            )
        
        return ConversationHandler.END
    
    async def fallback_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """معالج للأزرار التي لا تنتمي لمحادثة محددة"""
        query = update.callback_query
        await query.answer()
        
        logger.info(f"fallback_handler تم استدعاؤه مع: {query.data}")
        
        if query.data == "back_to_main":
            # العودة للقائمة الرئيسية
            keyboard = [
                [InlineKeyboardButton("📱 شراء رقم", callback_data="buy_number")],
                [InlineKeyboardButton("💰 رصيدي", callback_data="check_balance")],
                [InlineKeyboardButton("❓ مساعدة", callback_data="show_help")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.edit_message_text(
                "👫 **القائمة الرئيسية**\n\nاختر ما تريد:",
                reply_markup=reply_markup,
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                "❌ حدث خطأ. الرجاء استخدام الأزرار المتاحة أو إرسال /start",
                parse_mode='Markdown'
            )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """إلغاء المحادثة"""
        await update.message.reply_text(
            "تم إلغاء العملية.",
            parse_mode='Markdown'
        )
        return ConversationHandler.END
    
    async def webhook_handler(self, request_data: Dict[str, Any]):
        """معالج Webhook لاستقبال الرسائل من HeroSMS"""
        logger.info(f"استقبال Webhook: {request_data}")
        
        # معالجة بيانات الرسالة الواردة
        activation_id = request_data.get('activation_id')
        sms_code = request_data.get('code')
        sms_text = request_data.get('text')
        
        if activation_id and sms_code:
            # البحث عن المستخدم صاحب هذا التفعيل وإرسال الرسالة له
            # هذا يتطلب تخزين بيانات المستخدمين والتفعيلات في قاعدة بيانات
            
            logger.info(f"تم استلام كود للتفعيل {activation_id}: {sms_code}")
            
            # هنا يمكن إرسال رسالة للمستخدم عبر البوت
            # سيتم تطبيق هذا الجزء لاحقاً عند إضافة قاعدة بيانات
        
        return {"status": "ok"}
