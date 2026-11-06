import numpy as np
import xarray as xr
import datetime as dt

# Load saved data
base_ds = xr.open_dataset('/tmp/base_data.nc')
target_ds = xr.open_dataset('/tmp/target_data.nc')

base_sst = base_ds['analysed_sst'].values  # (4028, 60, 60)
target_sst = target_ds['analysed_sst'].values  # (92, 60, 60)

base_time = base_ds['time'].values  # datetime64
target_time = target_ds['time'].values

lat_vals = base_ds['latitude'].values
lon_vals = base_ds['longitude'].values

print("Base time range:", base_time[0], base_time[-1], len(base_time))
print("Target time range:", target_time[0], target_time[-1], len(target_time))
print("Base SST shape:", base_sst.shape, base_sst.dtype)
print("Target SST shape:", target_sst.shape, target_sst.dtype)
print("NaN in base:", np.isnan(base_sst).sum())
print("NaN in target:", np.isnan(target_sst).sum())
