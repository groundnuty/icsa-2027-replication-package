
import numpy as np
import datetime

# Load data
baseline_vals = np.load('baseline_vals.npy')  # (4028, 60, 60)
target_vals = np.load('target_vals.npy')  # (92, 60, 60)
baseline_dates = np.load('baseline_dates.npy', allow_pickle=True)  # strings
target_dates = np.load('target_dates.npy', allow_pickle=True)

# Convert to datetime objects
def parse_date(s):
    return datetime.datetime.strptime(str(s), '%Y-%m-%d')

baseline_dt = [parse_date(d) for d in baseline_dates]
target_dt = [parse_date(d) for d in target_dates]

print("Baseline first:", baseline_dt[0])
print("Baseline last:", baseline_dt[-1])
print("Target first:", target_dt[0])
print("Target last:", target_dt[-1])
print("N baseline:", len(baseline_dt))
print("N target:", len(target_dt))

# Define day-of-year mapping
def day_of_year(dt):
    """Map date to day of year 1-366 (as if every year is leap)."""
    month_offsets = [0, 0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_offsets[dt.month] + dt.day

# Test
print("1992-02-28 doy:", day_of_year(datetime.datetime(1992,2,28)))  # 59
print("1992-02-29 doy:", day_of_year(datetime.datetime(1992,2,29)))  # 60
print("1993-03-01 doy:", day_of_year(datetime.datetime(1993,3,1)))  # 61
print("1992-01-01 doy:", day_of_year(datetime.datetime(1992,1,1)))  # 1
print("1992-12-31 doy:", day_of_year(datetime.datetime(1992,12,31)))  # 366
