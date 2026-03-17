import os
import asyncio
from aiohttp import web
from aiogram import types
from bot import bot, dp

# الإعدادات من Render
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))

async def handle_webhook(request):
    """معالج استقبال التحديثات من تلجرام"""
    url = str(request.url)
    if url.endswith("/"):
        # صفحة بسيطة للتأكد أن البوت يعمل
        return web.Response(text="Bot is running smoothly! 🚀")

    try:
        payload = await request.json()
        update = types.Update.model_validate(payload, context={"bot": bot})
        await dp.feed_update(bot, update)
        return web.Response(text="OK")
    except Exception as e:
        print(f"Error handling update: {e}")
        return web.Response(status=500, text="Internal Error")

async def on_startup(app):
    """يتم تنفيذه عند بدء التشغيل"""
    print(f"Setting webhook to: {WEBHOOK_URL}")
    await bot.set_webhook(WEBHOOK_URL)

async def on_cleanup(app):
    """إغلاق الجلسات عند التوقف"""
    await bot.delete_webhook()
    await bot.session.close()

def main():
    app = web.Application()
    # ربط المسارات (الرابط الرئيسي للويب هوك)
    app.router.add_post("/", handle_webhook)
    app.router.add_get("/", handle_webhook)

    # إضافة مهام البدء والإغلاق
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)

    # تشغيل السيرفر
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
