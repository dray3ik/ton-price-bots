import asyncio, logging, aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web
import os

API_TOKEN = os.getenv("API_TOKEN")
TARGET_CHAT_ID = int(os.getenv("TARGET_CHAT_ID"))

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

async def get_ton_stats():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    params = {"symbol": "TONUSDT"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            return {
                "price": float(data["lastPrice"]),
                "high": float(data["highPrice"]),
                "low": float(data["lowPrice"]),
                "change": float(data["priceChangePercent"])
            }

def format_stats(s):
    return (
        f"💰 <b>Toncoin (TON)</b>\n"
        f"• Price: <code>${s['price']:.4f}</code>\n"
        f"• 24h High: <code>${s['high']:.4f}</code>\n"
        f"• 24h Low: <code>${s['low']:.4f}</code>\n"
        f"• 24h Change: <code>{s['change']:+.2f}%</code>"
    )

def refresh_btn():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🔄 Refresh", callback_data="refresh_price")]
    ])

@dp.message(Command("tonprice"))
async def cmd_price(m: Message):
    s = await get_ton_stats()
    await m.answer(format_stats(s), parse_mode=ParseMode.HTML, reply_markup=refresh_btn())

@dp.callback_query(F.data=="refresh_price")
async def cb_refresh(c: types.CallbackQuery):
    s = await get_ton_stats()
    await c.message.edit_text(format_stats(s), parse_mode=ParseMode.HTML, reply_markup=refresh_btn())
    await c.answer("🔁 Updated")

@dp.message(Command("tonmood"))
async def cmd_mood(m: Message):
    s = await get_ton_stats()
    c = s["change"]
    mood = (
        "🟢 TON is pumping!"
        if c >=5 else
        "📈 TON is rising."
        if c>=1 else
        "🟡 TON is calm."
        if c>-1 else
        "🔻 TON is dipping."
        if c>-5 else
        "🔴 TON is crashing!"
    )
    await m.answer(f"{mood}\n\n24h Change: <code>{c:+.2f}%</code>", parse_mode=ParseMode.HTML)

async def auto_post_loop():
    while True:
        s = await get_ton_stats()
        await bot.send_message(TARGET_CHAT_ID, format_stats(s), parse_mode=ParseMode.HTML, reply_markup=refresh_btn())
        logging.info("Posted auto update")
        await asyncio.sleep(60)

async def handle_ping(r):
    return web.Response(text="✅ Bot is running")

async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    web_app = web.Application()
    web_app.router.add_get("/", handle_ping)
    runner = web.AppRunner(web_app)
    await runner.setup()
    await web.TCPSite(runner,"0.0.0.0",8080).start()
    asyncio.create_task(auto_post_loop())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
