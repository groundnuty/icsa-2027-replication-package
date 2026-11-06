
import xarray as xr
import json
import numpy as np

# Read back the NetCDF
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print(ds)
print("\nmhw dtype:", ds.mhw.dtype)
print("mhw shape:", ds.mhw.shape)
print("mhw min/max:", ds.mhw.values.min(), ds.mhw.values.max())
print("time:", ds.time.values[0], "to", ds.time.values[-1], "n=", len(ds.time))
print("lat:", ds.lat.values[0], "to", ds.lat.values[-1], "n=", len(ds.lat))
print("lon:", ds.lon.values[0], "to", ds.lon.values[-1], "n=", len(ds.lon))

# Verify all coordinates are within region bounds
assert 64.39 <= ds.lat.values.min() <= 65.59
assert 64.39 <= ds.lat.values.max() <= 65.59
assert 23.41 <= ds.lon.values.min() <= 24.61
assert 23.41 <= ds.lon.values.max() <= 24.61

# Verify time range
from datetime import date
assert ds.time.values[0] == np.datetime64('2019-06-01')
assert ds.time.values[-1] == np.datetime64('2019-08-31')

# Read back report
with open('output/report.json') as f:
    report = json.load(f)
print("\n=== report.json ===")
print(json.dumps(report, indent=2))

# Verify report fields
expected_fields = {"region", "baseline_analysed", "target_analysed", "events", "complete", "caveats"}
assert set(report.keys()) == expected_fields, f"Unexpected fields: {set(report.keys()) ^ expected_fields}"
assert set(report["region"].keys()) == {"lat_min", "lat_max", "lon_min", "lon_max"}
assert set(report["baseline_analysed"].keys()) == {"start", "end"}
assert set(report["target_analysed"].keys()) == {"start", "end"}
for ev in report["events"]:
    assert set(ev.keys()) == {"onset", "end"}
assert isinstance(report["complete"], bool)
assert isinstance(report["caveats"], str)

print("\nAll verifications passed!")
