
import os
import json
import numpy as np
import xarray as xr

# Verify output files exist
print("Checking output files:")
print(f"  output/mhw_mask.nc exists: {os.path.exists('output/mhw_mask.nc')}")
print(f"  output/report.json exists: {os.path.exists('output/report.json')}")

# Read and verify report
with open('output/report.json', 'r') as f:
    report = json.load(f)

# Verify required fields
required = ["region", "baseline_analysed", "target_analysed", "events", "complete", "caveats"]
assert all(k in report for k in required), "Missing required fields!"
assert set(report.keys()) == set(required), f"Extra fields: {set(report.keys()) - set(required)}"

# Verify region
assert report["region"] == {"lat_min": 63.31, "lat_max": 64.51, "lon_min": 21.31, "lon_max": 22.51}

# Verify baseline_analysed format
assert report["baseline_analysed"]["start"] == "1991-12-27"
assert report["baseline_analysed"]["end"] == "2003-01-05"

# Verify target_analysed format
assert report["target_analysed"]["start"] == "2004-06-01"
assert report["target_analysed"]["end"] == "2004-08-31"

# Verify events format
assert isinstance(report["events"], list)
for ev in report["events"]:
    assert "onset" in ev and "end" in ev
    assert isinstance(ev["onset"], str) and isinstance(ev["end"], str)

# Verify complete is boolean
assert isinstance(report["complete"], bool)
assert report["complete"] == True

# Verify caveats is string
assert isinstance(report["caveats"], str)

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
assert ds['mhw'].dtype == np.uint8
assert ds['mhw'].dims == ('time', 'lat', 'lon')
assert ds.sizes['time'] == 92
assert ds.sizes['lat'] == 60
assert ds.sizes['lon'] == 60

print("\nAll verifications passed!")
print("Output files are correctly written.")
