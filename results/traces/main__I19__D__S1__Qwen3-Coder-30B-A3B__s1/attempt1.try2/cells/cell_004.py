import datetime
import numpy as np

def date_to_doy(date_str):
    """Convert YYYY-MM-DD to day of year (1-366)"""
    date_obj = datetime.datetime.strptime(date_str, '%Y-%m-%d')
    doy = date_obj.timetuple().tm_yday
    # Handle leap year special case for Feb 29
    if date_obj.month > 2 and date_obj.year % 4 == 0 and (date_obj.year % 100 != 0 or date_obj.year % 400 == 0):
        # This is a leap year and we're past Feb 28, so Feb 29 is already counted
        pass
    return doy

def get_doy_range(start_date, end_date, include_leap=True):
    """Get all day-of-year values between start and end dates"""
    start = datetime.datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.datetime.strptime(end_date, '%Y-%m-%d')
    
    doys = []
    current = start
    
    while current <= end:
        doy = current.timetuple().tm_yday
        # Special handling for leap year Feb 29
        if current.month == 2 and current.day == 29:
            doys.append(60)  # Feb 29 maps to day 60
        else:
            doys.append(doy)
        
        current += datetime.timedelta(days=1)
    
    return sorted(list(set(doys)))

# Test the function
print("Testing date conversion:")
print(f"2014-06-01 -> doy: {date_to_doy('2014-06-01')}")
print(f"2014-08-31 -> doy: {date_to_doy('2014-08-31')}")
print(f"2014-02-28 -> doy: {date_to_doy('2014-02-28')}")
print(f"2014-03-01 -> doy: {date_to_doy('2014-03-01')}")

# Get doys for the baseline period
baseline_doy = get_doy_range('1992-01-01', '2002-12-31')
print(f"\nBaseline DOYs count: {len(baseline_doy)}")
print(f"Unique baseline DOYs: {sorted(baseline_doy)[:10]}...{sorted(baseline_doy)[-10:]}")