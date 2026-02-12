import json
from src.config.config import STOCK_FILE, PORTFOLIO_FILE

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


def load_portfolio():
    """Load portfolio for portfolio specific tasks from a stored file."""
    try:
        with open(PORTFOLIO_FILE, 'r') as f:
            data = json.load(f)
            portfolio = data.get('registered_portfolio')
            if isinstance(portfolio, list):
                return portfolio[0] if portfolio else None
            return portfolio if portfolio else None
    except FileNotFoundError:
        save_portfolio(None)
        return None
    
def save_portfolio(portfolio_name):
    """
    Save and register a portfolio name for portfolio tasks.
    Only one name is stored, otherwise overwrite the existing name.
    
    :param portfolio_name: desired portfolio name
    """
    with open(PORTFOLIO_FILE, 'w') as f:
        json.dump({'registered_portfolio': portfolio_name}, f, indent=2)
