
import fsspec
import xarray as xr
import numpy as np
fs = fsspec.filesystem('onedata')

f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

times = ds.time.values
lat = ds.latitude.values
lon = ds.longitude.values

# Region indices
lat_idx = np.where((lat >= 59.93) & (lat <= 61.13))[0]
lon_idx = np.where((lon >= 18.69) & (lon <= 19.89))[0]
print(f"lat_idx: {lat_idx[0]} to {lat_idx[-1]}, {len(lat_idx)} cells")
print(f"lon_idx: {lon_idx[0]} to {lon_idx[-1]}, {len(lon_idx)} cells")

# Time indices
dt_times = np.array([np.datetime64(t) for t in times])

# Baseline: 1991-12-27 to 2003-01-05
bl_start_idx = np.searchsorted(dt_times, np.datetime64('1991-12-27'))
bl_end_idx = np.searchsorted(dt_times, np.datetime64('2003-01-05'), side='right') - 1
print(f"Baseline indices: {bl_start_idx} to {bl_end_idx}")

# Target: 2009-06-01 to 2009-08-31
tg_start_idx = np.searchsorted(dt_times, np.datetime64('2009-06-01'))
tg_end_idx = np.searchsorted(dt_times, np.datetime64('2009-08-31'), side='right') - 1
print(f"Target indices: {tg_start_idx} to {tg_end_idx}")

# Extract region for baseline
# This is 4028 x 60 x 60 float32 = about 58 MB, manageable
baseline_sst = ds.analysed_sst.isel(time=slice(bl_start_idx, bl_end_idx+1), 
                                     latitude=slice(lat_idx[0], lat_idx[-1]+1),
                                     longitude=slice(lon_idx[0], lon_idx[-1]+1)).values
print(f"Baseline SST shape: {baseline_sst.shape}")
print(f"Baseline NaN count: {np.isnan(baseline_sst).sum()}")
print(f"Baseline dtype: {baseline_sst.dtype}")

# Extract region for target
target_sst = ds.analysed_sst.isel(time=slice(tg_start_idx, tg_end_idx+1),
                                   latitude=slice(lat_idx[0], lat_idx[-1]+1),
                                   longitude=slice(lon_idx[0], lon_idx[-1]+1)).values
print(f"Target SST shape: {target_sst.shape}")
print(f"Target NaN count: {np.isnan(target_sst).sum()}")
print(f"Target dtype: {target_sst.dtype}")

# Save to local files for later processing
np.save('/tmp/baseline_sst.npy', baseline_sst)
np.save('/tmp/target_sst.npy', target_sst)
np.save('/tmp/baseline_times.npy', dt_times[bl_start_idx:bl_end_idx+1])
np.save('/tmp/target_times.npy', dt_times[tg_start_idx:tg_end_idx+1])
print("Saved to /tmp/")
