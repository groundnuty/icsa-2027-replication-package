
import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

time = ds.time.values

# Region indices
lat = ds.latitude.values
lon = ds.longitude.values
lat_idx = np.where((lat >= 64.39) & (lat <= 65.59))[0]
lon_idx = np.where((lon >= 23.41) & (lon <= 24.61))[0]

# Extended baseline: 1991-12-27 to 2003-01-05
ext_base_start = np.datetime64('1991-12-27')
ext_base_end = np.datetime64('2003-01-05')
ext_base_mask = (time >= ext_base_start) & (time <= ext_base_end)
ext_base_time_idx = np.where(ext_base_mask)[0]

# Target period
target_start = np.datetime64('2013-06-01')
target_end = np.datetime64('2013-08-31')
target_mask = (time >= target_start) & (time <= target_end)
target_time_idx = np.where(target_mask)[0]

print("ext base time range:", time[ext_base_time_idx[0]], "to", time[ext_base_time_idx[-1]])
print("n ext base days:", len(ext_base_time_idx))
print("target time range:", time[target_time_idx[0]], "to", time[target_time_idx[-1]])
print("n target days:", len(target_time_idx))

# Load region data for ext baseline and target
ext_data = ds.analysed_sst.isel(time=ext_base_time_idx, latitude=lat_idx, longitude=lon_idx).values
target_data = ds.analysed_sst.isel(time=target_time_idx, latitude=lat_idx, longitude=lon_idx).values

print("ext_data shape:", ext_data.shape, "dtype:", ext_data.dtype)
print("target_data shape:", target_data.shape, "dtype:", target_data.dtype)

# Check for NaN
print("ext_data NaN count:", np.isnan(ext_data).sum())
print("target_data NaN count:", np.isnan(target_data).sum())

# Check ext data time values
print("ext times first/last:", time[ext_base_time_idx[0]], time[ext_base_time_idx[-1]])
