
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_indices = np.where((lat_vals >= lat_min) & (lat_vals <= lat_max))[0]
lon_indices = np.where((lon_vals >= lon_min) & (lon_vals <= lon_max))[0]

time_vals = ds.time.values

# Baseline indices
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
baseline_mask = (time_vals >= baseline_start) & (time_vals <= baseline_end)
baseline_time_indices = np.where(baseline_mask)[0]

# Target indices
target_start = np.datetime64('2015-06-01')
target_end = np.datetime64('2015-08-31')
target_mask = (time_vals >= target_start) & (time_vals <= target_end)
target_time_indices = np.where(target_mask)[0]

# Extract baseline data
baseline_sst = ds['analysed_sst'].isel(
    time=baseline_time_indices,
    latitude=lat_indices,
    longitude=lon_indices
).values.astype(np.float64)

print(f"Baseline SST shape: {baseline_sst.shape}")
print(f"Baseline NaN count: {np.isnan(baseline_sst).sum()}")
print(f"Baseline non-NaN count: {np.sum(~np.isnan(baseline_sst))}")

# Extract target data
target_sst = ds['analysed_sst'].isel(
    time=target_time_indices,
    latitude=lat_indices,
    longitude=lon_indices
).values.astype(np.float64)

print(f"Target SST shape: {target_sst.shape}")
print(f"Target NaN count: {np.isnan(target_sst).sum()}")
print(f"Target non-NaN count: {np.sum(~np.isnan(target_sst))}")

# Get the times
baseline_times = time_vals[baseline_time_indices]
target_times = time_vals[target_time_indices]
print(f"Baseline times: {baseline_times[0]} to {baseline_times[-1]}, count={len(baseline_times)}")
print(f"Target times: {target_times[0]} to {target_times[-1]}, count={len(target_times)}")

# Save for later use
np.save('/work/baseline_sst.npy', baseline_sst)
np.save('/work/target_sst.npy', target_sst)
np.save('/work/baseline_times.npy', baseline_times)
np.save('/work/target_times.npy', target_times)
np.save('/work/lat_indices.npy', lat_indices)
np.save('/work/lon_indices.npy', lon_indices)

print("\nSaved all data.")
