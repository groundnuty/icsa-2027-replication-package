import os
import json
import xarray as xr

# Final check
print("=== Final verification ===")

# Check files exist
assert os.path.exists('output/mhw_mask.nc'), "mhw_mask.nc not found"
assert os.path.exists('output/report.json'), "report.json not found"
print("Both output files exist ✓")

# Check mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc')
assert ds['mhw'].dtype == 'uint8', f"mhw dtype is {ds['mhw'].dtype}, expected uint8"
assert ds['mhw'].shape == (92, 60, 60), f"mhw shape is {ds['mhw'].shape}, expected (92, 60, 60)"
assert set(ds['mhw'].values.flatten()) == {0, 1}, "mhw should only contain 0 and 1"
print("mhw_mask.nc: dtype=uint8, shape=(92,60,60), values={0,1} ✓")

# Check time dimension
assert len(ds['time']) == 92
assert str(ds['time'].values[0])[:10] == '2004-06-01'
assert str(ds['time'].values[-1])[:10] == '2004-08-31'
print(f"Time: 2004-06-01 to 2004-08-31, {len(ds['time'])} days ✓")

# Check lat/lon
assert len(ds['lat']) == 60
assert len(ds['lon']) == 60
assert 63.31 <= ds['lat'].values.min() and ds['lat'].values.max() <= 64.51
assert 21.31 <= ds['lon'].values.min() and ds['lon'].values.max() <= 22.51
print(f"Lat: {ds['lat'].values.min():.2f}-{ds['lat'].values.max():.2f}, Lon: {ds['lon'].values.min():.2f}-{ds['lon'].values.max():.2f} ✓")

# Check report.json
with open('output/report.json') as f:
    report = json.load(f)

assert report['complete'] == True
assert report['caveats'] == ''
assert len(report['events']) == 1
assert report['events'][0]['onset'] == '2004-08-07'
assert report['events'][0]['end'] == '2004-08-12'
print("report.json: complete=true, 1 event (2004-08-07 to 2004-08-12) ✓")

print("\nAll final checks passed ✓")
