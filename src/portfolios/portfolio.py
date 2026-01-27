import discord
from discord.ext import commands
import sqlite3 as sq
from datetime import datetime as dt
import yfinance as yf

from src.portfolios.database.procedures import *


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
        await ctx.send(details)

    @bot.command()
    async def buy(ctx, portfolio_name: str, symbol, shares) -> str:
        """
        Buy shares of a stock to a portfolio.

        Command:
        !buy <portfolio_name> <stock_symbol> <amount_of_shares>
        """

        summary = buy_stock(conn, portfolio_name, symbol, shares)
        await ctx.send(summary)

    @bot.command()
    async def sell(ctx, portfolio_name: str, symbol, shares) -> str:
        """
        Sell shares of a stock to a portfolio.

        Command:
        !sell <portfolio_name> <stock_symbol> <amount_of_shares>
        """

        summary = sell_stock(conn, portfolio_name, symbol, shares)
        await ctx.send(summary)