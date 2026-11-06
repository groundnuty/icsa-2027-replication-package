
import numpy as np
import datetime as dt

def day_of_year(ts):
    d = dt.datetime.fromtimestamp(ts.astype('datetime64[ns]').astype(np.int64) / 1e9, tz=dt.timezone.utc)
    year = d.year
    month = d.month
    day = d.day
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    if is_leap:
        days_in_month[1] = 29
    std_doy = sum(days_in_month[:month-1]) + day
    if not is_leap and month > 2:
        std_doy += 1
    return std_doy

base_times = np.load('/tmp/base_times.npy')
base_doy = np.load('/tmp/base_doy.npy')

# Check which baseline dates have day-of-year 366
baseline_idx = np.where((base_times >= np.datetime64('1992-01-01')) & (base_times <= np.datetime64('2002-12-31')))[0]
d366_idx = baseline_idx[base_doy[baseline_idx] == 366]
print("Baseline dates with day 366:")
for i in d366_idx:
    print(f"  Index {i}: {base_times[i]}, day-of-year = {base_doy[i]}")

# Check which baseline dates have day 365
d365_idx = baseline_idx[base_doy[baseline_idx] == 365]
print("Baseline dates with day 365:")
for i in d365_idx:
    print(f"  Index {i}: {base_times[i]}, day-of-year = {base_doy[i]}")
