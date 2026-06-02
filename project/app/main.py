import asyncio
import logging

from app.bootstrap import create_app
from infrastructure.config.settings import Settings


async def main() -> None:
    settings = Settings()
    logging.basicConfig(level=settings.bot_log_level)

    bot, dispatcher, container = create_app(settings)
    await container.database.connect()

    try:
        await dispatcher.start_polling(bot)
    finally:
        await container.database.dispose()


if __name__ == "__main__":
    asyncio.run(main())

