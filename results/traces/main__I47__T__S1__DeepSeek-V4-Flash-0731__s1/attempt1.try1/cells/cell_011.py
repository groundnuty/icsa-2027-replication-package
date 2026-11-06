
import xarray as xr, fsspec, numpy as np
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Select region
lat_mask = (ds.latitude >= 64.39) & (ds.latitude <= 65.59)
lon_mask = (ds.longitude >= 23.41) & (ds.longitude <= 24.61)

# Time selection for baseline: 1991-12-27 to 2003-01-05
t_start_base = np.datetime64('1991-12-27')
t_end_base = np.datetime64('2003-01-05')
# Target: 2019-06-01 to 2019-08-31
t_start_tgt = np.datetime64('2019-06-01')
t_end_tgt = np.datetime64('2019-08-31')

time_vals = ds.time.values
print("Time range:", time_vals[0], time_vals[-1])

# Find indices
base_mask = (time_vals >= t_start_base) & (time_vals <= t_end_base)
tgt_mask = (time_vals >= t_start_tgt) & (time_vals <= t_end_tgt)
print("Baseline days:", base_mask.sum(), "Target days:", tgt_mask.sum())

# Extract the data
ds_base = ds.isel(time=base_mask, latitude=lat_mask, longitude=lon_mask)
ds_tgt = ds.isel(time=tgt_mask, latitude=lat_mask, longitude=lon_mask)

print("Baseline shape:", ds_base.analysed_sst.shape)
print("Target shape:", ds_tgt.analysed_sst.shape)
print("Baseline time range:", ds_base.time.values[0], ds_base.time.values[-1])
print("Target time range:", ds_tgt.time.values[0], ds_tgt.time.values[-1])

# Check for NaN
base_data = ds_base.analysed_sst.values
tgt_data = ds_tgt.analysed_sst.values
print("Baseline NaN count:", np.isnan(base_data).sum())
print("Target NaN count:", np.isnan(tgt_data).sum())
print("Baseline total:", base_data.size)
print("Target total:", tgt_data.size)
