import numpy as np
from datetime import datetime, timedelta

def date_to_doy(date_str):
    """Convert YYYY-MM-DD to day of year (1-366)"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    
    # For Feb 29, always return 60 regardless of leap year
    if dt.month == 2 and dt.day == 29:
        return 60
    
    # For Feb 28, check if it's a leap year
    if dt.month == 2 and dt.day == 28:
        # Check if leap year - if so, Feb 28 is day 59, otherwise day 59
        year = dt.year
        is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
        if is_leap:
            return 60  # In leap year, Feb 28 is day 60
        else:
            return 59  # In non-leap year, Feb 28 is day 59
            
    # Standard calculation
    jan1 = datetime(dt.year, 1, 1)
    doy = (dt - jan1).days + 1
    
    # Adjust for leap year if needed (dates after Feb 28)
    if (dt.year % 4 == 0 and dt.year % 100 != 0) or (dt.year % 400 == 0):
        # Leap year: dates after Feb 28 are shifted by 1 day
        if dt.month > 2:
            doy += 1
    
    return doy

# Let's test the logic with a cleaner approach
def date_to_doy_simple(date_str):
    """Simpler approach to DOY conversion"""
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    
    # Calculate base DOY
    base_doy = (dt - datetime(dt.year, 1, 1)).days + 1
    
    # For leap year, adjust dates after Feb 28
    is_leap = (dt.year % 4 == 0 and dt.year % 100 != 0) or (dt.year % 400 == 0)
    
    if is_leap and dt.month > 2:
        return base_doy + 1
    else:
        return base_doy

# Test our simpler version
test_dates = ["2000-01-01", "2000-02-28", "2000-02-29", "2001-02-28", "2000-12-31"]
for date in test_dates:
    doy = date_to_doy_simple(date)
    print(f"{date} -> DOY {doy}")

# Now let's focus on the actual implementation for the problem
print("\nTarget period analysis:")
start_date = "2007-06-01"
end_date = "2007-08-31"
start_doy = date_to_doy_simple(start_date)
end_doy = date_to_doy_simple(end_date)
print(f"{start_date} -> DOY {start_doy}")
print(f"{end_date} -> DOY {end_doy}")

# Let's also create a function to generate all dates in a range
def generate_date_range(start_date, end_date):
    """Generate a list of dates between start and end (inclusive)"""
    start = datetime.strptime(start_date, "%Y-%m-%d")
    end = datetime.strptime(end_date, "%Y-%m-%d")
    dates = []
    current = start
    while current <= end:
        dates.append(current.strftime("%Y-%m-%d"))
        current += timedelta(days=1)
    return dates

# Generate our target period dates
target_dates = generate_date_range("2007-06-01", "2007-08-31")
print(f"\nTotal target dates: {len(target_dates)}")
print(f"First few dates: {target_dates[:5]}")
print(f"Last few dates: {target_dates[-5:]}")