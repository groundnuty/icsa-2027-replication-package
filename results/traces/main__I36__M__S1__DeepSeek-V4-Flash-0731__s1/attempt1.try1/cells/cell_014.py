
import numpy as np
from datetime import date, timedelta

# Load baseline data
baseline_data = np.load('/tmp/baseline_data.npy')
with open('/tmp/baseline_dates.txt') as f:
    baseline_dates_str = [line.strip() for line in f]
baseline_dates = [date.fromisoformat(s) for s in baseline_dates_str]
print(f"Baseline data shape: {baseline_data.shape}")
print(f"Dates: {baseline_dates[0]} to {baseline_dates[-1]}")
print(f"Date count: {len(baseline_dates)}")

# Day of year mapping (perpetual leap year)
def day_of_year(d):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    return d.day + sum(month_days[:d.month])

# Verify some day-of-year mappings
test_dates = [date(2003,1,1), date(2003,2,28), date(2004,2,29), date(2003,3,1), 
              date(2003,6,1), date(2003,8,31), date(2003,12,31)]
for td in test_dates:
    print(f"{td} -> doy {day_of_year(td)}")

# Check: which day-of-year values exist in baseline?
doy_counts = {}
for d in baseline_dates:
    doy = day_of_year(d)
    doy_counts[doy] = doy_counts.get(doy, 0) + 1

# Check doy 60 (Feb 29) - should only be present in leap years
print(f"doy 60 count: {doy_counts.get(60, 0)}")
# Check which dates have doy 60
doy60_dates = [d for d in baseline_dates if day_of_year(d) == 60]
print(f"doy 60 dates: {doy60_dates}")

# Map doy to (month, day)
def doy_to_month_day(doy):
    month_days = [0, 31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    for m in range(1, 13):
        if doy <= sum(month_days[:m+1]):
            return m, doy - sum(month_days[:m])
    return None

# Verify
for d in [1, 59, 60, 61, 153, 244, 366]:
    m, dd = doy_to_month_day(d)
    print(f"doy {d} -> month {m}, day {dd}")
