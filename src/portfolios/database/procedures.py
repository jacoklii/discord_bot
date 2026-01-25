# Portfolio Management Functions (CRUD Operations)
# Make functions for portfolio management and transaction/trading handling?

import sqlite3 as sq
from datetime import datetime as dt
import pandas as pd
import yfinance as yf


def create_portfolio(conn, name, initial_balance):
    """Create a new portfolio."""

    created_at = dt.now()
    timestamp_str = created_at.strftime('%Y-%m-%d %H:%M:%S')

    cur = conn.cursor()
    try:
        cur.execute('''
                    INSERT INTO portfolios (name, balance, created_at)
                    VALUES (?, ?, ?)
                    ''', (name, initial_balance, timestamp_str)
        )
        conn.commit()
        return f'Created portfolio {name}:\nCapital ${initial_balance:,.2f}\nCurrency: USD'
    
    except sq.IntegrityError as e:
        return f'Portfolio {name} already exists: {e}'

def get_portfolio(conn, name):
    """Get portfolio details from table."""
    cur = conn.cursor()
    cur.execute('''
                SELECT * FROM portfolios WHERE name = ?
                ''', (name,)
    )
    result = cur.fetchone()
    return result[0] if result else None

def get_portfolio_id(conn, name):
    """Get portfolio ID from table."""
    cur = conn.cursor()
    cur.execute('''
                SELECT portfolio_id FROM portfolios WHERE name = ?
                ''', (name,)
    )
    result = cur.fetchone()
    return result[0] if result else None

def update_portfolio_name(conn, portfolio_id, new_name):
    """Update portfolio name in table."""
    cur = conn.cursor()
    cur.execute('''
                UPDATE portfolios
                SET name = ?
                WHERE portfolio_id = ?
                ''', (new_name, portfolio_id)
    )
    conn.commit()

def delete_portfolio(conn, name):
    cur = conn.cursor()
    cur.execute('''
                DELETE FROM portfolios WHERE name = ?
                ''', (name,)
    )
    conn.commit()


def get_holdings(conn, portfolio_id):
    """Get portfolio holdings from table."""
    cur = conn.cursor()
    cur.execute('''
                SELECT symbol, total_shares, (total_shares * price_per_share) AS initial_value
                FROM (
                    SELECT symbol,
                    SUM(CASE WHEN operation = 'BUY' THEN shares ELSE -shares END) AS total_shares
                    FROM transactions)
                )
                WHERE portfolio_id = ?
                GROUP BY symbol
                HAVING total_shares > 0
                ''', (portfolio_id,)
    )

def insert_transaction(conn, portfolio_id, symbol, operation, shares, price_per_share, total_price, timestamp):
    """Insert a new transaction into transaction table."""
    cur = conn.cursor()
    cur.execute('''
                INSERT INTO transactions (portfolio_id, symbol, operation, shares, price_per_share, total_price, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (portfolio_id, symbol, operation, shares, price_per_share, total_price, timestamp)
    )
    conn.commit()

    
def get_portfolio_balance(conn, name):
    """Get portfolio balance from table."""
    cur = conn.cursor()
    cur.execute('''
                SELECT balance FROM balances WHERE portfolio_id = ?
                ''', (get_portfolio_id(conn, name),)
    )
    result = cur.fetchone()
    return result[0] if result else None

def update_portfolio_balance(conn, portfolio_id, new_balance):
    """Update portfolio balance in table."""
    cur = conn.cursor()
    cur.execute('''
                UPDATE balances
                SET balance = ?
                WHERE portfolio_id = ?
                ''', (new_balance, portfolio_id)
    )
    conn.commit()


def buy_stock(conn, portfolio_name, symbol, shares):
    """Buy stock shares"""
    portfolio_id = get_portfolio_id(conn, portfolio_name)
    if not portfolio_id:
        return f'portfolio {portfolio_name} not found.'

    operation = 'BUY'
    ticker = yf.Ticker(symbol)
    current_price = ticker.fast_info.last_price
    if not current_price:
        return f'Error retrieving current price for {symbol}.'
    
    total_price = current_price * shares
    current_time = dt.datetime.now().strftime('%Y-%m-%d %H:%M')

    insert_transaction(conn, portfolio_id, symbol, operation, shares, current_price, total_price, current_time)

    new_balance = get_portfolio_balance(conn, portfolio_id) - total_price
    update_portfolio_balance(conn, portfolio_id, new_balance)

def sell_stock(conn, portfolio_name, symbol, shares):
    """Sell stock shares"""
    portfolio_id = get_portfolio_id(conn, portfolio_name)
    if not portfolio_id:
        return f'portfolio {portfolio_name} not found.'

    operation = 'SELL'
    ticker = yf.Ticker(symbol)
    current_price = ticker.fast_info.last_price
    total_price = current_price * shares
    current_time = dt.datetime.now().strftime('%Y-%m-%d %H:%M')

    insert_transaction(conn, portfolio_id, symbol, operation, shares, current_price, total_price, current_time)

    new_balance = get_portfolio_balance(conn, portfolio_id) + total_price
    update_portfolio_balance(conn, portfolio_id, new_balance)

# def get_portfolio_value(conn, portfolio_name):
#     """Calculate total portfolio value (balance + holdings)"""
#     portfolio_id = get_portfolio_id(conn, portfolio_name)
#     if not portfolio_id:
#         return None

#     balance = get_portfolio_balance(conn, portfolio_id)
#     holdings = get_holdings(conn, portfolio_id)
    

def view_portfolio(conn, name):
    result = ''

    portfolio_id = get_portfolio_id(conn, name)
    if not portfolio_id:
        return f"Portfolio '{name}' not found."
    
    balance = get_portfolio_balance(conn, portfolio_id)
    holdings = get_holdings(conn, portfolio_id)

    result += f'Portfolio: {name}\nBalance: ${balance:,.2f}\n'
    if holdings:
        result += f'Holdings:\n'
        for symbol, shares, initial_value in holdings.items():
            try:
                ticker = yf.Ticker(symbol)
                price = float(ticker.fast_info.last_price)
                total_value = price * shares
                result += f'  {symbol}: Shares = {shares} Stock Price = ${price:.2f} Initial Value = ${initial_value:.2f} Total Value = ${total_value:.2f}\n'
            except:
                result += f'  {symbol}: Shares = {shares} Initial Value = ${initial_value:.2f} (Current price unavailable.)'
    else:
        result += 'No holdings in this portfolio.\n'
    
    return result

def list_portfolios(conn):
    """List all portfolios."""
    result = ''

    cur = conn.cursor()
    cur.execute('''
                SELECT name, balance, created_at FROM portfolios
                ''')
    portfolios =  cur.fetchall()

    if not portfolios:
        return 'No portfolios found.'
    
    result += 'Portfolios:\n'
    for name, balance in portfolios:
        result += f"    {name}: Balance ${balance:,.2f}"

    return result
