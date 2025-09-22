import argparse
import json
import sys

from .client import HttpClient
from .parse_category import parse_category_page
from .parse_product import parse_product_page


def run() -> int:
    parser = argparse.ArgumentParser(description="Парсер категории HobbyGames")
    parser.add_argument(
        "url", help="URL категории, напр. https://hobbygames.ru/nastolnie"
    )
    parser.add_argument(
        "-p", "--pages", type=int, default=1, help="Сколько страниц парсить"
    )
    parser.add_argument(
        "--deep",
        action="store_true",
        help="Заходить в карточки и вытягивать подробности",
    )
    parser.add_argument(
        "-o",
        "--output",
        help="Файл для сохранения JSON (по умолчанию вывод в консоль)",
    )
    args = parser.parse_args()

    client = HttpClient()

    items = []
    for page in range(1, args.pages + 1):
        page_url = args.url if page == 1 else f"{args.url}?PAGEN_1={page}"
        html = client.get_text(page_url)
        page_items = parse_category_page(html, page_url)
        if not args.deep:
            items.extend(page_items)
            continue

        for it in page_items:
            try:
                prod_html = client.get_text(it["url"])
            except Exception:
                items.append(it)
                continue
            details = parse_product_page(prod_html, it["url"])
            merged = {**it, **{k: v for k, v in details.items() if v is not None}}
            items.append(merged)

    json_str = json.dumps(items, ensure_ascii=False, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(json_str)
        print(f"Сохранено {len(items)} товаров в {args.output}")
    else:
        print(json_str)

    return 0


if __name__ == "__main__":
    sys.exit(run())
