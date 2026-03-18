from flask import Flask, request, jsonify
import os
import asyncio
import logging
from bot import NumberSellingBot
from telegram import Update
import threading
import time
import atexit

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
start_time = time.time()

def run_bot_in_background():
    """تشغيل البوت في خلفية مع حلقة أحداث دائمة"""
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
        
        # حذف webhook القديم أولاً (للتأكد)
        loop.run_until_complete(application.bot.delete_webhook())
        logger.info("✅ تم حذف webhook القديم")
        
        # تعيين webhook الجديد
        result = loop.run_until_complete(application.bot.set_webhook(
            url=webhook_url,
            allowed_updates=['message', 'callback_query', 'inline_query'],
            max_connections=40
        ))
        
        if result:
            logger.info(f"✅ Webhook تم تعيينه بنجاح: {webhook_url}")
        else:
            logger.error("❌ فشل تعيين webhook!")
            return
        
        # بدء التطبيق
        logger.info("🔄 جاري بدء التطبيق...")
        loop.run_until_complete(application.start())
        logger.info("✅ تم بدء التطبيق")
        
        bot_ready = True
        ready_time = time.time() - start_time
        logger.info(f"✅ البوت جاهز لاستقبال الأوامر! (استغرق {ready_time:.2f} ثانية)")
        
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

def start_bot_thread():
    """بدء تشغيل البوت في خيط منفصل"""
    global background_thread
    if background_thread is None or not background_thread.is_alive():
        background_thread = threading.Thread(target=run_bot_in_background, daemon=True)
        background_thread.start()
        logger.info("✅ تم بدء تشغيل البوت في الخلفية")
        
        # انتظر حتى يصبح البوت جاهزاً (مع مهلة)
        wait_start = time.time()
        timeout = 30  # 30 ثانية مهلة
        
        while not bot_ready and (time.time() - wait_start) < timeout:
            logger.info(f"⏳ انتظار تهيئة البوت... {(time.time() - wait_start):.1f} ثانية")
            time.sleep(2)
        
        if bot_ready:
            logger.info(f"✅ البوت جاهز بعد {(time.time() - wait_start):.1f} ثانية")
        else:
            logger.warning(f"⚠️ البوت لم يصبح جاهزاً بعد {timeout} ثانية")
        
        return True
    return False

def cleanup():
    """تنظيف الموارد عند إيقاف التطبيق"""
    global loop, application, bot_ready
    logger.info("🛑 جاري إيقاف البوت...")
    bot_ready = False
    
    if application and loop and loop.is_running():
        try:
            # إيقاف التطبيق
            future = asyncio.run_coroutine_threadsafe(
                application.stop(),
                loop
            )
            future.result(timeout=5)
            
            # إغلاق التطبيق
            future = asyncio.run_coroutine_threadsafe(
                application.shutdown(),
                loop
            )
            future.result(timeout=5)
            
            logger.info("✅ تم إيقاف البوت بنجاح")
        except Exception as e:
            logger.error(f"❌ خطأ في إيقاف البوت: {e}")

# تسجيل دالة التنظيف
atexit.register(cleanup)

# بدء تشغيل البوت عند استيراد الملف - مع الانتظار
logger.info("🚀 بدء تشغيل تطبيق Flask...")
start_bot_thread()

@app.route('/webhook', methods=['POST'])
def webhook():
    """نقطة نهاية Webhook من تلغرام"""
    global application, loop, bot_ready, start_time
    
    # تحقق من جاهزية البوت
    if not bot_ready:
        elapsed = time.time() - start_time
        logger.warning(f"⚠️ البوت ليس جاهزاً بعد (بعد {elapsed:.1f} ثانية)")
        
        # تحقق مما إذا كان الخيط لا يزال يعمل
        if background_thread and background_thread.is_alive():
            return jsonify({
                "error": "Bot initializing",
                "status": "initializing",
                "elapsed": f"{elapsed:.1f}s"
            }), 503
        else:
            # الخيط مات، حاول إعادة تشغيله
            logger.error("❌ خلفية البوت توقفت! محاولة إعادة التشغيل...")
            start_bot_thread()
            return jsonify({
                "error": "Bot restarted",
                "status": "restarting"
            }), 503
    
    if not application or not loop:
        logger.error("❌ التطبيق أو حلقة الأحداث غير موجودة!")
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
    elapsed = time.time() - start_time
    
    if bot_ready:
        status = "✅ يعمل"
        status_class = "ok"
    else:
        status = f"⏳ يبدأ التشغيل... ({elapsed:.0f} ثانية)"
        status_class = "wait"
    
    thread_status = "✅ يعمل" if background_thread and background_thread.is_alive() else "❌ متوقف"
    
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
                .error {{ color: #ff7675; }}
                .info {{ opacity: 0.9; }}
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🤖 بوت بيع الأرقام الافتراضية</h1>
                <p class="status">حالة البوت: <strong class="{status_class}">{status}</strong></p>
                <p class="status">خلفية البوت: <strong class="{'ok' if background_thread and background_thread.is_alive() else 'error'}">{thread_status}</strong></p>
                <p class="info">الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                <p class="info">المنفذ: {PORT}</p>
                <p class="info">عدد المشرفين: {len(admin_ids)}</p>
                <p class="info">🚀 البوت يبدأ التشغيل... انتظر لحظات</p>
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
        "thread": "running" if background_thread and background_thread.is_alive() else "stopped",
        "uptime": f"{time.time() - start_time:.1f}s"
    }), 200 if bot_ready else 503

@app.route('/debug', methods=['GET'])
def debug():
    """معلومات التصحيح"""
    return jsonify({
        "bot_ready": bot_ready,
        "application_exists": application is not None,
        "loop_exists": loop is not None,
        "loop_running": loop.is_running() if loop else False,
        "thread_alive": background_thread.is_alive() if background_thread else False,
        "admin_ids": admin_ids,
        "webhook_url": f"{WEBHOOK_URL}/webhook" if WEBHOOK_URL else None,
        "token_exists": bool(TELEGRAM_BOT_TOKEN),
        "api_key_exists": bool(SMS_ACTIVATE_API_KEY),
        "uptime": f"{time.time() - start_time:.1f}s"
    })

@app.route('/force-ready', methods=['POST'])
def force_ready():
    """نقطة نهاية لإجبار البوت على الجاهزية (للمشرفين فقط)"""
    global bot_ready
    # يمكن إضافة تحقق من IP أو توكن هنا
    bot_ready = True
    logger.warning("⚠️ تم إجبار البوت على الجاهزية!")
    return jsonify({"status": "bot forced ready"}), 200

if __name__ == "__main__":
    # للتشغيل المحلي فقط
    app.run(host="0.0.0.0", port=PORT, debug=False)
