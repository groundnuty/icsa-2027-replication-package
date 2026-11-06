
import numpy as np
import datetime

# Reload everything
baseline_sst = np.load('baseline_sst.npy')
base_dates = np.load('base_dates.npy')
base_dates = [datetime.date.fromordinal(int(x)) for x in base_dates]
sea_cells = np.load('sea_cells.npy')

def date_to_doy(d):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = d.day
    for m in range(1, d.month):
        doy += days_in_month[m-1]
    return doy

baseline_dates = [d for d in base_dates if 1992 <= d.year <= 2002]
date_to_idx = {d: i for i, d in enumerate(base_dates)}

# Build pool indices for each doy
pool_date_indices = {}
for doy in range(1, 367):
    if doy == 60:
        continue
    indices = set()
    for bd in baseline_dates:
        if date_to_doy(bd) == doy:
            for offset in range(-5, 6):
                idx = date_to_idx.get(bd + datetime.timedelta(days=offset))
                if idx is not None:
                    indices.add(idx)
    pool_date_indices[doy] = sorted(indices)

# Compute threshold and climatology for each sea cell and doy
# threshold[doy, i, j] and clim[doy, i, j] for sea cells
n_doy = 366
threshold = np.full((n_doy, 60, 60), np.nan, dtype=np.float64)
clim = np.full((n_doy, 60, 60), np.nan, dtype=np.float64)

sea_cells_2d = sea_cells

# For each doy, compute threshold and clim for all cells
import time
start = time.time()

for doy in range(1, 367):
    if doy == 60:
        continue
    idx_list = pool_date_indices[doy]
    pool_data = baseline_sst[idx_list]  # shape (n_doy, 60, 60)
    # pool_data may contain NaN values
    # Compute threshold (90th percentile, hazen) ignoring NaN
    # and mean ignoring NaN for each cell
    
    # For efficiency, use np.nanquantile and np.nanmean
    threshold[doy] = np.nanquantile(pool_data, 0.9, axis=0, method='hazen')
    clim[doy] = np.nanmean(pool_data, axis=0)

elapsed = time.time() - start
print(f"Computed thresholds and climatologies in {elapsed:.2f} seconds")

# Set day 60 = mean of days 59 and 61
threshold[59] = (threshold[58] + threshold[60]) / 2  # indices 59=doy60, 58=doy59, 60=doy61
clim[59] = (clim[58] + clim[60]) / 2

# Verify
print(f"threshold shape: {threshold.shape}")
print(f"clim shape: {clim.shape}")
print(f"NaN in threshold: {np.isnan(threshold).sum()}")
print(f"NaN in clim: {np.isnan(clim).sum()}")

# Check a few values
print(f"\nSample threshold at cell (0,0):")
for doy in [59, 60, 61, 180, 365, 366]:
    print(f"  doy={doy}: {threshold[doy-1, 0, 0]}")

np.save('threshold.npy', threshold)
np.save('clim.npy', clim)
print("\nSaved threshold and clim")
