
import xarray as xr
import numpy as np
import json

# Verify the output NetCDF
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== Output NetCDF ===")
print(f"Dimensions: {dict(ds.sizes)}")
print(f"mhw dtype: {ds['mhw'].dtype}")
print(f"mhw shape: {ds['mhw'].shape}")
print(f"mhw unique values: {np.unique(ds['mhw'].values)}")
print(f"mhw sum: {ds['mhw'].sum().values}")
print(f"time range: {ds['time'].values[0]} to {ds['time'].values[-1]}, count={len(ds['time'])}")
print(f"lat range: {ds['lat'].values[0]} to {ds['lat'].values[-1]}, count={len(ds['lat'])}")
print(f"lon range: {ds['lon'].values[0]} to {ds['lon'].values[-1]}, count={len(ds['lon'])}")

# Verify time values match
target_times_full = np.load('/tmp/target_times_full.npy')
print(f"\nTime values match original: {np.array_equal(ds['time'].values, target_times_full)}")

# Verify coordinates match
region_lat = np.load('/tmp/region_lat.npy')
region_lon = np.load('/tmp/region_lon.npy')
print(f"Lat values match: {np.allclose(ds['lat'].values, region_lat)}")
print(f"Lon values match: {np.allclose(ds['lon'].values, region_lon)}")

# Verify MHW mask matches
mhw_mask = np.load('/tmp/mhw_mask_f64.npy')
print(f"MHW mask matches: {np.array_equal(ds['mhw'].values, mhw_mask.astype(np.uint8))}")

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\n=== Report ===")
print(json.dumps(report, indent=2))

# Verify report has exactly the required fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"
print("\nAll required fields present")

# Verify region
assert report['region'] == {'lat_min': 59.93, 'lat_max': 61.13, 'lon_min': 18.69, 'lon_max': 19.89}
print("Region correct")

# Verify baseline_analysed
assert report['baseline_analysed'] == {'start': '1991-12-27', 'end': '2003-01-05'}
print("Baseline correct")

# Verify target_analysed
assert report['target_analysed'] == {'start': '2009-06-01', 'end': '2009-08-31'}
print("Target correct")

# Verify events
print(f"Events: {report['events']}")
assert report['complete'] == True
print("Complete: True")
