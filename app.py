from flask import Flask, request, jsonify
import os
import asyncio
from bot import NumberSellingBot
import logging
from telegram import Update
import json

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
    if admin_id.strip().isdigit():
        admin_ids.append(int(admin_id.strip()))

# متغيرات عامة
bot_instance = None
application = None
loop = None

def init_bot():
    """تهيئة البوت بشكل متزامن"""
    global bot_instance, application, loop
    
    if bot_instance is None:
        try:
            # إنشاء حلقة أحداث جديدة
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # إنشاء كائن البوت
            bot_instance = NumberSellingBot(
                token=TELEGRAM_BOT_TOKEN,
                api_key=SMS_ACTIVATE_API_KEY,
                admin_ids=admin_ids
            )
            
            application = bot_instance.application
            
            # تعيين webhook في Telegram (بشكل متزامن)
            webhook_url = f"{WEBHOOK_URL}/webhook"
            future = asyncio.run_coroutine_threadsafe(
                application.bot.set_webhook(url=webhook_url),
                loop
            )
            future.result()  # انتظر النتيجة
            logger.info(f"✅ Webhook تم تعيينه بنجاح: {webhook_url}")
            
            # تهيئة التطبيق
            future = asyncio.run_coroutine_threadsafe(
                application.initialize(),
                loop
            )
            future.result()
            
            logger.info("✅ تم تهيئة البوت بنجاح")
            
        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة البوت: {e}")
            bot_instance = None
            raise e

# تهيئة البوت عند بدء التشغيل
init_bot()

@app.route('/webhook', methods=['POST'])
def webhook():
    """نقطة نهاية Webhook من تلغرام"""
    global application, loop
    
    if application is None:
        init_bot()
    
    try:
        # استلام البيانات
        update_data = request.get_json()
        if not update_data:
            return jsonify({"status": "no data"}), 200
        
        logger.info(f"📨 استقبال تحديث: {update_data.get('update_id')}")
        
        # تحويل البيانات إلى كائن Update
        update = Update.de_json(update_data, application.bot)
        
        # معالجة التحديث في حلقة الأحداث
        future = asyncio.run_coroutine_threadsafe(
            application.process_update(update),
            loop
        )
        future.result(timeout=5)  # انتظر حتى 5 ثوان
        
        logger.info(f"✅ تم معالجة تحديث: {update.update_id}")
        return jsonify({"status": "ok"}), 200
        
    except asyncio.TimeoutError:
        logger.error("⏱️ تجاوز الوقت المسموح لمعالجة التحديث")
        return jsonify({"status": "timeout"}), 200
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة webhook: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/sms-webhook', methods=['POST'])
def sms_webhook():
    """نقطة نهاية Webhook من HeroSMS لاستقبال الرسائل"""
    global bot_instance, loop
    
    if bot_instance is None:
        init_bot()
    
    try:
        data = request.get_json()
        if data:
            logger.info(f"📨 استقبال SMS webhook: {data}")
            
            # معالجة رسالة SMS الواردة في حلقة الأحداث
            future = asyncio.run_coroutine_threadsafe(
                bot_instance.webhook_handler(data),
                loop
            )
            future.result(timeout=5)
            
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
    from datetime import datetime
    return f"""
    <html>
        <head>
            <title>Telegram Number Selling Bot</title>
            <style>
                body {{ font-family: Arial; text-align: center; padding: 50px; }}
                h1 {{ color: #2ecc71; }}
                .status {{ color: #3498db; }}
                .info {{ color: #7f8c8d; margin-top: 20px; }}
            </style>
        </head>
        <body>
            <h1>✅ بوت بيع الأرقام الافتراضية</h1>
            <p class="status">البوت يعمل بشكل طبيعي ✓</p>
            <p>تم تعيين Webhook بنجاح</p>
            <p class="info">بتاريخ: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p class="info">البوت جاهز لاستقبال الأوامر 🚀</p>
        </body>
    </html>
    """

@app.errorhandler(404)
def not_found(error):
    return jsonify({"error": "Not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"error": "Internal server error"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT)
