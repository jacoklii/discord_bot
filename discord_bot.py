# imports

import time
from pandas._libs import interval
import yfinance as yf
import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import pytz
import os
from dotenv import load_dotenv

# .env and Tokens
load_dotenv()
discord_token = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

# channel id and stock symbols
CHANNEL_ID = 1435810254783778933
STOCK_SYMBOLS = ['AAPL', 'NVDA', 'GOOG', 'TSLA', 'META']
last_checked_prices = {}

# function to get the current price of the stock and the percentage change data
# compares price from 4 hours ago to current time to get percent change and total change
def get_stock_prices():
    stock_data = [] # to store the stock price data
    for stock_symbol in STOCK_SYMBOLS:
        try:
            ticker = yf.Ticker(stock_symbol)
            eastern = pytz.timezone('US/Eastern')
            # get time now data and date in eastern time
            time_now = datetime.now(eastern)

            # fall back statement to get the updates on weekends
            if time_now.weekday() >= 5:  # 5 = Saturday, 6 = Sunday
                while time_now.weekday() >= 5:  # weekend
                    time_now -= timedelta(days=1)
                print(f"Market closed for {stock_symbol}")

            # get the rest of the data and date
            time_4_hours_ago = time_now - timedelta(hours=4)
            start_time = time_now - timedelta(days=1)
            end_time = time_now
            
            # Download stock price data
            data = yf.download(
                stock_symbol,
                start = start_time,
                end=end_time,
                interval='5m',
                prepost=True
            )
            
            # statement when first running the script if theirs data to calculate percentage change to avoid errors
            if not data.empty:
                closest_index = data.index.get_indexer([time_4_hours_ago], method='nearest')[0] # get the last price from 4 hours ago
                last_price = float(data.iloc[closest_index]['Close']) # locate the last price
                current_price = ticker.fast_info.last_price # current price using fast info of the stock

                # grab the current price and the last price from the dataframe to calculate change
                change = current_price - last_price
                percentage_change = ((current_price - last_price) / last_price) * 100 # stock data percentage change

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

# get current price and compare it to last_checked_price
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

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')
    send_stock_prices.start()
    check_big_changes.start()

@bot.command()
async def current_price(ctx):
    # check current stock price of the given stock
    input_text = ctx.message.content.split()
    if len(input_text) < 2:
        await ctx.send('Please provide a stock symbol')

    # checks if stock symbol was asked
    for stock_symbol in input_text[1:]:
        ticker = yf.Ticker(str(stock_symbol)) # grabs ticker
        todays_price = ticker.fast_info.last_price
        await ctx.send(f'The current price of {stock_symbol} is ${todays_price}')

# --- Send notification of the stock prices and percent changes ---
@tasks.loop(hours=1, count=None)
async def send_stock_prices():
    """send stock notifications to the channel"""

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f'Channel {CHANNEL_ID} not found')
        return

    stock_data = get_stock_prices()

    if stock_data:
        # message format: embedded
        embed = discord.Embed(
            title='UPDATE: Current stock prices:',
            color=discord.Color.blue(),
            timestamp=datetime.now(),
            )
        # give percentage change greater than 0 or less than 0 a different color
        for stock in stock_data:
            change_emoji = '🟢' if stock['change'] >= 0 else '🔴'
            change_sign = "+" if stock['change'] >= 0 else ""

            # adding stock info to embed parameters
            embed.add_field(
                name=f"{change_emoji} {stock['symbol']}",
                value=f"${stock['current_price']:.2f}\n{change_sign}${stock['change']:.2f}\n{change_sign}{stock['percentage_change']:.2f}%", 
                inline=True
            )

        # sending the embed through the message type
        await channel.send(embed=embed)
    else:
        await channel.send('Could not get stock prices/data')

# --- send alert if stock price made a big change ---
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
        embed = discord.Embed(
            title='ALERT: Big Price Movement',
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


bot.run(discord_token)
