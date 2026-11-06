
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

base_data = np.load('/tmp/base_data.npy')
base_times = np.load('/tmp/base_times.npy')
base_doy = np.load('/tmp/base_doy.npy')

# Identify which indices are in the baseline period (1992-01-01 to 2002-12-31)
base_start = np.datetime64('1992-01-01')
base_end = np.datetime64('2002-12-31')
is_baseline = (base_times >= base_start) & (base_times <= base_end)
print("Number of dates in baseline period:", is_baseline.sum())
print("Dates before baseline:", (~is_baseline).sum() if (~is_baseline[:100]).sum() > 0 else "check")
print("Indices before baseline:", np.where(~is_baseline)[0][:10] if len(np.where(~is_baseline)[0]) > 0 else "none at start")
print("Indices after baseline:", np.where(~is_baseline)[0][-10:] if len(np.where(~is_baseline)[0]) > 0 else "none at end")

# Let's check the dates at the boundaries
base_idx = np.where(is_baseline)[0]
print("First baseline index:", base_idx[0], "date:", base_times[base_idx[0]])
print("Last baseline index:", base_idx[-1], "date:", base_times[base_idx[-1]])
print("First extended date:", base_times[0])
print("Last extended date:", base_times[-1])
