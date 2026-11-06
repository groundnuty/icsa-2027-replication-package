
import numpy as np
import datetime

def day_of_year(date):
    y, m, d = date.year, date.month, date.day
    months = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    is_leap = (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
    doy = sum(months[:m-1]) + d
    if m > 2 and is_leap:
        doy += 1
    if not is_leap and m > 2:
        doy += 1
    return doy

# Load data
cached = np.load('cache/baseline_data.npz')
dates = [datetime.date.fromordinal(int(d)) for d in np.load('cache/baseline_dates.npy')]
sst_data = {}
for d in dates:
    sst_data[d] = cached[d.strftime('%Y%m%d')]

# Verify pool for doy 221 (Aug 8)
# Baseline dates with doy 221: Aug 8 in each year 1992-2002
baseline_start = datetime.date(1992, 1, 1)
baseline_end = datetime.date(2002, 12, 31)

centers_221 = []
dy = baseline_start
while dy <= baseline_end:
    if day_of_year(dy) == 221:
        centers_221.append(dy)
    dy += datetime.timedelta(days=1)

print(f'Baseline dates with doy 221: {centers_221}')

# Get pool dates
pool_221 = []
for c in centers_221:
    for k in range(-5, 6):
        pool_221.append(c + datetime.timedelta(days=k))

print(f'Pool size for doy 221: {len(pool_221)}')
print(f'First few: {pool_221[:5]}')
print(f'Last few: {pool_221[-5:]}')

# Cell (53, 40)
i, j = 53, 40
values = np.array([sst_data[d][i, j] for d in pool_221])
valid = values[~np.isnan(values)]
print(f'Valid values: {len(valid)}')
print(f'Values: {np.sort(valid)}')

# Raw 90th percentile with hazen method
p90 = np.percentile(valid, 90, method='hazen')
mean_val = np.mean(valid)
print(f'Raw 90th percentile (hazen): {p90:.6f}')
print(f'Raw mean: {mean_val:.6f}')

# Compare with the value we stored
threshold_raw = np.load('cache/threshold_raw.npy')
clim_raw = np.load('cache/clim_raw.npy')
print(f'Stored raw threshold for doy 221, cell ({i},{j}): {threshold_raw[220, i, j]:.6f}')
print(f'Stored raw clim for doy 221, cell ({i},{j}): {clim_raw[220, i, j]:.6f}')
