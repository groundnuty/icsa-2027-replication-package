
import numpy as np
from datetime import date
from collections import defaultdict
import xarray as xr
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
region = ds.sel(latitude=slice(55.67, 56.87), longitude=slice(16.45, 17.65))

target = region.sel(time=slice('2021-06-01', '2021-08-31'))
target_sst = target.analysed_sst.values.astype(np.float64)
target_dates = pd.to_datetime(target.time.values).date

baseline_ext = region.sel(time=slice('1991-12-27', '2003-01-05'))
baseline_sst = baseline_ext.analysed_sst.values.astype(np.float64)
baseline_dates = pd.to_datetime(baseline_ext.time.values).date

sea_mask = np.all(np.isfinite(target_sst), axis=0)
n_sea = sea_mask.sum()
print("Sea cells:", n_sea)

# Day of year
CUM = [0, 31, 60, 91, 121, 152, 182, 213, 244, 274, 305, 335]
def doy_from_md(month, day):
    return CUM[month-1] + day

def get_doy(d):
    return doy_from_md(d.month, d.day)

# Build pools
baseline_mask = np.array([(date(1992,1,1) <= d <= date(2002,12,31)) for d in baseline_dates])
baseline_idx = np.where(baseline_mask)[0]

pool_indices = defaultdict(list)
for bi in baseline_idx:
    b = baseline_dates[bi]
    b_doy = get_doy(b)
    if b_doy == 60:
        continue
    lo = max(0, bi - 5)
    hi = min(len(baseline_dates)-1, bi + 5)
    pool_indices[b_doy].extend(list(range(lo, hi+1)))

# Compute threshold and climatology for each day-of-year pool
sea_cell_positions = np.where(sea_mask)
sea_cell_idx = list(zip(sea_cell_positions[0], sea_cell_positions[1]))

# Arrays indexed by doy-1 (0-365)
threshold = np.zeros((366, 60, 60), dtype=np.float64)
climatology = np.zeros((366, 60, 60), dtype=np.float64)

for d in range(1, 367):
    if d == 60:
        continue
    idx = pool_indices.get(d, [])
    if not idx:
        continue
    idx = np.array(idx)
    sst_sub = baseline_sst[idx]  # shape (n_dates, 60, 60)
    for cell_i, cell_j in sea_cell_idx:
        vals = sst_sub[:, cell_i, cell_j]
        vals = vals[np.isfinite(vals)]
        if len(vals) > 0:
            threshold[d-1, cell_i, cell_j] = np.percentile(vals, 90, method='hazen')
            climatology[d-1, cell_i, cell_j] = np.mean(vals)

print("Computed thresholds and climatology for all pools")
print("Threshold[90] sample:", threshold[89, sea_cell_idx[0]])
print("Climatology[90] sample:", climatology[89, sea_cell_idx[0]])
