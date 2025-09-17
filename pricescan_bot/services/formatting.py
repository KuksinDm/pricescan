def fmt_dt_iso(ts: str | None) -> str:
    if not ts:
        return "-"
    ts = ts.replace("Z", "+00:00")
    return ts.replace("T", " ")[:16]  # YYYY-MM-DD HH:MM


def format_offer_text(o: dict) -> str:
    return (
        f"Игра: {o['product_title']}\n"
        f"Автор: {o.get('product_author') or '-'} | Издатель: {o.get('product_publisher') or '-'}\n"
        f"Категория: {o.get('product_category') or '-'}\n"
        f"Игроки: {o.get('min_players') or '?'}–{o.get('max_players') or '?'} | "
        f"Время: {o.get('playtime_min') or '?'} мин | Возраст: {o.get('min_age') or '?'}+\n"
        f"Цена: {o['price']} {o['currency']} | Магазин: {o['shop']['name']}\n"
        f"\n{(o.get('description') or '')[:400]}"
    )
