# Portfolio Management Functions (CRUD Operations)
# Make functions for portfolio management and transaction/trading handling

import sqlite3 as sq
import datetime as dt
import pandas as pd
import yfinance as yf

from src.utils.stock_data import get_batch_prices

def get_portfolio(conn, name):
    """Get portfolio details from table."""
    cur = conn.cursor()
    cur.execute('''
                SELECT * FROM portfolios WHERE name = ?
                ''', (name,)
    )
    result = cur.fetchall()
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


def get_portfolio_balance(conn, portfolio_id):
    """Get portfolio balance from table."""
    cur = conn.cursor()
    cur.execute('''
                SELECT balance FROM balances WHERE portfolio_id = ?
                ''', (portfolio_id,)
    )

    result = cur.fetchone()
    return result[0] if result else None

def update_portfolio_balance(conn, portfolio_id, new_balance, timestamp):
    """Log portfolio balance into Balances table."""
    try:
        cur = conn.cursor()
        cur.execute('''
                    INSERT INTO balances 
                    (portfolio_id, balance, timestamp)
                    VALUES (?, ?, ?)
                    ''', (portfolio_id, new_balance, timestamp)
        )
        conn.commit()
            
    except sq.IntegrityError as e:
        print(f'update_portfolio_balance() error: {e}')

def create_portfolio(conn, name, initial_balance):
    """Create a new portfolio."""

    created_at = dt.now()
    timestamp_str = created_at.strftime('%Y-%m-%d %H:%M:%S')

    cur = conn.cursor()
    try:
        cur.execute('''
                    INSERT INTO portfolios (name, initial_balance, created_at)
                    VALUES (?, ?, ?)
                    ''', (name, initial_balance, timestamp_str)
        )

        portfolio_id = cur.lastrowid

        cur.execute('''
                    INSERT INTO balances (portfolio_id, balance, timestamp)
                    VALUES (?, ?, ?)
                    ''', (portfolio_id, initial_balance, timestamp_str)
        )

        conn.commit()

        return f'Created portfolio {name}:\nCapital ${initial_balance:,.2f}\nCurrency: USD'
    
    except sq.IntegrityError as e:
        print(f'create_portfolio() error: {e}')
        return f'Portfolio {name} already exists.'


def update_portfolio_name(conn, old_name, new_name):
    """Update portfolio name in table."""
    cur = conn.cursor()

    try:
        portfolio_id = get_portfolio_id(conn, old_name)
        if not portfolio_id:
            return f'Portfolio {old_name} does not exist.'
        
        cur.execute('''
                    UPDATE portfolios
                    SET name = ?
                    WHERE portfolio_id = ?
                    ''', (new_name, portfolio_id)
        )
        conn.commit()
        return f'Updated portfolio {old_name} to {new_name}.'

    except sq.IntegrityError as e:
        print(f'update_portfolio_name() error: {e}')
        return f'Portfolio {new_name} already exists.'

def delete_portfolio(conn, name):
    cur = conn.cursor()

    portfolio_id = get_portfolio_id(conn, name)
    if not portfolio_id:
        return 0
    
    cur.execute('''
                DELETE FROM portfolios WHERE portfolio_id = ?
                ''', (portfolio_id,)
    )
    cur.execute('''
                DELETE FROM balances WHERE portfolio_id = ?
                ''', (portfolio_id,)
    )
    conn.commit()

    return 1


def get_holdings(conn, portfolio_id):
    """Get portfolio holdings from table."""
    cur = conn.cursor()

    # get all holdings when first bought and previous sold as initial_value to compare to the total value
    cur.execute('''
                SELECT 
                symbol,
                SUM(CASE WHEN operation = 'BUY' THEN shares ELSE -shares END) AS total_shares,
                SUM(CASE WHEN operation = 'BUY' THEN shares * price_per_share ELSE -(shares * price_per_share) END) AS initial_price
                FROM transactions
                WHERE portfolio_id = ?
                GROUP BY symbol
                HAVING total_shares > 0
                ''', (portfolio_id,)
    )

    results = cur.fetchall()
    return results

