
import numpy as np
import datetime

# Load baseline data
baseline_sst = np.load('baseline_sst.npy')
base_dates = np.load('base_dates.npy')
base_dates = [datetime.date.fromordinal(int(x)) for x in base_dates]
sea_cells = np.load('sea_cells.npy')

# Build date -> index mapping
date_to_idx = {d: i for i, d in enumerate(base_dates)}

# Load the pool_dates structure (need to reconstruct it)
def date_to_doy(d):
    days_in_month = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    doy = d.day
    for m in range(1, d.month):
        doy += days_in_month[m-1]
    return doy

baseline_dates = [d for d in base_dates if 1992 <= d.year <= 2002]

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

# Check sizes
for doy in [1, 59, 61, 180, 365, 366]:
    print(f"doy={doy}: {len(pool_date_indices[doy])} indices")

# For each sea cell and doy, compute threshold and climatology
# sea_cells is (60, 60) boolean
n_sea = sea_cells.sum()
print(f"\nNumber of sea cells: {n_sea}")

# Get sea cell indices
sea_indices = np.argwhere(sea_cells)
print(f"Sea cell indices shape: {sea_indices.shape}")

# Let's compute for a small test first
# Test with one cell
test_cell = sea_indices[0]
i, j = test_cell
print(f"\nTest cell: ({i}, {j})")

doy = 180
idx_list = pool_date_indices[doy]
values = baseline_sst[idx_list, i, j]
values = values[np.isfinite(values)]
print(f"doy=180: {len(values)} finite values out of {len(idx_list)}")
if len(values) > 0:
    print(f"  threshold (hazen 90th): {np.quantile(values, 0.9, method='hazen')}")
    print(f"  mean: {np.mean(values)}")
