
from datetime import date, timedelta
import numpy as np

# Reload data
all_data = np.load('/tmp/baseline_data.npy')
print('Baseline data shape:', all_data.shape)

# Day of year function
month_starts = [1, 32, 61, 92, 122, 153, 183, 214, 245, 275, 306, 336]
def doy(dt):
    return month_starts[dt.month - 1] + dt.day - 1

baseline_start = date(1991, 12, 27)
baseline_end = date(2003, 1, 5)
baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append(d)
    d += timedelta(days=1)
date_to_idx = {baseline_dates[i]: i for i in range(len(baseline_dates))}

# Find baseline dates for each day-of-year
baseline_dates_by_doy = {}
for year in range(1992, 2003):
    d = date(year, 1, 1)
    while d.year == year:
        d_doy = doy(d)
        if d_doy not in baseline_dates_by_doy:
            baseline_dates_by_doy[d_doy] = []
        baseline_dates_by_doy[d_doy].append(d)
        d += timedelta(days=1)

# Pool dates for each day-of-year
pool_dates_by_doy = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool = set()
    for B in baseline_dates_by_doy.get(d, []):
        for i in range(-5, 6):
            pool.add(B + timedelta(days=i))
    pool_dates_by_doy[d] = sorted(pool)

# Compute thresholds and climatology
n_cells = 60 * 60
thresholds = np.zeros((366, n_cells), dtype=np.float64)
climatology = np.zeros((366, n_cells), dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    pool_dates = pool_dates_by_doy[d]
    idxs = [date_to_idx[D] for D in pool_dates]
    pool = all_data[idxs].reshape(len(idxs), -1)  # (n_pool, 3600)
    
    # Compute threshold (90th percentile, hazan method) and climatology (mean)
    thresholds[d] = np.nanquantile(pool, 0.9, axis=0, method='hazen')
    climatology[d] = np.nanmean(pool, axis=0)
    
    if d % 50 == 0:
        print(f'Processed DOY {d}')

# Handle day 60
thresholds[60] = (thresholds[59] + thresholds[61]) / 2
climatology[60] = (climatology[59] + climatology[61]) / 2
print('Day 60 set to mean of days 59 and 61')

# Check for NaN in thresholds and climatology
print('NaN in thresholds:', np.isnan(thresholds).sum())
print('NaN in climatology:', np.isnan(climatology).sum())

# Save intermediate results
np.save('/tmp/thresholds.npy', thresholds)
np.save('/tmp/climatology.npy', climatology)
print('Saved thresholds and climatology')
