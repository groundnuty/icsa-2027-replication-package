
# Final comprehensive check
import json
import numpy as np
import xarray as xr

# Verify both files can be read correctly
print("=== FINAL CHECK ===")

# NetCDF
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"mhw_mask.nc: OK")
print(f"  shape: {ds.mhw.shape}")
print(f"  dtype: {ds.mhw.dtype}")
print(f"  dims: {dict(ds.sizes)}")
print(f"  time: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"  lat: {ds.lat.values[0]:.2f} to {ds.lat.values[-1]:.2f}")
print(f"  lon: {ds.lon.values[0]:.2f} to {ds.lon.values[-1]:.2f}")
ds.close()

# Report
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\nreport.json: OK")
print(f"  region: {report['region']}")
print(f"  baseline: {report['baseline_analysed']}")
print(f"  target: {report['target_analysed']}")
print(f"  events: {len(report['events'])}")
for ev in report['events']:
    print(f"    {ev['onset']} → {ev['end']}")
print(f"  complete: {report['complete']}")
print(f"  caveats: '{report['caveats']}'")

print("\nAll output files are valid and complete.")