def insert_transaction(conn, portfolio_id, symbol, operation, shares, price_per_share, total_price, timestamp):
    """Insert a new transaction into transaction table."""
    cur = conn.cursor()
    cur.execute('''
                INSERT INTO transactions (portfolio_id, symbol, operation, shares, price_per_share, total_price, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (portfolio_id, symbol.upper(), operation, shares, price_per_share, total_price, timestamp)
    )
    conn.commit()


def buy_stock(conn, portfolio_name, symbol, shares):
    """Buy stock shares"""
    portfolio_id = get_portfolio_id(conn, portfolio_name)
    if not portfolio_id:
        return f'portfolio {portfolio_name} not found.'
    
    symbol = symbol.upper()
    operation = 'BUY'

    ticker = yf.Ticker(symbol)

    current_price = ticker.fast_info.last_price
    if not current_price:
        return f'Error retrieving current price for {symbol}.'

    total_price = current_price * float(shares)
    current_time = dt.datetime.now().strftime('%Y-%m-%d %H:%M')

    insert_transaction(conn, portfolio_id, symbol, operation, shares, current_price, total_price, current_time)

    # update portfolio balance to Balances
    new_balance = get_portfolio_balance(conn, portfolio_id) - total_price
    update_portfolio_balance(conn, portfolio_id, new_balance, current_time)

    message = f"""
            Bought {shares} shares of {symbol}.
            Purchase Summary -- {portfolio_name}:
                Operation: BUY
                Total Shares: {shares}
                Price-Per-Share: ${current_price:.2f}
                Total Price: ${total_price:.2f}
                New Balance: ${new_balance:.2f}

                At: {current_time}
    """
    return message

def sell_stock(conn, portfolio_name, symbol, shares):
    """Sell stock shares"""
    portfolio_id = get_portfolio_id(conn, portfolio_name)
    if not portfolio_id:
        return f'portfolio {portfolio_name} not found.'

    symbol = symbol.upper()
    operation = 'SELL'
    ticker = yf.Ticker(symbol)
    current_price = ticker.fast_info.last_price
    total_price = current_price * float(shares)
    current_time = dt.datetime.now().strftime('%Y-%m-%d %H:%M')

    insert_transaction(conn, portfolio_id, symbol, operation, shares, current_price, total_price, current_time)

    new_balance = get_portfolio_balance(conn, portfolio_id) + total_price
    update_portfolio_balance(conn, portfolio_id, new_balance, current_time)

    message = f"""
            Sold {shares} shares of {symbol}.
            Purchase Summary -- {portfolio_name}:
                Operation: SELL
                Total Shares: {shares}
                Price-Per-Share: ${current_price:.2f}
                Total Price: ${total_price:.2f}
                New Balance: ${new_balance:.2f}

                At: {current_time}
    """
    return message


def view_portfolio(conn, name):
    """View current data of a portfolio."""

    portfolio_id = get_portfolio_id(conn, name)
    if not portfolio_id:
        return f"Portfolio '{name}' not found."
    
    balance = get_portfolio_balance(conn, portfolio_id)
    holdings = get_holdings(conn, portfolio_id)

    symbols = [row[0].upper() for row in holdings]
    current_prices = get_batch_prices(symbols)

    holdings_str = ''
    holdings_value = 0

    if holdings:
        for symbol, shares, initial_value in holdings:
            price = current_prices.get(symbol, 0)

            if price:
                stock_value = price * shares
                holdings_value += stock_value
                returns = stock_value - initial_value
                returns_pc = (returns / initial_value) * 100
                change_sign = '+' if returns >= 0 else ''

                holdings_str += f'''{symbol}: Shares = {shares} | Stock Price = ${price:.2f} 
                                Initial Value = ${initial_value:.2f} | Total Value = ${stock_value:.2f} | Returns = {change_sign}${returns:.2f} ({change_sign}{returns_pc:.2f}%)\n
                            '''
            else:
                holdings_str += f'    {symbol}: Shares = {shares} | Initial Value = ${initial_value:.2f} (Current price unavailable.)\n'    
    else:
        holdings_str += 'No holdings in this portfolio.'

    result = f"""
            Portfolio Summary: {name}
                Balance: ${balance:,.2f}
                Total Holdings Value: ${holdings_value:,.2f}
                Total Value: ${balance + holdings_value:,.2f}

            Current Holdings:
            {holdings_str}
            """.rstrip()

def list_portfolios(conn):
    """List all portfolios."""

    cur = conn.cursor()
    cur.execute('''
                SELECT p.name, b.balance FROM balances b
                JOIN portfolios p ON b.portfolio_id = p.portfolio_id
                ''')
    portfolios =  cur.fetchall()

    if not portfolios:
        return 'No portfolios found.'
    
    result = 'Portfolios:\n'
    for name, balance in portfolios:
        result += f"    {name}: Balance ${balance:,.2f}\n"

    return result
