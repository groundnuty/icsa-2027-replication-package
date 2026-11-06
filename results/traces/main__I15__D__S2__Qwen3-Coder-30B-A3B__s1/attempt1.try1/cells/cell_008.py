import numpy as np
from datetime import datetime, date

def day_of_year(date_obj):
    """Convert a date to day of year (1-366)"""
    # Convert numpy datetime64 to Python datetime if needed
    if isinstance(date_obj, np.datetime64):
        # Convert numpy datetime64 to datetime
        date_obj = date_obj.astype(datetime)
    
    # Handle case where it might be a date object (not datetime)
    if isinstance(date_obj, date) and not isinstance(date_obj, datetime):
        # Convert date to datetime
        date_obj = datetime.combine(date_obj, datetime.min.time())
    
    # Handle leap year cases - Feb 29 is day 60
    if date_obj.month == 2 and date_obj.day == 29:
        return 60
    
    # Create a date for Jan 1 of the same year
    jan1 = datetime(date_obj.year, 1, 1)
    # Calculate the difference in days
    delta = date_obj - jan1
    return delta.days + 1

# Test the corrected function
test_cases = [
    np.datetime64('2000-01-01'),
    np.datetime64('2000-02-29'),  # leap day
    np.datetime64('2000-12-31'),
    datetime(2000, 1, 1),
    datetime(2000, 2, 29),
    date(2000, 1, 1)
]

for case in test_cases:
    try:
        result = day_of_year(case)
        print(f"{case} -> day {result}")
    except Exception as e:
        print(f"Error with {case}: {e}")