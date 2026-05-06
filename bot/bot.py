"""
bot.py — Asosiy Telegram Bot fayli

Bu fayl botni ishga tushiradi va barcha handler'larni ro'yxatga oladi.

Ishga tushirish: python bot.py
"""

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

import database as db

# Handler'larni import qilish
from handlers import registration, learning, quiz, shop, admin, subscription, ai_chat


BOT_TOKEN = os.getenv("TOKEN") 

# Logging sozlash — botning ish jarayonini konsolda ko'rish uchun
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def on_startup(bot: Bot):
    """
    Bot ishga tushganda bajariladigan amallar.
    1. Ma'lumotlar bazasi jadvallarini yaratish
    2. Admin(lar)ga xabar yuborish
    """
    db.create_tables()
    logger.info("✅ Ma'lumotlar bazasi tayyorlandi.")

    # Adminlarga bot ishga tushgani haqida xabar
    from config import ADMIN_IDS
    for admin_id in ADMIN_IDS:
        try:
            await bot.send_message(
                admin_id,
                "🚀 <b>Bot ishga tushdi!</b>\n"
                "Admin panel: /admin",
                parse_mode="HTML"
            )
        except Exception as e:
            logger.warning(f"Admin {admin_id} ga xabar yuborib bo'lmadi: {e}")


async def on_shutdown(bot: Bot):
    """Bot to'xtaganda bajariladigan amallar."""
    logger.info("🛑 Bot to'xtatildi.")




async def main():
    """
    Asosiy funksiya — botni sozlash va ishga tushirish.
    """
    # 2. Token mavjudligini tekshirish (Xatolikni oldini olish uchun)
    if not BOT_TOKEN:
        logger.error("❌ BOT_TOKEN topilmadi! Railway Variables bo'limini tekshiring.")
        return

    # Bot obyekti yaratish
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    # Dispatcher — barcha handler'larni boshqaruvchi
    dp = Dispatcher()

    # Ishga tushish va to'xtash signallarini ulash
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Handler'larni router sifatida ro'yxatga olish
    dp.include_router(registration.router)
    dp.include_router(learning.router)
    dp.include_router(quiz.router)
    dp.include_router(shop.router)
    dp.include_router(admin.router)
    dp.include_router(subscription.router)
    dp.include_router(ai_chat.router)

    logger.info("🤖 Bot ishga tushmoqda...")

    # Polling
    await dp.start_polling(bot, skip_updates=True)


if __name__ == "__main__":
    asyncio.run(main())
