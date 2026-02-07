import discord
from discord.ext import commands
import sqlite3 as sq
from datetime import datetime as dt
import yfinance as yf

from src.stock_data import get_asset_type
from src.portfolios.database.procedures import *
from src.portfolios.portfolio_logic import *
from src.config.utils import is_market_open, is_weekend


def setup_portfolio_commands(bot, conn):
    """Setup portfolio commands."""

    @bot.command()
    async def create(ctx, portfolio_name: str, initial_balance: float):
        """
        Create a new portfolio.

        Command:
        !create <portfolio_name> <initial_balance>
        """

        try:
            portfolio = create_portfolio(conn, portfolio_name, initial_balance)

            if portfolio is None:
                await ctx.send(f'portfolio {portfolio_name} already exists')
                return

            await ctx.send(portfolio)

        except Exception as e:
            await ctx.send(f'Error creating portfolio: {e}')

    @bot.command()
    async def balance(ctx, portfolio_name: str):
        """
        Check portfolio balance.
        
        Command:
        !balance <portfolio_name>
        """
        try:
            balance = portfolio_balance(conn, portfolio_name)

            await ctx.send(f'Portfolio {portfolio_name} balance: {balance["balance"]}')
        
        except Exception as e:
            print(f'Error retrieving balance for {portfolio_name}: {e}')

    @bot.command()
    async def rename(ctx, old_name: str, new_name: str):
        """
        Rename portfolio.
        
        Command:
        !rename <old_name> <new_name>
        """
        try:
            result = update_portfolio_name(conn, old_name, new_name)

            await ctx.send(result)

        except Exception as e:
            await ctx.send(f'Error renaming portfolio: {e}')

    @bot.command()
    async def delete(ctx, portfolio_name: str):
            """
            Delete portfolio.
            
            Command:
            !delete <portfolio_name>
            """

            try:
                deleted_rows = delete_portfolio(conn, portfolio_name)

                if deleted_rows == 0:
                    await ctx.send(f'Portfolio {portfolio_name} does not exist.')
                    return
                else:
                    await ctx.send(f'Deleted portfolio: {portfolio_name}')
                    return

            except Exception as e:
                await ctx.send(f'Error deleting portfolio')
                print(e)


    @bot.command()
    async def summary(ctx, portfolio_name: str):
        """
        View portfolio details.

        Command:
        !summary <portfolio_name>
        """

        summary_data = portfolio_data(conn, portfolio_name)
        
        
        embed = discord.Embed(
            title=f'Portfolio Summary: {summary_data["name"]}',
            description=f'''
            Current Balance: {summary_data['balance']}
            Total Holdings Value: {summary_data['total_holdings_value']}
            Total Portfolio Value: {summary_data['total_value']}
            Total Returns: {summary_data['total_returns']}
            ''',
            color = discord.Color.blue()
        )

        embed.add_field(name='\u200b', value='\u200b', inline=False)
        embed.add_field(name='Holdings:', value='\u200b', inline=False)

        for sector, holdings_list in summary_data['current_holdings'].items():

            embed.add_field(
                name=f'Sector: {sector}',
                value='\u200b',
                inline=False
            )
            for holdings in holdings_list:
                if 'total_value' not in holdings:
                    embed.add_field(
                        name=holdings['symbol'],
                        value=f'''
                        Shares: {holdings["shares"]}
                        Initial Value: {holdings["initial_value"]}
                        (Current price unavailable.)
                    ''', inline=True)
                else:  
                    embed.add_field(
                        name=holdings['symbol'],
                        value=f'''
                        Price: {holdings["price"]}
                        Shares: {holdings["shares"]}
                        Initial Value: {holdings["initial_value"]}
                        Total Value: {holdings['total_value']}
                        Returns: {holdings['returns']}''', inline=True)

        await ctx.send(embed=embed)

    @bot.command()
    async def assets(ctx, portfolio_name: str):
        """
        Check total value of a portfolio.
        
        Command: !assets <portfolio_name>
        """
        try:
            asset_metrics = get_asset_weights(conn, portfolio_name)

            description = f''
            for asset_name, metrics in asset_metrics.items():
        
                description += f"""
                Asset_type: {asset_name}
                Shares Metric: {metrics['share_weight']:.2%}
                Initial Value Metric: {metrics['initial_value_weight']:.2%}
                Value Metric: {metrics['current_value_weight']:.2%}
                """

            embed = discord.Embed(
                title=f'Portfolio Holdings: {portfolio_name}',
                description=f'{description}',
                color=discord.Color.blue()
            )  

            await ctx.send(embed=embed)
        except Exception as e:
            await ctx.send(f'Error retrieving asset data for {portfolio_name}: {e}')

    @bot.command()
    async def holdings(ctx, portfolio_name: str):
        """
        View portfolio holdings
        
        :param ctx: Description
        :param portfolio_name: Description
        :type portfolio_name: str
        """

        holdings_data = portfolio_data(conn, portfolio_name)

        embed = discord.Embed(
            title=f'Portfolio Holdings: {portfolio_name}',
            color=discord.Color.blue()
        )

        for sector, holdings_list in holdings_data['current_holdings'].items():
            
            embed.add_field(
                name=f'Sector: {sector}',
                value='\u200b',
                inline=False
            )
            for holdings in holdings_list:
                if 'total_value' not in holdings:
                    embed.add_field(
                        name=holdings['symbol'],
                        value=f'''
                        Shares: {holdings["shares"]}
                        Initial Value: {holdings["initial_value"]}
                        (Current price unavailable.)
                        ''',
                        inline=True
                    )
                else:  
                    embed.add_field(
                        name=holdings['symbol'],
                        value=f'''
                        Price: {holdings["price"]}
                        Shares: {holdings["shares"]}
                        Initial Value: {holdings["initial_value"]}
                        Total Value: {holdings['total_value']}
                        Returns: {holdings['returns']} 
                        ''',
                        inline=True
                    )
        
        await ctx.send(embed=embed)


    @bot.command()
    async def buy(ctx, portfolio_name: str, symbol, shares):
        """
        Buy shares of a stock to a portfolio.

        Command:
        !buy <portfolio_name> <stock_symbol> <amount_of_shares>
        """

        symbol = symbol.upper()

        if is_weekend():
            await ctx.send(f'Market is closed on weekends. Cannot execute buy order for {symbol}.')
            return
        if is_market_open(symbol) == False:
            await ctx.send(f'Market is closed. Cannot execute buy order for {symbol}.')
            return

        details = buy_stock(conn, portfolio_name, symbol, shares)

        embed = discord.Embed(
            title=f'Bought {shares} shares of {symbol} for portfolio: {portfolio_name}\nAsset Type: {details["asset_type"]}',
            description=f'''
            Operation: BUY
            Total Shares: {shares}
            Price-Per-Share: {details['price_per_share']}
            Total Price: {details['total_price']}
            New Balance: {details['new_balance']}
            ''',
            color = discord.Color.green()
        )
        embed.set_footer(text=f'At: {details["timestamp"]}')

        await ctx.send(embed=embed)

    @bot.command()
    async def sell(ctx, portfolio_name: str, symbol, shares):
        """
        Sell shares of a stock to a portfolio.

        Command:
        !sell <portfolio_name> <stock_symbol> <amount_of_shares>
        """

        symbol = symbol.upper()

        if is_market_open(symbol) == False:
            await ctx.send(f'Market is closed. Cannot execute sell order for {symbol} {is_market_open(symbol)}.')
            return
        
        details = sell_stock(conn, portfolio_name, symbol, shares)

        embed = discord.Embed(
            title=f'Sold {shares} shares of {symbol} for portfolio: {portfolio_name}\nAsset Type: {details["asset_type"]}',
            description=f'''
            Operation: SELL
            Total Shares: {shares}
            Price-Per-Share: {details['price_per_share']}
            Total Price: {details['total_price']}
            New Balance: {details['new_balance']}
            ''',
            color = discord.Color.green()
        )
        embed.set_footer(text=f'At: {details["timestamp"]}')

        await ctx.send(embed=embed)
    
