
import xarray as xr
import json
import numpy as np
import os

# Check files exist
print("=== Output files ===")
for f in ['output/mhw_mask.nc', 'output/report.json']:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"  {f}: {size} bytes ({size/1024:.1f} KB)")
    else:
        print(f"  {f}: MISSING!")

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("\n=== mhw_mask.nc ===")
print(f"  Dimensions: {ds.sizes}")
print(f"  Variable 'mhw': dtype={ds.mhw.dtype}, shape={ds.mhw.shape}")
print(f"  mhw values: {np.unique(ds.mhw.values)}")
print(f"  Number of 1s: {int(ds.mhw.sum().values)}")
print(f"  Number of 0s: {int((ds.mhw == 0).sum().values)}")
print(f"  Total: {int(ds.mhw.size)}")

# Check land cells are all 0
# Sea cells had SST finite on all 92 target days
# For the mask, land cells should be 0

# Verify time coordinates
print(f"\n  Time coordinates (first 5): {ds.time.values[:5]}")
print(f"  Time coordinates (last 5): {ds.time.values[-5:]}")

# Verify lat/lon coordinates match original dataset
ds_orig = xr.open_dataset('/data/icsa2027_data_20261101T090944Z/s1z/sst_20030601.nc', engine='h5netcdf')
orig_lats = ds_orig.latitude.values
orig_lons = ds_orig.longitude.values

# Check that the lat/lon values in the output match the original dataset
lat_match = np.allclose(ds.lat.values, orig_lats[350:410], rtol=0, atol=1e-6)
lon_match = np.allclose(ds.lon.values, orig_lons[413:473], rtol=0, atol=1e-6)
print(f"  Lat values match original dataset: {lat_match}")
print(f"  Lon values match original dataset: {lon_match}")
ds_orig.close()
ds.close()

# Verify report.json
with open('output/report.json') as f:
    report = json.load(f)
print("\n=== report.json ===")
print(json.dumps(report, indent=2))

# Verify all required fields
required = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required:
    if field not in report:
        print(f"  MISSING FIELD: {field}")
    else:
        print(f"  ✓ {field}")

print("\n=== FINAL VERIFICATION COMPLETE ===")
