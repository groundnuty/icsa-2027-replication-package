
import numpy as np
from datetime import datetime, timedelta

def day_of_year(month, day):
    """Map month/day to day-of-year 1-366."""
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    if month == 2 and day == 29:
        return 60
    doy = sum(days_in_month[:month-1]) + day
    if month > 2:
        doy += 1
    return doy

# Generate all baseline dates (1992-01-01 to 2002-12-31) and their day-of-year
baseline_start = datetime(1992, 1, 1)
baseline_end = datetime(2002, 12, 31)

# Generate all dates in the extended range (1991-12-27 to 2003-01-05)
ext_start = datetime(1991, 12, 27)
ext_end = datetime(2003, 1, 5)

# Create mapping from date string to day-of-year
def date_to_doy(dt):
    return day_of_year(dt.month, dt.day)

# For each day-of-year d (1-366, excluding 60), find which dates X in ext range belong to pool d
# X belongs to pool d if there exists a baseline date Y with doy(Y)=d and |X-Y| <= 5 days

# Build list of baseline dates with their day-of-year
baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append((d, date_to_doy(d)))
    d += timedelta(days=1)

# Group baseline dates by day-of-year
from collections import defaultdict
doy_to_baseline_dates = defaultdict(list)
for dt, doy in baseline_dates:
    doy_to_baseline_dates[doy].append(dt)

print("Day-of-year values present in baseline:", sorted(doy_to_baseline_dates.keys())[:5], "...", sorted(doy_to_baseline_dates.keys())[-5:])
print("Num doy values:", len(doy_to_baseline_dates))
print("Day 60 present?", 60 in doy_to_baseline_dates)

# Check which doy values are present
for d in range(1, 367):
    if d not in doy_to_baseline_dates:
        print(f"Missing doy: {d}")
