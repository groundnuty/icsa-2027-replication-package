
from datetime import date, timedelta
import numpy as np

# Reload data
all_data = np.load('/tmp/baseline_data.npy')
target_data = np.load('/tmp/target_data.npy')
print('Baseline data shape:', all_data.shape)
print('Target data shape:', target_data.shape)

# Day of year function
month_starts = [1, 32, 61, 92, 122, 153, 183, 214, 245, 275, 306, 336]
def doy(dt):
    return month_starts[dt.month - 1] + dt.day - 1

# Reconstruct baseline dates
baseline_start = date(1991, 12, 27)
baseline_end = date(2003, 1, 5)
baseline_dates = []
d = baseline_start
while d <= baseline_end:
    baseline_dates.append(d)
    d += timedelta(days=1)
n_dates = len(baseline_dates)
print('Number of baseline dates:', n_dates)

# Verify doy function
assert doy(date(2000, 1, 1)) == 1
assert doy(date(2000, 2, 28)) == 59
assert doy(date(2000, 2, 29)) == 60
assert doy(date(2000, 3, 1)) == 61
assert doy(date(1999, 3, 1)) == 61  # non-leap year
assert doy(date(2000, 12, 31)) == 366
assert doy(date(1999, 12, 31)) == 366
print('Day-of-year function verified')

# Map dates to indices
date_to_idx = {baseline_dates[i]: i for i in range(n_dates)}

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

# Print some stats
for d in [1, 59, 60, 61, 100, 153, 366]:
    dates_list = baseline_dates_by_doy.get(d, [])
    print(f'DOY {d}: {len(dates_list)} baseline dates')

# Compute pool dates for each day-of-year
pool_dates_by_doy = {}
for d in range(1, 367):
    if d == 60:
        continue
    pool = set()
    for B in baseline_dates_by_doy.get(d, []):
        for i in range(-5, 6):
            pool.add(B + timedelta(days=i))
    pool_dates_by_doy[d] = sorted(pool)

# Verify all pool dates are in our loaded data range
all_ok = True
for d in range(1, 367):
    if d == 60:
        continue
    for D in pool_dates_by_doy[d]:
        if D not in date_to_idx:
            print(f'Pool date {D} for DOY {d} not in loaded data')
            all_ok = False
if all_ok:
    print('All pool dates are in loaded data')

# Check pool sizes
for d in [1, 59, 60, 61, 100, 153, 366]:
    if d != 60:
        print(f'DOY {d}: {len(pool_dates_by_doy[d])} pool dates')
