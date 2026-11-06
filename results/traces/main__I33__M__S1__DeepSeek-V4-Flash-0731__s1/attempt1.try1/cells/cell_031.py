
import numpy as np
import json
import xarray as xr

# Verify output files
print("=== Verifying mhw_mask.nc ===")
ds = xr.open_dataset('output/mhw_mask.nc')
print(f"Dimensions: {dict(ds.dims)}")
print(f"Variables: {list(ds.variables)}")
print(f"mhw dtype: {ds['mhw'].dtype}")
print(f"mhw shape: {ds['mhw'].shape}")
print(f"mhw values: {np.unique(ds['mhw'].values)}")
print(f"mhw sum: {ds['mhw'].sum().values}")
print(f"time: {ds['time'].values[0]} to {ds['time'].values[-1]}")
print(f"lat: {ds['lat'].values[0]} to {ds['lat'].values[-1]}")
print(f"lon: {ds['lon'].values[0]} to {ds['lon'].values[-1]}")
ds.close()

print("\n=== Verifying report.json ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))

# Verify events match the mhw_mask
mhw_mask = np.load('output/mhw_mask.npy')
active = mhw_mask.sum(axis=(1, 2)) > 0
n_days = mhw_mask.shape[0]
events = []
i = 0
while i < n_days:
    if active[i]:
        start = i
        while i < n_days and active[i]:
            i += 1
        events.append((start, i-1))
    else:
        i += 1

print(f"\nEvents from mhw_mask: {events}")
print(f"Events in report: {[(e['onset'], e['end']) for e in report['events']]}")
