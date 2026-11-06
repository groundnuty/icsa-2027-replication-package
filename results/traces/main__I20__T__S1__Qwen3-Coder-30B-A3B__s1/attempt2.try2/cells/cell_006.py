import datetime
import numpy as np

def date_to_doy(year, month, day):
    """Convert date to day of year (1-366)"""
    # Create a date object
    date_obj = datetime.date(year, month, day)
    # Get day of year (1-366)
    doy = date_obj.timetuple().tm_yday
    
    # Special handling for Feb 29 in non-leap years
    # In our context, we want to handle Feb 29 differently for the calculation
    # We'll treat Feb 29 as belonging to the adjacent days
    if month == 2 and day == 29:
        # Feb 29 exists only in leap years
        # For our purposes, we'll treat it as part of the Feb 28 window
        return 59  # Feb 28
    elif month == 3 and day == 1:
        # March 1 should be day 61 (after Feb 28)
        return 61
    
    return doy

# Let's test a bit more systematically
print("Day of year conversions:")
test_dates = [
    (2000, 1, 1),   # 1
    (2000, 2, 28),  # 59  
    (2000, 3, 1),   # 61
    (2000, 2, 29),  # 60 (leap year)
    (2001, 2, 28),  # 59 (non-leap year)
]

for year, month, day in test_dates:
    doy = date_to_doy(year, month, day)
    print(f"{year}-{month:02d}-{day:02d}: {doy}")