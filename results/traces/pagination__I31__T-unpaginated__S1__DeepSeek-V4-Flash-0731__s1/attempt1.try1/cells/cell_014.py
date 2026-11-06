
import numpy as np
import datetime as dt

# Reconstruct the needed variables
month_offsets = {1: 0, 2: 31, 3: 60, 4: 91, 5: 121, 6: 152, 7: 182, 8: 213, 9: 244, 10: 274, 11: 305, 12: 335}
def date_to_doy(y, m, d):
    return month_offsets[m] + d

baseline_start = dt.date(1992, 1, 1)
baseline_end = dt.date(2002, 12, 31)
doy_to_baseline_dates = {d: [] for d in range(1, 367)}
d = baseline_start
while d <= baseline_end:
    doy = date_to_doy(d.year, d.month, d.day)
    doy_to_baseline_dates[doy].append(d)
    d += dt.timedelta(days=1)

doy_to_pool_dates = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    pool_dates = set()
    for B in doy_to_baseline_dates[doy]:
        for offset in range(-5, 6):
            pool_dates.add(B + dt.timedelta(days=offset))
    doy_to_pool_dates[doy] = sorted(pool_dates)

dates_baseline = []
d = dt.date(1991, 12, 27)
while d <= dt.date(2003, 1, 5):
    dates_baseline.append(d)
    d += dt.timedelta(days=1)
date_to_index = {date: i for i, date in enumerate(dates_baseline)}

doy_to_pool_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    indices = [date_to_index[d] for d in doy_to_pool_dates[doy]]
    doy_to_pool_indices[doy] = np.array(indices)

# Now compute thresholds and climatology for all cells
# baseline_sst shape: (4028, 60, 60)
# We need to compute for all 60x60 cells (will handle sea cells later)

n_doy = 366
n_lat = 60
n_lon = 60

threshold = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)
climatology = np.full((n_doy, n_lat, n_lon), np.nan, dtype=np.float64)

for doy in range(1, 367):
    if doy == 60:
        continue
    pool_idx = doy_to_pool_indices[doy]
    pool_data = baseline_sst[pool_idx, :, :]  # (n_pool, 60, 60)
    
    for i in range(n_lat):
        for j in range(n_lon):
            vals = pool_data[:, i, j]
            valid = vals[~np.isnan(vals)]
            if len(valid) > 0:
                threshold[doy-1, i, j] = np.percentile(valid, 90, method='hazen')
                climatology[doy-1, i, j] = np.mean(valid)
            # else leave as NaN

print("Computed thresholds and climatology for doy 1-59 and 61-366")

# Set doy 60 (index 59) to mean of doy 59 and 61
threshold[59, :, :] = (threshold[58, :, :] + threshold[60, :, :]) / 2.0
climatology[59, :, :] = (climatology[58, :, :] + climatology[60, :, :]) / 2.0

# Check some values
print("Threshold doy 59, cell (0,0):", threshold[58, 0, 0])
print("Threshold doy 60, cell (0,0):", threshold[59, 0, 0])
print("Threshold doy 61, cell (0,0):", threshold[60, 0, 0])
print()
print("Climatology doy 59, cell (0,0):", climatology[58, 0, 0])
print("Climatology doy 60, cell (0,0):", climatology[59, 0, 0])
print("Climatology doy 61, cell (0,0):", climatology[60, 0, 0])
print()
print("NaN in threshold:", np.isnan(threshold).sum())
print("NaN in climatology:", np.isnan(climatology).sum())
