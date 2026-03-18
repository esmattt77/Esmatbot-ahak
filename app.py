from flask import Flask, request, jsonify
import os
import asyncio
import logging
from bot import NumberSellingBot
from telegram import Update
import threading
import time

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
background_thread = None
bot_ready = False

def run_bot_forever():
    """تشغيل البوت في حلقة أحداث دائمة في خيط منفصل"""
    global bot_instance, application, loop, bot_ready
    
    logger.info("🚀 بدء تشغيل البوت في الخلفية...")
    
    # إنشاء حلقة أحداث جديدة
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # إنشاء البوت
        bot_instance = NumberSellingBot(
            token=TELEGRAM_BOT_TOKEN,
            api_key=SMS_ACTIVATE_API_KEY or "",
            admin_ids=admin_ids
        )
        application = bot_instance.application
        
        # تهيئة التطبيق
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
        
        bot_ready = True
        logger.info("✅ البوت جاهز لاستقبال الأوامر!")
        
        # تشغيل حلقة الأحداث إلى الأبد
        loop.run_forever()
        
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البوت: {e}")
        import traceback
        traceback.print_exc()
        bot_ready = False
    finally:
        logger.info("🛑 تم إغلاق حلقة الأحداث")
        if loop and loop.is_running():
            loop.close()

# بدء تشغيل البوت في خيط منفصل
background_thread = threading.Thread(target=run_bot_forever, daemon=True)
background_thread.start()
logger.info("✅ تم بدء تشغيل البوت في الخلفية")

@app.route('/webhook', methods=['POST'])
def webhook():
    """نقطة نهاية Webhook من تلغرام"""
    global application, loop, bot_ready
    
    if not bot_ready:
        logger.warning("⚠️ البوت ليس جاهزاً بعد")
        return jsonify({"error": "Bot not ready"}), 503
    
    try:
        # استلام البيانات
        update_data = request.get_json()
        if not update_data:
            return jsonify({"status": "no data"}), 200
        
        update_id = update_data.get('update_id')
        logger.info(f"📨 استقبال تحديث: {update_id}")
        
        # تحويل البيانات إلى كائن Update
        update = Update.de_json(update_data, application.bot)
        
        # معالجة التحديث في حلقة الأحداث - استخدام run_coroutine_threadsafe
        future = asyncio.run_coroutine_threadsafe(
            application.process_update(update),
            loop
        )
        
        # انتظر النتيجة مع مهلة
        future.result(timeout=30)
        
        logger.info(f"✅ تمت معالجة التحديث: {update_id}")
        return jsonify({"status": "ok"}), 200
        
    except asyncio.TimeoutError:
        logger.error("⏱️ تجاوز الوقت المسموح لمعالجة التحديث")
        return jsonify({"status": "timeout"}), 200
        
    except Exception as e:
        logger.error(f"❌ خطأ في معالجة webhook: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/', methods=['GET'])
def index():
    """الصفحة الرئيسية"""
    from datetime import datetime
    status = "✅ يعمل" if bot_ready else "⏳ يبدأ التشغيل..."
    
    return f"""
    <html>
        <head>
            <title>بوت بيع الأرقام</title>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: 'Arial', sans-serif; text-align: center; padding: 50px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }}
                .container {{ background: rgba(255,255,255,0.1); padding: 40px; border-radius: 15px; backdrop-filter: blur(10px); }}
                h1 {{ font-size: 2.5em; margin-bottom: 20px; }}
                .status {{ font-size: 1.2em; margin: 15px 0; }}
                .ok {{ color: #a8e6cf; }}
                .wait {{ color: #ffeaa7; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 بوت بيع الأرقام الافتراضية</h1>
                <p class="status">حالة البوت: <strong class="{'ok' if bot_ready else 'wait'}">{status}</strong></p>
                <p class="info">الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p class="info">المنفذ: {PORT}</p>
                <p class="info">عدد المشرفين: {len(admin_ids)}</p>
                <p class="info">🚀 البوت جاهز لاستقبال الأوامر</p>
            </div>
        </body>
    </html>
    """

@app.route('/health', methods=['GET'])
def health():
    """نقطة نهاية فحص الصحة"""
    return jsonify({
        "status": "healthy" if bot_ready else "starting",
        "bot": "active" if bot_ready else "initializing",
        "thread": "running" if background_thread and background_thread.is_alive() else "stopped"
    }), 200 if bot_ready else 503

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=PORT, debug=False)
