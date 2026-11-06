import xarray as xr
import numpy as np

# Load without dask
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# The file is 40GB. Let me try to load just the needed portion.
# First, get the time indices
times = ds.time.values
base_idx_start = np.where(times >= np.datetime64('1991-12-27'))[0][0]
base_idx_end = np.where(times <= np.datetime64('2003-01-05'))[0][-1]
targ_idx_start = np.where(times >= np.datetime64('2007-06-01'))[0][0]
targ_idx_end = np.where(times <= np.datetime64('2007-08-31'))[0][-1]

print(f"Baseline: {base_idx_start} to {base_idx_end} ({base_idx_end - base_idx_start + 1} days)")
print(f"Target: {targ_idx_start} to {targ_idx_end} ({targ_idx_end - targ_idx_start + 1} days)")

# Get lat/lon indices for region
lats = ds.latitude.values
lons = ds.longitude.values
lat_sel = np.where((lats >= 57.83) & (lats <= 59.03))[0]
lon_sel = np.where((lons >= 17.41) & (lons <= 18.61))[0]
print(f"Lat indices: {lat_sel[0]} to {lat_sel[-1]}, count={len(lat_sel)}")
print(f"Lon indices: {lon_sel[0]} to {lon_sel[-1]}, count={len(lon_sel)}")

# Extract baseline
baseline_data = ds.analysed_sst.values[base_idx_start:base_idx_end+1, lat_sel[0]:lat_sel[-1]+1, lon_sel[0]:lon_sel[-1]+1]
print("Baseline shape:", baseline_data.shape)
print("Baseline dtype:", baseline_data.dtype)
print("Baseline non-NaN:", np.sum(~np.isnan(baseline_data)))

# Extract target
target_data = ds.analysed_sst.values[targ_idx_start:targ_idx_end+1, lat_sel[0]:lat_sel[-1]+1, lon_sel[0]:lon_sel[-1]+1]
print("Target shape:", target_data.shape)
print("Target dtype:", target_data.dtype)
print("Target non-NaN:", np.sum(~np.isnan(target_data)))
