
import numpy as np
import datetime

# Load the data
baseline_sst = np.load('/work/baseline_sst.npy')
target_sst = np.load('/work/target_sst.npy')
baseline_time_idx = np.load('/work/baseline_time_idx.npy')
target_time_idx = np.load('/work/target_time_idx.npy')

print(f"Baseline SST: {baseline_sst.shape}, dtype: {baseline_sst.dtype}")
print(f"Target SST: {target_sst.shape}, dtype: {target_sst.dtype}")

# Load the time array from the dataset
import xarray as xr
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
time = ds.time.values
baseline_dates = time[baseline_time_idx]
target_dates = time[target_time_idx]

# Print some baseline dates
print(f"\nBaseline dates: {baseline_dates[0]} to {baseline_dates[-1]}")
print(f"Target dates: {target_dates[0]} to {target_dates[-1]}")

# Function to compute day of year (1-366)
def day_of_year(y, m, d):
    """Return day of year 1-366."""
    if m == 1:
        return d
    elif m == 2:
        return 31 + d
    elif m == 3:
        return 59 + d  # day 60 is Feb 29 in leap years, Mar 1 is day 61
    elif m == 4:
        return 90 + d
    elif m == 5:
        return 120 + d
    elif m == 6:
        return 151 + d
    elif m == 7:
        return 181 + d
    elif m == 8:
        return 212 + d
    elif m == 9:
        return 243 + d
    elif m == 10:
        return 273 + d
    elif m == 11:
        return 304 + d
    elif m == 12:
        return 334 + d
    return -1  # shouldn't happen

# Check: Jan 1 = 1, Feb 28 = 59, Feb 29 = 60, Mar 1 = 61, Dec 31 = 366
print(f"\nDay of year checks:")
print(f"Jan 1: {day_of_year(2020, 1, 1)}")
print(f"Feb 28: {day_of_year(2020, 2, 28)}")
print(f"Feb 29: {day_of_year(2020, 2, 29)}")
print(f"Mar 1: {day_of_year(2020, 3, 1)}")
print(f"Dec 31: {day_of_year(2020, 12, 31)}")
print(f"Jan 1 (2012): {day_of_year(2012, 1, 1)}")
print(f"Dec 31 (2011): {day_of_year(2011, 12, 31)}")

# Actually the mapping given in the task is:
# 1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61, ..., 31 December = 366
# This is different from the standard day of year!
# Standard DOY for March 1 in non-leap year is 60, but here it's 61.
# So the mapping is: all months after Feb shift by 1 in non-leap years.

# Let me re-read: "Map every date to a day of year from 1 to 366 by month and day:
# 1 January = 1, 28 February = 59, 29 February = 60, 1 March = 61, ..., 31 December = 366."

# So this is a fixed mapping that does NOT depend on whether it's a leap year!
# Jan 1 = 1, ..., Jan 31 = 31
# Feb 1 = 32, ..., Feb 28 = 59
# Feb 29 = 60 (only in leap years)
# Mar 1 = 61, ..., Mar 31 = 91
# Apr 1 = 92, ...
# Dec 31 = 366

# So the mapping is:
# Jan: d -> d
# Feb: 31 + d
# Mar: 60 + d
# Apr: 91 + d
# May: 121 + d
# Jun: 152 + d
# Jul: 182 + d
# Aug: 213 + d
# Sep: 244 + d
# Oct: 274 + d
# Nov: 305 + d
# Dec: 335 + d

# Check: Mar 1 = 60+1 = 61 ✓
# Dec 31 = 335+31 = 366 ✓
# Feb 28 = 31+28 = 59 ✓
# Feb 29 = 31+29 = 60 ✓

# But wait - "Non-leap years have no day 60." So in non-leap years, Feb 29 doesn't exist,
# and the mapping still uses the same formula, meaning Mar 1 is always day 61 regardless.

# This means days 60 only exists in leap years. And the mapping is a fixed formula.

def doy_from_date(date):
    """Compute day of year (1-366) using the task's mapping."""
    y = date.year
    m = date.month
    d = date.day
    if m == 1:
        return d
    elif m == 2:
        return 31 + d
    elif m == 3:
        return 60 + d
    elif m == 4:
        return 91 + d
    elif m == 5:
        return 121 + d
    elif m == 6:
        return 152 + d
    elif m == 7:
        return 182 + d
    elif m == 8:
        return 213 + d
    elif m == 9:
        return 244 + d
    elif m == 10:
        return 274 + d
    elif m == 11:
        return 305 + d
    elif m == 12:
        return 335 + d
    return -1

# Verify
print(f"\nVerify day of year mapping:")
print(f"Jan 1 1992: {doy_from_date(datetime.date(1992,1,1))}")
print(f"Feb 28 1992: {doy_from_date(datetime.date(1992,2,28))}")
print(f"Feb 29 1992: {doy_from_date(datetime.date(1992,2,29))}")
print(f"Mar 1 1992: {doy_from_date(datetime.date(1992,3,1))}")
print(f"Mar 1 1993 (non-leap): {doy_from_date(datetime.date(1993,3,1))}")
print(f"Dec 31 1992: {doy_from_date(datetime.date(1992,12,31))}")

# Check non-leap year: there's no Feb 29 in 1993, so no day 60 in 1993
# In 1993, Feb 28 = 59, then Mar 1 = 61 (no day 60)
print(f"Feb 28 1993: {doy_from_date(datetime.date(1993,2,28))}")
print(f"Mar 1 1993: {doy_from_date(datetime.date(1993,3,1))}")
