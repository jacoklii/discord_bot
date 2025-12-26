# Time 
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
# Visuals
import mplfinance as mpf
import seaborn as sns
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt


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
    try:
        with open(STOCK_FILE, 'r') as f:
            data = json.load(f)
            return data.get('symbols', [])
    except FileNotFoundError:
        save_stocks([])
        return []

def save_stocks(stocks):
    with open(STOCK_FILE, 'w') as f:
        json.dump({'symbols': stocks}, f, indent=2)

STOCK_SYMBOLS = load_stocks()


# --- FUNCTIONS: Prices ---
def get_stock_prices(compare_to='previous_close'):
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
                hist_5m = yf.download(symbol, period='5d', interval='5m', progress=False)
                hist_5m = hist_5m[hist_5m.index.dayofweek == 0]

                if not hist_5m.empty:
                    reference_price = hist_5m['Close'].iloc[0]
                # quick fallback if market was closed on monday
                else:
                    reference_price = hist['Close'].iloc[-2]

            # default to get yesterdays price
            else:
                reference_price = hist['Close'].iloc[-2]

            change = current_price - reference_price
            percentage_change = ((current_price - reference_price) / reference_price) * 100

            # add data captured to the stock data list
            stock_data.append({
                'symbol': symbol,
                'current_price': current_price,
                'percentage_change': percentage_change,
                'change': change
            })
        
        except Exception as e:
            print(f'Error getting data for {symbol}: {e}')

    return stock_data

def check_price_changes():
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

    global sp500_cycle

    try:
        csv_url = 'https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv'
        
        response = requests.get(csv_url)
        response.raise_for_status()

        lines = response.text.strip().split('\n')
        # headers = lines[0].split(',')
        sp500_symbols = [line.split(',')[0] for line in lines[1:]]

        if sp500_cycle is None:
            sp500_cycle = itertools.cycle(sp500_symbols)

        batch = [next(sp500_cycle) for _ in range(batch_size)]
        big_movers = []
        for symbol in batch:
            if symbol not in STOCK_SYMBOLS: #checks if s&p 500 symbol isn't already in watchlist
                try:
                    ticker = yf.Ticker(symbol)

                    if symbol in sp500_last_checked_prices:
                        last_price = sp500_last_checked_prices[symbol] # gets the last checked price and compares percentage to it
                        percentage_change = ((current_price - last_price) / last_price) * 100

                        # checks the pecent change if the absolute value is greater than threshold
                        if abs(percentage_change) >= percent_threshold:
                            current_price = ticker.fast_info.last_price

                            big_movers.append({
                                'symbol': symbol,
                                'current_price': current_price,
                                'last_price': last_price,
                                'percentage_change': percentage_change,
                            })

                    # updates last checked price for next comparison
                    sp500_last_checked_prices[symbol] = current_price

                except:
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
    Create a Candlestick Chart for a stock
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
        plt.close('all')
        return buf

    except Exception as e:
        print(f'Error creating graph for {symbol}: {e}')
        plt.close('all')
        return None

def create_stock_graph(symbol, period, interval, after_hours=False):
    """
    Create a Chart for stock report
    """
    try:
        ticker = yf.Ticker(symbol)

        hist = ticker.history(period=period, interval=interval, prepost=True)

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

        plt.figure(figsize=(10, 6))
        sns.set_style('whitegrid')

        sns.lineplot(data=hist_reset, x=range(len(hist_reset)), y='Close', linewidth=1.5)

        total_days = (hist_reset['Date'].iloc[-1] - hist_reset['Date'].iloc[0]).days

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
        tick_labels = [hist_reset['Date'].iloc[i].strftime(date_format) for i in tick_positions]

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
    Calculate Bollinger Bands for a stock
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
    print(f'We have logged in as {bot.user}')
    if not market_open_report.is_running():
        market_open_report.start()
    if not check_big_changes.is_running():
        check_big_changes.start()
    if not sp500_movers_alert.is_running():
        sp500_movers_alert.start()


# --- COMMANDS ---
# Command: !current_price
@bot.command()
async def current_price(ctx):
    input_text = ctx.message.content.split()
    if len(input_text) < 2:
        await ctx.send('Please provide a stock symbol')

    # checks if stock symbol was asked
    for stock_symbol in input_text[1:]:
        ticker = yf.Ticker(str(stock_symbol)) # grab ticker
        todays_price = ticker.fast_info.last_price
        await ctx.send(f'The current price of {stock_symbol} is ${todays_price:.2f}')

# --- Manage Stocks Commands ---
# manage stocks: !add
@bot.command()
async def add(ctx,symbol):
    symbol = symbol.upper()

    if symbol not in STOCK_SYMBOLS:
        STOCK_SYMBOLS.append(symbol)
        save_stocks(STOCK_SYMBOLS)
        await ctx.send(f'Added {symbol} to watchlist.')
    else:
        await ctx.send(f'{symbol} already in watchlist.')

# manage stocks: !remove
@bot.command()
async def remove(ctx, stock):
    symbol = stock.upper()

    if symbol in STOCK_SYMBOLS:
        STOCK_SYMBOLS.remove(symbol)
        save_stocks(STOCK_SYMBOLS)
        await ctx.send(f'Successfully removed {symbol} from watchlist.')
    else:
        await ctx.send(f'{symbol} is not found in watchlist.')

# manage stocks: !Watchlist
@bot.command()
async def watchlist(ctx):
    if not STOCK_SYMBOLS:
        await ctx.send(f'Watchlist is empty. Please use !add <symbol> to add stocks.')
        return

    stock_data = get_stock_prices()

    if stock_data:
        embed = discord.Embed(
            title='Watchlist Prices',
            color=discord.Color.blue(),
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
# Visuals: !chart 
@bot.command()
async def chart(ctx, symbol, period, interval):
    symbol = symbol.upper()

    await ctx.send(f"Generating chart for {symbol}...")

    try:
        # Use candlestick chart only for short periods and intervals
        candlestick_periods = ['60m', '90m','1h', '4h','1d','5d']
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
            await ctx.send(f"Could not generate chart for {symbol}.")
    
    except Exception as e:
        await ctx.send(f'Error generating chart for {symbol}: {str(e)}')

@bot.command()
async def bollinger(ctx, symbol, period='1mo', interval='4h'):
    symbol = symbol.upper()

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


# --- Task loops ---
# Send notification of stock prices and percent change
timezone = ZoneInfo('America/New_York')
report_time = dt.time(hour=9, minute=30, tzinfo=timezone)
@tasks.loop(time=report_time)
async def market_open_report():
    """send stock notifications to the channel"""

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
    stock_data = get_stock_prices(compare_to='week_start' if is_weekend else 'previous_close')

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
                    graph = create_candlestick_graph(stock['symbol'], period='5d', interval='60m', after_hours=True)
                elif time_now.weekday() == 0: # Monday: last market open (Friday) for reference
                    graph = create_candlestick_graph(stock['symbol'], period='3d', interval='15m', after_hours=True)
                else: # last market open (Tuesday - Friday) for reference
                    graph = create_candlestick_graph(stock['symbol'], period='2d', interval='15m', after_hours=True)

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
