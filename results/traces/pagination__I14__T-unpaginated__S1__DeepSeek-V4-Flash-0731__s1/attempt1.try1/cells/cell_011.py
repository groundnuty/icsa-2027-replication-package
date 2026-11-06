
import numpy as np
from datetime import date, timedelta

def day_of_year_fixed(y, m, d):
    """Map a date to day of year 1-366 as per the task spec."""
    if m == 1:
        return d
    elif m == 2:
        return 31 + d
    elif m >= 3:
        days_before_month = {3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}
        return days_before_month[m] + d

# Generate all baseline dates
baseline_start = date(1991, 12, 27)
baseline_end = date(2003, 1, 5)
all_dates = []
d = baseline_start
while d <= baseline_end:
    all_dates.append(d)
    d += timedelta(days=1)

# Compute day-of-year for each date
doy_values = np.array([day_of_year_fixed(d.year, d.month, d.day) for d in all_dates])
print(f"Number of dates: {len(all_dates)}")
print(f"Day-of-year range: {doy_values.min()} to {doy_values.max()}")

# Check which day-of-year values exist
unique_doy = np.unique(doy_values)
print(f"Unique day-of-year values: {unique_doy}")
print(f"Day 60 exists? {60 in unique_doy}")
print(f"Day 366 exists? {366 in unique_doy}")
