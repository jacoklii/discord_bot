# Database needs
# - stock history logging
# - stock metadata and watchlist management

# reduce API rate limiting/calls, to call directally from the database
import datetime as dt
import yfinance as yf
import sqlite3 as sq

import sys 
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))
from src.config.storage import STOCK_SYMBOLS


def setup_database():
    db_path = Path(__file__).resolve().parent / 'watchlist_history.db'
    conn = sq.connect(str(db_path))
    cur = conn.cursor()

    cur.execute('''
        CREATE TABLE IF NOT EXISTS stock_history (
            id INTEGER PRIMARY KEY,
            symbol TEXT NOT NULL,
            open REAL NOT NULL,
            close REAL NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    return conn

def log_stock_history(conn, symbol, open, close, timestamp):
    """
    Log stock history to a database.
    Args:
        conn: Database connection
        symbol: Stock symbol
        open: Opening price
        close: Closing Price
        timestamp: Time/date of the interval
    Returns:
        Row(s): Logging a stock's data to a database.
    """
    cur = conn.cursor()
    try:
        # Convert pandas Timestamp to string format that SQLite can handle
        timestamp_str = timestamp.strftime('%Y-%m-%d %H:%M:%S')
        cur.execute('''
            INSERT INTO stock_history (symbol, open, close, timestamp)
                    VALUES (?, ?, ?, ?)
            ''', (symbol, open, close, timestamp_str))
        conn.commit()
    except sq.IntegrityError as e:
        print(f"Error logging stock data: {e}")

def get_latest_timestamp_for_symbol(conn, symbol):
    """
    Get the latest timestamp for a given symbol in the database.
    Args:
        conn: Database connection
        symbol: Stock symbol  
    Returns:
        datetime.date or None: Latest date in database for the symbol, or None if no data exists
    """
    cur = conn.cursor()
    cur.execute('''
        SELECT MAX(timestamp) FROM stock_history WHERE symbol = ?
    ''', (symbol,))
    result = cur.fetchone()
    
    if result and result[0]:
        # Parse the timestamp string back to a date object
        return dt.datetime.strptime(result[0], '%Y-%m-%d %H:%M:%S').date()
    return None

def backfill_all_stocks(conn):
    """
    Backfill stock history, adding only new data since the last recorded entry.
    Fetches 2 years of history but only inserts rows that don't already exist.
    """
    for symbol in STOCK_SYMBOLS:
        try:
            # Get the latest date we have for this symbol
            latest_date = get_latest_timestamp_for_symbol(conn, symbol)
            
            ticker = yf.Ticker(symbol)
            history = ticker.history(period='2y', interval='1d')
            
            added_count = 0
            for index, row in history.iterrows():
                # Only add if this date is newer than what we have
                if latest_date is None or index.date() > latest_date:
                    log_stock_history(conn, symbol, row['Open'], row['Close'], index)
                    added_count += 1
            
            if added_count > 0:
                print(f'Backfilled {symbol}: Added {added_count} new entries.')
            else:
                print(f'Backfilled {symbol}: No new data to add.')
        except Exception as e:
            print(f'Error backfilling {symbol}: {e}')


if __name__ == "__main__":
    conn = setup_database()

    backfill_all_stocks(conn)

    conn.close()