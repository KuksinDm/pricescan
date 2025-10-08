import logging
import os
import sys

from .app import run, run_api, run_polling
from .logging_config import setup_logging

logger = logging.getLogger(__name__)


def main():
    setup_logging(
        log_dir=os.path.join(os.getcwd(), "logs"),
        level=os.getenv("BOT_LOG_LEVEL", "INFO"),
    )

    logger.info("Starting PriceScan bot...")

    try:
        if len(sys.argv) > 1:
            mode = sys.argv[1]
            logger.info(f"Starting in {mode} mode")

            if mode == "polling":
                run_polling()
            elif mode == "api":
                host = sys.argv[2] if len(sys.argv) > 2 else "0.0.0.0"
                port = int(sys.argv[3]) if len(sys.argv) > 3 else 8000
                logger.info(f"Starting API server on {host}:{port}")
                run_api(host, port)
            else:
                logger.error(f"Unknown mode: {mode}")
                print("Usage: python -m pricescan_bot [polling|api [host] [port]]")
                sys.exit(1)
        else:
            logger.info("No mode specified, starting in default API mode")
            run()

    except KeyboardInterrupt:
        logger.info("Bot stopped by user (Ctrl+C)")
        sys.exit(0)
    except Exception as e:
        logger.exception("Failed to start bot: %s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
