import os
import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, types, F
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

# === Configuration ===
API_TOKEN = os.getenv("BOT_TOKEN")  # or replace with your token string
TARGET_CHAT_ID = int(os.getenv("CHAT_ID", "-1001234567890"))  # Replace with your channel/group ID

# === Logging ===
logging.basicConfig(level=logging.INFO)

# === Bot Initialization ===
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


# === TON Price Fetching ===
async def get_ton_stats():
    url = "https://api.binance.com/api/v3/ticker/24hr"
    params = {"symbol": "TONUSDT"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            if "lastPrice" not in data:
                raise ValueError(f"Invalid response: {data}")
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


@dp.message(Command("tonprice"))
async def cmd_price(m: Message):
    s = await get_ton_stats()
    await m.answer(format_stats_message(s), parse_mode=ParseMode.HTML, reply_markup=get_refresh_button())


@dp.callback_query(F.data == "refresh_price")
async def cb_refresh(c: types.CallbackQuery):
    s = await get_ton_stats()
    await c.message.edit_text(format_stats_message(s), parse_mode=ParseMode.HTML, reply_markup=get_refresh_button())
    await c.answer("🔁 Updated")


@dp.message(Command("tonmood"))
async def cmd_mood(m: Message):
    s = await get_ton_stats()
    c = s["change"]
    mood = (
        "🟢 <b>TON is pumping!</b>" if c >= 5 else
        "📈 <b>TON is rising steadily.</b>" if c >= 1 else
        "🟡 <b>TON is calm.</b>" if c > -1 else
        "🔻 <b>TON is dipping.</b>" if c > -5 else
        "🔴 <b>TON is crashing!</b>"
    )
    await m.answer(f"{mood}\n\n24h Change: <code>{c:+.2f}%</code>", parse_mode=ParseMode.HTML)


async def auto_post_loop():
    while True:
        try:
            s = await get_ton_stats()
            await bot.send_message(
                TARGET_CHAT_ID,
                format_stats_message(s),
                parse_mode=ParseMode.HTML,
                reply_markup=get_refresh_button()
            )
            logging.info("✅ Auto update sent")
        except Exception as e:
            logging.error(f"❌ Auto post failed: {e}")
        await asyncio.sleep(60)


async def handle_ping(request):
    return web.Response(text="✅ Bot is running")


async def main():
    await bot.delete_webhook(drop_pending_updates=True)
    web_app = web.Application()
    web_app.router.add_get("/", handle_ping)
    runner = web.AppRunner(web_app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", 8080).start()
    asyncio.create_task(auto_post_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
