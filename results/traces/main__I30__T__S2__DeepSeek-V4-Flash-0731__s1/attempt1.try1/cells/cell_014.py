
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

# Load saved data
baseline_sst = np.load('/tmp/baseline_sst.npy')
target_sst = np.load('/tmp/target_sst.npy')
baseline_time = np.load('/tmp/baseline_time.npy')
target_time = np.load('/tmp/target_time.npy')
region_lat = np.load('/tmp/region_lat.npy')
region_lon = np.load('/tmp/region_lon.npy')

print("Shapes:", baseline_sst.shape, target_sst.shape)
print("Time types:", type(baseline_time), baseline_time.dtype)

# Define day-of-year mapping (leap year style regardless of actual year)
def doy_from_date(dt):
    """Map a datetime to day of year 1-366 using leap-year calendar."""
    month_days_cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return month_days_cum[dt.month - 1] + dt.day

# Convert numpy datetime64 to datetime objects
baseline_dates = [pd.Timestamp(t).to_pydatetime() for t in baseline_time]
target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]

# Compute day-of-year for each baseline date
base_doy = np.array([doy_from_date(d) for d in baseline_dates])
print("Baseline DOY distribution:")
for d in [1, 59, 60, 61, 366]:
    print(f"  DOY {d}: {np.sum(base_doy == d)} dates")

# Identify sea cells: finite on all target days
sea_mask = ~np.isnan(target_sst).any(axis=0)
print("Sea cells:", sea_mask.sum())

# Convert to float64
baseline_sst64 = baseline_sst.astype(np.float64)
target_sst64 = target_sst.astype(np.float64)
