
import numpy as np
import xarray as xr
from datetime import datetime, timedelta

# Load the data
baseline_data = xr.open_dataset('baseline_data.nc')
target_data = xr.open_dataset('target_data.nc')

baseline_sst = baseline_data.analysed_sst.values  # (4028, 60, 60)
baseline_time = baseline_data.time.values  # datetime64
target_sst = target_data.analysed_sst.values  # (92, 60, 60)
target_time = target_data.time.values

print("Baseline shape:", baseline_sst.shape)
print("Target shape:", target_sst.shape)

# Function to map date to day of year (1-366)
def day_of_year(dt):
    """Map a datetime to day of year 1-366 using the specified scheme."""
    month = dt.month
    day = dt.day
    # Days before the month
    days_in_month = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = sum(days_in_month[:month]) + day
    return doy

# Test
test_dates = [
    datetime(1992, 1, 1),
    datetime(1992, 2, 28),
    datetime(1992, 2, 29),
    datetime(1992, 3, 1),
    datetime(1992, 12, 31),
]
for d in test_dates:
    print(f"{d} -> day {day_of_year(d)}")

# For a non-leap year, Feb 29 doesn't exist, so March 1 is still day 61
test2 = datetime(1993, 2, 28)
print(f"1993-02-28 -> day {day_of_year(test2)}")  # Should be 59
