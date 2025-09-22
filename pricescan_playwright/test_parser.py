#!/usr/bin/env python3
"""
Тестовый скрипт для проверки парсера mosigra.ru
"""

import asyncio
import sys

from main import MosigraParser


async def test_parser():
    """Тестируем парсер с минимальными настройками"""
    print("🧪 Запуск тестирования парсера...")

    parser = MosigraParser(max_retries=2, retry_delay=1)

    try:
        # Тестируем только первую страницу с 3 товарами
        await parser.run(max_pages=1, max_products=3)

        # Выводим результаты
        stats = parser.get_statistics()

        print(f"\n{'=' * 40}")
        print("РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
        print(f"{'=' * 40}")

        if stats["total_products"] > 0:
            print(f"✅ Успешно! Найдено {stats['total_products']} товаров")

            # Показываем первый товар
            if parser.products:
                product = parser.products[0]
                print("\nПример товара:")
                print(f"  📦 Название: {product.title}")
                print(f"  🔗 URL: {product.url}")
                print(
                    f"  💰 Цена: {product.price_rub} руб."
                    if product.price_rub
                    else "  💰 Цена: не найдена"
                )
                print(
                    f"  🏭 Производитель: {product.manufacturer}"
                    if product.manufacturer
                    else "  🏭 Производитель: не найден"
                )

        else:
            print("❌ Товары не найдены")
            print("Возможные причины:")
            print("  - Сайт изменил структуру")
            print("  - Блокировка по IP")
            print("  - Проблемы с интернетом")

            if parser.failed_urls:
                print(f"\nНеудачные URL ({len(parser.failed_urls)}):")
                for url in parser.failed_urls[:3]:
                    print(f"  - {url}")

        # Сохраняем результаты
        parser.save_results("test_results.json")
        print("\nРезультаты сохранены в test_results.json")

    except KeyboardInterrupt:
        print("\n⚠️ Тестирование прервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка при тестировании: {e}")
    finally:
        print("\n🏁 Тестирование завершено")


if __name__ == "__main__":
    try:
        asyncio.run(test_parser())
    except KeyboardInterrupt:
        print("\nВыход...")
        sys.exit(0)
