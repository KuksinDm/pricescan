#!/usr/bin/env python3
"""
Скрипт для запуска парсера mosigra.ru с различными настройками
"""

import argparse
import asyncio

from playwright.async_api import async_playwright

from main import MosigraParser


async def run_parser_with_config(
    max_pages: int, max_products: int, retries: int, delay: int, headless: bool
):
    """Запуск парсера с заданными параметрами"""
    print("Настройки парсера:")
    print(f"  Максимум страниц: {max_pages}")
    print(f"  Максимум товаров: {max_products}")
    print(f"  Количество повторов: {retries}")
    print(f"  Задержка между повторами: {delay} сек")
    print(f"  Режим браузера: {'headless' if headless else 'с интерфейсом'}")
    print("-" * 50)

    parser = MosigraParser(max_retries=retries, retry_delay=delay)

    # Модифицируем запуск браузера для headless режима
    if headless:

        async def start_browser_headless():
            parser.playwright = await async_playwright().start()
            browser = await parser.playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_viewport_size({"width": 1920, "height": 1080})
            return browser, page

        parser.start_browser = start_browser_headless

    try:
        await parser.run(max_pages=max_pages, max_products=max_products)
        parser.save_results()

        stats = parser.get_statistics()

        print(f"\n{'=' * 50}")
        print("РЕЗУЛЬТАТЫ ПАРСИНГА")
        print(f"{'=' * 50}")
        print(f"Успешно спаршено: {stats['total_products']} товаров")
        print(f"Неудачных попыток: {stats['failed_urls']}")
        print(f"Процент успеха: {stats['success_rate']}%")
        print("Полнота данных:")
        print(f"  - С ценой: {stats['products_with_price']}/{stats['total_products']}")
        print(
            f"  - С производителем: "
            f"{stats['products_with_manufacturer']}/{stats['total_products']}"
        )
        print(f"  - С годом: {stats['products_with_year']}/{stats['total_products']}")
        print(
            f"  - С описанием: "
            f"{stats['products_with_description']}/{stats['total_products']}"
        )

    except KeyboardInterrupt:
        print("\nПарсинг прерван пользователем")
        parser.save_results()
    except Exception as e:
        print(f"Ошибка: {e}")
        parser.save_results()


def main():
    parser = argparse.ArgumentParser(description="Парсер настольных игр mosigra.ru")

    parser.add_argument(
        "--pages",
        "-p",
        type=int,
        default=2,
        help="Максимальное количество страниц для парсинга (по умолчанию: 2)",
    )

    parser.add_argument(
        "--products",
        "-n",
        type=int,
        default=20,
        help="Максимальное количество товаров для парсинга (по умолчанию: 20)",
    )

    parser.add_argument(
        "--retries",
        "-r",
        type=int,
        default=3,
        help="Количество повторных попыток при ошибке (по умолчанию: 3)",
    )

    parser.add_argument(
        "--delay",
        "-d",
        type=int,
        default=2,
        help="Задержка между повторными попытками в секундах (по умолчанию: 2)",
    )

    parser.add_argument(
        "--headless",
        action="store_true",
        help="Запустить браузер в headless режиме (без интерфейса)",
    )

    # Предустановленные конфигурации
    parser.add_argument(
        "--quick", action="store_true", help="Быстрый тест (1 страница, 5 товаров)"
    )

    parser.add_argument(
        "--full", action="store_true", help="Полный парсинг (10 страниц, 500 товаров)"
    )

    args = parser.parse_args()

    # Применяем предустановленные конфигурации
    if args.quick:
        max_pages, max_products = 1, 5
    elif args.full:
        max_pages, max_products = 10, 500
    else:
        max_pages, max_products = args.pages, args.products

    asyncio.run(
        run_parser_with_config(
            max_pages=max_pages,
            max_products=max_products,
            retries=args.retries,
            delay=args.delay,
            headless=args.headless,
        )
    )


if __name__ == "__main__":
    main()
