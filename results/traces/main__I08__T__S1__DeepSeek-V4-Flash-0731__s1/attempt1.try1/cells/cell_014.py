
import numpy as np
import datetime as dt
from collections import defaultdict

# Load the data
base_data = np.load('/tmp/base_data.npy')  # (4028, 60, 60) float32
target_data = np.load('/tmp/target_data.npy')  # (92, 60, 60) float32
base_times = np.load('/tmp/base_times.npy')
tgt_times = np.load('/tmp/tgt_times.npy')
lat_vals = np.load('/tmp/lat_vals.npy')
lon_vals = np.load('/tmp/lon_vals.npy')

print("base_data shape:", base_data.shape, "dtype:", base_data.dtype)
print("target_data shape:", target_data.shape)
print("base_times:", base_times[0], "to", base_times[-1])
print("tgt_times:", tgt_times[0], "to", tgt_times[-1])

# Function to compute day-of-year (1-366)
def day_of_year(ts):
    """Compute day of year for a numpy datetime64 timestamp.
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366.
    """
    d = dt.datetime.utcfromtimestamp(ts.astype('datetime64[ns]').astype(np.int64) / 1e9)
    year = d.year
    month = d.month
    day = d.day
    
    # Days before current month
    days_in_month = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    # Check leap year
    is_leap = (year % 4 == 0 and year % 100 != 0) or (year % 400 == 0)
    if is_leap:
        days_in_month[1] = 29
    
    doy = sum(days_in_month[:month-1]) + day
    return doy

# Test
test_dates = [
    np.datetime64('1992-01-01'),
    np.datetime64('1992-02-28'),
    np.datetime64('1992-02-29'),
    np.datetime64('1992-03-01'),
    np.datetime64('1992-12-31'),
    np.datetime64('1993-01-01'),
    np.datetime64('1993-02-28'),
    np.datetime64('1993-03-01'),
    np.datetime64('1993-12-31'),
]
for t in test_dates:
    print(t, "->", day_of_year(t))
