import discord
from discord.ext import tasks

from src.config.config import TIMEZONE, TIME_NOW, CHANNEL_ID
from src.config.storage import STOCK_SYMBOLS
from src.stock_data import check_price_changes, get_sp500_movers
import datetime as dt
from datetime import datetime
import asyncio
from functools import partial

from src.config.utils import is_weekend
from src.stock_data import get_batch_prices, get_price_comparison, get_sp500_movers, percent_change

def setup_tasks(bot):
    # --- Task loops ---
    report_time = dt.time(hour=9, minute=30, tzinfo=TIMEZONE)
    @tasks.loop(hours=24)
    async def market_open_report():
        """ 
        Periodic task that runs at market open (9:30am EST) on weekdays to send
        a summary report of the stock prices in watchlist and runs a weekend 
        summary of the previous week's performance on Saturdays to the channel. 
        """
        pass
        print(f"[{TIME_NOW}] Sending market open report...")

        channel = bot.get_channel(CHANNEL_ID)

        if not channel:
            print(f'Channel {CHANNEL_ID} not found')
            return
        if not STOCK_SYMBOLS:
            await channel.send('No stocks in watchlist.')
            return

        current_prices = get_batch_prices(STOCK_SYMBOLS)
        comparison_prices = get_price_comparison(STOCK_SYMBOLS, compare_to='week')
        
        stock_data = []
        for symbol in STOCK_SYMBOLS:
            if symbol in current_prices and symbol in comparison_prices:
                current_price = current_prices[symbol]
                compare_price = comparison_prices[symbol]
                percentage_change, change = percent_change(current_price, compare_price)
                
                stock_data.append({
                    'symbol': symbol,
                    'current_price': current_price,
                    'percentage_change': percentage_change,
                    'change': change
                })

        if stock_data:
            if is_weekend():
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
            
            for stock in stock_data:
                star = '⭐️' if abs(stock['percentage_change']) >= 2 else ''
                change_emoji = '🟢' if stock['change'] >= 0 else '🔴'
                change_sign = "+" if stock['change'] >= 0 else ""

                embed.add_field(
                    name=f"{star} {change_emoji} {stock['symbol']}",
                    value=f"${stock['current_price']:.2f}\n{change_sign}{stock['percentage_change']:.2f}%", 
                    inline=True
                )
            await channel.send(embed=embed)
        else:
            await channel.send('Could not get stock prices/data.')

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

        big_changes = check_price_changes(STOCK_SYMBOLS, percent_threshold=1)

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
