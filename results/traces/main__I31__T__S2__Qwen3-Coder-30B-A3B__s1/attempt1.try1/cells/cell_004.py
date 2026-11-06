import numpy as np
from datetime import datetime, timedelta

def date_to_doy(date):
    """Convert a date to day of year (1-366)"""
    # Convert to datetime if it's a string
    if isinstance(date, str):
        date = datetime.strptime(date, "%Y-%m-%d")
    
    # Get the day of year
    doy = date.timetuple().tm_yday
    
    # Handle leap year special case for Feb 29
    if date.month > 2 and date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0):
        # This is a leap year, so Feb 29 exists
        if date.month == 3 and date.day == 1:
            # March 1 is day 61 in a leap year
            return 61
        elif date.month == 2 and date.day == 29:
            # Feb 29 is day 60 in a leap year  
            return 60
        elif date.month == 3 and date.day > 1:
            # After March 1, add 1 to account for Feb 29
            return doy + 1
        else:
            return doy
    else:
        return doy

def get_baseline_days():
    """Get all baseline days from 1992-01-01 to 2002-12-31"""
    start = datetime(1992, 1, 1)
    end = datetime(2002, 12, 31)
    
    days = []
    current = start
    while current <= end:
        days.append(current)
        current += timedelta(days=1)
    
    return days

def get_pool_dates(doy, baseline_days):
    """Get all dates that should contribute to the pool for a given day of year"""
    # Create a mapping of dates to day-of-year
    date_to_doy_map = {}
    for day in baseline_days:
        date_to_doy_map[day] = date_to_doy(day)
    
    # Find all dates within ±5 days of any date with the same DOY
    pool_dates = []
    for day in baseline_days:
        if date_to_doy_map[day] == doy:
            # Add all dates within ±5 days of this date
            for i in range(-5, 6):
                candidate_date = day + timedelta(days=i)
                if candidate_date >= datetime(1991, 12, 27) and candidate_date <= datetime(2003, 1, 5):
                    pool_dates.append(candidate_date)
    
    # Special handling for day 60 (Feb 29)
    if doy == 60:
        # We want to handle Feb 29 specially
        for day in baseline_days:
            if date_to_doy_map[day] == 60:
                for i in range(-5, 6):
                    candidate_date = day + timedelta(days=i)
                    if candidate_date >= datetime(1991, 12, 27) and candidate_date <= datetime(2003, 1, 5):
                        pool_dates.append(candidate_date)
    
    # Remove duplicates
    pool_dates = list(set(pool_dates))
    return sorted(pool_dates)

# Test our function
baseline_days = get_baseline_days()
print(f"Baseline period: {baseline_days[0]} to {baseline_days[-1]}")
print(f"Total baseline days: {len(baseline_days)}")

# Test day of year conversion
test_dates = [
    datetime(1992, 1, 1),
    datetime(1992, 2, 28),
    datetime(1992, 3, 1),
    datetime(1992, 12, 31),
    datetime(2000, 2, 29)  # Leap year
]

for d in test_dates:
    print(f"{d.strftime('%Y-%m-%d')} -> DOY {date_to_doy(d)}")