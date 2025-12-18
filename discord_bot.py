# Time 
from ast import Dict
import time
import datetime as dt
from datetime import datetime, timedelta, time as dtime
from turtle import title
# Data & API
from pandas._libs import interval
from pandas.core.arrays import period
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



# --- FUNCTIONS ---
# --- Get Stock Price Data ---
def get_stock_prices():
    # compare prices from 4 hours ago to current price
    stock_data = [] # to store the stock price data
    for symbol in STOCK_SYMBOLS:
        try:
            ticker = yf.Ticker(symbol)
            eastern = pytz.timezone('US/Eastern')
            time_now = dt.datetime.now(eastern)

            # fall back statement to get the updates on weekends
            if time_now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
                while time_now.weekday() >= 5:  # weekend
                    time_now -= timedelta(days=1)
                print(f'Market Closed for {symbol}')

            current_price = ticker.fast_info.last_price

            # get yesterdays price
            hist = ticker.history(period='5d')
            if not hist.empty and len(hist) >= 2:
                # get most recent previous close from yesterday
                prev_close = hist['Close'].iloc[-2]

                change = current_price - prev_close
                percentage_change = ((current_price - prev_close) / prev_close) * 100

                # add data captured to the stock data list
                stock_data.append({
                    'symbol': symbol,
                    'current_price': current_price,
                    'percentage_change': percentage_change,
                    'change': change
                })
        except Exception as e:
            print(f'Error getting data for {symbol}: {e}')

    # pass stock data to notifications
    return stock_data

# --- Check price changes command ---
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

                # checks the pecent change if the absolute value is greater than 4
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

# --- S&P 500 Alerts Function ---
sp500_cycle = None
def get_sp500_movers(percent_threshold=2, batch_size=50):

    global sp500_cycle

    try:
        csv_url = 'https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents.csv'
        
        response = requests.get(csv_url)
        response.raise_for_status()

        lines = response.text.strip().split('\n')
        headers = lines[0].split(',')

        sp500_symbols = [line.split(',')[0] for line in lines[1:]]

        if sp500_cycle is None:
            sp500_cycle = itertools.cycle(sp500_symbols)

        batch = [next(sp500_cycle) for _ in range(batch_size)]
        big_movers = []

        for symbol in batch:
            if symbol not in STOCK_SYMBOLS: #checks if s&p 500 symbol isn't in watchlist
                try:
                    #get the ticker symbols
                    ticker = yf.Ticker(symbol)
                    #get the last price/current price
                    current_price = ticker.fast_info.last_price

                    # check if stock symbol is in last checked prices to move on with the function
                    if symbol in sp500_last_checked_prices:
                        last_price = sp500_last_checked_prices[symbol] # gets the last checked price and compares percentage to it
                        percentage_change = ((current_price - last_price) / last_price) * 100

                        # checks the pecent change if the absolute value is greater than 4
                        if abs(percentage_change) >= percent_threshold:
                            # add stock data to big_changes list
                            big_movers.append({
                                'symbol': symbol,
                                'current_price': current_price,
                                'last_price': last_price,
                                'percentage_change': percentage_change,
                            })

                    # checks if price of the stock is equal to current price for storing reference for next comparison
                    sp500_last_checked_prices[symbol] = current_price

                except Exception as e:
                    print(f'Error getting data for {symbol}: {e}')

        # pass big changes
        return big_movers

    except Exception as e:
        print(f'Error checking S&P 500: {e}')  
        return []

# --- Create a Candlestick Chart for a stock ---
def create_candlestick_graph(symbol, days, interval, filter_hours=True):
    # create candlestick chart for a stock
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=f'{days}d', interval=f'{interval}')

        hist = hist.tz_convert('US/Eastern') # convert time to eastern time for graphs
            
        if filter_hours:   
            hist = hist[hist.index.dayofweek < 5]
            hist = hist.between_time('9:30', '16:00')

        if hist.empty:
            return None
        
        hist_reset = hist.reset_index()

        buf = io.BytesIO()

        mpf.plot(
            hist, 
            type='candle',
            style='charles',
            title=f"{symbol} - Last {days} Day{'s' if days != 1 else ''}",
            ylabel='Price ($)',
            volume=True,
            savefig=dict(fname=buf, dpi=150, bbox_inches='tight')
        )
        buf.seek(0)
        plt.close('all')
        return buf

    except Exception as e:
        print(f'Error creating graph for {symbol}: {e}')
        plt.close('all')
        return None

