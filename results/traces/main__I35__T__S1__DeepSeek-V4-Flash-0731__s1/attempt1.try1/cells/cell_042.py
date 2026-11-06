
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

# Time indices
dt_times = np.array([np.datetime64(t) for t in times])

# Baseline: 1991-12-27 to 2003-01-05
bl_start_idx = np.searchsorted(dt_times, np.datetime64('1991-12-27'))
bl_end_idx = np.searchsorted(dt_times, np.datetime64('2003-01-05'), side='right') - 1

# Target: 2009-06-01 to 2009-08-31
tg_start_idx = np.searchsorted(dt_times, np.datetime64('2009-06-01'))
tg_end_idx = np.searchsorted(dt_times, np.datetime64('2009-08-31'), side='right') - 1

# Extract and convert to float64
baseline_sst = ds.analysed_sst.isel(time=slice(bl_start_idx, bl_end_idx+1), 
                                     latitude=slice(lat_idx[0], lat_idx[-1]+1),
                                     longitude=slice(lon_idx[0], lon_idx[-1]+1)).values.astype(np.float64)
target_sst = ds.analysed_sst.isel(time=slice(tg_start_idx, tg_end_idx+1),
                                   latitude=slice(lat_idx[0], lat_idx[-1]+1),
                                   longitude=slice(lon_idx[0], lon_idx[-1]+1)).values.astype(np.float64)

print(f"Baseline SST shape: {baseline_sst.shape}, dtype: {baseline_sst.dtype}")
print(f"Target SST shape: {target_sst.shape}, dtype: {target_sst.dtype}")

np.save('/tmp/baseline_sst_f64.npy', baseline_sst)
np.save('/tmp/target_sst_f64.npy', target_sst)
np.save('/tmp/baseline_times.npy', dt_times[bl_start_idx:bl_end_idx+1])
np.save('/tmp/target_times.npy', dt_times[tg_start_idx:tg_end_idx+1])

# Also save region coords and full target times
region_lat = lat[lat_idx]
region_lon = lon[lon_idx]
target_times_full = times[tg_start_idx:tg_end_idx+1]
np.save('/tmp/region_lat.npy', region_lat)
np.save('/tmp/region_lon.npy', region_lon)
np.save('/tmp/target_times_full.npy', target_times_full)
print("Saved all data in float64")
