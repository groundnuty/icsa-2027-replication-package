
import xarray as xr
import numpy as np

path = "/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc"
ds = xr.open_dataset(path, engine="h5netcdf")

# Region indices
lat_idx = list(range(34, 94))  # 54.18 to 55.36
lon_idx = list(range(213, 273))  # 13.26 to 14.44

time = ds['time'].values

# Target period
target_start = np.datetime64('2014-06-01')
target_end = np.datetime64('2014-08-31')
target_mask = (time >= target_start) & (time <= target_end)
target_time_idx = np.where(target_mask)[0]

# Load target data for region
target_sst = ds['analysed_sst'].isel(time=target_time_idx, latitude=lat_idx, longitude=lon_idx).values
print("Target SST shape:", target_sst.shape, "dtype:", target_sst.dtype)
print("Target dates:", ds['time'].values[target_time_idx[0]], "to", ds['time'].values[target_time_idx[-1]])
print("Target lat:", ds['latitude'].values[lat_idx[0]], "to", ds['latitude'].values[lat_idx[-1]], "count:", len(lat_idx))
print("Target lon:", ds['longitude'].values[lon_idx[0]], "to", ds['longitude'].values[lon_idx[-1]], "count:", len(lon_idx))
print("NaN count in target:", np.isnan(target_sst).sum(), "of", target_sst.size)
