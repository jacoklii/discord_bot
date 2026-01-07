# Time Date
import time
import datetime as dt
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
# Data
import pandas as pd
import yfinance as yf
# Utilities
import io
import logging
# Graphing
import mplfinance as mpf
import seaborn as sns
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def create_candlestick_graph(symbol, period, interval, after_hours=False):
    """
    Create a candlestick chart image for the given symbol and return a
    BytesIO buffer containing the PNG image.

    Args:
        symbol (str): Stock ticker symbol.
        period (str): Period string accepted by yfinance (e.g. '4h', '5d').
        interval (str): Interval string accepted by yfinance (e.g. '1m', '1h').
        after_hours (bool): If True, include extended/pre/post market hours.

    Returns:
        io.BytesIO or None: In-memory PNG image buffer on success, or None on error.
    """
    try:
        ticker = yf.Ticker(symbol)
        hist = ticker.history(period=period, interval=interval, prepost=True)

        hist = hist.tz_convert('US/Eastern') # convert time to eastern time for graphs          
        hist = hist[hist.index.dayofweek < 5]

        # filter hours
        if not after_hours:
            hist = hist.between_time('9:30', '16:00')
        else:
            hist = hist.between_time('4:00', '20:00')

        if hist.empty:
            return None

        buf = io.BytesIO()

        mpf.plot(
            hist, 
            type='candle',
            style='charles',
            title=f"{symbol} - Last {period}",
            ylabel='Price ($)',
            savefig=dict(fname=buf, dpi=100, bbox_inches='tight')
        )

        buf.seek(0)
        plt.close()
        return buf

    except Exception as e:
        logging.error(f'Error creating graph for {symbol}: {e}')
        plt.close()
        return None

def create_stock_graph(symbol, period, interval, after_hours=False):
    """
    Create a line chart of the stock's closing prices and return a PNG buffer.

    Args:
        symbol (str): Stock ticker symbol.
        period (str): Time range to fetch (yfinance format, e.g. '1mo').
        interval (str): Data interval (e.g. '1d', '4h').
        after_hours (bool): Whether to include after-hours data.

    Returns:
        io.BytesIO or None: PNG image buffer if successful, otherwise None.
    """
    try:
        ticker = yf.Ticker(symbol)

        hist = ticker.history(period=period, interval=interval, prepost=True)

        if hist.index.tz is None:
            hist = hist.tz_localize('UTC').tz_convert('US/Eastern') # ensure tz-aware before converting
        else:
            hist = hist.tz_convert('US/Eastern') # convert time to eastern time for graphs
        hist = hist[hist.index.dayofweek < 5] # remove weekends

        # filter hours
        if 'm' in interval or 'h' in interval:
            if not after_hours:
                hist = hist.between_time('9:30', '16:00')
            else:
                hist = hist.between_time('4:00', '20:00')

        if hist.empty:
            return None
        
        hist_reset = hist.reset_index()

        date_col = 'Date' if 'Date' in hist_reset.columns else 'Datetime'

        plt.figure(figsize=(10, 6))
        sns.set_style('whitegrid')

        sns.lineplot(data=hist_reset, x=range(len(hist_reset)), y='Close', linewidth=1.5)

        total_days = (hist_reset[date_col].iloc[-1] - hist_reset[date_col].iloc[0]).days

        # custom ticks
        if total_days <= 1:
            num_ticks = min(8, len(hist_reset))
            date_format = '%H:%M'
        elif total_days <= 7:
            num_ticks = min(7, len(hist_reset))
            date_format = '%m/%d %H:%M'
        elif total_days <= 31:
            num_ticks = min(10, len(hist_reset))
            date_format = '%m/%d'
        elif total_days <= 365:
            num_ticks = min(12, len(hist_reset))
            date_format = '%b %d'
        else:
            num_ticks = min(12, len(hist_reset))
            date_format = '%b %Y'

        tick_positions = [int(i * (len(hist_reset) - 1) / (num_ticks - 1)) for i in range(num_ticks)]
        tick_labels = [hist_reset[date_col].iloc[i].strftime(date_format) for i in tick_positions]

        plt.xticks(tick_positions, tick_labels, fontsize=9, rotation=45)
        plt.yticks(fontsize=9)

        plt.title(f'{symbol} Stock Price - Last {period}', fontsize=17, fontweight='bold')
        plt.xlabel('Date', fontsize=11)
        plt.ylabel('Closing Price ($)', fontsize=11)
        plt.yticks(fontsize=9)
        plt.tight_layout()

        # Buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close('all')

        return buf

    except Exception as e:
        print(f'Error creating graph for {symbol}: {e}')
        plt.close('all')
        return None

