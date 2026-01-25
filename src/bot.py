# Time Date
import time
import datetime as dt
from datetime import datetime
# Data & API
import pandas as pd
import yfinance as yf
# Discord
import discord
from discord.ext import commands, tasks
# Utilities
import pytz
import asyncio
from functools import partial
import logging
# Scripts
from src.config.config import CHANNEL_ID, TIMEZONE, TIME_NOW, discord_token
from src.config.storage import STOCK_SYMBOLS, save_stocks
from src.utils.stock_data import get_prices_fast, get_prices_batch, check_price_changes, get_sp500_movers
from src.utils.charts import create_stock_graph, create_candlestick_graph, create_bollinger_bands

# --- Logging ---
logging.getLogger('discord').setLevel(logging.WARNING)
logging.getLogger('discord.http').setLevel(logging.WARNING)
logging.getLogger('discord.gateway').setLevel(logging.WARNING)

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)


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

# --- Visual Commands for Stocks ---
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
report_time = dt.time(hour=9, minute=30, tzinfo=TIMEZONE)
@tasks.loop(time=report_time)
async def market_open_report():
    """ 
    Periodic task that runs at market open (9:30am EST) on weekdays to send
    a summary report of the stock prices in watchlist and runs a weekend 
    summary of the previous week's performance on Saturdays to the channel. 
    """

    print(f"[{TIME_NOW}] Sending market open report...")

    channel = bot.get_channel(CHANNEL_ID)

    # fallback for channel id not found
    if not channel:
        print(f'Channel {CHANNEL_ID} not found')
        return

    # fallback for no stocks in watchlist
    if not STOCK_SYMBOLS:
        await channel.send('No stocks in watchlist.')
        return

    is_weekend = TIME_NOW.weekday() >= 5
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
                elif TIME_NOW.weekday() == 0: # Monday: last market open (Friday) for reference
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

    if TIME_NOW.weekday() >= 5:
        return
    if TIME_NOW.hour < 9 or (TIME_NOW.hour == 9 and TIME_NOW.minute < 30) or TIME_NOW.hour > 16:
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
@tasks.loop(minutes=15)
async def sp500_movers_alert():
    """
    Periodic task that checks a rotating subset of S&P 500 constituents for
    large moves and posts alerts to the configured channel during market hours.
    """

    await bot.wait_until_ready()

    if TIME_NOW.weekday() >= 5:
        return
    if TIME_NOW.hour < 9 or (TIME_NOW.hour == 9 and TIME_NOW.minute < 30) or TIME_NOW.hour >= 16:
        return

    print(f"[{TIME_NOW}] S&P 500: Checking for big changes...")

    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f'Channel {CHANNEL_ID} not found')
        return
    
    # Run the blocking stock data operation in a separate thread to prevent blocking the event loop
    loop = asyncio.get_event_loop()
    sp_movers = await loop.run_in_executor(None, partial(get_sp500_movers, percent_threshold=3, batch_size=50))

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