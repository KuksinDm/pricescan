import logging

from aiogram.types import Message

from ..api import ApiClient

logger = logging.getLogger(__name__)


async def ensure_jwt(message: Message, api: ApiClient) -> None:
    user = message.from_user
    if not user:
        logger.warning("Message without user in ensure_jwt")
        return

    try:
        await api.ensure_jwt(
            telegram_id=user.id,
            telegram_username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code,
        )
        logger.debug(f"JWT ensured for user {user.id}")
    except Exception as e:
        logger.exception(f"Failed to ensure JWT for user {user.id}: {e}")
        raise
