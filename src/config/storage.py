import json
from src.config.config import STOCK_FILE

# --- file management for stocks ---
def load_stocks():
    """
    Load watchlist symbols from the persistent JSON file.

    Returns:
        list: List of stock symbol strings loaded from `watchlist.json`.
              If the file does not exist, an empty list is returned and
              an empty watchlist file is created.
    """
    try:
        with open(STOCK_FILE, 'r') as f:
            data = json.load(f)
            return data.get('symbols', [])
    except FileNotFoundError:
        save_stocks([])
        return []

def save_stocks(stocks):
    """
    Persist the provided list of stock symbols to the watchlist JSON file.

    Args:
        stocks (list): List of stock symbol strings to save to disk.
    """
    with open(STOCK_FILE, 'w') as f:
        json.dump({'symbols': stocks}, f, indent=2)

STOCK_SYMBOLS = load_stocks()