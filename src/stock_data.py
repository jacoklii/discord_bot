import requests
import pandas as pd
import yfinance as yf
import itertools 
# Scripts
from src.config.config import last_checked_prices, sp500_last_checked_prices
from src.config.storage import STOCK_SYMBOLS
from src.config.utils import clean_symbol, percent_change, stock_change

sp500_cycle = None
def get_sp500_movers(percent_threshold=2, batch_size=25):
    """
    Check a rotating batch of S&P 500 constituents and return symbols that
    moved more than `percent_threshold` since the last check.

    Note: The S&P 500 symbol list is fetched from a remote CSV on every call,
    which may have rate-limit or performance implications.

    This function maintains an internal cycling iterator so that subsequent
    calls examine different batches of S&P 500 symbols.

    Args:
        percent_threshold (float): Minimum absolute percent change to report.
        batch_size (int): Number of symbols to check on this invocation.

    Returns:
        list[dict]: List of movers with keys 'symbol', 'current_price', 'last_price', 'percentage_change'.
    """
    global sp500_cycle

    try:
        csv_url = 'https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv'
        
        response = requests.get(csv_url)
        response.raise_for_status()

        lines = response.text.strip().split('\n')
        sp500_symbols = [line.split(',')[0] for line in lines[1:]]

        if sp500_cycle is None:
            sp500_cycle = itertools.cycle(sp500_symbols)

        batch = [next(sp500_cycle) for _ in range(batch_size)]
        big_movers = []

        for symbol in batch:
            if symbol not in STOCK_SYMBOLS: #checks if s&p 500 symbol isn't already in watchlist
                try:
                    yf_symbol = clean_symbol(symbol)
                    ticker = yf.Ticker(yf_symbol)
                    current_price = ticker.fast_info.last_price

                    if symbol in sp500_last_checked_prices:
                        last_price = sp500_last_checked_prices[symbol] # gets the last checked price and compares percentage to it
                        percentage_change = ((current_price - last_price) / last_price) * 100

                        # checks the pecent change if the absolute value is greater than threshold
                        if abs(percentage_change) >= percent_threshold:
                            big_movers.append({
                                'symbol': symbol,
                                'current_price': current_price,
                                'last_price': last_price,
                                'percentage_change': percentage_change,
                            })

                    # updates last checked price for next comparison
                    sp500_last_checked_prices[symbol] = current_price
                except Exception:
                    continue
            else:
                continue

        return big_movers

    except Exception as e:
        print(f'Error checking S&P 500: {e}')  
        return []


def get_batch_prices(symbols, price_change=False, compare_to='custom', custom_prices=None):
    """
    batch processing to get stock price data for multiple symbols.
    Use price_change=True to get percent change vs compare_to price.
    
    :param symbols: list of symbols
    :param price_change: bool, whether to compute price change info
    :param compare_to: 'week' or 'day' or 'portfolio' for price comparison
    :param portfolio_prices: dict of symbol to price if compare_to='portfolio'

    :return: dict of symbol to last close price, or dict with price change info

    """
        
    data = yf.download(symbols, period='5d', interval='1d', group_by='ticker', progress=False, auto_adjust=False)
            
    prices = {}

    try:
        if len(symbols) == 1:
            if isinstance(data.columns, pd.MultiIndex):
                close_series = data[symbols[0]]['Close']
                if close_series.empty:
                    raise ValueError(f"No close price data found for symbol {symbols[0]}")

            last_close = close_series.iloc[-1]

            if price_change:
                if compare_to == 'day':
                    compare_price = close_series.iloc[-2]
                elif compare_to == 'week':
                    compare_price = close_series.iloc[-5]
                elif compare_to == 'portfolio':
                    compare_price = portfolio_prices.get(symbols[0], 0)
                else:
                    raise ValueError("Invalid compare_to value. Use 'day' or 'week' or 'portfolio'.")

                percentage_change, change = stock_change(last_close, compare_price)

                prices[symbols[0]] = {
                    'last_close': float(last_close),
                    'compare_price': float(compare_price),
                    'change': change,
                    'percentage_change': percentage_change
                }
            else:
                prices[symbols[0]] = float(last_close)

        else:
            for i, symbol in enumerate(symbols):
                if isinstance(data.columns, pd.MultiIndex):
                    close_series = data[symbol]['Close']
                    if close_series.empty:
                        raise ValueError(f"No close price data found for symbol {symbol}")
     
                last_close = close_series.iloc[-1]

                if price_change:
                    if compare_to == 'day':
                        compare_price = close_series.iloc[-2]
                    elif compare_to == 'week':
                        compare_price = close_series.iloc[-5]
                    elif compare_to == 'custom':
                        if custom_prices is None or i >= len(custom_prices):
                            raise ValueError(f"Not enough custom prices provided for comparison. Expected at least {i+1}, got {len(custom_prices)}.")
                        compare_price = custom_prices[i]
                    else:
                        raise ValueError("Invalid compare_to value. Use 'day' or 'week' or 'custom'.")
                    percentage_change, change = stock_change(last_close, compare_price)

                    prices[symbol] = {
                        'last_close': float(last_close),
                        'compare_price': float(compare_price),
                        'change': change,
                        'percentage_change': percentage_change
                    }
                else:
                    prices[symbol] = float(last_close)

        return prices
    
    except Exception as e:
        print(f"Error getting close for {symbol}: {e}")
        return prices


