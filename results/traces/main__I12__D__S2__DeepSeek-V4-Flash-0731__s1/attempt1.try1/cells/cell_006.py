
import xarray as xr
import numpy as np
import pandas as pd

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

lat = ds.latitude.values
lon = ds.longitude.values
time = pd.to_datetime(ds.time.values)

lat_idx = np.where((lat >= 56.09) & (lat <= 57.29))[0]
lon_idx = np.where((lon >= 10.55) & (lon <= 11.75))[0]

# Load baseline data: 1991-12-27 to 2003-01-05
t_start = pd.Timestamp('1991-12-27')
t_end = pd.Timestamp('2003-01-05')
mask = (time >= t_start) & (time <= t_end)
idx_base = np.where(mask)[0]

# Load target data: 2009-06-01 to 2009-08-31
t_start_t = pd.Timestamp('2009-06-01')
t_end_t = pd.Timestamp('2009-08-31')
mask_t = (time >= t_start_t) & (time <= t_end_t)
idx_target = np.where(mask_t)[0]

# Read the subset
base_sst = ds['analysed_sst'].isel(time=idx_base, latitude=lat_idx, longitude=lon_idx).values
target_sst = ds['analysed_sst'].isel(time=idx_target, latitude=lat_idx, longitude=lon_idx).values

print("base_sst shape:", base_sst.shape)
print("target_sst shape:", target_sst.shape)
print("Base time range:", time[idx_base[0]], "to", time[idx_base[-1]])
print("Target time range:", time[idx_target[0]], "to", time[idx_target[-1]])

# Check NaN pattern
print("Base NaN fraction:", np.isnan(base_sst).mean())
print("Target NaN fraction:", np.isnan(target_sst).mean())

# Check units - is SST in kelvin?
print(ds['analysed_sst'].attrs)
