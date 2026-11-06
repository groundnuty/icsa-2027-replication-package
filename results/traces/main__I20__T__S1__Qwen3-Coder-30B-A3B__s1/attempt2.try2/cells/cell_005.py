import datetime
import numpy as np

def date_to_doy(year, month, day):
    """Convert date to day of year (1-366)"""
    # Create a date object
    date_obj = datetime.date(year, month, day)
    # Get day of year (1-366)
    doy = date_obj.timetuple().tm_yday
    
    # Handle leap year special case for Feb 29
    if month > 2 and datetime.date(year, 1, 1).strftime('%L') == '000':
        # Not a leap year, so Feb 29 doesn't exist
        if doy == 60:  # This would be Feb 29 in a leap year
            doy = 59  # Adjust to Feb 28
    return doy

# Test it
print("Testing date conversion:")
print("Jan 1:", date_to_doy(2000, 1, 1))  # Should be 1
print("Feb 28:", date_to_doy(2000, 2, 28))  # Should be 59
print("Mar 1:", date_to_doy(2000, 3, 1))  # Should be 61
print("Feb 29 (leap year):", date_to_doy(2000, 2, 29))  # Should be 60
print("Feb 29 (non-leap year):", date_to_doy(2001, 2, 28))  # Should be 59