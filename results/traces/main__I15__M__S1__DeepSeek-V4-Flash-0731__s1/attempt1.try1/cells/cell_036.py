import os

# Check output files
print("Output files:")
for root, dirs, files in os.walk('output'):
    for f in files:
        path = os.path.join(root, f)
        size = os.path.getsize(path)
        print(f"  {path}: {size} bytes")

# Final verification of both files
import json
import xarray as xr

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\nmhw_mask.nc:")
print(f"  Variable: {list(ds.data_vars)}")
print(f"  mhw dtype: {ds['mhw'].dtype}")
print(f"  mhw dims: {dict(ds['mhw'].sizes)}")
print(f"  mhw min/max: {ds['mhw'].min().values}/{ds['mhw'].max().values}")
print(f"  mhw sum: {ds['mhw'].sum().values}")
print(f"  time: {len(ds.time.values)} values")
print(f"  lat: {len(ds.lat.values)} values")
print(f"  lon: {len(ds.lon.values)} values")
ds.close()

# Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print(f"\nreport.json:")
print(f"  Fields: {list(report.keys())}")
print(f"  region: {report['region']}")
print(f"  baseline_analysed: {report['baseline_analysed']}")
print(f"  target_analysed: {report['target_analysed']}")
print(f"  events: {report['events']}")
print(f"  complete: {report['complete']}")
print(f"  caveats: '{report['caveats']}'")
