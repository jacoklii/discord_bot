# Portfolio Management Functions (CRUD Operations)
# Make functions for portfolio management and transaction/trading handling

import sqlite3 as sq
import datetime as dt
import pandas as pd
import yfinance as yf

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
                ORDER BY balance_id DESC LIMIT 1
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
                sector,
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

def get_symbols(conn, portfolio_id):
    """Get a list of all symbols in a portfolio."""
    cur = conn.cursor()
    cur.execute('''
                SELECT DISTINCT symbol, price_per_share FROM transactions
                WHERE portfolio_id = ?
                ''', (portfolio_id,)
    )

    results = cur.fetchall()
    return results

def insert_transaction(conn, portfolio_id, symbol, sector, operation, shares, price_per_share, total_price, timestamp):
    """Insert a new transaction into transaction table."""
    cur = conn.cursor()
    cur.execute('''
                INSERT INTO transactions (portfolio_id, symbol, sector, operation, shares, price_per_share, total_price, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (portfolio_id, symbol.upper(), sector, operation, shares, price_per_share, total_price, timestamp)
    )
    conn.commit()
