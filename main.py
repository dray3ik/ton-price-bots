import asyncio
import logging
import os

import aiohttp
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.client.default import DefaultBotProperties

# === Environment Variables (set these in Render) ===
API_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = int(os.getenv("CHAT_ID"))

# === Logging and Bot Setup ===
logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# === Toncoin Price Fetcher ===
async def get_ton_stats():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    params = {"symbol": "TONUSDT"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            if "lastPrice" not in data:
                raise ValueError(f"Invalid Binance API response: {data}")
            return {
                "price": float(data["lastPrice"]),
                "high": float(data["highPrice"]),
                "low": float(data["lowPrice"]),
                "change": float(data["priceChangePercent"])
            }

def format_stats_message(s):
    return (
        f"💰 <b>Toncoin (TON)</b>\n"
        f"• Price: <code>${s['price']:.4f}</code>\n"
        f"• 24h High: <code>${s['high']:.4f}</code>\n"
        f"• 24h Low: <code>${s['low']:.4f}</code>\n"
        f"• 24h Change: <code>{s['change']:+.2f}%</code>"
    )

def get_refresh_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Refresh", callback_data="refresh_price")]
    ])

# === Bot Commands ===
@dp.message(Command("tonprice"))
async def cmd_price(message: Message):
    try:
        s = await get_ton_stats()
        await message.answer(format_stats_message(s), reply_markup=get_refresh_button())
    except Exception as e:
        await message.answer(f"❌ Failed to fetch price: {e}")

@dp.callback_query(F.data == "refresh_price")
async def refresh_price(callback: CallbackQuery):
    try:
        s = await get_ton_stats()
        await callback.message.edit_text(format_stats_message(s), reply_markup=get_refresh_button())
        await callback.answer("🔁 Updated!")
    except Exception as e:
        await callback.answer("❌ Error updating price")

@dp.message(Command("tonmood"))
async def ton_mood(message: Message):
    try:
        s = await get_ton_stats()
        c = s["change"]
        mood = (
            "🟢 <b>TON is pumping!</b>" if c >= 5 else
            "📈 <b>TON is rising steadily.</b>" if c >= 1 else
            "🟡 <b>TON is calm.</b>" if c > -1 else
            "🔻 <b>TON is dipping.</b>" if c > -5 else
            "🔴 <b>TON is crashing!</b>"
        )
        await message.answer(f"{mood}\n\n24h Change: <code>{c:+.2f}%</code>")
    except Exception as e:
        await message.answer(f"❌ Failed to fetch mood: {e}")

# === Auto Posting Loop ===
async def auto_post_loop():
    while True:
        try:
            s = await get_ton_stats()
            await bot.send_message(CHAT_ID, format_stats_message(s), reply_markup=get_refresh_button())
            logging.info("✅ Auto post sent.")
        except Exception as e:
            logging.error(f"❌ Auto post failed: {e}")
        await asyncio.sleep(60)  # Post every minute

# === HTTP server for keep-alive ===
async def handle_ping(request):
    return web.Response(text="✅ Bot is running!")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)

    # Start small web server (for uptime monitoring)
    app = web.Application()
    app.router.add_get("/", handle_ping)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8080).start()

    # Start background post loop and polling
    asyncio.create_task(auto_post_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
