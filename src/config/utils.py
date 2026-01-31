from src.config.config import TIMEZONE, TIME_NOW

def percent_change(current, reference):
    """Calculate percentage change and compare reference to current value."""
    try:
        change = current - reference
        percentage = float(change / reference) * 100

        return percentage, change
    
    except ZeroDivisionError:
        return 0.0, 0.0
    
    except Exception as e:
        print(f'Error calculating percent change: {e}')
        return 0.0, 0.0

def clean_symbol(symbol):
    """Convert symbol format for yfinance from dots to hyphens"""
    return symbol.replace('.','-')

def is_weekend() -> bool:
    """Check if the current day is a weekend."""
    return TIME_NOW.weekday() >= 5

def is_market_open(current_time=None, after_hours=False) -> bool:
    """Check if the stock market is currently open."""
    if current_time is None:
        current_time = TIME_NOW
    
    # Market hours: 9:30 AM to 4:00 PM Eastern Time, Monday to Friday
    market_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
    
    is_weekday = current_time.weekday() < 5
    if after_hours:
        market_close = current_time.replace(hour=20, minute=0, second=0, microsecond=0)
        market_open = current_time.replace(hour=4, minute=0, second=0, microsecond=0)

    return is_weekday and (market_open <= current_time <= market_close)
