
import xarray as xr
import json
import numpy as np

# ============================================================
# Final verification
# ============================================================

# 1. Verify mhw_mask.nc
print("=== Verifying mhw_mask.nc ===")
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
assert ds['mhw'].dtype == np.uint8, f"mhw dtype is {ds['mhw'].dtype}, expected uint8"
assert ds['mhw'].dims == ('time', 'lat', 'lon'), f"mhw dims are {ds['mhw'].dims}"
assert ds['mhw'].shape == (92, 60, 60), f"mhw shape is {ds['mhw'].shape}"

# Check time dimension
time_vals = ds.time.values
assert len(time_vals) == 92
assert str(time_vals[0]) == '2014-06-01T00:00:00.000000000'
assert str(time_vals[-1]) == '2014-08-31T00:00:00.000000000'
print(f"Time: {time_vals[0]} to {time_vals[-1]}, count: {len(time_vals)} ✓")

# Check lat and lon
lat_vals = ds.lat.values
lon_vals = ds.lon.values
assert len(lat_vals) == 60 and len(lon_vals) == 60
print(f"Lat: {lat_vals[0]} to {lat_vals[-1]}, count: {len(lat_vals)}")
print(f"Lon: {lon_vals[0]} to {lon_vals[-1]}, count: {len(lon_vals)}")

# Check values
assert np.all((ds['mhw'].values == 0) | (ds['mhw'].values == 1))
print("mhw values are 0 or 1 ✓")

# 2. Verify report.json
print("\n=== Verifying report.json ===")
with open('output/report.json') as f:
    report = json.load(f)

assert set(report.keys()) == {'region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats'}
assert report['region'] == {'lat_min': 54.17, 'lat_max': 55.37, 'lon_min': 13.25, 'lon_max': 14.45}
assert report['baseline_analysed'] == {'start': '1991-12-27', 'end': '2003-01-05'}
assert report['target_analysed'] == {'start': '2014-06-01', 'end': '2014-08-31'}
assert report['complete'] == True
assert isinstance(report['caveats'], str)
assert isinstance(report['events'], list)
for ev in report['events']:
    assert set(ev.keys()) == {'onset', 'end'}
    assert isinstance(ev['onset'], str) and isinstance(ev['end'], str)

print(f"Events: {report['events']}")
print("Report structure ✓")

# Verify events are in time order
events = report['events']
for i in range(1, len(events)):
    assert events[i-1]['onset'] < events[i]['onset']
print("Events in time order ✓")

print("\n=== ALL CHECKS PASSED ===")
