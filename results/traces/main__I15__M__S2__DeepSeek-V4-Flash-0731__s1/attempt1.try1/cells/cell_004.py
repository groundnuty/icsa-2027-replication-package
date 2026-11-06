
import xarray as xr
import numpy as np

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

lat_sel = ds.latitude.values
lon_sel = ds.longitude.values
lat_idx = np.where((lat_sel >= lat_min) & (lat_sel <= lat_max))[0]
lon_idx = np.where((lon_sel >= lon_min) & (lon_sel <= lon_max))[0]

time_vals = ds.time.values
target_start = np.datetime64('2019-06-01')
target_end = np.datetime64('2019-08-31')
target_idx = np.where((time_vals >= target_start) & (time_vals <= target_end))[0]

sst = ds.analysed_sst.isel(time=target_idx, latitude=lat_idx, longitude=lon_idx).values
print("sst shape", sst.shape)
print("NaN count", np.isnan(sst).sum())
# Find which cells have all finite
all_finite = np.all(np.isfinite(sst), axis=0)
print("all finite cells count", all_finite.sum(), "of", all_finite.size)
print("NaN per day", np.isnan(sst).sum(axis=(1,2)))
