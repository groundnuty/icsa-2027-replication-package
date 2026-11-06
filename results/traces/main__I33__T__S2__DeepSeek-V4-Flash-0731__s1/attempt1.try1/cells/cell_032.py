
import os

# Check all files
files = ['baseline_data.nc', 'target_data.nc', 'thresholds_smooth.npy', 'climatology_smooth.npy',
         'output/mhw_mask.nc', 'output/report.json']
for f in files:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"  {f}: {size} bytes")
    else:
        print(f"  {f}: MISSING")

# Verify output files
import json
with open('output/report.json') as f:
    report = json.load(f)
print("\nReport:", json.dumps(report, indent=2))

import xarray as xr
ds = xr.open_dataset('output/mhw_mask.nc')
print("\nmhw_mask.nc:")
print(f"  Shape: {ds.mhw.shape}")
print(f"  Dtype: {ds.mhw.dtype}")
print(f"  Sum: {int(ds.mhw.sum())}")
print(f"  Time range: {ds.time.values[0]} to {ds.time.values[-1]}")
