import os
from dotenv import load_dotenv

# --- .env & Tokens ---
load_dotenv()
discord_token = os.getenv("DISCORD_TOKEN")

# --- Channel ID & Stock Symbols ---
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
STOCK_FILE = 'watchlist.json'

last_checked_prices = {}
sp500_last_checked_prices = {}