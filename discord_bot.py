# Time Date
import time
import datetime as dt
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
# Data & API
import requests
import pandas as pd
import yfinance as yf
# Discord
import discord
from discord.ext import commands, tasks
# Utilities
import pytz
import io
import os
import json
import itertools # for S&P 500
from dotenv import load_dotenv
import logging
# Visuals
import mplfinance as mpf
import seaborn as sns
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# --- Logging ---
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('discord.gateway').setLevel(logging.WARNING)


# --- .env & Tokens ---
load_dotenv()
discord_token = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


# --- Channel ID & Stock Symbols ---
CHANNEL_ID = 1435810254783778933
STOCK_FILE = 'watchlist.json'

last_checked_prices = {}
sp500_last_checked_prices = {}


# --- file management for stocks ---
def load_stocks():
    """
    Load watchlist symbols from the persistent JSON file.

    Returns:
        list: List of stock symbol strings loaded from `watchlist.json`.
              If the file does not exist, an empty list is returned and
              an empty watchlist file is created.
    """
    try:
        with open(STOCK_FILE, 'r') as f:
            data = json.load(f)
            return data.get('symbols', [])
    except FileNotFoundError:
        save_stocks([])
        return []

def save_stocks(stocks):
    """
    Persist the provided list of stock symbols to the watchlist JSON file.

    Args:
        stocks (list): List of stock symbol strings to save to disk.
    """
    with open(STOCK_FILE, 'w') as f:
        json.dump({'symbols': stocks}, f, indent=2)

STOCK_SYMBOLS = load_stocks()

# --- FUNCTIONS: Prices ---
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

#TODO: Make a function only for taskloops and reports for batching prices info
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
                    # add stock data to big_changes list
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
    # pass big changes
    return big_changes

sp500_cycle = None
def get_sp500_movers(percent_threshold=1, batch_size=50):
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
                    ticker = yf.Ticker(symbol)
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
        # pass big movers
        return big_movers

    except Exception as e:
        print(f'Error checking S&P 500: {e}')  
        return []

