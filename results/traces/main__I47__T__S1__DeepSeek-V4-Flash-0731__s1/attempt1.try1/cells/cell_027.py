
import numpy as np
import pandas as pd
import json
import os
import xarray as xr

# Load saved data
mhw_mask = np.load('/tmp/mhw_mask.npy')  # (92, 60, 60) bool
tgt_times = np.load('/tmp/tgt_times.npy')
lats = np.load('/tmp/lats.npy')
lons = np.load('/tmp/lons.npy')

# Verify shapes
print("mhw_mask shape:", mhw_mask.shape)
print("tgt_times shape:", tgt_times.shape)
print("lats shape:", lats.shape)
print("lons shape:", lons.shape)

# Create output directory
os.makedirs('output', exist_ok=True)

# Convert to uint8 for NetCDF
mhw_uint8 = mhw_mask.astype(np.uint8)

# Create xarray Dataset
ds_out = xr.Dataset(
    {
        'mhw': (('time', 'lat', 'lon'), mhw_uint8)
    },
    coords={
        'time': tgt_times,
        'lat': lats,
        'lon': lons
    }
)

# Add attributes
ds_out['mhw'].attrs['long_name'] = 'Marine heatwave mask'
ds_out['mhw'].attrs['description'] = '1 where the cell is inside a per-cell MHW, 0 otherwise'
ds_out['mhw'].attrs['units'] = '1'

# Write NetCDF
ds_out.to_netcdf('output/mhw_mask.nc')
print("Wrote output/mhw_mask.nc")

# Verify
ds_check = xr.open_dataset('output/mhw_mask.nc')
print("Verification:")
print("  dims:", dict(ds_check.sizes))
print("  mhw dtype:", ds_check['mhw'].dtype)
print("  mhw values:", ds_check['mhw'].values.min(), "-", ds_check['mhw'].values.max())
print("  time range:", ds_check.time.values[0], "-", ds_check.time.values[-1])
