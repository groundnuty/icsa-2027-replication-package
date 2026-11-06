import numpy as np
from datetime import datetime, timedelta

# Define the day-of-year mapping function
def day_of_year(month, day):
    """Map month and day to day of year (1-366) using leap-year calendar."""
    # Days in each month (leap year)
    month_days = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(month_days[:month-1]) + day
    return doy

# Test
assert day_of_year(1, 1) == 1
assert day_of_year(2, 28) == 59
assert day_of_year(2, 29) == 60
assert day_of_year(3, 1) == 61
assert day_of_year(12, 31) == 366
print("Day-of-year mapping verified")

# Generate dates for the baseline
baseline_dates = []
d = datetime(1991, 12, 27)
end = datetime(2003, 1, 5)
while d <= end:
    baseline_dates.append(d)
    d += timedelta(days=1)
print(f"Baseline dates: {len(baseline_dates)} from {baseline_dates[0]} to {baseline_dates[-1]}")

# Compute day-of-year for each baseline date
baseline_doy = [day_of_year(d.month, d.day) for d in baseline_dates]
print(f"DOY range: {min(baseline_doy)} to {max(baseline_doy)}")