def setup_portfolio_tasks(bot, conn):
    """Setup portfolio-related background tasks."""
    
    from src.config.config import CHANNEL_ID, TIME_NOW
    from src.stock_data import check_price_changes

    async def portfolio_changes(portfolio_name):
        """ 
        Detect large price changes for stocks in portfolios and send alerts to discord channel. 
        """
        await bot.wait_until_ready()
        
        if TIME_NOW.weekday() >= 5:
            return
        if TIME_NOW.hour < 9 or (TIME_NOW.hour == 9 and TIME_NOW.minute < 30) or TIME_NOW.hour > 16:
            return

        print(f"[{TIME_NOW}] PORTFOLIO - {portfolio_name}: Checking for big changes...")

        channel = bot.get_channel(CHANNEL_ID)
        if not channel:
            print(f'Channel {CHANNEL_ID} not found')
            return
        
        portfolio_id = get_portfolio_id(conn, portfolio_name)
        symbols = get_symbols(conn, portfolio_id)

        big_changes = check_price_changes(symbols, percent_threshold=1)

        if big_changes:
            print(f"PORTFOLIO - {portfolio_name}: Big price changes found.")

            symbols = ', '.join(stock['symbol'] for stock in big_changes)
            embed = discord.Embed(
                title=f"ALERT: Big Price Movement for {symbols} in Portfolio {portfolio_name}",
                color=discord.Color.red(),
                timestamp=TIME_NOW,
                )

            for stock in big_changes:
                star = '⭐️' if abs(stock['percentage_change']) >= 2 else ''
                change_emoji = '🟢' if stock['change'] >= 0 else '🔴'
                change_sign = "+" if stock['change'] >= 0 else ""

                embed.add_field(
                    name=f"{star} {change_emoji} {stock['symbol']}",
                    value=f"${stock['current_price']:.2f}\n{change_sign}{stock['percentage_change']:.2f}%", 
                    inline=True
                )
            await channel.send(embed=embed)

