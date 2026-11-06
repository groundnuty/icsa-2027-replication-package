import xarray as xr
import numpy as np
import json

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc')
print("=== mhw_mask.nc ===")
print("Dimensions:", dict(ds.sizes))
print("Variables:", list(ds.data_vars))
print("Coordinates:", list(ds.coords))

mhw = ds['mhw']
print(f"\nmhw dtype: {mhw.dtype}")
print(f"mhw shape: {mhw.shape}")
print(f"mhw values: {np.unique(mhw.values)}")

# Verify time
print(f"\ntime values: {ds['time'].values[0]} to {ds['time'].values[-1]}, n={len(ds['time'])}")
print(f"time dtype: {ds['time'].dtype}")

# Verify lat/lon
print(f"\nlat: {ds['lat'].values[0]} to {ds['lat'].values[-1]}, n={len(ds['lat'])}")
print(f"lon: {ds['lon'].values[0]} to {ds['lon'].values[-1]}, n={len(ds['lon'])}")

# Check that mhw has 0 for land cells
# Load original sea mask
sea_mask = np.load('/tmp/sea_mask.npy')
print(f"\nSea cells in mask: {sea_mask.sum()}")

# Check land cells are 0 in mhw
mhw_vals = mhw.values
# For all days, check land cells are 0
for t in range(mhw_vals.shape[0]):
    land_mhw = mhw_vals[t, ~sea_mask]
    if np.any(land_mhw != 0):
        print(f"WARNING: Land cell has mhw=1 on day {t}")
        break
else:
    print("All land cells have mhw=0 ✓")

# Check some sea cells have mhw=1
print(f"Max mhw value: {mhw_vals.max()}")
print(f"Min mhw value: {mhw_vals.min()}")

# Verify report.json
print("\n=== report.json ===")
with open('output/report.json') as f:
    report = json.load(f)

# Check exact fields
expected_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
actual_fields = list(report.keys())
print(f"Fields: {actual_fields}")
assert set(expected_fields) == set(actual_fields), f"Fields mismatch: expected {expected_fields}, got {actual_fields}"

print(f"region: {report['region']}")
print(f"baseline_analysed: {report['baseline_analysed']}")
print(f"target_analysed: {report['target_analysed']}")
print(f"events: {report['events']}")
print(f"complete: {report['complete']}")
print(f"caveats: {report['caveats']}")

# Verify event format
for e in report['events']:
    assert 'onset' in e and 'end' in e
    print(f"  Event: onset={e['onset']}, end={e['end']}")

print("\nAll checks passed ✓")
