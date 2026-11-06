
import numpy as np
import xarray as xr
import json
from datetime import datetime

# Open the original dataset to verify coordinates
ds_orig = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Verify our output coordinates match the original dataset
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')

# Check lat/lon from output match original
orig_lats = ds_orig['latitude'].values
orig_lons = ds_orig['longitude'].values
out_lats = ds_out['lat'].values
out_lons = ds_out['lon'].values

print("Output lat range:", out_lats[0], "to", out_lats[-1])
print("Output lon range:", out_lons[0], "to", out_lons[-1])

# Find the matching indices in the original
lat_idx = np.where((orig_lats >= 63.31) & (orig_lats <= 64.51))[0]
lon_idx = np.where((orig_lons >= 21.31) & (orig_lons <= 22.51))[0]
print("Original lat at those indices:", orig_lats[lat_idx[0]], "to", orig_lats[lat_idx[-1]])
print("Original lon at those indices:", orig_lons[lon_idx[0]], "to", orig_lons[lon_idx[-1]])

# Check they match
print("\nLats match:", np.allclose(out_lats, orig_lats[lat_idx]))
print("Lons match:", np.allclose(out_lons, orig_lons[lon_idx]))

# Check time coordinates
orig_times = ds_orig['time'].values
# Find target period in original
target_mask = (orig_times >= np.datetime64('2009-06-01')) & (orig_times <= np.datetime64('2009-08-31'))
orig_target_times = orig_times[target_mask]
out_times = ds_out['time'].values
print("\nTime count in output:", len(out_times))
print("Time count in original target:", len(orig_target_times))
print("Output time[0]:", out_times[0])
print("Original time[0]:", orig_target_times[0])
print("Output time[-1]:", out_times[-1])
print("Original time[-1]:", orig_target_times[-1])
print("Times match:", np.all(out_times == orig_target_times))

# Check dtype
print("\nmhw dtype:", ds_out['mhw'].dtype)
print("mhw shape:", ds_out['mhw'].shape)
print("mhw unique:", np.unique(ds_out['mhw'].values))

ds_orig.close()
ds_out.close()
