
import xarray as xr
import numpy as np
import json

# Final comprehensive verification
print("=== FINAL VERIFICATION ===")

# 1. Check output files exist
import os
print("\n1. Output files:")
print(f"   mhw_mask.nc exists: {os.path.exists('output/mhw_mask.nc')}")
print(f"   report.json exists: {os.path.exists('output/report.json')}")

# 2. Check mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\n2. mhw_mask.nc:")
print(f"   Dimensions: {dict(ds.sizes)}")
print(f"   mhw dtype: {ds['mhw'].dtype}")
print(f"   mhw values: min={ds['mhw'].min().values}, max={ds['mhw'].max().values}")
print(f"   Time: {str(ds['time'].values[0])[:10]} to {str(ds['time'].values[-1])[:10]}, n={len(ds['time'])}")
print(f"   Lat: {ds['lat'].values[0]} to {ds['lat'].values[-1]}, n={len(ds['lat'])}")
print(f"   Lon: {ds['lon'].values[0]} to {ds['lon'].values[-1]}, n={len(ds['lon'])}")

# 3. Check report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\n3. report.json:")
print(f"   Fields: {list(report.keys())}")
print(f"   Region: {report['region']}")
print(f"   Baseline: {report['baseline_analysed']}")
print(f"   Target: {report['target_analysed']}")
print(f"   Events: {report['events']}")
print(f"   Complete: {report['complete']}")

# 4. Verify regional events from the mask
active = ds['mhw'].sum(dim=('lat', 'lon')) > 0
active_days = np.where(active.values)[0]
print(f"\n4. Active days in mask: {active_days}")

# Find events
events = []
if len(active_days) > 0:
    start = active_days[0]
    prev = start
    for d in active_days[1:]:
        if d - prev > 1:
            events.append((start, prev))
            start = d
        prev = d
    events.append((start, prev))

print(f"   Events from mask:")
for s, e in events:
    onset = str(ds['time'].values[s])[:10]
    end = str(ds['time'].values[e])[:10]
    print(f"     {onset} to {end}")

# Compare with report
report_events = [(e['onset'], e['end']) for e in report['events']]
mask_events = [(str(ds['time'].values[s])[:10], str(ds['time'].values[e])[:10]) for s, e in events]
print(f"\n   Report events: {report_events}")
print(f"   Mask events: {mask_events}")
print(f"   Match: {report_events == mask_events}")

print("\n=== VERIFICATION COMPLETE ===")
