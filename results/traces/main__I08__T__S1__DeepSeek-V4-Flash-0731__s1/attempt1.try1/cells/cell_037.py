
import os
import numpy as np
import xarray as xr
import json

# Check output files exist
print("=== Output files ===")
for f in ['output/mhw_mask.nc', 'output/report.json']:
    print(f"{f}: exists = {os.path.exists(f)}, size = {os.path.getsize(f) if os.path.exists(f) else 'N/A'} bytes")

# Final verification of mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc')
print(f"\nmhw_mask.nc dims: {dict(ds.sizes)}")
print(f"mhw dtype: {ds['mhw'].dtype}")
print(f"mhw values: 0={np.sum(ds['mhw'].values==0)}, 1={np.sum(ds['mhw'].values==1)}")
print(f"Time: {str(ds.time.values[0])[:10]} to {str(ds.time.values[-1])[:10]} (n={len(ds.time)})")
print(f"Lat: {ds.lat.values[0]} to {ds.lat.values[-1]} (n={len(ds.lat)})")
print(f"Lon: {ds.lon.values[0]} to {ds.lon.values[-1]} (n={len(ds.lon)})")

# Final verification of report.json
with open('output/report.json') as f:
    report = json.load(f)
print(f"\nReport fields: {sorted(report.keys())}")
print(f"Events: {report['events']}")
print(f"Complete: {report['complete']}")

# Verify region bounds match the actual grid cells analysed
# The grid cells cover lat 54.82-56.0 (inclusive) and lon 19.62-20.8 (inclusive)
# All within the specified region bounds [54.81, 56.01] x [19.61, 20.81]
lat_cells = ds.lat.values
lon_cells = ds.lon.values
assert np.all(lat_cells >= 54.81) and np.all(lat_cells <= 56.01), "Lat cells out of region!"
assert np.all(lon_cells >= 19.61) and np.all(lon_cells <= 20.81), "Lon cells out of region!"
print("\nAll grid cells are within the specified region bounds.")

# Final check: the events are in time order
events = report['events']
for i in range(len(events)-1):
    assert events[i]['end'] < events[i+1]['onset'], "Events not in time order!"
print("Events are in time order.")

print("\n=== ALL CHECKS PASSED ===")
