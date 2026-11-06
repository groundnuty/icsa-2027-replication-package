
import xarray as xr
import json
import numpy as np
import pandas as pd

# Verify output files
ds_check = xr.open_dataset("output/mhw_mask.nc", engine="h5netcdf")
print("=== mhw_mask.nc ===")
print("Time range:", ds_check['time'].values[0], "to", ds_check['time'].values[-1])
print("Num time steps:", len(ds_check['time']))
print("Lat range:", ds_check['lat'].values[0], "to", ds_check['lat'].values[-1])
print("Lon range:", ds_check['lon'].values[0], "to", ds_check['lon'].values[-1])
print("mhw dtype:", ds_check['mhw'].dtype)
print("mhw shape:", ds_check['mhw'].shape)
print("mhw sum:", int(ds_check['mhw'].sum().item()))
print("mhw unique values:", np.unique(ds_check['mhw'].values))

# Check active days
active = ds_check['mhw'].any(dim=('lat', 'lon'))
active_days = active.values
n_active = active_days.sum()
print(f"Active days: {n_active}")

# Get active date list
active_dates = ds_check['time'].values[active_days]
for d in active_dates:
    print("  Active:", pd.Timestamp(d).strftime('%Y-%m-%d'))

print("\n=== report.json ===")
with open("output/report.json", "r") as f:
    report = json.load(f)
print(json.dumps(report, indent=2))

# Verify required fields
required = ["region", "baseline_analysed", "target_analysed", "events", "complete", "caveats"]
for f in required:
    assert f in report, f"Missing field: {f}"
print("\nAll required fields present in report.json ✓")

# Verify region
assert report["region"] == {"lat_min": 55.67, "lat_max": 56.87, "lon_min": 16.45, "lon_max": 17.65}
print("Region matches spec ✓")

# Verify events are in time order
for i in range(len(report["events"])-1):
    assert report["events"][i]["onset"] < report["events"][i+1]["onset"]
print("Events in time order ✓")

# Verify events match active days
for e in report["events"]:
    onset = pd.Timestamp(e["onset"]).date()
    end = pd.Timestamp(e["end"]).date()
    print(f"Event: {onset} to {end}")
