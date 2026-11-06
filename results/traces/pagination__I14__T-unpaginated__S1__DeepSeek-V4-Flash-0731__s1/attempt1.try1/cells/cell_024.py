
import xarray as xr
import numpy as np
import json

# Read back the NetCDF file
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("NetCDF structure:")
print(ds)
print(f"\nmhw dtype: {ds.mhw.dtype}")
print(f"mhw shape: {ds.mhw.shape}")
print(f"mhw unique values: {np.unique(ds.mhw.values)}")
print(f"mhw non-zero: {(ds.mhw.values > 0).sum()}")

# Check coordinates
print(f"\ntime: {ds.time.values[0]} to {ds.time.values[-1]}, count={len(ds.time)}")
print(f"lat: {ds.lat.values[0]} to {ds.lat.values[-1]}, count={len(ds.lat)}")
print(f"lon: {ds.lon.values[0]} to {ds.lon.values[-1]}, count={len(ds.lon)}")
ds.close()

# Read back the report
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\nReport: {json.dumps(report, indent=2)}")

# Verify report fields are exactly as required
expected_keys = {'region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats'}
print(f"\nReport keys: {set(report.keys())}")
print(f"Expected keys: {expected_keys}")
print(f"Keys match: {set(report.keys()) == expected_keys}")
