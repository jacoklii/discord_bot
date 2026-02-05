import yfinance as yf
import discord
from discord.ext import commands

from src.config.storage import STOCK_SYMBOLS, save_stocks
from src.stock_data import get_batch_prices
from src.charts import create_stock_graph, create_candlestick_graph, create_bollinger_bands

# --- Watchlist Commands ---
def setup_watchlist_commands(bot):

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

        stock_data = get_batch_prices(STOCK_SYMBOLS)

        if stock_data:
            embed = discord.Embed(
                title='Watchlist Prices',
                color=discord.Color.blue()
                )
    
            for symbol, price in stock_data.items():
                embed.add_field(
                    name=symbol,
                    value=f'${price:.2f}'
                )

            await ctx.send(embed=embed)
        else:
            await ctx.send(f"Watching:\n {', '.join(sorted(STOCK_SYMBOLS))}.\n Could not get stock prices/data.")

# --- Visual Commands ---
def setup_chart_commands(bot):

    @bot.command()
    async def chart(ctx, symbol, period='5d', interval='30m'):
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
            await ctx.send(f'An error occurred while generating the chart for {symbol}: {str(e)} Please try again later.')

    @bot.command()
    async def bollinger(ctx, symbol, period='1mo', interval='4h'):
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

    @bot.command()
    async def periods(ctx):
        """
        Command: !periods

        Sends a list of valid periods for chart generation.
        """
        periods = [
            '1m', '2m', '5m', '15m', '30m', '60m', '90m', '4h',
            '1d', '2d', '3d', '5d', '1wk', '1mo', '3mo', '6mo',
            '1y', '2y', '5y', '10y', 'ytd', 'max'
        ]
        await ctx.send(f'Valid periods are: {", ".join(periods)}')
        
    @bot.command()
    async def intervals(ctx):
        """
        Command: !intervals

        Sends a list of valid intervals for chart generation.
        """
        intervals = [
            '1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h',
            '1d', '5d', '1wk', '1mo', '3mo'
        ]
        await ctx.send(f'Valid intervals are: {", ".join(intervals)}')