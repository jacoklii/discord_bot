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
PORTFOLIO_FILE = 'src/config/portfolio.json'
TIMEZONE = pytz.timezone('US/Eastern')
TIME_NOW = dt.datetime.now(TIMEZONE)

last_checked_prices = {}
sp500_last_checked_prices = {}
