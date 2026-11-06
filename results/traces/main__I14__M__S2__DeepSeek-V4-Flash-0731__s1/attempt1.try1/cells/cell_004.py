
import xarray as xr
import numpy as np
import os

path = '/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds = xr.open_dataset(path, engine='h5netcdf')

lat_min, lat_max = 56.13, 57.33
lon_min, lon_max = 17.71, 18.91

lat_idx = np.where((ds.latitude.values >= lat_min) & (ds.latitude.values <= lat_max))[0]
lon_idx = np.where((ds.longitude.values >= lon_min) & (ds.longitude.values <= lon_max))[0]

# Load the region data as numpy
sst = ds.analysed_sst.isel(latitude=lat_idx, longitude=lon_idx)
print("Loaded shape:", sst.shape)

# Convert to numpy float64
sst_data = sst.values.astype(np.float64)
times = ds.time.values
lat_vals = ds.latitude.values[lat_idx]
lon_vals = ds.longitude.values[lon_idx]

# Save for later use
np.save('/tmp/sst_data.npy', sst_data)
np.save('/tmp/times.npy', times.astype('datetime64[D]').astype('int64'))
np.save('/tmp/lat_vals.npy', lat_vals)
np.save('/tmp/lon_vals.npy', lon_vals)
print("Saved")
print("SST sample:", sst_data[100, 10, 10], "nan count:", np.isnan(sst_data).sum())
