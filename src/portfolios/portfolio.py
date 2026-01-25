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
        result = create_portfolio(conn, portfolio_name, initial_balance)
        await ctx.send(result)
    
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
    async def delete(ctx, portfolio_name: str):
        """
        Delete portfolio.
        
        Command:
        !delete <portfolio_name>
        """

        portfolio = delete_portfolio(conn, portfolio_name)

        await ctx.send(portfolio)