import discord
from discord.ext import tasks

from src.config.config import TIME_NOW, CHANNEL_ID
from src.config.storage import STOCK_SYMBOLS
import datetime as dt
from datetime import datetime
import asyncio

from src.config.utils import is_weekend, stock_changes
from src.stock_data import check_price_changes

def setup_watchlist_tasks(bot):

    @tasks.loop(minutes=5)
    async def watchlist_changes():
        """
        Periodic task that runs every five minutes during market hours to check
        the watchlist for large price movements and post alerts to the channel.
        """

        await bot.wait_until_ready()

        if is_weekend():
            return
        if TIME_NOW.hour < 9 or (TIME_NOW.hour == 9 and TIME_NOW.minute < 30) or TIME_NOW.hour > 16:
            return

        print(f"[{datetime.now()}] WATCHLIST: Checking for big changes...")

        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            print(f'Channel {CHANNEL_ID} not found')
            return

        big_changes_dict = check_price_changes(STOCK_SYMBOLS, percent_threshold=1)

        # statement to detect if big changes is True
        if big_changes_dict:
            print("WATCHLIST: Big price changes found.")

            symbols = ', '.join(big_changes_dict.keys())
            embed = discord.Embed(
                title=f"ALERT: Big Price Movement for {symbols}",
                color=discord.Color.red(),
                timestamp=datetime.now(),
                )

            for stock in big_changes_dict.values():
                star, emoji, sign = stock_changes(stock['percentage_change'])


                embed.add_field(
                    name=f"{star}{emoji} {stock['symbol']}",
                    value=f"${stock['current_price']:.2f}\n{sign}{stock['percentage_change']:.2f}%", 
                    inline=True
                    )
            await channel.send(embed=embed)
        else:
            print("WATCHLIST: Big price changes not found.")

    return {
        'watchlist_changes': watchlist_changes,
    }