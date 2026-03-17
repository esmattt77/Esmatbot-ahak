import os
import asyncio
from flask import Flask, request
from aiogram import types
from bot import bot, dp

app = Flask(__name__)

WEBHOOK_URL = os.getenv("WEBHOOK_URL")
PORT = int(os.getenv("PORT", 10000))

@app.route("/", methods=["GET", "HEAD"])
async def index():
    return "Bot is running..."

@app.route("/", methods=["POST"])
async def webhook():
    update = types.Update.model_validate(request.json, context={"bot": bot})
    await dp.feed_update(bot, update)
    return "OK"

async def setup_webhook():
    webhook_path = f"{WEBHOOK_URL}"
    await bot.set_webhook(webhook_path)

if __name__ == "__main__":
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(setup_webhook())
    app.run(host="0.0.0.0", port=PORT)