# --- FUNCTIONS: Visuals ---
def create_candlestick_graph(symbol, period, interval, after_hours=False):
    """
    Create a candlestick chart image for the given symbol and return a
    BytesIO buffer containing the PNG image.

    Args:
        symbol (str): Stock ticker symbol.
        period (str): Period string accepted by yfinance (e.g. '4h', '5d').
        interval (str): Interval string accepted by yfinance (e.g. '1m', '1h').
        after_hours (bool): If True, include extended/pre/post market hours.

    Returns:
        io.BytesIO or None: In-memory PNG image buffer on success, or None on error.
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval, prepost=True)

        hist = hist.tz_convert('US/Eastern') # convert time to eastern time for graphs          
        hist = hist[hist.index.dayofweek < 5]

        # filter hours
        if not after_hours:
            hist = hist.between_time('9:30', '16:00')
        else:
            hist = hist.between_time('4:00', '20:00')

        if hist.empty:
            return None

        buf = io.BytesIO()

        mpf.plot(
            hist, 
            type='candle',
            style='charles',
            title=f"{symbol} - Last {period}",
            ylabel='Price ($)',
            savefig=dict(fname=buf, dpi=100, bbox_inches='tight')
        )

        buf.seek(0)
        plt.close()
        return buf

    except Exception as e:
        logging.error(f'Error creating graph for {symbol}: {e}')
        plt.close()
        return None

def create_stock_graph(symbol, period, interval, after_hours=False):
    """
    Create a line chart of the stock's closing prices and return a PNG buffer.

    Args:
        symbol (str): Stock ticker symbol.
        period (str): Time range to fetch (yfinance format, e.g. '1mo').
        interval (str): Data interval (e.g. '1d', '4h').
        after_hours (bool): Whether to include after-hours data.

    Returns:
        io.BytesIO or None: PNG image buffer if successful, otherwise None.
    """
    try:
        ticker = yf.Ticker(symbol)

        hist = ticker.history(period=period, interval=interval, prepost=True)

        if hist.index.tz is None:
            hist = hist.tz_localize('UTC').tz_convert('US/Eastern') # ensure tz-aware before converting
        else:
            hist = hist.tz_convert('US/Eastern') # convert time to eastern time for graphs
        hist = hist[hist.index.dayofweek < 5] # remove weekends

        # filter hours
        if 'm' in interval or 'h' in interval:
            if not after_hours:
                hist = hist.between_time('9:30', '16:00')
            else:
                hist = hist.between_time('4:00', '20:00')

        if hist.empty:
            return None
        
        hist_reset = hist.reset_index()

        date_col = 'Date' if 'Date' in hist_reset.columns else 'Datetime'

        plt.figure(figsize=(10, 6))
        sns.set_style('whitegrid')

        sns.lineplot(data=hist_reset, x=range(len(hist_reset)), y='Close', linewidth=1.5)

        total_days = (hist_reset[date_col].iloc[-1] - hist_reset[date_col].iloc[0]).days

        # custom ticks
        if total_days <= 1:
            num_ticks = min(8, len(hist_reset))
            date_format = '%H:%M'
        elif total_days <= 7:
            num_ticks = min(7, len(hist_reset))
            date_format = '%m/%d %H:%M'
        elif total_days <= 31:
            num_ticks = min(10, len(hist_reset))
            date_format = '%m/%d'
        elif total_days <= 365:
            num_ticks = min(12, len(hist_reset))
            date_format = '%b %d'
        else:
            num_ticks = min(12, len(hist_reset))
            date_format = '%b %Y'

        tick_positions = [int(i * (len(hist_reset) - 1) / (num_ticks - 1)) for i in range(num_ticks)]
        tick_labels = [hist_reset[date_col].iloc[i].strftime(date_format) for i in tick_positions]

        plt.xticks(tick_positions, tick_labels, fontsize=9, rotation=45)
        plt.yticks(fontsize=9)

        plt.title(f'{symbol} Stock Price - Last {period}', fontsize=17, fontweight='bold')
        plt.xlabel('Date', fontsize=11)
        plt.ylabel('Closing Price ($)', fontsize=11)
        plt.yticks(fontsize=9)
        plt.tight_layout()

        # Buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close('all')

        return buf

    except Exception as e:
        print(f'Error creating graph for {symbol}: {e}')
        plt.close('all')
        return None

def create_bollinger_bands(symbol, period='1mo', interval='1d', window=20, num_of_std=2):
    """
    Calculate Bollinger Bands for a symbol, render the bands and price as a
    PNG image, and return an in-memory buffer.

    Args:
        symbol (str): Stock ticker symbol.
        period (str): Period string for historical data (default '1mo').
        interval (str): Interval for data points (default '1d').
        window (int): Rolling window size for the moving average (default 20).
        num_of_std (int): Number of standard deviations for the upper/lower bands.

    Returns:
        io.BytesIO or None: PNG image buffer containing the plotted Bollinger Bands, or None on error.
    """

    try:
        ticker = yf.Ticker(symbol)
        prepost = 'm' in interval or 'h' in interval
        hist = ticker.history(period=period, interval=interval, prepost=prepost, auto_adjust=False)

        if prepost:
            hist = hist.tz_convert('US/Eastern')
            hist = hist[hist.index.dayofweek < 5]

        rolling_mean = hist['Close'].rolling(window=window).mean()
        rolling_std = hist['Close'].rolling(window=window).std()

        upper_band = rolling_mean + (rolling_std * num_of_std)
        lower_band = rolling_mean - (rolling_std * num_of_std)

        df = pd.DataFrame({
            'Close': hist['Close'],
            'Middle_Band': rolling_mean,
            'Upper_Band': upper_band,
            'Lower_Band': lower_band
        }).dropna()

        df_reset = df.reset_index()
        df_reset = df_reset.rename(columns={df_reset.columns[0]: 'Date'})

        plt.figure(figsize=(10, 6))
        sns.set_style('whitegrid')
        sns.lineplot(data=df_reset, x=range(len(df_reset)), y='Close', label=f'{symbol} Close Price', color='blue')
        
        # Bollinger Bands
        sns.lineplot(data=df_reset, x=range(len(df_reset)), y='Middle_Band', label='Middle Band (SMA)', color='orange')
        sns.lineplot(data=df_reset, x=range(len(df_reset)), y='Upper_Band', label='Upper Band', color='green')
        sns.lineplot(data=df_reset, x=range(len(df_reset)), y='Lower_Band', label='Lower Band', color='red')


        plt.fill_between(range(len(df_reset)), df_reset['Close'].values, df_reset['Upper_Band'].values, 
        where=(df_reset['Close'].values <= df_reset['Upper_Band'].values), 
        alpha=0.1, color='green', label='Overbought Zone')

        plt.fill_between(range(len(df_reset)), df_reset['Close'].values, df_reset['Lower_Band'].values, 
        where=(df_reset['Close'].values >= df_reset['Lower_Band'].values), 
        alpha=0.1, color='red', label='Oversold Zone')


        total_days = (df_reset['Date'].iloc[-1] - df_reset['Date'].iloc[0]).days
        
        if total_days <= 1:
            num_ticks = min(8, len(df_reset))
            date_format = '%H:%M'
        elif total_days <= 7:
            num_ticks = min(7, len(df_reset))
            date_format = '%m/%d %H:%M'
        elif total_days <= 31:
            num_ticks = min(10, len(df_reset))
            date_format = '%m/%d'
        elif total_days <= 365:
            num_ticks = min(12, len(df_reset))
            date_format = '%b %d'
        else:
            num_ticks = min(12, len(df_reset))
            date_format = '%b %Y'

        tick_positions = [int(i * (len(df_reset) - 1) / (num_ticks - 1)) for i in range(num_ticks)]
        tick_labels = [df_reset['Date'].iloc[i].strftime(date_format) for i in tick_positions]

        plt.title(f'Bollinger Bands - {symbol} Stock Price - Last {period}', fontsize=17, fontweight='bold')
        plt.xlabel('Date', fontsize=11)
        plt.ylabel('Price ($)', fontsize=11)
        plt.xticks(ticks=tick_positions, labels=tick_labels, fontsize=9, rotation=45)
        plt.yticks(fontsize=9)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        # Buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close('all')

        return buf

    except Exception as e:
        print(f'Error creating graph for {symbol}: {e}')
        plt.close('all')
        return None


# --- BOT EVENT ---
@bot.event
async def on_ready():
    """
    Discord event fired when the bot has connected and is ready.

    Starts the periodic background tasks if they are not already running.
    """
    print(f'We have logged in as {bot.user}')
    if not market_open_report.is_running():
        market_open_report.start()
    if not check_big_changes.is_running():
        check_big_changes.start()
    if not sp500_movers_alert.is_running():
        sp500_movers_alert.start()


# --- COMMANDS ---
@bot.command()
async def price(ctx, *symbols):
    """
    Command: !price <symbol1> (<symbol2> <symbol3> ...)

    Sends the current price for each provided stock symbol back to the channel.
    If no symbol is provided, prompts the user for input.
    """
    if not symbols:
        await ctx.send('Please provide atleast one stock symbol.')

    symbols_upper = [s.upper() for s in symbols]
    tickers = yf.Tickers(' '.join(symbols_upper))

    embed = discord.Embed(
        title='Stock Prices',
        color=discord.Color.blue()
    )

    try:
        # checks if stock symbol was asked
        for symbol in symbols_upper:
            current_price = tickers.tickers[symbol].fast_info.last_price

            embed.add_field(
                name=symbol,
                value=f'${current_price:.2f}',
                inline=True
            )

    except Exception as e:
        await ctx.send(f'Could not get the price of {symbol}.')
        print(f'Error getting stock price:\n{e}')
    
    await ctx.send(embed=embed)


# --- Manage Stocks Commands ---
@bot.command()
async def add(ctx, symbol):
    """
    Command: !add <symbol>

    Adds the given stock symbol to the persistent watchlist.
    """
    symbol = symbol.upper()

    if symbol not in STOCK_SYMBOLS:
        STOCK_SYMBOLS.append(symbol)
        save_stocks(STOCK_SYMBOLS)
        await ctx.send(f'Added {symbol} to watchlist.')
    else:
        await ctx.send(f'{symbol} already in watchlist.')

@bot.command()
async def remove(ctx, stock):
    """
    Command: !remove <symbol>

    Removes the given stock symbol from the persistent watchlist.
    """
    symbol = stock.upper()

    if symbol in STOCK_SYMBOLS:
        STOCK_SYMBOLS.remove(symbol)
        save_stocks(STOCK_SYMBOLS)
        await ctx.send(f'Successfully removed {symbol} from watchlist.')
    else:
        await ctx.send(f'{symbol} is not found in watchlist.')

@bot.command()
async def watchlist(ctx):
    """
    Command: !watchlist

    Sends an embed containing the current prices of all symbols in the watchlist.
    If the watchlist is empty, prompts the user to add symbols.
    """
    if not STOCK_SYMBOLS:
        await ctx.send(f'Watchlist is empty. Please use !add <symbol> to add stocks.')
        return

    stock_data = get_prices_fast()

    if stock_data:
        embed = discord.Embed(
            title='Watchlist Prices',
            color=discord.Color.blue()
            )
 
        for stock in stock_data:
            embed.add_field(
                name=f"{stock['symbol']}",
                value=f'${stock["current_price"]:.2f}'
            )

        await ctx.send(embed=embed)
    else:
        await ctx.send(f"Watching:\n {', '.join(sorted(STOCK_SYMBOLS))}.\n Could not get stock prices/data.")

# --- Visuals for Stocks ---
@bot.command()
async def chart(ctx, symbol: str, period: str = '5d', interval: str = '30m'):
    """
    Command: !chart <symbol> <period> <interval>

    Generates an appropriate chart (candlestick or line) for the requested
    symbol/period/interval and sends it back to the channel as an image file.
    """
    symbol = symbol.upper()

    await ctx.send(f"Generating chart for {symbol}...")

    try:
        # Use candlestick chart only for short periods and intervals
        candlestick_periods = ['60m','90m','4h','1d','2d','3d']
        candlestick_intervals = ['1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h']

        if period in candlestick_periods and interval in candlestick_intervals:
            graph = create_candlestick_graph(symbol, period, interval, after_hours=True)
            chart_type = 'candlestick'
        else:
            graph = create_stock_graph(symbol, period, interval, after_hours=True)
            chart_type = 'line'

        if graph:
            file = discord.File(graph, filename=f'{symbol}_{chart_type}_chart.png')
            await ctx.send(file=file)
        else:
            await ctx.send(f"Could not generate chart for {symbol}. Check if constraints are valid.")
    
    except Exception as e:
        logging.error(f'Error generating chart for {symbol}: {str(e)}')
        await ctx.send(f'An error occurred while generating the chart for {symbol}: {str(e)} Please try again later.')

@bot.command()
async def bollinger(ctx, symbol: str, period: str = '1mo', interval: str = '4h'):
    symbol = symbol.upper()
    """
    Command: !bollinger <symbol> [period] [interval]

    Generates a Bollinger Bands chart for the requested symbol and sends it
    back to the channel as an image file.
    """

    await ctx.send(f"Generating Bollinger chart for {symbol}...")
    
    try:
        graph = create_bollinger_bands(symbol, period, interval)
        chart_type = 'bollinger_bands'

        if graph:
            file = discord.File(graph, filename=f'{symbol}_{chart_type}_chart.png')
            await ctx.send(file=file)
        else:
            await ctx.send(f"Could not generate chart for {symbol}.")

    except Exception as e:
        await ctx.send(f'Error generating chart for {symbol}: {str(e)}')


# --- Info for Stocks ---
@bot.command()
async def helpme(ctx):
    """
    Command: !helpme

    Sends an embed that lists the bot's available commands and usage.
    """
    embed = discord.Embed(
        title='Stock Bot Commands',
        color=discord.Color.blue(),
        description=(
            "Available Commands:\n"
            " - !current_price <symbol> - Get the current price of a stock.\n"
            " - !add <symbol> - Add a stock to the watchlist.\n"
            " - !remove <symbol> - Remove a stock from the watchlist.\n"
            " - !watchlist - View the current watchlist and prices.\n"
            " - !chart <symbol> <period> <interval> - Generate a stock price chart.\n"
            " - !bollinger <symbol> [period] [interval] - Generate a Bollinger Bands chart.\n"
            " - !helpme - Shows this help message."
        )
    )
    await ctx.send(embed=embed)

@bot.command()
async def periods(ctx):
    """
    Command: !periods

    Sends an embed listing valid chart period strings the bot supports.
    """
    embed = discord.Embed(
        title='Stock Bot - Chart Periods',
        color=discord.Color.blue(),
        description=(
            """
            Note: The user is allowed to use any number for numeric periods.

            **Available Periods:**
            **Days**\n1d, 2d, 3d, 4d, ...
            **Weeks**\n1wk, 2wk, 3wk, 4wk, ...
            **Months**\n1mo, 2mo, 3mo, 4mo, ...
            **Year-to-date**\nytd
            **Years**\n1y, 2y, 3y, 4y, ...
            **Max history**\nmax
            """
        )
    )
    await ctx.send(embed=embed)

@bot.command()
async def intervals(ctx):
    """
    Command: !intervals

    Sends an embed listing valid chart interval strings the bot supports.
    """
    embed = discord.Embed(
        title='Stock Bot - Chart Intervals',
        color=discord.Color.blue(),
        description=(
            """
            Note: 'm' indicates minutes, 'h' indicates hours, 'd' indicates days,
            'wk' indicates weeks, and 'mo' indicates months.

            **Available Intervals:**
            **Minutes**\n1m, 2m, 5m, 15m, 30m, 60m, 90m
            **Hours**\n1h, 4h
            **Days**\n1d, 5d
            **Weeks**\n1wk
            **Months**\n1mo, 3mo
            """
        )
    )
    await ctx.send(embed=embed)


# --- Task loops ---
# Send notification of stock prices and percent change
timezone = ZoneInfo('America/New_York')
report_time = dt.time(hour=9, minute=30, tzinfo=timezone)
@tasks.loop(time=report_time)
async def market_open_report():
    """ 
    Periodic task that runs at market open (9:30am EST) on weekdays to send
    a summary report of the stock prices in watchlist and runs a weekend 
    summary of the previous week's performance on Saturdays to the channel. 
    """

    await bot.wait_until_ready()

    # timezone
    eastern = pytz.timezone('US/Eastern')
    time_now = dt.datetime.now(eastern)

    print(f"[{datetime.now()}] Sending market open report...")

    channel = bot.get_channel(CHANNEL_ID)

    # fallback for channel id not found
    if not channel:
        print(f'Channel {CHANNEL_ID} not found')
        return

    # fallback for no stocks in watchlist
    if not STOCK_SYMBOLS:
        await channel.send('No stocks in watchlist.')
        return

    is_weekend = time_now.weekday() >= 5
    stock_data = get_prices_batch(compare_to='week_start' if is_weekend else 'previous_close')

    if stock_data:
        # message format: embed
        if is_weekend:
            embed = discord.Embed(
                title='Weekend Market Report',
                description='Market is closed on weekends.',
                color=discord.Color.blue(),
                timestamp=dt.datetime.now(),
                )
        else:
            embed = discord.Embed(
                title='Market Open Report = 9:30 AM EST',
                color=discord.Color.green(),
                timestamp=dt.datetime.now(),
                )
        
        # give percentage change greater than 0 or less than 0 a different color
        for stock in stock_data:
            star = '⭐️' if abs(stock['percentage_change']) >= 2 else ''
            change_emoji = '🟢' if stock['change'] >= 0 else '🔴'
            change_sign = "+" if stock['change'] >= 0 else ""

            # add stock info to embed parameters
            embed.add_field(
                name=f"{star} {change_emoji} {stock['symbol']}",
                value=f"${stock['current_price']:.2f}\n{change_sign}{stock['percentage_change']:.2f}%", 
                inline=True
            )

        # send Graphs for each chart
        files = []
        for stock in stock_data:
            if abs(stock['percentage_change']) >= 1:
                if is_weekend:
                    graph = create_bollinger_bands(stock['symbol'], period='5d', interval='60m', after_hours=True)
                elif time_now.weekday() == 0: # Monday: last market open (Friday) for reference
                    graph = create_stock_graph(stock['symbol'], period='3d', interval='15m', after_hours=True)
                else: # last market open (Tuesday - Friday) for reference
                    graph = create_stock_graph(stock['symbol'], period='2d', interval='15m', after_hours=True)

                if graph:
                    files.append(discord.File(graph, filename=f"{stock['symbol']}_chart.png"))

        # send embed through the message type, send all charts at once
        if files:
            await channel.send(embed=embed, files=files)
        else:
            await channel.send(embed=embed)
            failed_symbols = [stock['symbol'] for stock in stock_data]
            await channel.send(f"Could not generate charts for {', '.join(failed_symbols)}")
    else:
        await channel.send('Could not get stock prices/data')

# send Alert if stock price made a big change
@tasks.loop(minutes=5)
async def check_big_changes():
    """
    Periodic task that runs every five minutes during market hours to check
    the watchlist for large price movements and post alerts to the channel.
    """

    await bot.wait_until_ready()

    time_now = dt.datetime.now(pytz.timezone('US/Eastern'))
    if time_now.weekday() >= 5:
        return
    if time_now.hour < 9 or (time_now.hour == 9 and time_now.minute < 30) or time_now.hour > 16:
        return

    print(f"[{datetime.now()}] WATCHLIST: Checking for big changes...")

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f'Channel {CHANNEL_ID} not found')
        return

    big_changes = check_price_changes()

    # statement to detect if big changes is True
    if big_changes:
        print("WATCHLIST: Big price changes found.")

        symbols = ', '.join(stock['symbol'] for stock in big_changes)
        embed = discord.Embed(
            title=f"ALERT: Big Price Movement for {symbols}",
            color=discord.Color.red(),
            timestamp=datetime.now(),
            )

        for stock in big_changes:
            change_emoji = '🟢' if stock['percentage_change'] >= 0 else '🔴'
            change_sign = "+" if stock['percentage_change'] >= 0 else ""

            embed.add_field(
                name=f"{change_emoji} {stock['symbol']}",
                value=f"${stock['current_price']:.2f}\n{change_sign}{stock['percentage_change']:.2f}%", 
                inline=True
                )
        await channel.send(embed=embed)
    else:
        print("WATCHLIST: Big price changes not found.")

# Send S&P 500 Movers Alerts
@tasks.loop(minutes=5)
async def sp500_movers_alert():
    """
    Periodic task that checks a rotating subset of S&P 500 constituents for
    large moves and posts alerts to the configured channel during market hours.
    """

    await bot.wait_until_ready()

    time_now = dt.datetime.now(pytz.timezone('US/Eastern'))
    if time_now.weekday() >= 5:
        return
    if time_now.hour < 9 or (time_now.hour == 9 and time_now.minute < 30) or time_now.hour >= 16:
        return

    print(f"[{datetime.now()}] S&P 500: Checking for big changes...")

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f'Channel {CHANNEL_ID} not found')
        return
    
    sp_movers = get_sp500_movers(percent_threshold=1, batch_size=50)

    if sp_movers:
        print("S&P 500 Big price movers found.")

        symbols = ', '.join(stock['symbol'] for stock in sp_movers[:5])

        embed = discord.Embed(
            title= f'S&P 500 ALERT: Big Price Movement for {symbols}{'...' if len(sp_movers) > 5 else ''}',
            color=discord.Color.red(),
            timestamp=datetime.now(),
        )

        for stock in sp_movers:
            change_emoji = '🟢' if stock['percentage_change'] >= 0 else '🔴'
            change_sign = "+" if stock['percentage_change'] >= 0 else ""

            embed.add_field(
                name=f"{change_emoji} {stock['symbol']}",
                value=f"${stock['current_price']:.2f}\n{change_sign}{stock['percentage_change']:.2f}%", 
                inline=True
                )
        await channel.send(embed=embed)

    else:
        print("S&P 500: Big price changes not found.")


bot.run(discord_token)