import datetime as dt
import pytz

TIMEZONE = pytz.timezone('US/Eastern')
TIME_NOW = dt.datetime.now(TIMEZONE)

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

def is_weekday() -> bool:
    """Check if the current day is a weekday."""
    return TIME_NOW.weekday() < 5

def is_market_open(symbol, after_hours=False) -> bool:
    """Check if the stock market is currently open."""
    from src.stock_data import get_asset_type
    
    # Market hours: 9:30 AM to 4:00 PM Eastern Time, Monday to Friday
    
    asset_type = get_asset_type(symbol)
    weekday = TIME_NOW.weekday()
    hour = TIME_NOW.hour
    minute = TIME_NOW.minute

    if asset_type == 'crypto':
        return True

    if asset_type in ['commodity', 'futures']:
        sunday_before_5pm = weekday == 6 and hour < 17 
        friday_after_5pm = weekday == 4 and hour >= 17
        is_saturday = weekday == 5
        trade_break = hour == 16

        return not (is_saturday or sunday_before_5pm or friday_after_5pm or trade_break)

    if asset_type == 'forex':
        sunday_before_5pm = weekday == 6 and hour < 17
        friday_after_5pm = weekday == 4 and hour >= 17

        return not (sunday_before_5pm or friday_after_5pm)
    

    if is_weekend():
        return False
    
    if after_hours:
        return 4 < hour < 20
    
    if hour < 9 or (hour == 9 and minute < 30) or hour >= 16:
        return False
    
    return True
