import numpy as np
from datetime import datetime, timedelta

def date_to_doy(date_str):
    """Convert YYYY-MM-DD string to day-of-year (1-366)"""
    dt = datetime.strptime(date_str, '%Y-%m-%d')
    # Handle leap year cases
    if dt.month == 2 and dt.day == 29:
        return 60  # Special case for Feb 29
    else:
        # Get day of year (1-365 for regular years, 1-366 for leap years)
        doy = int(dt.strftime('%j'))
        # Adjust for leap year cases (since we're dealing with 1992-2002 which includes 1992, 1996, 2000)
        # But for our purposes, we'll treat Feb 29 specially and keep all years consistent
        return doy

def get_baseline_window_dates(baseline_start, baseline_end, target_doy):
    """Get the window of dates for a given day of year in baseline period"""
    # Create a list of all dates in baseline period
    start_date = datetime.strptime(baseline_start, '%Y-%m-%d')
    end_date = datetime.strptime(baseline_end, '%Y-%m-%d')
    
    # Generate all dates in baseline period
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    
    # For each date, calculate its DOY and find dates within ±5 days
    window_dates = []
    for d in dates:
        d_doy = date_to_doy(d.strftime('%Y-%m-%d'))
        if abs(d_doy - target_doy) <= 5:
            window_dates.append(d)
    
    return window_dates

# Test our function
print("Testing date conversion:")
print(f"2005-01-01 -> DOY: {date_to_doy('2005-01-01')}")
print(f"2005-02-28 -> DOY: {date_to_doy('2005-02-28')}")
print(f"2005-03-01 -> DOY: {date_to_doy('2005-03-01')}")

# Test the baseline window
window = get_baseline_window_dates('1992-01-01', '2002-12-31', 60)
print(f"\nBaseline window for DOY 60 (Feb 29): {len(window)} dates")
print(f"First few dates: {[d.strftime('%Y-%m-%d') for d in window[:5]]}")
print(f"Last few dates: {[d.strftime('%Y-%m-%d') for d in window[-5:]]}")