# --- Create a Chart for stock report ---
def create_stock_graph(symbol, days, interval, filter_hours=True):
    try:
        ticker = yf.Ticker(symbol)

        hist = ticker.history(period=f'{days}d', interval=f'{interval}m')

        hist = hist.tz_convert('US/Eastern') # convert time to eastern time for graphs
            
        if filter_hours:   
            hist = hist[hist.index.dayofweek < 5]
            hist = hist.between_time('9:30', '16:00')

        if hist.empty:
            return None
        
        hist_reset = hist.reset_index()

        plt.figure(figsize=(10, 6))
        sns.set_style('whitegrid')

        ax = sns.lineplot(data=hist_reset, x=range(len(hist_reset)), y='Close', linewidth=1.5)

        # custom Xticks
        if days >= 7:
            # daily for each day of the week
            num_ticks = 5
            tick_positions = [int(i * (len(hist_reset) - 1) / (num_ticks - 1)) for i in range(num_ticks)]
            tick_labels = [hist_reset['Datetime'].iloc[i].strftime('%m/%d') for i in tick_positions]
        else:
            # hourly ticks from 9:30 to 4:00
            num_ticks = 8
            tick_positions = [int(i * (len(hist_reset) - 1) / (num_ticks - 1)) for i in range(num_ticks)]
            tick_labels = [hist_reset['Datetime'].iloc[i].strftime('%H:%M') for i in tick_positions]

        plt.xticks(tick_positions, tick_labels, fontsize=9)

        plt.title(f'{symbol} Stock Price - Last {days} Day{'s' if days != 1 else ''}', fontsize=17, fontweight='bold')
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
    

# TODO: bollinger bands function


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
    if STOCK_SYMBOLS:
        await ctx.send(f"Watching:\n {', '.join(sorted(STOCK_SYMBOLS))}")
    else:
        await ctx.send(f'Watchlist is empty. Please use !add <symbol> to add stocks.')


# --- Visuals for Stocks ---
# Visuals: !chart 
@bot.command()
async def chart(ctx, symbol, days, interval):
    symbol = symbol.upper()

    await ctx.send(f"Generating chart for {symbol}...")

    graph = create_candlestick_graph(symbol, days, interval)

    if graph:
        file = discord.File(graph, filename=f'{symbol}_chart.png')
        await ctx.send(file=file)

    else:
        await ctx.send(f"Could not generate chart for {symbol}.")


# --- Task loops ---
# Send notification of stock prices and percent change
@tasks.loop(minutes=30)
async def market_open_report():
    """send stock notifications to the channel"""

    # timezones
    eastern = pytz.timezone('US/Eastern')
    time_now = dt.datetime.now(eastern)

    if time_now.hour != 9 or time_now.minute < 30 or time_now.minute >= 40:
        return

    print(f"[{datetime.now()}] Sending market open report...") # terminal print to check if bot is running properly

    channel = bot.get_channel(CHANNEL_ID)

    # fallback for channel id not found
    if not channel:
        print(f'Channel {CHANNEL_ID} not found')
        return

    # fallback for no stocks in watchlist
    if not STOCK_SYMBOLS:
        await channel.send('No stocks in watchlist.')
        return

    stock_data = get_stock_prices()

    if stock_data:
        # message format: embedded
        is_weekend = time_now.weekday() >= 5

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
            if is_weekend:
                graph = create_candlestick_graph(stock['symbol'], days=5, interval='30m', filter_hours=False)
            elif time_now.weekday() == 0: # Monday: get the last time market was open (Friday) for reference
                graph = create_candlestick_graph(stock['symbol'], days=3, interval='5m', filter_hours=True)
            else: # get the last time market was open (Tuesday - Friday) for reference
                graph = create_candlestick_graph(stock['symbol'], days=2, interval='5m', filter_hours=True)

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

    # Checks if weekend - Doesn't run on weekends
    time_now = dt.datetime.now(pytz.timezone('US/Eastern'))
    if time_now.weekday() >= 5:
        return
    
    if time_now.hour < 9 or (time_now.hour == 9 and time_now.minute < 30) or time_now.hour > 16:
        return

    print(f"[{datetime.now()}] Checking for big changes...") # terminal print to check if bot is running properly

    # tells bot which channel to send the message to 
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f'Channel {CHANNEL_ID} not found') # error if channel ID doesnt exist
        return

    big_changes = check_price_changes()

    # statement to detect if big changes is True
    if big_changes:
        print("Big price changes found.") # Terminal print

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
        print("Big price changes not found.") # Terminal print

# Send S&P 500 Movers Alerts
@tasks.loop(minutes=10)
async def sp500_movers_alert():
     # Checks if weekend - Doesn't run on weekends
    time_now = dt.datetime.now(pytz.timezone('US/Eastern'))
    if time_now.weekday() >= 5:
        return
    
    if time_now.hour < 9 or (time_now.hour == 9 and time_now.minute < 30) or time_now.hour > 16:
        return
    
    # tells bot which channel to send the message to 
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f'Channel {CHANNEL_ID} not found') # error if channel ID doesnt exist
        return
    
    sp_movers = get_sp500_movers(threshold=2, batch_size=50)

    if sp_movers:
        symbols = ', '.join(stock['symbol'] for stock in sp_movers)

        embed = discord.Embed(
            title= f'S&P 500 ALERT: Big Price Movement for {symbols}',
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

# sending waiting until bot is connected before running to avoid errors and return nothing   
@check_big_changes.before_loop
async def before_check_big_prices():
    await bot.wait_until_ready()

@market_open_report.before_loop
async def before_send_stock_prices():
    await bot.wait_until_ready()

sp500_movers_alert.before_loop
async def before_send_sp500_alert():
    await bot.wait_until_ready()


bot.run(discord_token)
