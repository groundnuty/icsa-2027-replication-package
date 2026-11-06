
import numpy as np
from datetime import datetime, timedelta

# Build day-of-year mapping
days_before_month = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]

def doy_from_date(dt):
    """Map a date to day of year (1-366)."""
    return days_before_month[dt.month - 1] + dt.day

# Test the mapping
test_dates = [
    datetime(1992, 1, 1), datetime(1992, 2, 28), datetime(1992, 2, 29),
    datetime(1992, 3, 1), datetime(1993, 3, 1), datetime(1992, 12, 31)
]
for d in test_dates:
    print(d.date(), "->", doy_from_date(d))

# Check that 2008 is a leap year (yes), but for the mapping, doy doesn't depend on leap year
# except that the date itself must exist
print("2008-06-01 doy:", doy_from_date(datetime(2008, 6, 1)))
print("2008-08-31 doy:", doy_from_date(datetime(2008, 8, 31)))
