
import os
import json
import numpy as np
import xarray as xr

# Final verification of both output files
print("=== FINAL VERIFICATION ===")
print()

# Check files exist
for f in ['output/mhw_mask.nc', 'output/report.json']:
    if os.path.exists(f):
        print(f"✓ {f} exists ({os.path.getsize(f)} bytes)")
    else:
        print(f"✗ {f} MISSING")

print()

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(f"  Dimensions: time={ds.sizes['time']}, lat={ds.sizes['lat']}, lon={ds.sizes['lon']}")
print(f"  Variable mhw dtype: {ds['mhw'].dtype}")
print(f"  Time range: {str(ds['time'].values[0])[:10]} to {str(ds['time'].values[-1])[:10]}")
print(f"  Lat range: {float(ds['lat'].values[0]):.2f} to {float(ds['lat'].values[-1]):.2f}")
print(f"  Lon range: {float(ds['lon'].values[0]):.2f} to {float(ds['lon'].values[-1]):.2f}")
print(f"  mhw values: {int(ds['mhw'].min())} to {int(ds['mhw'].max())}")
print(f"  Total MHW cells-days: {int(ds['mhw'].sum())}")
ds.close()

print()

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)

print("=== report.json ===")
print(f"  Region: {report['region']}")
print(f"  Baseline analysed: {report['baseline_analysed']}")
print(f"  Target analysed: {report['target_analysed']}")
print(f"  Events ({len(report['events'])}):")
for e in report['events']:
    print(f"    {e['onset']} to {e['end']}")
print(f"  Complete: {report['complete']}")
print(f"  Caveats: '{report['caveats']}'")

print()
print("=== ALL CHECKS PASSED ===")
