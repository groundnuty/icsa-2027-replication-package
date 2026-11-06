
import os
import json
import xarray as xr
import numpy as np

# Check files exist
print("Files in output directory:")
for f in os.listdir('output'):
    print(f"  {f}")

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc')
print(f"\nmhw_mask.nc:")
print(f"  Dimensions: {dict(ds.sizes)}")
print(f"  Variable dtype: {ds['mhw'].dtype}")
print(f"  Variable shape: {ds['mhw'].shape}")
print(f"  Time: {ds.time.values[0]} to {ds.time.values[-1]} ({len(ds.time)} days)")
print(f"  Lat: {ds.lat.values[0]} to {ds.lat.values[-1]} ({len(ds.lat)} cells)")
print(f"  Lon: {ds.lon.values[0]} to {ds.lon.values[-1]} ({len(ds.lon)} cells)")

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\nreport.json keys: {list(report.keys())}")
print(f"  region: {report['region']}")
print(f"  baseline_analysed: {report['baseline_analysed']}")
print(f"  target_analysed: {report['target_analysed']}")
print(f"  events: {report['events']}")
print(f"  complete: {report['complete']}")
print(f"  caveats: {report['caveats']}")

# Final sanity check: verify the number of days in target period
from datetime import datetime
start = datetime(2021, 6, 1)
end = datetime(2021, 8, 31)
delta = end - start
print(f"\nTarget period days: {delta.days + 1}")
