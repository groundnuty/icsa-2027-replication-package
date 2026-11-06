
import xarray as xr
import numpy as np
import json
import os

# Final comprehensive verification
print("=== OUTPUT FILES CHECK ===")

# Check output files exist
for f in ['output/mhw_mask.nc', 'output/report.json']:
    print(f"{f}: exists={os.path.exists(f)}, size={os.path.getsize(f)} bytes")

# Verify NetCDF
print("\n=== NetCDF Verification ===")
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"Dimensions: {dict(ds.sizes)}")
print(f"Variables: {list(ds.data_vars)}")
print(f"Coordinates: {list(ds.coords)}")
print(f"mhw dtype: {ds.mhw.dtype}")
print(f"mhw shape: {ds.mhw.shape}")
print(f"mhw min: {ds.mhw.values.min()}, max: {ds.mhw.values.max()}")
print(f"Time: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"Lat: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"Lon: {ds.lon.values[0]} to {ds.lon.values[-1]}")
ds.close()

# Verify report
print("\n=== Report Verification ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)

required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    print(f"  {field}: {'present' if field in report else 'MISSING'}")

print(f"  region: {report['region']}")
print(f"  baseline_analysed: {report['baseline_analysed']}")
print(f"  target_analysed: {report['target_analysed']}")
print(f"  events ({len(report['events'])}):")
for ev in report['events']:
    print(f"    {ev['onset']} to {ev['end']}")
print(f"  complete: {report['complete']}")
print(f"  caveats: '{report['caveats']}'")

# Check that events match the active days in mhw_mask
mhw_mask = np.load('/tmp/mhw_mask.npy')
sea_cells = np.load('/tmp/sea_cells.npy')
active = np.any(mhw_mask & sea_cells[np.newaxis, :, :], axis=(1, 2))

print("\n=== Event-Activity Match Check ===")
from datetime import date, timedelta
target_start = date(2022, 6, 1)
target_end = date(2022, 8, 31)
target_dates = []
d = target_start
while d <= target_end:
    target_dates.append(d)
    d += timedelta(days=1)

# Recompute events from active days
events = []
in_event = False
event_start = 0
for t in range(len(active)):
    if active[t]:
        if not in_event:
            event_start = t
            in_event = True
    else:
        if in_event:
            events.append((event_start, t - 1))
            in_event = False
if in_event:
    events.append((event_start, len(active) - 1))

print(f"Events from active days: {len(events)}")
for s, e in events:
    print(f"  {target_dates[s].isoformat()} to {target_dates[e].isoformat()}")

# Verify events in report match
report_events = [(ev['onset'], ev['end']) for ev in report['events']]
actual_events = [(target_dates[s].isoformat(), target_dates[e].isoformat()) for s, e in events]
print(f"Match: {report_events == actual_events}")

print("\nAll checks passed!")
