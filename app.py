from flask import Flask, request, jsonify
import os
import asyncio
from bot import NumberSellingBot
import logging
import threading

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

# إنشاء كائن البوت
bot = NumberSellingBot(
    token=TELEGRAM_BOT_TOKEN,
    api_key=SMS_ACTIVATE_API_KEY,
    admin_ids=admin_ids
)

# حلقة الأحداث غير المتزامنة
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

@app.route('/webhook', methods=['POST'])
def webhook():
    """نقطة نهاية Webhook من تلغرام"""
    try:
        update_data = request.get_json()
        if update_data:
            # معالجة التحديث في حلقة الأحداث
            asyncio.run_coroutine_threadsafe(
                bot.application.process_update(update_data),
                loop
            )
            return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"خطأ في معالجة webhook: {e}")
        return jsonify({"status": "error"}), 500
    
    return jsonify({"status": "ok"}), 200

@app.route('/sms-webhook', methods=['POST'])
def sms_webhook():
    """نقطة نهاية Webhook من HeroSMS لاستقبال الرسائل"""
    try:
        data = request.get_json()
        if data:
            # معالجة رسالة SMS الواردة
            asyncio.run_coroutine_threadsafe(
                bot.webhook_handler(data),
                loop
            )
            return jsonify({"status": "ok"}), 200
    except Exception as e:
        logger.error(f"خطأ في معالجة sms webhook: {e}")
        return jsonify({"status": "error"}), 500
    
    return jsonify({"status": "ok"}), 200

@app.route('/health', methods=['GET'])
def health():
    """نقطة نهاية فحص الصحة"""
    return jsonify({"status": "healthy"}), 200

@app.route('/', methods=['GET'])
def index():
    """الصفحة الرئيسية"""
    return """
    <html>
        <head><title>Telegram Number Selling Bot</title></head>
        <body>
            <h1>بوت بيع الأرقام الافتراضية</h1>
            <p>البوت يعمل بشكل طبيعي ✓</p>
        </body>
    </html>
    """

def start_bot():
    """تشغيل البوت في حلقة الأحداث"""
    loop.run_until_complete(bot.run_webhook(WEBHOOK_URL, PORT))

if __name__ == '__main__':
    # تشغيل البوت في خيط منفصل
    bot_thread = threading.Thread(target=start_bot, daemon=True)
    bot_thread.start()
    
    # تشغيل تطبيق Flask
    app.run(host='0.0.0.0', port=PORT)
