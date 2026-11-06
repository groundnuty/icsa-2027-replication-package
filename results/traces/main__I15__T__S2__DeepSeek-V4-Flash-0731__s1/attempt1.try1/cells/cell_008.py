
import numpy as np
import pandas as pd
from datetime import date

# Load saved data
sst_target = np.load('sst_target.npy')
sst_base = np.load('sst_base.npy')
target_time = np.load('target_time.npy').astype('datetime64[D]').astype('datetime64[ns]')
base_time = np.load('base_time.npy').astype('datetime64[D]').astype('datetime64[ns]')
lats = np.load('lats.npy')
lons = np.load('lons.npy')

print('Shapes:', sst_target.shape, sst_base.shape)
print('Base time range:', base_time[0], base_time[-1])

# Function to compute day of year (1-366) from a date
def day_of_year(dt):
    """Map a date to day of year 1-366 by month and day.
    1 Jan = 1, 28 Feb = 59, 29 Feb = 60, 1 Mar = 61, ..., 31 Dec = 366.
    Non-leap years have no day 60.
    """
    month = dt.month
    day = dt.day
    # Use fixed table
    cum_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    return cum_days[month - 1] + day

# Convert to datetime objects
base_dates = [pd.Timestamp(t).to_pydatetime() for t in base_time]
target_dates = [pd.Timestamp(t).to_pydatetime() for t in target_time]

# Compute day of year for baseline dates
base_doy = np.array([day_of_year(d) for d in base_dates])
print('Base DOY range:', base_doy.min(), base_doy.max())
print('Unique base DOYs:', sorted(set(base_doy))[:10], '...', sorted(set(base_doy))[-10:])
print('Base DOY count unique:', len(set(base_doy)))
