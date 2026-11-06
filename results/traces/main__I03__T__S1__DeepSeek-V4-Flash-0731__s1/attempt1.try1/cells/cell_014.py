
import numpy as np
import datetime

# Month day counts (as if leap year for Feb)
month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

def doy_to_md(doy):
    """Convert day of year (1-366) to (month, day)."""
    cum = 0
    for m in range(12):
        if doy <= cum + month_days[m]:
            return m + 1, doy - cum
        cum += month_days[m]
    raise ValueError(f"Invalid day of year: {doy}")

# Test
print(doy_to_md(1))    # (1, 1)
print(doy_to_md(59))   # (2, 28)
print(doy_to_md(60))   # (2, 29)
print(doy_to_md(61))   # (3, 1)
print(doy_to_md(366))  # (12, 31)

# Check if (m, d) is a valid date for a given year
def is_valid_date(y, m, d):
    try:
        datetime.date(y, m, d)
        return True
    except ValueError:
        return False

# Check: Feb 29 is valid in leap years 1992, 1996, 2000
print("1992-02-29 valid:", is_valid_date(1992, 2, 29))
print("1993-02-29 valid:", is_valid_date(1993, 2, 29))
