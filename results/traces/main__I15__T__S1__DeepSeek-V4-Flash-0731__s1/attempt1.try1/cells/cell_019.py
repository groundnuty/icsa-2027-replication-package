import numpy as np
import xarray as xr
import fsspec
from datetime import datetime, timedelta

# Reload data
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

t_vals = ds.time.values

# Indices
base_start = np.datetime64('1991-12-27')
base_end = np.datetime64('2003-01-05')
b_idx = np.where((t_vals >= base_start) & (t_vals <= base_end))[0]

t_start = np.datetime64('2019-06-01')
t_end = np.datetime64('2019-08-31')
t_idx = np.where((t_vals >= t_start) & (t_vals <= t_end))[0]

lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_mask = (lat_vals >= 56.13) & (lat_vals <= 57.33)
lon_mask = (lon_vals >= 17.71) & (lon_vals <= 18.91)
lat_idx = np.where(lat_mask)[0]
lon_idx = np.where(lon_mask)[0]

baseline_sst = ds['analysed_sst'].isel(time=b_idx, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)
target_sst = ds['analysed_sst'].isel(time=t_idx, latitude=lat_idx, longitude=lon_idx).values.astype(np.float64)

# Check which cells have all-NaN in baseline
all_nan_baseline = np.all(np.isnan(baseline_sst), axis=0)
print(f"Cells all-NaN in baseline: {np.sum(all_nan_baseline)} out of {all_nan_baseline.size}")

# Check which cells have finite SST on all target days (sea cells)
all_finite_target = np.all(np.isfinite(target_sst), axis=0)
print(f"Sea cells (all finite on target): {np.sum(all_finite_target)}")

# Check overlap: cells that are all-NaN in baseline but sea cells in target
overlap = all_nan_baseline & all_finite_target
print(f"Cells all-NaN in baseline but sea in target: {np.sum(overlap)}")

# Check cells with some NaN in baseline
some_nan_baseline = np.any(np.isnan(baseline_sst), axis=0)
print(f"Cells with some NaN in baseline: {np.sum(some_nan_baseline)}")
print(f"Cells with some NaN in baseline AND sea in target: {np.sum(some_nan_baseline & all_finite_target)}")

# For sea cells, what fraction of baseline days have NaN?
sea_cells_mask = all_finite_target
baseline_frac_nan = np.zeros((60, 60))
for i in range(60):
    for j in range(60):
        if sea_cells_mask[i, j]:
            baseline_frac_nan[i, j] = np.isnan(baseline_sst[:, i, j]).mean()

print(f"\nSea cells with baseline NaN fraction > 0: {np.sum(baseline_frac_nan > 0)}")
if np.sum(baseline_frac_nan > 0) > 0:
    idx_nan = np.where(baseline_frac_nan > 0)
    for i, j in zip(idx_nan[0][:5], idx_nan[1][:5]):
        print(f"  Cell ({i},{j}): baseline NaN fraction = {baseline_frac_nan[i,j]:.4f}")
