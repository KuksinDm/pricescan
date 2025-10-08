import logging

from ..constants import DEFAULT_CURRENCY

logger = logging.getLogger(__name__)


def parse_callback_offset(data: str) -> int:
    try:
        return int(data.split(":")[1])
    except (IndexError, ValueError) as e:
        logger.error(f"Invalid offset in callback data: {data}, error: {e}")
        return 0


def parse_callback_product_id(data: str) -> int:
    try:
        return int(data.split(":")[1])
    except (IndexError, ValueError) as e:
        logger.error(f"Invalid product ID in callback data: {data}, error: {e}")
        raise ValueError(f"Invalid product ID: {data}")


def parse_callback_alert_id(data: str) -> int:
    try:
        return int(data.split(":")[1])
    except (IndexError, ValueError) as e:
        logger.error(f"Invalid alert ID in callback data: {data}, error: {e}")
        raise ValueError(f"Invalid alert ID: {data}")


def parse_callback_favorite_id(data: str) -> int:
    try:
        return int(data.split(":")[1])
    except (IndexError, ValueError) as e:
        logger.error(f"Invalid favorite ID in callback data: {data}, error: {e}")
        raise ValueError(f"Invalid favorite ID: {data}")


def parse_alert_new_data(data: str) -> tuple[int, str]:
    try:
        parts = data.split(":")
        if len(parts) < 3:
            raise ValueError("Insufficient parts in alert-new data")

        product_id = int(parts[1])
        currency = parts[2] if len(parts) > 2 else DEFAULT_CURRENCY

        return product_id, currency
    except (IndexError, ValueError) as e:
        logger.error(f"Invalid alert-new data: {data}, error: {e}")
        raise ValueError(f"Invalid alert-new data: {data}")
