
import numpy as np
import xarray as xr
import json

# Load data
target_sst = np.load('/tmp/target_sst.npy').astype(np.float64)
threshold_smooth = np.load('/tmp/threshold_smooth_v2.npy')
sea_cells = np.load('/tmp/sea_cells.npy')

# Read output
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw_mask = ds.mhw.values

# Recompute hot days to verify
import datetime

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

# Count hot days not in MHW
diff = np.sum(hot & ~(mhw_mask.astype(bool)))
print(f"Hot days not in any MHW: {diff}")

# Check per-cell: find cells where hot days differ from MHW days
for si in range(min(20, n_sea)):
    li, loi = sea_idx[0][si], sea_idx[1][si]
    h = hot[:, li, loi]
    m = mhw_mask[:, li, loi].astype(bool)
    if (h != m).any():
        # Find hot runs
        runs = []
        i = 0
        while i < 92:
            if h[i]:
                j = i
                while j < 92 and h[j]:
                    j += 1
                runs.append((i, j-1))
                i = j
            else:
                i += 1
        # Find MHW periods
        mhws = []
        i = 0
        while i < 92:
            if m[i]:
                j = i
                while j < 92 and m[j]:
                    j += 1
                mhws.append((i, j-1))
                i = j
            else:
                i += 1
        print(f"\nCell ({li},{loi}): hot runs={runs}, MHW periods={mhws}")
        print(f"  Hot days not in MHW: {(h & ~m).sum()}")
