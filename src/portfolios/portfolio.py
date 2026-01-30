import discord
from discord.ext import commands
import sqlite3 as sq
from datetime import datetime as dt
import yfinance as yf

from src.portfolios.database.procedures import *
from src.portfolios.portfolio_logic import *


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
    async def portfolios(ctx):
        """
        List all portfolios.

        Command:
        !portfolios
        """

        portfolios = list_portfolios(conn)

        await ctx.send(portfolios)

    @bot.command()
    async def view(ctx, portfolio_name: str):
        """
        View portfolio details.

        Command:
        !view <portfolio_name>
        """

        details = view_portfolio(conn, portfolio_name)
        
        
        embed = discord.Embed(
            title=f'Portfolio Summary: {details["name"]}',
            description=f'''
            Current Balance: {details['balance']}
            Total Holdings Value: {details['total_holdings_value']}
            Total Portfolio Value: {details['total_value']}
            Total Returns: {details['total_returns']}
            ''',
            color = discord.Color.blue()
        )

        embed.add_field(name='\u200b', value='\u200b', inline=False)
        embed.add_field(name='Holdings:', value='\u200b', inline=False)

        for holdings in details['current_holdings']:

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
    async def buy(ctx, portfolio_name: str, symbol, shares):
        """
        Buy shares of a stock to a portfolio.

        Command:
        !buy <portfolio_name> <stock_symbol> <amount_of_shares>
        """

        details = buy_stock(conn, portfolio_name, symbol, shares)
        
        embed = discord.Embed(
            title=f'Bought {shares} shares of {symbol} for portfolio: {portfolio_name}',
            description=f'''
            Operation: BUY
            Total Shares: {shares}
            Price-Per-Share: ${details['price_per_share']:.2f}
            Total Price: ${details['total_price']:.2f}
            New Balance: ${details['new_balance']:.2f}
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

        details = sell_stock(conn, portfolio_name, symbol, shares)

        embed = discord.Embed(
            title=f'Bought {shares} shares of {symbol} for portfolio: {portfolio_name}',
            description=f'''
            Operation: BUY
            Total Shares: {shares}
            Price-Per-Share: ${details['price_per_share']:.2f}
            Total Price: ${details['total_price']:.2f}
            New Balance: ${details['new_balance']:.2f}
            ''',
            color = discord.Color.green()
        )
        embed.set_footer(text=f'At: {details["timestamp"]}')

        await ctx.send(embed=embed)