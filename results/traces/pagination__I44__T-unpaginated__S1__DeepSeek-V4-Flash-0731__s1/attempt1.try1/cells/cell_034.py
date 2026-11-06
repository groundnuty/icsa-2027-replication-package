import xarray as xr
import json
import numpy as np
from datetime import date

# Load the output files
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
with open('output/report.json', 'r') as f:
    report = json.load(f)

# Verify the mhw mask
mhw_mask = ds['mhw'].values
print(f"mhw mask shape: {mhw_mask.shape}")
print(f"mhw mask dtype: {mhw_mask.dtype}")
print(f"mhw mask values: {np.unique(mhw_mask)}")
print(f"mhw mask sum: {mhw_mask.sum()}")

# Verify it matches per_cell_mhw
per_cell_mhw = np.load('/tmp/work/per_cell_mhw.npy')
print(f"Matches per_cell_mhw: {np.array_equal(mhw_mask, per_cell_mhw.astype(np.uint8))}")

# Verify the report
print(f"\nReport:")
print(f"  Region: {report['region']}")
print(f"  Baseline: {report['baseline_analysed']}")
print(f"  Target: {report['target_analysed']}")
print(f"  Events: {report['events']}")
print(f"  Complete: {report['complete']}")
print(f"  Caveats: '{report['caveats']}'")

# Verify events match
assert len(report['events']) == 1, f"Expected 1 event, got {len(report['events'])}"
assert report['events'][0]['onset'] == '2004-08-07', f"Wrong onset: {report['events'][0]['onset']}"
assert report['events'][0]['end'] == '2004-08-12', f"Wrong end: {report['events'][0]['end']}"

# Verify the time dimension values
time_vals = ds['time'].values
print(f"\nTime dimension: {time_vals[0]} to {time_vals[-1]}")
assert str(time_vals[0])[:10] == '2004-06-01', f"Wrong first time: {time_vals[0]}"
assert str(time_vals[-1])[:10] == '2004-08-31', f"Wrong last time: {time_vals[-1]}"

# Verify lat/lon
lat_vals = ds['lat'].values
lon_vals = ds['lon'].values
print(f"Lat range: {lat_vals[0]} to {lat_vals[-1]}")
print(f"Lon range: {lon_vals[0]} to {lon_vals[-1]}")

# Verify lat/lon are within region bounds
assert np.all(lat_vals >= 63.31) and np.all(lat_vals <= 64.51), "Lat out of bounds"
assert np.all(lon_vals >= 21.31) and np.all(lon_vals <= 22.51), "Lon out of bounds"

ds.close()

print("\nAll verification checks passed!")
