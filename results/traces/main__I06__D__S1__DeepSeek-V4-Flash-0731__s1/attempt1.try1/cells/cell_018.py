
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat_min, lat_max = 54.45, 55.65
lon_min, lon_max = 16.05, 17.25
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= lat_min) & (lat <= lat_max))[0]
lon_idx = np.where((lon >= lon_min) & (lon <= lon_max))[0]

time = ds.time.values

# Baseline: 1991-12-27 to 2003-01-05
baseline_start = np.datetime64('1991-12-27')
baseline_end = np.datetime64('2003-01-05')
baseline_time_idx = np.where((time >= baseline_start) & (time <= baseline_end))[0]

print(f"Loading baseline data...")
# Load the region slice for baseline period
baseline_sst = ds.analysed_sst.isel(
    time=baseline_time_idx,
    latitude=slice(lat_idx[0], lat_idx[-1]),
    longitude=slice(lon_idx[0], lon_idx[-1])
).values
print(f"Baseline SST shape: {baseline_sst.shape}")
print(f"Dtype: {baseline_sst.dtype}")

# Target: 2012-06-01 to 2012-08-31
target_start = np.datetime64('2012-06-01')
target_end = np.datetime64('2012-08-31')
target_time_idx = np.where((time >= target_start) & (time <= target_end))[0]

print(f"\nLoading target data...")
target_sst = ds.analysed_sst.isel(
    time=target_time_idx,
    latitude=slice(lat_idx[0], lat_idx[-1]),
    longitude=slice(lon_idx[0], lon_idx[-1])
).values
print(f"Target SST shape: {target_sst.shape}")

# Save to files for later use
np.save('/work/baseline_sst.npy', baseline_sst)
np.save('/work/target_sst.npy', target_sst)
np.save('/work/baseline_time_idx.npy', baseline_time_idx)
np.save('/work/target_time_idx.npy', target_time_idx)
np.save('/work/lat_idx.npy', lat_idx)
np.save('/work/lon_idx.npy', lon_idx)
print("\nSaved.")
