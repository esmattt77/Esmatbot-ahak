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

# متغيرات البيئة
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
SMS_ACTIVATE_API_KEY = os.environ.get('SMS_ACTIVATE_API_KEY')
ADMIN_IDS = os.environ.get('ADMIN_IDS', '').split(',')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
PORT = int(os.environ.get('PORT', 10000))

# تحويل ADMIN_IDS إلى أرقام صحيحة
admin_ids = []
for admin_id in ADMIN_IDS:
    admin_id = admin_id.strip()
    if admin_id and admin_id.isdigit():
        admin_ids.append(int(admin_id))

# متغيرات عامة
bot_instance = None
application = None
loop = None

def initialize_bot():
    """تهيئة البوت بشكل متزامن"""
    global bot_instance, application, loop
    
    logger.info("بدء تهيئة البوت...")
    
    if not TELEGRAM_BOT_TOKEN:
        logger.error("❌ توكن البوت غير موجود!")
        return False
    
    try:
        # إنشاء حلقة أحداث جديدة
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # إنشاء البوت
        bot_instance = NumberSellingBot(
            token=TELEGRAM_BOT_TOKEN,
            api_key=SMS_ACTIVATE_API_KEY or "",
            admin_ids=admin_ids
        )
        application = bot_instance.application
        
        # تهيئة التطبيق أولاً
        logger.info("🔄 جاري تهيئة التطبيق...")
        loop.run_until_complete(application.initialize())
        logger.info("✅ تم تهيئة التطبيق")
        
        # تعيين Webhook
        webhook_url = f"{WEBHOOK_URL}/webhook"
        logger.info(f"🔄 جاري تعيين Webhook على: {webhook_url}")
        
        # تعيين webhook
        loop.run_until_complete(application.bot.set_webhook(url=webhook_url))
        logger.info(f"✅ Webhook تم تعيينه بنجاح: {webhook_url}")
        
        # بدء التطبيق
        logger.info("🔄 جاري بدء التطبيق...")
        loop.run_until_complete(application.start())
        logger.info("✅ تم بدء التطبيق")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ فشل تهيئة البوت: {e}")
        import traceback
        traceback.print_exc()
        return False

# تهيئة البوت مباشرة
init_success = initialize_bot()
if init_success:
    logger.info("✅ البوت جاهز لاستقبال الأوامر!")
else:
    logger.error("❌ فشل تهيئة البوت!")

@app.route('/webhook', methods=['POST'])
def webhook():
    """نقطة نهاية Webhook من تلغرام"""
    global application, loop
    
    if not application:
        logger.error("❌ التطبيق غير مهيأ!")
        return jsonify({"error": "Bot not initialized"}), 500
    
    try:
        # استلام البيانات
        update_data = request.get_json()
        if not update_data:
            return jsonify({"status": "no data"}), 200
        
        update_id = update_data.get('update_id')
        logger.info(f"📨 استقبال تحديث: {update_id}")
        
        # تحويل البيانات إلى كائن Update
        update = Update.de_json(update_data, application.bot)
        
        # معالجة التحديث - استخدام حلقة الأحداث الموجودة
        asyncio.run_coroutine_threadsafe(
            application.process_update(update),
            loop
        ).result(timeout=30)
        
        logger.info(f"✅ تمت معالجة التحديث: {update_id}")
        return jsonify({"status": "ok"}), 200
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة webhook: {e}")
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """الصفحة الرئيسية"""
    from datetime import datetime
    status = "✅ يعمل" if application else "❌ غير نشط"
    
    return f"""
    <html>
        <head>
            <title>بوت بيع الأرقام</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial; text-align: center; padding: 50px; background: #f0f0f0; }}
                .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #2ecc71; }}
                .ok {{ color: green; }}
                .info {{ color: #7f8c8d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 بوت بيع الأرقام الافتراضية</h1>
                <p class="status">حالة البوت: <strong class="ok">{status}</strong></p>
                <p class="info">الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p class="info">المنفذ: {PORT}</p>
                <p class="info">البوت جاهز لاستقبال الأوامر 🚀</p>
            </div>
        </body>
    </html>
    """

@app.route('/health', methods=['GET'])
def health():
    """نقطة نهاية فحص الصحة"""
    return jsonify({
        "status": "healthy" if application else "unhealthy"
    }), 200 if application else 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