def check_price_changes(symbols, percent_threshold=1, initial_prices=None):
    """
    Compare current prices to initial or last checked prices and return symbols with
    significant short-term moves.

    The function compares current prices to provided initial_prices if available.
    If initial_prices is not provided or doesn't contain a symbol, it falls back to
    using the module-level `last_checked_prices` map.

    Args:
        symbols (list): List of stock symbols to check.
        percent_threshold (float): Minimum absolute percent change to report. Defaults to 1.
        initial_prices (dict, optional): Dictionary mapping symbols to initial prices for comparison.
                                         If not provided, uses last_checked_prices. Defaults to None.

    Returns:
        list[dict]: Each dict contains 'symbol', 'current_price', 'last_price', and 'percentage_change'.
    """
    
    big_changes = []
    
    try:
        prices = get_batch_prices(symbols, price_change=False)
        
        for i, symbol in enumerate(symbols):
            try:
                current_price = prices.get(symbol)
                if current_price is None:
                    continue

                if symbol in last_checked_prices:
                    last_price = last_checked_prices[symbol]
                else:
                    last_checked_prices[symbol] = current_price
                    continue

                # Measure the last checked price percentage change against the threshold for detection
                if abs(percent_change(current_price, last_price)) >= percent_threshold:

                    if isinstance(initial_prices, list) and i < len(initial_prices):
                        initial_price = initial_prices[i]
                    elif isinstance(initial_prices, dict) and symbol in initial_prices:
                        initial_price = initial_prices[symbol]
                    else: 
                        initial_price = None

                    # Calculate percentage change and change compared to the initial price for affects on investments
                    percentage_change, change = stock_change(current_price, initial_price)

                    big_changes[symbol] = {
                        'symbol': symbol,
                        'current_price': current_price,
                        'initial_price': initial_price,
                        'change': change,
                        'percentage_change': percentage_change
                    }

                # Update last checked price for next comparison
                last_checked_prices[symbol] = current_price

            except Exception as e:
                print(f'Error processing {symbol}: {e}')
    except Exception as e:
        print(f'Error getting data for {symbol}: {e}')

    return big_changes

def get_asset_type(symbol):
    """
    Determine if a symbol is a stock or cryptocurrency.

    Args:
        symbol (str): The ticker symbol to check.
    Returns:
        str: 'ETF' if the symbol is a market index
        str: 'Futures' if it's a futures contract
        str: 'Currency' if it's a forex pair
        str: 'Cryptocurrency' if the symbol is a cryptocurrency
        str: 'Commodity' if it's a commodity (e.g. gold, oil)
        str: 'Stock' otherwise.
    """
    commodity_symbols = ['GC=F', 'CL=F', 'SI=F', 'HG=F']  # Gold, Crude Oil, Silver, Copper futures
    
    ticker = yf.Ticker(symbol)
    asset = ticker.info.get('quoteType')

    if symbol in commodity_symbols:
        return 'Commodity'
    elif symbol == 'ETF':
        return symbol
    else:
        return asset.capitalize()

