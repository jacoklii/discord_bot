# portfolio functions to be used by discord bot commands.

import pandas as pd
import yfinance as yf
import sqlite3 as sq
import datetime as dt

from collections import defaultdict

from src.portfolios.database.procedures import get_portfolio_id, get_portfolio_balance, update_portfolio_balance, insert_transaction, get_holdings
from src.stock_data import get_batch_prices

def buy_stock(conn, portfolio_name, symbol, shares):
    """Buy stock shares"""
    portfolio_id = get_portfolio_id(conn, portfolio_name)
    if not portfolio_id:
        return f'portfolio {portfolio_name} not found.'
    
    symbol = symbol.upper()

    ticker = yf.Ticker(symbol)

    sector = ticker.info['sector'] if ticker.info and 'sector' in ticker.info else 'N/A'

    current_price = ticker.fast_info.last_price
    if not current_price:
        return f'Error retrieving current price for {symbol}.'

    total_price = current_price * float(shares)
    current_time = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    operation = 'BUY'

    insert_transaction(conn, portfolio_id, symbol, sector,operation, shares, current_price, total_price, current_time)

    new_balance = get_portfolio_balance(conn, portfolio_id) - total_price
    update_portfolio_balance(conn, portfolio_id, new_balance, current_time)

    result = {
        'portfolio_name': portfolio_name,
        'symbol': symbol,
        'shares': shares,
        'operation': operation,
        'price_per_share': f'${current_price:,.2f}',
        'total_price': f'${total_price:,.2f}',
        'new_balance': f'${new_balance:,.2f}',
        'timestamp': current_time
    }
    return result

def sell_stock(conn, portfolio_name, symbol, shares):
    """Sell stock shares"""
    portfolio_id = get_portfolio_id(conn, portfolio_name)
    if not portfolio_id:
        return f'portfolio {portfolio_name} not found.'

    symbol = symbol.upper()

    ticker = yf.Ticker(symbol)

    sector = ticker.info.get('sector')

    current_price = ticker.fast_info.last_price
    total_price = current_price * float(shares)
    current_time = dt.datetime.now().strftime('%Y-%m-%d %H:%M')
    operation = 'SELL'
    insert_transaction(conn, portfolio_id, symbol, sector, operation, shares, current_price=current_price, total_price=total_price, current_time=current_time)

    new_balance = get_portfolio_balance(conn, portfolio_id) + total_price
    update_portfolio_balance(conn, portfolio_id, new_balance, current_time)


    result = {
        'portfolio_name': portfolio_name,
        'symbol': symbol,
        'shares': shares,
        'price_per_share': f'${current_price:.2f}',
        'total_price': f'${total_price:.2f}',
        'new_balance': f'${new_balance:.2f}',
        'timestamp': current_time
    }
    return result

def portfolio_data(conn, name):
    """View current data of a portfolio."""

    portfolio_id = get_portfolio_id(conn, name)
    if not portfolio_id:
        return f"Portfolio '{name}' not found."
    
    balance = get_portfolio_balance(conn, portfolio_id)
    holdings = get_holdings(conn, portfolio_id)

    symbols = [row[0].upper() for row in holdings]
    current_prices = get_batch_prices(symbols)

    holdings_by_sector = defaultdict(list)
    holdings_value = 0
    total_returns = 0

    if holdings:
        for symbol, sector, shares, initial_value in holdings:

            price = current_prices.get(symbol, 0)
            if price:
                stock_value = price * shares
                holdings_value += stock_value
                returns = stock_value - initial_value
                total_returns += returns
                returns_pc = (returns / initial_value) * 100
                change_sign = '+' if returns >= 0 else ''

                stock_data = {
                    'symbol': symbol,
                    'shares': shares,
                    'price': f'${price:.2f}',
                    'initial_value': f'${initial_value:.2f}',
                    'total_value': f'${stock_value:.2f}',
                    'returns': f'${returns:.2f} ({change_sign}{returns_pc:.2f}%)',
                }

            else:
                stock_data = {
                    'symbol': symbol,
                    'shares': shares, 
                    'initial_value': f'${initial_value:.2f}',
                }

            holdings_by_sector[sector].append(stock_data)
    else:
        return f'No holdings for portfolio: {name}.'

    total_returns_pc = (total_returns / (balance + holdings_value - total_returns)) * 100

    result = {
        'name': name,
        'balance': f'${balance:,.2f}',
        'total_holdings_value': f'${holdings_value:,.2f}',
        'total_value': f'${balance + holdings_value:,.2f}',
        'total_returns': f'${total_returns:,.2f} ({total_returns_pc:.2f}%)',
        'current_holdings': dict(holdings_by_sector)
    }
    
    return result

def portfolio_balance(conn, name):
    """Get current balance of a portfolio."""

    portfolio_id = get_portfolio_id(conn, name)
    if not portfolio_id:
        return f"Portfolio '{name}' not found."
    
    balance = get_portfolio_balance(conn, portfolio_id)

    result = {
        'name': name,
        'balance': f'${balance:,.2f}',
    }
    
    return result

