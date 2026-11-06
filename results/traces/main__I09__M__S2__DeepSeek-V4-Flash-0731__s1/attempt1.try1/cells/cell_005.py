
import xarray as xr
import numpy as np
import pandas as pd

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

# Region
lat_min, lat_max = 54.81, 56.01
lon_min, lon_max = 19.61, 20.81

lat_sel = ds.latitude.values
lon_sel = ds.longitude.values
lat_idx = np.where((lat_sel >= lat_min) & (lat_sel <= lat_max))[0]
lon_idx = np.where((lon_sel >= lon_min) & (lon_sel <= lon_max))[0]

print("lat_idx range:", lat_idx[0], lat_idx[-1], "count:", len(lat_idx))
print("lon_idx range:", lon_idx[0], lon_idx[-1], "count:", len(lon_idx))

# Time: need from 1991-12-27 to 2022-08-31
time_vals = ds.time.values
t_start = np.datetime64('1991-12-27')
t_end = np.datetime64('2022-08-31')
t_idx = np.where((time_vals >= t_start) & (time_vals <= t_end))[0]

print("n time indices:", len(t_idx))
print("time range:", time_vals[t_idx[0]], "to", time_vals[t_idx[-1]])

# Load the data for the full needed period and region
# Use proper slicing (inclusive of last)
lat_start = lat_idx[0]
lat_end = lat_idx[-1] + 1
lon_start = lon_idx[0]
lon_end = lon_idx[-1] + 1

sst_region = ds['analysed_sst'].isel(
    time=t_idx,
    latitude=slice(lat_start, lat_end),
    longitude=slice(lon_start, lon_end)
)
print("sst_region shape:", sst_region.shape)

# Load into memory as float64
sst_data = sst_region.values.astype(np.float64)
time_sub = time_vals[t_idx]
print("Loaded data:", sst_data.shape, "dtype:", sst_data.dtype)
print("Any NaN?", np.isnan(sst_data).any())
print("NaN count:", np.isnan(sst_data).sum())
print("Data range:", np.nanmin(sst_data), "to", np.nanmax(sst_data))
