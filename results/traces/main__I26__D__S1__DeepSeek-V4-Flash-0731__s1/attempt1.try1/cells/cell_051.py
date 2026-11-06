import xarray as xr
import numpy as np
import json

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')

# Check specific cells
print("=== Specific cell checks ===")
# Cell (3,35) - has MHW on days 8-13
# Day 8 = June 9, 2007
# Day 0 = June 1, 2007
# Day 14 = June 15, 2007

# Find time indices
time_strs = [np.datetime_as_string(t) for t in ds.time.values]
day_0_idx = time_strs.index('2007-06-01T00:00:00.000000000')
day_8_idx = time_strs.index('2007-06-09T00:00:00.000000000')
day_13_idx = time_strs.index('2007-06-14T00:00:00.000000000')
day_14_idx = time_strs.index('2007-06-15T00:00:00.000000000')

print(f"Cell (3,35) on Jun 1: mhw={ds.mhw[day_0_idx, 3, 35].values} (expected 0)")
print(f"Cell (3,35) on Jun 9: mhw={ds.mhw[day_8_idx, 3, 35].values} (expected 1)")
print(f"Cell (3,35) on Jun 14: mhw={ds.mhw[day_13_idx, 3, 35].values} (expected 1)")
print(f"Cell (3,35) on Jun 15: mhw={ds.mhw[day_14_idx, 3, 35].values} (expected 0)")

# Check all values are 0 or 1
vals = ds.mhw.values
unique = np.unique(vals)
print(f"\nUnique mhw values: {unique}")
print(f"Total cells: {vals.size}, sum: {vals.sum()}")

# Verify dtype
print(f"mhw dtype: {ds.mhw.dtype}")
assert ds.mhw.dtype == np.uint8, f"Expected uint8, got {ds.mhw.dtype}"
assert set(unique.tolist()) <= {0, 1}, f"mhw values must be 0 or 1, got {unique}"

# Verify report.json
print("\n=== report.json ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)

# Check required fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"
    print(f"  {field}: {report[field]}")

# Validate types
assert isinstance(report['region']['lat_min'], (int, float))
assert isinstance(report['region']['lat_max'], (int, float))
assert isinstance(report['region']['lon_min'], (int, float))
assert isinstance(report['region']['lon_max'], (int, float))
assert isinstance(report['baseline_analysed'], dict) or report['baseline_analysed'] is None
assert isinstance(report['target_analysed'], dict) or report['target_analysed'] is None
assert isinstance(report['events'], list)
assert isinstance(report['complete'], bool)
assert isinstance(report['caveats'], str)

# Check events
for event in report['events']:
    assert isinstance(event['onset'], str)
    assert isinstance(event['end'], str)

print("\n=== All checks passed! ===")
