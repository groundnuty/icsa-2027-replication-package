
import numpy as np
import pandas as pd
from datetime import date, timedelta

# Load saved data
sst_target = np.load('sst_target.npy')
sst_base = np.load('sst_base.npy')
target_time = np.load('target_time.npy').astype('datetime64[D]').astype('datetime64[ns]')
base_time = np.load('base_time.npy').astype('datetime64[D]').astype('datetime64[ns]')
lats = np.load('lats.npy')
lons = np.load('lons.npy')

print('Base shape:', sst_base.shape)
print('Base time:', base_time[0], base_time[-1])

# Convert to datetime
base_dates = [pd.Timestamp(t).to_pydatetime() for t in base_time]

def day_of_year(dt):
    """Map a date to day of year 1-366 by month and day."""
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334]
    return cum_days[month - 1] + day

# Baseline dates: 1992-01-01 to 2002-12-31
base_start = date(1992, 1, 1)
base_end = date(2002, 12, 31)

# For each DOY d (1-366, d != 60), find the pool dates
# Pool for DOY d = all dates within ±5 calendar days of a baseline date with DOY=d
# We'll work with date objects

# All data dates in the loaded range
all_dates = [pd.Timestamp(t).to_pydatetime().date() for t in base_time]
all_dates_np = np.array([d.toordinal() for d in all_dates])

# Baseline dates with their DOY
baseline_dates = []
for d in all_dates:
    if base_start <= d <= base_end:
        baseline_dates.append(d)

baseline_doy = [day_of_year(d) for d in baseline_dates]

# For each DOY, find pool dates
pools = {}  # DOY -> list of indices into all_dates
for doy in range(1, 367):
    if doy == 60:
        continue
    # Find baseline dates with this DOY
    base_dates_for_doy = [d for d, dd in zip(baseline_dates, baseline_doy) if dd == doy]
    if not base_dates_for_doy:
        pools[doy] = []
        continue
    # For each such date, window = ±5 calendar days
    pool_dates = set()
    for bd in base_dates_for_doy:
        for offset in range(-5, 6):
            pool_dates.add(bd + timedelta(days=offset))
    # Map to indices
    pool_date_ords = np.array([d.toordinal() for d in pool_dates])
    idx = []
    for po in pool_date_ords:
        matches = np.where(all_dates_np == po)[0]
        if len(matches) > 0:
            idx.append(matches[0])
    pools[doy] = sorted(idx)

# Verify some pools
for doy in [1, 59, 61, 100, 200, 300, 365, 366]:
    print(f'DOY {doy}: {len(pools[doy])} dates, first few: {[all_dates[i].isoformat() for i in pools[doy][:5]]}')
