
import os
import json
import xarray as xr

# Check files exist
print("Files in output/:", os.listdir('output'))

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\nmhw_mask.nc:")
print(f"  Dims: {dict(ds.sizes)}")
print(f"  Variable: {list(ds.data_vars.keys())}")
print(f"  mhw dtype: {ds.mhw.dtype}")
print(f"  mhw min/max: {ds.mhw.min().values}, {ds.mhw.max().values}")
print(f"  Time: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"  Lat: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"  Lon: {ds.lon.values[0]} to {ds.lon.values[-1]}")
ds.close()

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\nreport.json fields: {list(report.keys())}")
print(f"  region: {report['region']}")
print(f"  baseline_analysed: {report['baseline_analysed']}")
print(f"  target_analysed: {report['target_analysed']}")
print(f"  events: {report['events']}")
print(f"  complete: {report['complete']}")
print(f"  caveats: '{report['caveats']}'")
