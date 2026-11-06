
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

def day_of_year(dt):
    month = dt.month
    day = dt.day
    cum_days = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
    return cum_days[month - 1] + day

# All dates in the loaded data
all_dates = [pd.Timestamp(t).to_pydatetime().date() for t in base_time]
all_dates_np = np.array([d.toordinal() for d in all_dates])

# Baseline dates: 1992-01-01 to 2002-12-31
base_start = date(1992, 1, 1)
base_end = date(2002, 12, 31)
baseline_dates = [d for d in all_dates if base_start <= d <= base_end]
baseline_doy = [day_of_year(d) for d in baseline_dates]

print(f'Baseline dates count: {len(baseline_dates)}')
print(f'Baseline DOY unique: {len(set(baseline_doy))}')

# For each DOY (1-366, except 60), find pool date indices
pools = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    # Find baseline dates with this DOY
    base_dates_for_doy = [d for d, dd in zip(baseline_dates, baseline_doy) if dd == doy]
    if not base_dates_for_doy:
        pools[doy] = []
        continue
    # Windows ±5 calendar days
    pool_dates = set()
    for bd in base_dates_for_doy:
        for offset in range(-5, 6):
            pool_dates.add(bd + timedelta(days=offset))
    # Map to indices in all_dates
    pool_ords = np.array([d.toordinal() for d in pool_dates])
    idx = []
    for po in pool_ords:
        matches = np.where(all_dates_np == po)[0]
        if len(matches) > 0:
            idx.append(matches[0])
    pools[doy] = sorted(idx)

# Check
for doy in [1, 59, 61, 100, 200, 300, 365, 366]:
    print(f'DOY {doy}: {len(pools[doy])} dates')
    if pools[doy]:
        print(f'  first: {all_dates[pools[doy][0]].isoformat()}, last: {all_dates[pools[doy][-1]].isoformat()}')

# Save pools
import pickle
with open('pools.pkl', 'wb') as f:
    pickle.dump(pools, f)
