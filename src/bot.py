import discord
from discord.ext import commands

from src.config.config import get_portfolio_connection, discord_token
from src.portfolios.database.schema import create_database_schema
from src.portfolios.portfolio import setup_portfolio_commands

from src.discord.commands import setup_watchlist_commands, setup_chart_commands
from src.discord.tasks import setup_tasks


intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    """
    Discord event fired when the bot has connected and is ready.

    Starts the periodic background tasks if they are not already running.
    """
    if not bot.is_ready():
        await bot.wait_until_ready()
        print(f"Bot is ready. Logged in as {bot.user}.")

    global task_dict

    for task_name, task in task_dict.items():

        if not task.is_running():
            task.start()
            print(f'Started {task_name} task.')

setup_watchlist_commands(bot)
setup_chart_commands(bot)

portfolio_db = get_portfolio_connection()
create_database_schema(portfolio_db)
setup_portfolio_commands(bot, portfolio_db)

task_dict = setup_tasks(bot)

@bot.event
async def on_close():
    """
    Stop the bot and close the portfolio database connection.
    """
    portfolio_db.close()
    bot.loop.stop()

bot.run(discord_token)