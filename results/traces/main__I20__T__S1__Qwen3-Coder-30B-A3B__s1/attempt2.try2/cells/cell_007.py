import datetime
import numpy as np

def date_to_doy(year, month, day):
    """
    Convert calendar date to day of year (1-366)
    1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61, etc.
    Non-leap years have no day 60.
    """
    # Create a date object
    date_obj = datetime.date(year, month, day)
    
    # Get day of year (1-366)
    doy = date_obj.timetuple().tm_yday
    
    # For the specific case of Feb 29 in non-leap years, 
    # we treat it as belonging to the Feb 28 window
    if month == 2 and day == 29:
        # In non-leap years, Feb 29 doesn't exist, so we treat it as Feb 28
        return 59
    elif month == 3 and day == 1:
        # March 1 is day 61
        return 61
        
    return doy

# Test with various cases
print("Day of year conversions:")
test_cases = [
    (2000, 1, 1),   # 1
    (2000, 2, 28),  # 59  
    (2000, 2, 29),  # 60 (leap year)
    (2001, 2, 28),  # 59 (non-leap year)
    (2001, 3, 1),   # 61
    (2000, 12, 31), # 366
]

for year, month, day in test_cases:
    doy = date_to_doy(year, month, day)
    print(f"{year}-{month:02d}-{day:02d}: {doy}")

# Let's also create a function to generate date ranges
def generate_date_range(start_date, end_date):
    """Generate list of (year, month, day) tuples between start and end dates"""
    start = datetime.date(*start_date)
    end = datetime.date(*end_date)
    dates = []
    current = start
    while current <= end:
        dates.append((current.year, current.month, current.day))
        current += datetime.timedelta(days=1)
    return dates

# Generate a sample range
sample_dates = generate_date_range((1992, 1, 1), (2002, 12, 31))
print(f"\nSample date range: {len(sample_dates)} days")
print("First few dates:", sample_dates[:5])
print("Last few dates:", sample_dates[-5:])