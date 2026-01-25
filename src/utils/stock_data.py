import requests
import pandas as pd
import yfinance as yf
import itertools # for S&P 500
# Scripts
from src.config.config import last_checked_prices, sp500_last_checked_prices
from src.config.storage import STOCK_SYMBOLS, clean_symbol

def get_prices_fast():
    """
    Get fast, real-time price fetch for commands to retrieve current prices 
    and percent changes for symbols in the watchlist.

    Returns:
        list[dict]: A list where each item contains keys:
            - 'symbol': stock symbol (str)
            - 'current_price': latest price (float)
            - 'percentage_change': percent difference vs reference (float)
            - 'change': absolute difference vs reference (float)
    """

    stock_data = [] # store stock price data
    
    if not STOCK_SYMBOLS:
        return stock_data

    # compare prices from last close to current price
    tickers = yf.Tickers(' '.join(STOCK_SYMBOLS))

    for symbol in STOCK_SYMBOLS:
        try:
            ticker = tickers.tickers[symbol]

            current_price = float(ticker.fast_info.last_price)
            prev_close = float(ticker.fast_info.previous_close)

            change = float(current_price - prev_close)
            percentage_change = float((current_price - prev_close) / prev_close) * 100

            # add data captured to the stock data list
            stock_data.append({
                'symbol': symbol,
                'current_price': current_price,
                'percentage_change': percentage_change,
                'change': change
            })
        
        except Exception as e:
            print(f'Error getting data for {symbol}: {e}')
            continue

    return stock_data

def get_prices_batch(compare_to='previous_close'):
    """
    Retrieve current prices and percent changes for symbols in the watchlist.

    Args:
        compare_to (str): Reference price used to compute change. Supported
            values: 'previous_close' (default) or 'week_start'.

    Returns:
        list[dict]: A list where each item contains keys:
            - 'symbol': stock symbol (str)
            - 'current_price': latest price (float)
            - 'percentage_change': percent difference vs reference (float)
            - 'change': absolute difference vs reference (float)
    """



    # compare prices from last close to current price
    stock_data = [] # store stock price data

    if not STOCK_SYMBOLS:
        return stock_data

    symbols = ' '.join(STOCK_SYMBOLS)
    data = yf.download(symbols, period = '5d', interval='1d', group_by='ticker', progress=False, auto_adjust=False)

    for symbol in STOCK_SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            current_price = ticker.fast_info.last_price

            if len(STOCK_SYMBOLS) == 1:
                hist = data
            else:
                hist = data[symbol]
            
            if hist.empty or len(hist) < 2:
                continue

            # get reference price on monday for week start comparison
            if compare_to == 'week_start':
                hist_5m = yf.download(symbol, period='5d', interval='5m', progress=False, auto_adjust=False)
                hist_5m = hist_5m[hist_5m.index.dayofweek == 0]

                if not hist_5m.empty:
                    reference_price = float(hist_5m['Close'].iloc[0])
                # quick fallback if market was closed on monday
                else:
                    reference_price = float(hist['Close'].iloc[-2])

            # default to get yesterdays price
            else:
                reference_price = float(hist['Close'].iloc[-2])

            change = float(current_price - reference_price)
            percentage_change = float((current_price - reference_price) / reference_price) * 100

            # add data captured to the stock data list
            stock_data.append({
                'symbol': symbol,
                'current_price': float(current_price),
                'percentage_change': percentage_change,
                'change': change
            })
        
        except Exception as e:
            print(f'Error getting data for {symbol}: {e}')
            continue

    return stock_data

def check_price_changes():
    """
    Compare current prices to the last saved checks and return symbols with
    significant short-term moves.

    The function uses the module-level `last_checked_prices` map to compute
    percentage change vs the last observed price and updates that map.

    Returns:
        list[dict]: Each dict contains 'symbol', 'current_price', 'last_price', and 'percentage_change'.
    """
    big_changes = []
    for symbol in STOCK_SYMBOLS:
        try:
            # get the ticker symbols
            ticker = yf.Ticker(symbol)
            #get the last price/current price
            current_price = ticker.fast_info.last_price

            # check if stock symbol is in last checked prices to move on with the function
            if symbol in last_checked_prices:
                last_price = last_checked_prices[symbol] # gets the last checked price and compares percentage to it

                percentage_change = ((current_price - last_price) / last_price) * 100

                # checks the pecent change if the absolute value is greater than 1
                if abs(percentage_change) >= 1:
                    big_changes.append({
                        'symbol': symbol,
                        'current_price': current_price,
                        'last_price': last_price,
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
