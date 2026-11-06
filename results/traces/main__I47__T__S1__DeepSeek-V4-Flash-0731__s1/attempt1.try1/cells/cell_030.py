
import json
import xarray as xr
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc')
print("=== mhw_mask.nc ===")
print("Dimensions:", dict(ds.sizes))
print("Variable 'mhw' dtype:", ds['mhw'].dtype)
print("mhw shape:", ds['mhw'].shape)
print("mhw min/max:", ds['mhw'].values.min(), ds['mhw'].values.max())
print("Time range:", str(ds.time.values[0])[:10], "to", str(ds.time.values[-1])[:10])
print("Lat range:", ds.lat.values[0], "to", ds.lat.values[-1])
print("Lon range:", ds.lon.values[0], "to", ds.lon.values[-1])
print("Total mhw=1 cells:", ds['mhw'].values.sum())

# Check daily MHW activity from the netcdf
daily = ds['mhw'].values.sum(axis=(1,2))
active_days = np.where(daily > 0)[0]
print("\nActive days (indices):", active_days)

# Find events from the netcdf data
active = daily > 0
events = []
t = 0
while t < len(active):
    if active[t]:
        start = t
        while t < len(active) and active[t]:
            t += 1
        end = t - 1
        events.append((start, end))
    else:
        t += 1

print("\nRegional events from mhw_mask.nc:")
for start, end in events:
    onset = str(ds.time.values[start])[:10]
    end_date = str(ds.time.values[end])[:10]
    print(f"  {onset} to {end_date}")

# Verify report.json
print("\n=== report.json ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("Fields:", sorted(report.keys()))
print("Region:", report["region"])
print("Baseline:", report["baseline_analysed"])
print("Target:", report["target_analysed"])
print("Events:", report["events"])
print("Complete:", report["complete"])
print("Caveats:", repr(report["caveats"]))

# Verify all required fields present
required = {'region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats'}
actual = set(report.keys())
assert required == actual, f"Field mismatch: {required ^ actual}"
print("\nAll required fields present and no extras ✓")
