import os
import logging
from flask import Flask, request
import telebot
from bot import setup_bot
from async_utils import async_loop

# بدء حلقة الأحداث عند تشغيل التطبيق
async_loop.start()

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

# إعداد معالجات البوت - تمرير البوت كمعامل
setup_bot(bot)

# إنشاء تطبيق Flask
app = Flask(__name__)

# مسار webhook الصحيح
@app.route('/webhook', methods=['POST'])
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
    """الصفحة الرئيسية"""
    return f"""
    <html>
        <head>
            <title>بوت بيع الأرقام</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial; text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
                .container {{ background: rgba(255,255,255,0.1); padding: 30px; border-radius: 10px; max-width: 600px; margin: 0 auto; }}
                h1 {{ color: #fff; font-size: 2.5em; }}
                .status {{ font-size: 1.2em; margin: 20px 0; }}
                .info {{ opacity: 0.9; }}
                code {{ background: rgba(0,0,0,0.3); padding: 5px 10px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 بوت بيع الأرقام الافتراضية</h1>
                <p class="status">✅ البوت يعمل بنجاح!</p>
                <p class="info">تم تعيين Webhook على: <code>/webhook</code></p>
                <p class="info">أرسل <strong>/start</strong> للبوت في Telegram</p>
            </div>
        </body>
    </html>
    """

@app.route('/health', methods=['GET'])
def health():
    """نقطة نهاية فحص الصحة"""
    return {"status": "healthy", "bot": "running"}, 200

@app.route('/debug', methods=['GET'])
def debug():
    """معلومات التصحيح"""
    return {
        "bot_token_configured": bool(TELEGRAM_BOT_TOKEN),
        "webhook_url_configured": WEBHOOK_URL,
        "webhook_full": f"{WEBHOOK_URL}/webhook",
        "port": PORT
    }

@app.route('/set_webhook', methods=['GET'])
def set_webhook_manually():
    """نقطة نهاية لتعيين webhook يدوياً"""
    global bot
    
    webhook_url_full = f"{WEBHOOK_URL}/webhook"
    
    try:
        # حذف webhook القديم
        bot.delete_webhook()
        logger.info("✅ تم حذف webhook القديم")
        
        # تعيين webhook جديد
        result = bot.set_webhook(url=webhook_url_full)
        
        if result:
            logger.info(f"✅ تم تعيين webhook على: {webhook_url_full}")
            return {"status": "success", "webhook": webhook_url_full}, 200
        else:
            logger.error("❌ فشل تعيين webhook")
            return {"status": "error", "message": "Failed to set webhook"}, 500
            
    except Exception as e:
        logger.error(f"❌ خطأ في تعيين webhook: {e}")
        return {"status": "error", "message": str(e)}, 500

if __name__ == '__main__':
    logger.info("🚀 جاري تشغيل البوت...")
    
    # لا نعين webhook هنا - سنعينه يدوياً بعد تشغيل التطبيق
    logger.info("✅ البوت جاهز، يرجى زيارة /set_webhook لتعيين webhook")
    
    # تشغيل Flask
    app.run(host='0.0.0.0', port=PORT)
