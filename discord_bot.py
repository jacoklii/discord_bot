# Time Imports
import time
import datetime as dt
from datetime import datetime, timedelta, time as dtime
# Data imports
import requests
from curl_cffi.requests import headers
import pandas as pd
from pandas._libs import interval
import discord
from discord.ext import commands, tasks
import yfinance as yf
# Management Imports
import pytz
import os
import json
import itertools
from dotenv import load_dotenv


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
    for stock_symbol in STOCK_SYMBOLS:
        try:
            ticker = yf.Ticker(stock_symbol)
            eastern = pytz.timezone('US/Eastern')
            time_now = dt.datetime.now(eastern)

            # fall back statement to get the updates on weekends
            if time_now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
                while time_now.weekday() >= 5:  # weekend
                    time_now -= timedelta(days=1)
                print(f"Market closed for {stock_symbol}.")

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
                    'symbol': stock_symbol,
                    'current_price': current_price,
                    'percentage_change': percentage_change,
                    'change': change
                })
        except Exception as e:
            print(f'Error getting data for {stock_symbol}: {e}')

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
def get_sp500_movers(threshold=1, batch_size=50):

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
            try:
                #get the ticker symbols
                ticker = yf.Ticker(symbol)
                #get the last price/current price
                current_price = ticker.fast_info.last_price

                # check if stock symbol is in last checked prices to move on with the function
                if symbol in last_checked_prices:
                    last_price = last_checked_prices[symbol] # gets the last checked price and compares percentage to it
                    percentage_change = ((current_price - last_price) / last_price) * 100

                    # checks the pecent change if the absolute value is greater than 4
                    if abs(percentage_change) >= threshold:
                        # add stock data to big_changes list
                        big_movers.append({
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
        return big_movers

    except Exception as e:
        print(f'Error checking S&P 500: {e}')  
        return []

# TODO: visual graphing       
# TODO: bollinger bands function



# --- BOT EVENT ---
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    market_open_report.start()
    check_big_changes.start()



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


# --- Task loops ---
# Send notification of stock prices and percent change
@tasks.loop(hours=24)
async def market_open_report():
    """send stock notifications to the channel"""

    # timezones
    eastern = pytz.timezone('US/Eastern')
    time_now = dt.datetime.now(eastern)
    
    if time_now.hour != 9 or time_now.minute < 30 or time_now.minute >= 35: # only run between 9:30-9:35 AM
        return

    # get discord channel
    channel = bot.get_channel(CHANNEL_ID)

    # fallback for channel ide not found
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
        weekday_embed = discord.Embed(
            title='Market Open Report = 9:30 AM EST',
            color=discord.Color.green(),
            timestamp=dt.datetime.now(),
            )
        
        weekend_embed = discord.Embed(
            title='Weekend Market report',
            description='Market is closed on weekends.',
            color=discord.Color.blue(),
            timestamp=dt.datetime.now(),
            )
        
        # give percentage change greater than 0 or less than 0 a different color
        for stock in stock_data:
            star = '⭐️' if abs(stock['percentage_change']) >= 2 else ''
            change_emoji = '🟢' if stock['change'] >= 0 else '🔴'
            change_sign = "+" if stock['change'] >= 0 else ""

            # fall back for weekends
            if time_now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
                while time_now.weekday() >= 5:  # weekend
                    time_now -= timedelta(days=1)

                weekend_embed.add_field(
                name=f"{change_emoji} {stock['symbol']}",
                value=f"${stock['current_price']:.2f}\n{change_sign}{stock['percentage_change']:.2f}%", 
                inline=True
                )
                # send the weekend embed for weekends
                await channel.send(embed=weekend_embed)
                return
            
            # adding stock info to embed parameters
            weekday_embed.add_field(
                name=f"{star} {change_emoji} {stock['symbol']}",
                value=f"${stock['current_price']:.2f}\n{change_sign}{stock['percentage_change']:.2f}%", 
                inline=True
            )

        # sending the embed through the message type
        await channel.send(embed=weekday_embed)
    else:
        await channel.send('Could not get stock prices/data')

# send Alert if stock price made a big change
@tasks.loop(minutes=5)
async def check_big_changes():

    print(f"[{datetime.now()}] Checking for big changes...") # terminal print to check if bot is running properly

    # tells bot which channel to send the message to 
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f'Channel {CHANNEL_ID} not found') # error if channel ID doesnt exist
        return

    big_changes = check_price_changes()

    # statement to detect if big changes is True
    if big_changes:
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



# sending waiting until bot is connected before running to avoid errors and return nothing   
@check_big_changes.before_loop
async def before_check_big_prices():
    await bot.wait_until_ready()

@market_open_report.before_loop
async def before_send_stock_prices():
    await bot.wait_until_ready()


bot.run(discord_token)
