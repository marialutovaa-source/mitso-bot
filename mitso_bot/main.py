import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN, SUPER_ADMIN_IDS
from db.models import init_db
from db.queries import set_user_role
from handlers.common  import router as common_router
from handlers.admin   import router as admin_router
from handlers.starost import router as starost_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())

    dp.include_router(common_router)
    dp.include_router(admin_router)
    dp.include_router(starost_router)

    logger.info("Инициализация базы данных...")
    await init_db()

    for admin_id in SUPER_ADMIN_IDS:
        await set_user_role(admin_id, "superadmin")
        logger.info(f"Суперадмин: {admin_id}")

    logger.info("Бот запущен.")
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
    asyncio.run(main())
