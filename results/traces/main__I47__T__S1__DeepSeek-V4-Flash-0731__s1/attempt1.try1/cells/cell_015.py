
import xarray as xr, fsspec, numpy as np
from datetime import datetime, timedelta
from collections import defaultdict

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Select region
lat_mask = (ds.latitude >= 64.39) & (ds.latitude <= 65.59)
lon_mask = (ds.longitude >= 23.41) & (ds.longitude <= 24.61)

# Time selection
t_start_base = np.datetime64('1991-12-27')
t_end_base = np.datetime64('2003-01-05')
t_start_tgt = np.datetime64('2019-06-01')
t_end_tgt = np.datetime64('2019-08-31')

time_vals = ds.time.values
base_mask = (time_vals >= t_start_base) & (time_vals <= t_end_base)
tgt_mask = (time_vals >= t_start_tgt) & (time_vals <= t_end_tgt)

# Extract data
ds_base = ds.isel(time=base_mask, latitude=lat_mask, longitude=lon_mask)
ds_tgt = ds.isel(time=tgt_mask, latitude=lat_mask, longitude=lon_mask)

# Convert to numpy arrays
base_data = ds_base.analysed_sst.values.astype(np.float64)  # (4028, 60, 60)
tgt_data = ds_tgt.analysed_sst.values.astype(np.float64)    # (92, 60, 60)

base_times = ds_base.time.values
tgt_times = ds_tgt.time.values

print("Base data shape:", base_data.shape)
print("Target data shape:", tgt_data.shape)
print("Base times:", base_times[0], base_times[-1])
print("Target times:", tgt_times[0], tgt_times[-1])
print("Num base NaN:", np.isnan(base_data).sum())
print("Num target NaN:", np.isnan(tgt_data).sum())

# Save these arrays for later use
np.save('/tmp/base_data.npy', base_data)
np.save('/tmp/tgt_data.npy', tgt_data)
np.save('/tmp/base_times.npy', base_times)
np.save('/tmp/tgt_times.npy', tgt_times)

# Also save lat/lon
lats = ds_base.latitude.values
lons = ds_base.longitude.values
np.save('/tmp/lats.npy', lats)
np.save('/tmp/lons.npy', lons)
print("Saved.")
