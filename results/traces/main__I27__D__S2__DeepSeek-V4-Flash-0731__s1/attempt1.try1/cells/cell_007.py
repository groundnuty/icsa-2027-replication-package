
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

baseline_arr = np.load('/work/baseline_arr.npy')
target_arr = np.load('/work/target_arr.npy')
baseline_time = np.load('/work/baseline_time.npy').astype('datetime64[D]')
target_time = np.load('/work/target_time.npy').astype('datetime64[D]')
lat = np.load('/work/lat.npy')
lon = np.load('/work/lon.npy')

nlat, nlon = baseline_arr.shape[1], baseline_arr.shape[2]
ntarget = target_arr.shape[0]
print("baseline shape:", baseline_arr.shape, "target shape:", target_arr.shape)
print("nlat, nlon:", nlat, nlon)

# Step 1: Identify sea cells - cells with finite SST on every target day
sea_mask = np.all(np.isfinite(target_arr), axis=0)  # (nlat, nlon) boolean
print("Number of sea cells:", sea_mask.sum())
print("Total cells:", nlat*nlon)

# Step 2: Day of year mapping (leap-year convention)
def date_to_doy(dt):
    """Map a date to day of year 1-366 using leap-year convention."""
    # dt is a datetime64[D] or pandas Timestamp
    d = pd.Timestamp(dt)
    month, day = d.month, d.day
    # Cumulative days at start of each month (leap year)
    cum = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum[month-1] + day

# Test the mapping
test_dates = [pd.Timestamp('1992-01-01'), pd.Timestamp('1992-02-28'), 
              pd.Timestamp('1992-02-29'), pd.Timestamp('1992-03-01'),
              pd.Timestamp('1992-12-31'), pd.Timestamp('1993-03-01'),
              pd.Timestamp('1993-12-31')]
for t in test_dates:
    print(t, "->", date_to_doy(t))

# Verify: Jan 1 = 1, Feb 28 = 59, Feb 29 = 60, Mar 1 = 61, Dec 31 = 366
