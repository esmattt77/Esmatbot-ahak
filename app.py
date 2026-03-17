from flask import Flask, request, jsonify
import os
import asyncio
import logging
from bot import NumberSellingBot
from telegram import Update

# إعداد التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# إنشاء تطبيق Flask
app = Flask(__name__)

# متغيرات البيئة - تأكد من صحتها في Render Dashboard
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
SMS_ACTIVATE_API_KEY = os.environ.get('SMS_ACTIVATE_API_KEY')
ADMIN_IDS = os.environ.get('ADMIN_IDS', '').split(',')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
PORT = int(os.environ.get('PORT', 10000))  # المنفذ الافتراضي 10000

# تحويل ADMIN_IDS إلى أرقام صحيحة
admin_ids = [int(a.strip()) for a in ADMIN_IDS if a.strip().isdigit()]

# متغيرات عامة
bot_instance = None
application = None

def initialize_bot():
    """تهيئة البوت بشكل متزامن - تستدعى مرة واحدة عند بدء التشغيل"""
    global bot_instance, application
    
    logger.info("بدء تهيئة البوت...")
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ توكن البوت غير موجود!")
        return False
    
    try:
        # إنشاء البوت
        bot_instance = NumberSellingBot(
            token=TELEGRAM_BOT_TOKEN,
            api_key=SMS_ACTIVATE_API_KEY or "",
            admin_ids=admin_ids
        )
        application = bot_instance.application
        
        # تعيين Webhook
        webhook_url = f"{WEBHOOK_URL}/webhook"
        logger.info(f"محاولة تعيين Webhook على: {webhook_url}")
        
        # استخدام asyncio للتشغيل المتزامن
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # تعيين webhook
        future = asyncio.run_coroutine_threadsafe(
            application.bot.set_webhook(url=webhook_url),
            loop
        )
        future.result(timeout=10)
        logger.info(f"✅ Webhook تم تعيينه بنجاح: {webhook_url}")
        
        # تهيئة التطبيق
        future = asyncio.run_coroutine_threadsafe(
            application.initialize(),
            loop
        )
        future.result(timeout=10)
        logger.info("✅ تم تهيئة البوت بنجاح")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ فشل تهيئة البوت: {e}")
        return False

# تهيئة البوت عند استيراد الملف (قبل تشغيل الخادم)
init_success = initialize_bot()
if not init_success:
    logger.error("❌ فشل تهيئة البوت. تحقق من التوكن والإعدادات.")

@app.route('/webhook', methods=['POST'])
def webhook():
    """نقطة نهاية Webhook من تلغرام"""
    if not application:
        return jsonify({"error": "Bot not initialized"}), 500
    
    try:
        update_data = request.get_json()
        if not update_data:
            return jsonify({"status": "no data"}), 200
        
        logger.info(f"📨 استقبال تحديث: {update_data.get('update_id')}")
        
        # معالجة التحديث
        update = Update.de_json(update_data, application.bot)
        
        # تشغيل المعالجة في حلقة الأحداث
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(application.process_update(update))
        loop.close()
        
        logger.info(f"✅ تمت معالجة التحديث: {update.update_id}")
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة webhook: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """الصفحة الرئيسية - نقطة فحص الصحة"""
    from datetime import datetime
    status = "✅ يعمل" if bot_instance else "❌ غير نشط"
    return f"""
    <html>
        <head><title>بوت بيع الأرقام</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>🤖 بوت بيع الأرقام الافتراضية</h1>
            <p>حالة البوت: <strong>{status}</strong></p>
            <p>تم تعيين Webhook: <strong>{'✅' if bot_instance else '❌'}</strong></p>
            <p>الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            <p>المنفذ: {PORT}</p>
        </body>
    </html>
    """

@app.route('/health', methods=['GET'])
def health():
    """نقطة نهاية فحص الصحة لـ Render"""
    return jsonify({
        "status": "healthy" if bot_instance else "unhealthy",
        "bot": "active" if bot_instance else "inactive"
    }), 200 if bot_instance else 500

if __name__ == "__main__":
    # للتشغيل المحلي فقط
    app.run(host="0.0.0.0", port=PORT, debug=False)
else:
    # عند التشغيل مع Gunicorn
    pass
