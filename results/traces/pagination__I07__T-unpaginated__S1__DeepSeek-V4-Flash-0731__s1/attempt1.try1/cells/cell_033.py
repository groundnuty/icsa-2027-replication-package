
import numpy as np
import xarray as xr
import json
import datetime

# Load data
target_sst = np.load('/tmp/target_sst.npy').astype(np.float64)
threshold_smooth = np.load('/tmp/threshold_smooth_v2.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Read output mhw_mask
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw_mask_out = ds.mhw.values.astype(bool)

# Recompute hot days
def doy_from_date(date):
    month_starts = [1, 32, 61, 92, 122, 153, 183, 214, 245, 275, 306, 336]
    return month_starts[date.month - 1] + date.day - 1

target_dates = []
d = datetime.date(2021, 6, 1)
while d <= datetime.date(2021, 8, 31):
    target_dates.append(d)
    d += datetime.timedelta(days=1)
target_doys = [doy_from_date(d) for d in target_dates]

sea_idx = np.where(sea_cells)
n_sea = len(sea_idx[0])

hot = np.zeros((92, 60, 60), dtype=bool)
for si in range(n_sea):
    li, loi = sea_idx[0][si], sea_idx[1][si]
    for i in range(92):
        d = target_doys[i] - 1
        sst_val = target_sst[i, li, loi]
        thr_val = threshold_smooth[d, li, loi]
        if not np.isnan(sst_val) and not np.isnan(thr_val):
            hot[i, li, loi] = sst_val >= thr_val

print(f"Hot day count (verification): {hot.sum()}")
print(f"Hot day count (main): 175928")

# Now find per-cell MHWs independently
def find_per_cell_mhws(hot_array):
    n = len(hot_array)
    runs = []
    i = 0
    while i < n:
        if hot_array[i]:
            j = i
            while j < n and hot_array[j]:
                j += 1
            runs.append((i, j-1))
            i = j
        else:
            i += 1
    mhws = [(s, e) for s, e in runs if e - s + 1 >= 5]
    merged = []
    for mhw in mhws:
        if not merged:
            merged.append(mhw)
        else:
            prev_end = merged[-1][1]
            gap = mhw[0] - prev_end - 1
            if 1 <= gap <= 2:
                merged[-1] = (merged[-1][0], mhw[1])
            else:
                merged.append(mhw)
    return merged

# Recompute mhw_mask independently
mhw_mask_recomputed = np.zeros((92, 60, 60), dtype=bool)
for si in range(n_sea):
    li, loi = sea_idx[0][si], sea_idx[1][si]
    mhws = find_per_cell_mhws(hot[:, li, loi])
    for (s, e) in mhws:
        mhw_mask_recomputed[s:e+1, li, loi] = True

# Compare with output
print(f"MHW mask sum (recomputed): {mhw_mask_recomputed.sum()}")
print(f"MHW mask sum (output): {mhw_mask_out.sum()}")
print(f"Difference: {(mhw_mask_recomputed != mhw_mask_out).sum()}")

# Verify all cells match
mismatches = np.where(mhw_mask_recomputed != mhw_mask_out)
if len(mismatches[0]) > 0:
    print(f"Mismatch at: {list(zip(mismatches[0][:10], mismatches[1][:10], mismatches[2][:10]))}")
else:
    print("All MHW masks match!")

# Compute regional events from recomputed mask
active = mhw_mask_recomputed.max(axis=(1, 2))
regional_events = []
i = 0
while i < 92:
    if active[i]:
        j = i
        while j < 92 and active[j]:
            j += 1
        regional_events.append((i, j-1))
        i = j
    else:
        i += 1

print(f"\nRegional events (recomputed): {len(regional_events)}")
for s, e in regional_events:
    print(f"  Event: {target_dates[s]} to {target_dates[e]} ({e-s+1} days)")
