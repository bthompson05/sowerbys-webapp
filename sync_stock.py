"""Daily Render entry point: python -u sync_stock.py (does not import Flask)."""
import logging
import os
import tempfile

from modules.ShopifyResources import ShopifyResources


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    required = ("API-Url", "X-Shopify-Access-Token", "UKDLocationID")
    missing = [name for name in required if not os.environ.get(name)]
    if missing:
        logging.error("Missing environment variables: %s", ", ".join(missing))
        return 1
    # Each run starts with fresh feeds and exports, never repository-cached stock.
    previous_directory = os.getcwd()
    try:
        with tempfile.TemporaryDirectory(prefix="ukd-sync-") as directory:
            os.chdir(directory)
            logging.info("Starting daily UKD stock sync")
            result = ShopifyResources().UKDStockUpdate()
            logging.info("Stock sync succeeded: %s", result)
        return 0
    except Exception:
        logging.exception("Stock sync failed")
        return 1
    finally:
        os.chdir(previous_directory)


if __name__ == "__main__":
    raise SystemExit(main())
