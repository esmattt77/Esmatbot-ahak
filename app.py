import os
import logging
from flask import Flask, request
from bot import bot, setup_bot
import telebot

# إعداد التسجيل
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# متغيرات البيئة
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
WEBHOOK_URL = os.environ.get('WEBHOOK_URL')
PORT = int(os.environ.get('PORT', 10000))

if not TELEGRAM_BOT_TOKEN or not WEBHOOK_URL:
    logger.error("❌ TELEGRAM_BOT_TOKEN and WEBHOOK_URL must be set!")
    exit(1)

# تهيئة البوت (بدون threading)
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN, threaded=False)

# إعداد معالجات البوت
setup_bot(bot)

# إنشاء تطبيق Flask
app = Flask(__name__)

@app.route(f'/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    """معالج Webhook الرئيسي"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        
        try:
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
            logger.info(f"✅ تم معالجة تحديث: {update.update_id}")
        except Exception as e:
            logger.error(f"❌ خطأ في معالجة التحديث: {e}")
        
        return 'OK', 200
    else:
        return 'Hello, World!', 200

@app.route('/', methods=['GET'])
def index():
    return """
    <html>
        <head><title>بوت بيع الأرقام</title></head>
        <body style="font-family: Arial; text-align: center; padding: 50px;">
            <h1>🤖 بوت بيع الأرقام يعمل بنجاح!</h1>
            <p>تم تعيين Webhook ✅</p>
        </body>
    </html>
    """

if __name__ == '__main__':
    logger.info("🚀 جاري تشغيل البوت...")
    
    # تعيين Webhook
    webhook_url_full = f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}"
    
    try:
        bot.delete_webhook()
        logger.info("✅ تم حذف webhook القديم")
    except Exception as e:
        logger.warning(f"⚠️ فشل حذف webhook القديم: {e}")
    
    bot.set_webhook(url=webhook_url_full)
    logger.info(f"✅ تم تعيين webhook على: {webhook_url_full}")
    
    # تشغيل Flask
    app.run(host='0.0.0.0', port=PORT)
