# pricescan_bot/services/state.py
from typing import Dict, Set

_wait_mode: Dict[int, str] = {}
_multi_selected: Dict[int, Set[int]] = {}


def set_wait_mode(user_id: int, mode: str) -> None:
    _wait_mode[user_id] = mode


def get_wait_mode(user_id: int) -> str | None:
    return _wait_mode.get(user_id)


def clear_wait_mode(user_id: int) -> None:
    _wait_mode.pop(user_id, None)


def toggle_multi_selected(user_id: int, item_id: int) -> set[int]:
    s = _multi_selected.setdefault(user_id, set())
    if item_id in s: s.remove(item_id)
    else: s.add(item_id)
    return s


def get_selected_ids(user_id: int) -> list[int]:
    return list(_multi_selected.get(user_id, set()))


def clear_multi(user_id: int) -> None:
    _multi_selected.pop(user_id, None)
