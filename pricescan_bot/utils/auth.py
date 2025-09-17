from aiogram.types import Message

from ..api import ApiClient


async def ensure_jwt(message: Message, api: ApiClient) -> None:
    user = message.from_user
    if not user:
        return
    await api.ensure_jwt(
        telegram_id=user.id,
        telegram_username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
    )
