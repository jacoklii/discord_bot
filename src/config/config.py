import os
import pytz
import datetime as dt
from dotenv import load_dotenv

# --- .env & Tokens ---
load_dotenv()
discord_token = os.getenv("DISCORD_TOKEN")

# --- Discord ---
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
STOCK_FILE = 'src/config/watchlist.json'
TIMEZONE = pytz.timezone('US/Eastern')
TIME_NOW = dt.datetime.now(TIMEZONE)

last_checked_prices = {}
sp500_last_checked_prices = {}

# --- Database ---
DB_DIR = 'src/portfolios/database'
PORTFOLIO_DB_DIR = os.path.join(DB_DIR, 'portfolios.db')

os.makedirs(DB_DIR, exist_ok=True)

import sqlite3 as sq
from src.config.config import PORTFOLIO_DB_DIR

def get_portfolio_connection():
    """Create a database connection to the portfolio database."""

    return sq.connect(PORTFOLIO_DB_DIR)
