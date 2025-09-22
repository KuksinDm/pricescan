import asyncio
import logging

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def main():
    """Главная функция"""
    print("🎲 PriceScan Parser для HobbyGames.ru")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
