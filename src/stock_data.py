import requests
import pandas as pd
import yfinance as yf
import itertools 
# Scripts
from src.config.config import last_checked_prices, sp500_last_checked_prices
from src.config.storage import STOCK_SYMBOLS
from src.config.utils import clean_symbol, percent_change


def check_price_changes(symbols, percent_threshold=1):
    """
    Compare current prices to the last saved checks and return symbols with
    significant short-term moves.

    The function uses the module-level `last_checked_prices` map to compute
    percentage change vs the last observed price and updates that map.

    Returns:
        list[dict]: Each dict contains 'symbol', 'current_price', 'last_price', and 'percentage_change'.
    """
    big_changes = []
    for symbol in symbols:
        try:
            # get the ticker symbols
            ticker = yf.Ticker(symbol)
            #get the last price/current price
            current_price = ticker.fast_info.last_price

            # check if stock symbol is in last checked prices to move on with the function
            if symbol in last_checked_prices:
                last_price = last_checked_prices[symbol]
                percentage_change, change = percent_change(current_price, last_price)

                # checks the pecent change if the absolute value is greater than percent_threshold
                if abs(percentage_change) >= percent_threshold:
                    big_changes.append({
                        'symbol': symbol,
                        'current_price': current_price,
                        'last_price': last_price,
                        'change': change,
                        'percentage_change': percentage_change,
                    })

            # checks if price of the stock is equal to current price for storing reference for next comparison
            last_checked_prices[symbol] = current_price

        except Exception as e:
            print(f'Error getting data for {symbol}: {e}')

    return big_changes

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


def get_batch_prices(symbols, price_change=False, compare_to='week'):
    """
    batch processing to get stock price data for multiple symbols.
    Use price_change=True to get percent change vs compare_to price.
    
    :param symbols: list of symbols
    :param price_change: bool, whether to compute price change info
    :param compare_to: 'week' or 'day' for price comparison

    :return: dict of symbol to last close price, or dict with price change info

    """
    tickers = [sym for sym in symbols]
    symbols_str = ' '.join(tickers)
        
    data = yf.download(symbols_str, period='5d', interval='1d', group_by='ticker', progress=False, auto_adjust=False)
            
    prices = {}

    try:
        if len(symbols) == 1:
            if isinstance(data.columns, pd.MultiIndex):
                close_series = data[symbols[0]]['Close']

            last_close = close_series.iloc[-1]

            if price_change:
                if compare_to == 'day':
                    compare_price = close_series.iloc[-2]
                elif compare_to == 'week':
                    compare_price = close_series.iloc[-5]
                else:
                    raise ValueError("Invalid compare_to value. Use 'day' or 'week'.")

                percentage_change, change = percent_change(last_close, compare_price)

                prices[symbols[0]] = {
                    'last_close': float(last_close),
                    'compare_price': float(compare_price),
                    'change': change,
                    'percentage_change': percentage_change
                }
            else:
                prices[symbols[0]] = float(last_close)

        else:
            for symbol in symbols:
                if isinstance(data.columns, pd.MultiIndex):
                    close_series = data[symbol]['Close']

                last_close = close_series.iloc[-1]

                if price_change:
                    if compare_to == 'day':
                        compare_price = close_series.iloc[-2]
                    elif compare_to == 'week':
                        compare_price = close_series.iloc[-5]
                    else:
                        raise ValueError("Invalid compare_to value. Use 'day' or 'week'.")
                    
                    percentage_change, change = percent_change(last_close, compare_price)

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
        return {}


def get_asset_type(symbol):
    """
    Determine if a symbol is a stock or cryptocurrency.

    Notation:
    '^' prefix for market indices (e.g. ^GSPC)
    '=F' suffix for futures contracts (e.g. ES=F)
    '=X' suffix for forex pairs (e.g. EURUSD=X)
    '-USD' suffix for cryptocurrencies (e.g. BTC-USD)


    Args:
        symbol (str): The ticker symbol to check.
    Returns:
        str: 'etf' if the symbol is a market index
        str: 'futures' if it's a futures contract
        str: 'forex' if it's a forex pair
        str: 'crypto' if the symbol is a cryptocurrency
        str: 'commodity' if it's a commodity (e.g. gold, oil)
        str: 'stock' otherwise.
    """

    crypto_suffixes = ['-USD', '-USDT', '-USDC', '-DAI']
    commodity_symbols = ['GC=F', 'CL=F', 'SI=F', 'NG=F']  # Gold, Crude Oil, Silver, Natural Gas
    
    if symbol.startswith('^'):
        return 'etf'
    elif any(symbol.endswith(suffix) for suffix in crypto_suffixes):
        return 'crypto'
    elif symbol in commodity_symbols:
        return 'commodity'
    elif symbol.endswith('=F'):
        return 'futures'
    elif symbol.endswith('=X'):
        return 'forex'
    else:
        return 'stock'

