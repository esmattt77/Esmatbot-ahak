from flask import Flask, request, jsonify
import os
import asyncio
from bot import NumberSellingBot
import logging
from telegram import Update
from telegram.ext import Application

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
PORT = int(os.environ.get('PORT', 8080))

# تحويل ADMIN_IDS إلى أرقام صحيحة
admin_ids = []
for admin_id in ADMIN_IDS:
    if admin_id.strip().isdigit():
        admin_ids.append(int(admin_id.strip()))

# متغير عام لحفظ البوت
bot_instance = None
application = None

@app.before_request
async def init_bot():
    """تهيئة البوت عند أول طلب"""
    global bot_instance, application
    if bot_instance is None:
        try:
            # إنشاء كائن البوت
            bot_instance = NumberSellingBot(
                token=TELEGRAM_BOT_TOKEN,
                api_key=SMS_ACTIVATE_API_KEY,
                admin_ids=admin_ids
            )
            
            # تعيين webhook
            application = bot_instance.application
            
            # تعيين webhook في Telegram
            webhook_url = f"{WEBHOOK_URL}/webhook"
            await application.bot.set_webhook(url=webhook_url)
            logger.info(f"✅ Webhook تم تعيينه بنجاح: {webhook_url}")
            
            # تهيئة التطبيق
            await application.initialize()
            
        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة البوت: {e}")
            bot_instance = None

@app.route('/webhook', methods=['POST'])
async def webhook():
    """نقطة نهاية Webhook من تلغرام"""
    global application
    
    if application is None:
        await init_bot()
    
    try:
        update_data = await request.get_json()
        if update_data:
            # تحويل البيانات إلى كائن Update
            update = Update.de_json(update_data, application.bot)
            
            # معالجة التحديث
            await application.process_update(update)
            logger.info(f"✅ تم معالجة تحديث: {update.update_id}")
            
            return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500
    
    return jsonify({"status": "ok"}), 200

@app.route('/sms-webhook', methods=['POST'])
async def sms_webhook():
    """نقطة نهاية Webhook من HeroSMS لاستقبال الرسائل"""
    global bot_instance
    
    if bot_instance is None:
        await init_bot()
    
    try:
        data = await request.get_json()
        if data:
            logger.info(f"📨 استقبال SMS webhook: {data}")
            # معالجة رسالة SMS الواردة
            await bot_instance.webhook_handler(data)
            return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة sms webhook: {e}")
        return jsonify({"status": "error"}), 500
    
    return jsonify({"status": "ok"}), 200

@app.route('/health', methods=['GET'])
def health():
    """نقطة نهاية فحص الصحة"""
    return jsonify({
        "status": "healthy",
        "bot_initialized": bot_instance is not None
    }), 200

@app.route('/', methods=['GET'])
def index():
    """الصفحة الرئيسية"""
    return """
    <html>
        <head>
            <title>Telegram Number Selling Bot</title>
            <style>
                body { font-family: Arial; text-align: center; padding: 50px; }
                h1 { color: #2ecc71; }
                .status { color: #3498db; }
            </style>
        </head>
        <body>
            <h1>✅ بوت بيع الأرقام الافتراضية</h1>
            <p class="status">البوت يعمل بشكل طبيعي ✓</p>
            <p>تم تعيين Webhook بنجاح</p>
            <p><small>بتاريخ: """ + __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</small></p>
        </body>
    </html>
    """

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

# هذا الجزء ضروري لتشغيل التطبيق مع Gunicorn
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
else:
    # عند التشغيل مع Gunicorn، نحتاج إلى حلقة أحداث
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    # تهيئة البوت بشكل متزامن
    async def init_bot_sync():
        global bot_instance, application
        try:
            bot_instance = NumberSellingBot(
                token=TELEGRAM_BOT_TOKEN,
                api_key=SMS_ACTIVATE_API_KEY,
                admin_ids=admin_ids
            )
            application = bot_instance.application
            webhook_url = f"{WEBHOOK_URL}/webhook"
            await application.bot.set_webhook(url=webhook_url)
            logger.info(f"✅ Webhook تم تعيينه بنجاح (Gunicorn): {webhook_url}")
            await application.initialize()
        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة البوت (Gunicorn): {e}")
    
    # تشغيل التهيئة
    loop.run_until_complete(init_bot_sync())
