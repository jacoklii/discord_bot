from src.config.config import TIME_NOW

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
    import datetime as dt
    import pytz
    # Market hours: 9:30 AM to 4:00 PM Eastern Time, Monday to Friday
    
    eastern = pytz.timezone('US/Eastern')
    time_now = dt.datetime.now(eastern)

    asset_type = get_asset_type(symbol)
    weekday = time_now.weekday()
    hour = time_now.hour
    minute = time_now.minute

    if asset_type == 'crypto':
        return True
    if asset_type in ['etf', 'stock']:
        if after_hours:
            return (weekday < 5) and (hour >= 4) and (hour < 20)
        else:
            return (weekday < 5) and (hour > 9 or (hour == 9 and minute >= 30)) and (hour < 16)

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
