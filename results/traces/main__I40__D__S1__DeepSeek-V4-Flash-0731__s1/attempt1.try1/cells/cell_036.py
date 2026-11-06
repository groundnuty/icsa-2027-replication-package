
import os
import json
import xarray as xr
import numpy as np

# Verify output files exist
print(f"output/mhw_mask.nc exists: {os.path.exists('output/mhw_mask.nc')}")
print(f"output/report.json exists: {os.path.exists('output/report.json')}")

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\nmhw_mask.nc:")
print(f"  Variable: {list(ds.data_vars.keys())}")
print(f"  Dimensions: {dict(ds.sizes)}")
print(f"  dtype: {ds.mhw.dtype}")
print(f"  Time range: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"  Lat range: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"  Lon range: {ds.lon.values[0]} to {ds.lon.values[-1]}")
print(f"  mhw unique values: {np.unique(ds.mhw.values)}")
print(f"  mhw sum: {ds.mhw.values.sum()}")

# Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print(f"\nreport.json:")
print(f"  region: {report['region']}")
print(f"  baseline_analysed: {report['baseline_analysed']}")
print(f"  target_analysed: {report['target_analysed']}")
print(f"  events: {report['events']}")
print(f"  complete: {report['complete']}")
print(f"  caveats: {report['caveats']}")

# Verify report fields exactly match required fields
required = {'region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats'}
actual = set(report.keys())
print(f"\nRequired fields: {required}")
print(f"Actual fields: {actual}")
print(f"Match: {required == actual}")

# Verify event count and format
print(f"\nNumber of events: {len(report['events'])}")
for e in report['events']:
    print(f"  {e['onset']} to {e['end']}")
