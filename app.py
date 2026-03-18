from flask import Flask, request, jsonify
import os
import asyncio
import logging
from bot import NumberSellingBot
from telegram import Update

# إعداد التسجيل
logging.basicConfig(
    format='%(asname)s - %(name)s - %(levelname)s - %(message)s',
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
admin_ids = [int(a.strip()) for a in ADMIN_IDS if a.strip().isdigit()]

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

# تهيئة البوت عند بدء التشغيل
logger.info("🚀 بدء تشغيل تطبيق Flask...")
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
        
        # معالجة التحديث في حلقة الأحداث
        if loop and loop.is_running():
            # إذا كانت الحلقة تعمل، استخدم run_coroutine_threadsafe
            future = asyncio.run_coroutine_threadsafe(
                application.process_update(update),
                loop
            )
            future.result(timeout=10)
        else:
            # وإلا، أنشئ حلقة جديدة
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            new_loop.run_until_complete(application.process_update(update))
            new_loop.close()
        
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
    status = "✅ يعمل" if bot_instance and application else "❌ غير نشط"
    webhook_status = "✅" if application and application.bot else "❌"
    
    # معلومات إضافية للتصحيح
    bot_info = ""
    if application and application.bot:
        try:
            # محاولة جلب معلومات البوت
            loop2 = asyncio.new_event_loop()
            asyncio.set_event_loop(loop2)
            bot_info = loop2.run_until_complete(application.bot.get_me())
            loop2.close()
        except:
            pass
    
    return f"""
    <html>
        <head>
            <title>بوت بيع الأرقام</title>
            <style>
                body {{ font-family: Arial; text-align: center; padding: 50px; background: #f0f0f0; }}
                .container {{ background: white; padding: 30px; border-radius: 10px; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
                h1 {{ color: #2ecc71; }}
                .status {{ font-size: 18px; margin: 10px 0; }}
                .ok {{ color: green; }}
                .info {{ color: #7f8c8d; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 بوت بيع الأرقام الافتراضية</h1>
                <p class="status">حالة البوت: <strong class="ok">{status}</strong></p>
                <p class="status">تم تعيين Webhook: <strong>{webhook_status}</strong></p>
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
        "status": "healthy",
        "bot": "active" if bot_instance and application else "inactive",
        "webhook": "set" if application and application.bot else "not set"
    }), 200

@app.route('/debug', methods=['GET'])
def debug():
    """معلومات التصحيح"""
    return jsonify({
        "bot_initialized": bot_instance is not None,
        "application_initialized": application is not None,
        "loop_exists": loop is not None,
        "loop_running": loop.is_running() if loop else False,
        "admin_ids": admin_ids,
        "webhook_url": f"{WEBHOOK_URL}/webhook" if WEBHOOK_URL else None
    })

if __name__ == "__main__":
    # للتشغيل المحلي فقط
    app.run(host="0.0.0.0", port=PORT, debug=False)
