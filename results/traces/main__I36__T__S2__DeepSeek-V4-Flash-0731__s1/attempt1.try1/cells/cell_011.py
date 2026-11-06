
import numpy as np
from datetime import datetime, timedelta
import fsspec
import xarray as xr

# Load all needed data first
fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
f = fs.open(path, 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
times = ds.time.values

# Region indices
lat_idx = slice(330, 390)
lon_idx = slice(551, 611)

# Extended baseline: indices 3647 to 7674 inclusive (4028 days)
baseline_data = ds['analysed_sst'].isel(time=slice(3647, 7675),
                                         latitude=lat_idx, longitude=lon_idx).values
baseline_times = times[3647:7675]
print(f"Baseline data shape: {baseline_data.shape}")
print(f"Baseline time range: {baseline_times[0]} to {baseline_times[-1]}")

# Target: indices 7821 to 7912 inclusive (92 days)
target_data = ds['analysed_sst'].isel(time=slice(7821, 7913),
                                       latitude=lat_idx, longitude=lon_idx).values
target_times = times[7821:7913]
print(f"Target data shape: {target_data.shape}")
print(f"Target time range: {target_times[0]} to {target_times[-1]}")
