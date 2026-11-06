
import xarray as xr
import numpy as np
import json

# Verify the output files
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("Output NetCDF:")
print(ds)
print(f"\nmhw dtype: {ds['mhw'].dtype}")
print(f"mhw shape: {ds['mhw'].shape}")
print(f"mhw sum: {ds['mhw'].sum().values}")
print(f"mhw unique values: {np.unique(ds['mhw'].values)}")
print(f"Time range: {ds['time'].values[0]} to {ds['time'].values[-1]}")
print(f"Lat range: {ds['lat'].values[0]} to {ds['lat'].values[-1]}")
print(f"Lon range: {ds['lon'].values[0]} to {ds['lon'].values[-1]}")

# Check that the mhw_mask values match what we computed
mhw_mask = np.load('/tmp/mhw_mask.npy')
print(f"\nOriginal mhw_mask sum: {mhw_mask.sum()}")
print(f"NetCDF mhw sum: {ds['mhw'].values.sum()}")
print(f"Match: {np.array_equal(mhw_mask.astype(np.uint8), ds['mhw'].values)}")

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\nReport:")
print(json.dumps(report, indent=2))
