import numpy as np
from datetime import datetime, timedelta

def date_to_doy(date):
    """Convert a datetime object to day-of-year (1-366)"""
    # Handle leap years correctly
    if isinstance(date, datetime):
        # Create a date for the same year (we'll handle Feb 29 separately)
        jan1 = datetime(date.year, 1, 1)
        doy = (date - jan1).days + 1
        
        # Special case for Feb 29 in leap years
        if date.month > 2 and date.day == 29 and date.month == 2:
            # This shouldn't happen because we're using the same year
            pass
            
        return doy
    else:
        # Handle numpy datetime64
        jan1 = np.datetime64(str(date.astype('datetime64[Y]')), 'D')
        doy = int((date - jan1).astype('timedelta64[D]') + 1)
        return doy

def doy_to_date(doy, year=2000):
    """Convert day-of-year back to a date (assuming year 2000 for reference)"""
    jan1 = datetime(year, 1, 1)
    date = jan1 + timedelta(days=doy-1)
    return date

# Test it
test_dates = [
    datetime(2000, 1, 1),
    datetime(2000, 2, 28), 
    datetime(2000, 3, 1),
    datetime(2000, 12, 31),
    datetime(2000, 2, 29)  # leap year
]

for d in test_dates:
    doy = date_to_doy(d)
    print(f"{d.strftime('%Y-%m-%d')} -> DOY {doy}")