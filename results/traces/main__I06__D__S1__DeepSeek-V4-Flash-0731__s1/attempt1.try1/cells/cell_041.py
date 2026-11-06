
import os
import json
import xarray as xr
import numpy as np

# Final verification of output files
print("=== Final Verification ===")

# Check files exist
assert os.path.exists('output/mhw_mask.nc'), "mhw_mask.nc not found!"
assert os.path.exists('output/report.json'), "report.json not found!"
print("Both output files exist.")

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
assert ds.mhw.dtype == np.uint8, f"mhw dtype should be uint8, got {ds.mhw.dtype}"
assert ds.mhw.shape == (92, 60, 60), f"mhw shape should be (92,60,60), got {ds.mhw.shape}"
assert set(ds.mhw.values.flatten()) <= {0, 1}, "mhw should only contain 0 and 1"
print(f"\nmhw_mask.nc:")
print(f"  Dimensions: time={len(ds.time)}, lat={len(ds.lat)}, lon={len(ds.lon)}")
print(f"  mhw dtype: {ds.mhw.dtype}")
print(f"  mhw sum (cell-days in MHW): {ds.mhw.sum().item()}")
print(f"  Time: {str(ds.time.values[0])[:10]} to {str(ds.time.values[-1])[:10]}")
print(f"  Lat: {ds.lat.values[0]:.4f} to {ds.lat.values[-1]:.4f}")
print(f"  Lon: {ds.lon.values[0]:.4f} to {ds.lon.values[-1]:.4f}")
ds.close()

# Verify report.json
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(f"\nreport.json:")
print(json.dumps(report, indent=2))

# Verify required fields
required_fields = ['region', 'baseline_analysed', 'target_analysed', 'events', 'complete', 'caveats']
for field in required_fields:
    assert field in report, f"Missing field: {field}"
print(f"\nAll required fields present.")

# Verify events format
for ev in report['events']:
    assert 'onset' in ev and 'end' in ev, f"Invalid event: {ev}"
print(f"Events format correct. {len(report['events'])} events.")

print("\n=== Analysis Complete ===")
