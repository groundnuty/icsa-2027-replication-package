import numpy as np
from datetime import datetime, timedelta

def date_to_doy(date_str):
    """Convert YYYY-MM-DD string to day-of-year (1-366)"""
    date = datetime.strptime(date_str, "%Y-%m-%d")
    # Handle leap year cases properly
    if date.month == 2 and date.day == 29:
        return 60
    
    # Create a reference date (non-leap year) for calculation
    jan1 = datetime(date.year, 1, 1)
    doy = (date - jan1).days + 1
    
    # Adjust for leap year if needed
    if date.year % 4 == 0 and (date.year % 100 != 0 or date.year % 400 == 0):
        if doy > 59:  # After Feb 28 in leap year
            doy += 1
    
    return doy

def get_baseline_dates():
    """Get all dates from 1992-01-01 to 2002-12-31"""
    start = datetime(1992, 1, 1)
    end = datetime(2002, 12, 31)
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

# Test the function
print("Testing date conversion:")
test_dates = ["1992-01-01", "1992-02-28", "1992-02-29", "1992-03-01", "2002-12-31"]
for date in test_dates:
    print(f"{date} -> DOY {date_to_doy(date)}")

print("\nBaseline dates count:", len(get_baseline_dates()))