import os
import asyncio
from aiohttp import web
from aiogram import types
from bot import bot, dp

# إعدادات Render
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))

async def handle_webhook(request):
    """استقبال التحديثات من تلجرام"""
    if request.method == "GET":
        return web.Response(text="Bot is running! 🚀")

    try:
        data = await request.json()
        update = types.Update.model_validate(data, context={"bot": bot})
        await dp.feed_update(bot, update)
        return web.Response(text="OK")
    except Exception as e:
        print(f"Error: {e}")
        return web.Response(status=500, text="Internal Error")

async def on_startup(app):
    """ضبط الويب هوك عند تشغيل السيرفر"""
    # حذف الويب هوك القديم وضبط الجديد
    await bot.delete_webhook(drop_pending_updates=True)
    await bot.set_webhook(WEBHOOK_URL)
    print(f"Webhook set to: {WEBHOOK_URL}")

def main():
    app = web.Application()
    app.router.add_post("/", handle_webhook)
    app.router.add_get("/", handle_webhook)
    app.on_startup.append(on_startup)
    
    # تشغيل السيرفر على المنفذ المطلوب من Render
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    main()
