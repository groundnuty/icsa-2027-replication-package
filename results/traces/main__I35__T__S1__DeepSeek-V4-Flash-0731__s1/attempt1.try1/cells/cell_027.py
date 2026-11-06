
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values

# Region indices
lat_idx = np.where((lat >= 59.93) & (lat <= 61.13))[0]
lon_idx = np.where((lon >= 18.69) & (lon <= 19.89))[0]

region_lat = lat[lat_idx]
region_lon = lon[lon_idx]

# Target times
times = ds.time.values
dt_times = np.array([np.datetime64(t) for t in times])
tg_start = np.searchsorted(dt_times, np.datetime64('2009-06-01'))
tg_end = np.searchsorted(dt_times, np.datetime64('2009-08-31'), side='right') - 1
target_times_full = times[tg_start:tg_end+1]

print(f"Region lat: {region_lat[0]} to {region_lat[-1]}, {len(region_lat)} cells")
print(f"Region lon: {region_lon[0]} to {region_lon[-1]}, {len(region_lon)} cells")
print(f"Target times: {len(target_times_full)}, first={target_times_full[0]}, last={target_times_full[-1]}")
print(f"Target times dtype: {target_times_full.dtype}")
