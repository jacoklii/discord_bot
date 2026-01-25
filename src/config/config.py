import os
import pytz
import datetime as dt
from dotenv import load_dotenv

# --- .env & Tokens ---
load_dotenv()
discord_token = os.getenv("DISCORD_TOKEN")

# --- Config ---
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
STOCK_FILE = 'watchlist.json'
TIMEZONE = pytz.timezone('US/Eastern')
TIME_NOW = dt.datetime.now(TIMEZONE)

last_checked_prices = {}
sp500_last_checked_prices = {}