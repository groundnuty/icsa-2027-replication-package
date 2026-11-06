import numpy as np
from datetime import datetime, timedelta

# Test the day_of_year function with actual data
test_date = np.datetime64('2000-01-01')
print(f"Test date: {test_date}")
print(f"Type: {type(test_date)}")

# Convert properly
dt = test_date.astype(datetime)
print(f"Converted date: {dt}")
print(f"Type after conversion: {type(dt)}")

# Test day_of_year function
def day_of_year(date):
    """Convert a date to day of year (1-366)"""
    # Convert to datetime if it's not already
    if isinstance(date, np.datetime64):
        # Convert numpy datetime64 to Python datetime
        date = date.astype(datetime)
    
    # Handle leap year cases - Feb 29 is day 60
    if date.month == 2 and date.day == 29:
        return 60
    
    # Create a date for Jan 1 of the same year
    jan1 = datetime(date.year, 1, 1)
    # Calculate the difference in days
    delta = date - jan1
    return delta.days + 1

# Test with various inputs
test_cases = [
    np.datetime64('2000-01-01'),
    np.datetime64('2000-02-29'),  # leap day
    np.datetime64('2000-12-31'),
    datetime(2000, 1, 1),
    datetime(2000, 2, 29)
]

for case in test_cases:
    try:
        result = day_of_year(case)
        print(f"{case} -> day {result}")
    except Exception as e:
        print(f"Error with {case}: {e}")