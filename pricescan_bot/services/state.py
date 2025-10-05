import logging
from typing import Dict, Set

logger = logging.getLogger(__name__)

_wait_mode: Dict[int, str] = {}
_multi_selected: Dict[int, Set[int]] = {}


def set_wait_mode(user_id: int, mode: str) -> None:
    """Устанавливает режим ожидания для пользователя"""
    if not mode:
        logger.warning(f"Empty wait mode for user {user_id}")
        return

    _wait_mode[user_id] = mode
    logger.debug(f"Set wait mode for user {user_id}: {mode}")


def get_wait_mode(user_id: int) -> str | None:
    """Получает текущий режим ожидания пользователя"""
    mode = _wait_mode.get(user_id)
    logger.debug(f"Get wait mode for user {user_id}: {mode}")
    return mode


def clear_wait_mode(user_id: int) -> None:
    """Очищает режим ожидания для пользователя"""
    if user_id in _wait_mode:
        mode = _wait_mode.pop(user_id)
        logger.debug(f"Cleared wait mode for user {user_id}: {mode}")
    else:
        logger.debug(f"No wait mode to clear for user {user_id}")


def toggle_multi_selected(user_id: int, item_id: int) -> set[int]:
    """Переключает выбор элемента в множественном выборе"""
    selected_items = _multi_selected.setdefault(user_id, set())

    if item_id in selected_items:
        selected_items.remove(item_id)
        logger.debug(f"Removed item {item_id} from selection for user {user_id}")
    else:
        selected_items.add(item_id)
        logger.debug(f"Added item {item_id} to selection for user {user_id}")

    return selected_items


def get_selected_ids(user_id: int) -> list[int]:
    """Получает список выбранных элементов для пользователя"""
    selected_ids = list(_multi_selected.get(user_id, set()))
    logger.debug(f"Get selected items for user {user_id}: {len(selected_ids)} items")
    return selected_ids


def clear_multi(user_id: int) -> None:
    """Очищает множественный выбор для пользователя"""
    if user_id in _multi_selected:
        count = len(_multi_selected[user_id])
        _multi_selected.pop(user_id)
        logger.debug(f"Cleared {count} selected items for user {user_id}")
    else:
        logger.debug(f"No selection to clear for user {user_id}")


def get_state_info(user_id: int) -> dict:
    """Получает информацию о состоянии пользователя для отладки"""
    return {
        "wait_mode": _wait_mode.get(user_id),
        "selected_count": len(_multi_selected.get(user_id, set())),
        "selected_items": list(_multi_selected.get(user_id, set())),
    }
