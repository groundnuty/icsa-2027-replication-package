
import numpy as np
from datetime import date, timedelta

# Load data
base_data = np.load('/work/base_data.npy').astype(np.float64)  # (4028, 60, 60)
tgt_data = np.load('/work/tgt_data.npy').astype(np.float64)    # (92, 60, 60)
base_time = np.load('/work/base_time.npy')  # int64 days since epoch
tgt_time = np.load('/work/tgt_time.npy')
lat_vals = np.load('/work/lat_vals.npy')
lon_vals = np.load('/work/lon_vals.npy')

print("base_data shape", base_data.shape)
print("tgt_data shape", tgt_data.shape)
print("lat", lat_vals[:5], lat_vals[-5:])
print("lon", lon_vals[:5], lon_vals[-5:])

# Day of year mapping: given month, day, return day of year 1-366
def day_of_year(month, day):
    # fixed mapping as per spec
    # Jan 1 = 1, Feb 28 = 59, Feb 29 = 60, Mar 1 = 61, ..., Dec 31 = 366
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]  # Feb has 29 in mapping
    doy = sum(days_in_month[:month-1]) + day
    return doy

# Test
assert day_of_year(1,1) == 1
assert day_of_year(2,28) == 59
assert day_of_year(2,29) == 60
assert day_of_year(3,1) == 61
assert day_of_year(12,31) == 366
print("day_of_year mapping OK")