def create_bollinger_bands(symbol, period='1mo', interval='1d', window=20, num_of_std=2):
    """
    Calculate Bollinger Bands for a symbol, render the bands and price as a
    PNG image, and return an in-memory buffer.

    Args:
        symbol (str): Stock ticker symbol.
        period (str): Period string for historical data (default '1mo').
        interval (str): Interval for data points (default '1d').
        window (int): Rolling window size for the moving average (default 20).
        num_of_std (int): Number of standard deviations for the upper/lower bands.

    Returns:
        io.BytesIO or None: PNG image buffer containing the plotted Bollinger Bands, or None on error.
    """

    try:
        ticker = yf.Ticker(symbol)
        prepost = 'm' in interval or 'h' in interval
        hist = ticker.history(period=period, interval=interval, prepost=prepost, auto_adjust=False)

        if prepost:
            hist = hist.tz_convert('US/Eastern')
            hist = hist[hist.index.dayofweek < 5]

        rolling_mean = hist['Close'].rolling(window=window).mean()
        rolling_std = hist['Close'].rolling(window=window).std()

        upper_band = rolling_mean + (rolling_std * num_of_std)
        lower_band = rolling_mean - (rolling_std * num_of_std)

        df = pd.DataFrame({
            'Close': hist['Close'],
            'Middle_Band': rolling_mean,
            'Upper_Band': upper_band,
            'Lower_Band': lower_band
        }).dropna()

        df_reset = df.reset_index()
        df_reset = df_reset.rename(columns={df_reset.columns[0]: 'Date'})

        plt.figure(figsize=(10, 6))
        sns.set_style('whitegrid')
        sns.lineplot(data=df_reset, x=range(len(df_reset)), y='Close', label=f'{symbol} Close Price', color='blue')
        
        # Bollinger Bands
        sns.lineplot(data=df_reset, x=range(len(df_reset)), y='Middle_Band', label='Middle Band (SMA)', color='orange')
        sns.lineplot(data=df_reset, x=range(len(df_reset)), y='Upper_Band', label='Upper Band', color='green')
        sns.lineplot(data=df_reset, x=range(len(df_reset)), y='Lower_Band', label='Lower Band', color='red')


        plt.fill_between(range(len(df_reset)), df_reset['Close'].values, df_reset['Upper_Band'].values, 
        where=(df_reset['Close'].values <= df_reset['Upper_Band'].values), 
        alpha=0.1, color='green', label='Overbought Zone')

        plt.fill_between(range(len(df_reset)), df_reset['Close'].values, df_reset['Lower_Band'].values, 
        where=(df_reset['Close'].values >= df_reset['Lower_Band'].values), 
        alpha=0.1, color='red', label='Oversold Zone')


        total_days = (df_reset['Date'].iloc[-1] - df_reset['Date'].iloc[0]).days
        
        if total_days <= 1:
            num_ticks = min(8, len(df_reset))
            date_format = '%H:%M'
        elif total_days <= 7:
            num_ticks = min(7, len(df_reset))
            date_format = '%m/%d %H:%M'
        elif total_days <= 31:
            num_ticks = min(10, len(df_reset))
            date_format = '%m/%d'
        elif total_days <= 365:
            num_ticks = min(12, len(df_reset))
            date_format = '%b %d'
        else:
            num_ticks = min(12, len(df_reset))
            date_format = '%b %Y'

        tick_positions = [int(i * (len(df_reset) - 1) / (num_ticks - 1)) for i in range(num_ticks)]
        tick_labels = [df_reset['Date'].iloc[i].strftime(date_format) for i in tick_positions]

        plt.title(f'Bollinger Bands - {symbol} Stock Price - Last {period}', fontsize=17, fontweight='bold')
        plt.xlabel('Date', fontsize=11)
        plt.ylabel('Price ($)', fontsize=11)
        plt.xticks(ticks=tick_positions, labels=tick_labels, fontsize=9, rotation=45)
        plt.yticks(fontsize=9)
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        # Buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        buf.seek(0)
        plt.close('all')

        return buf

    except Exception as e:
        print(f'Error creating graph for {symbol}: {e}')
        plt.close('all')
        return None
