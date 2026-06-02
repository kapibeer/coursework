from aiogram import Bot
from aiogram.client.session.aiohttp import AiohttpSession

from infrastructure.config.settings import Settings


def build_bot(settings: Settings) -> Bot:
    session = None
    if settings.bot_proxy_url:
        session = AiohttpSession(proxy=settings.bot_proxy_url)
    return Bot(token=settings.bot_token, session=session)
