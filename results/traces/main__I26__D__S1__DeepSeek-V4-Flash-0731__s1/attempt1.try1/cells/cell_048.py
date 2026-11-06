import xarray as xr
import json
import numpy as np

# Verify mhw_mask.nc
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("=== mhw_mask.nc ===")
print("Variable:", list(ds.data_vars))
print("mhw dtype:", ds.mhw.dtype)
print("Dimensions:", dict(ds.sizes))
print("Time:", ds.time.values[0], "to", ds.time.values[-1], f"({len(ds.time)} values)")
print("Lat:", ds.lat.values[0], "to", ds.lat.values[-1], f"({len(ds.lat)} values)")
print("Lon:", ds.lon.values[0], "to", ds.lon.values[-1], f"({len(ds.lon)} values)")
print("mhw values range:", ds.mhw.min().values, "to", ds.mhw.max().values)
print("mhw sum:", ds.mhw.sum().values)

# Check that mhw is 1 on active days and 0 elsewhere
active_mask = ds.mhw.sum(dim=('lat', 'lon')).values
print("\nActive days (sum of mhw over lat/lon):")
for t in range(len(ds.time)):
    if active_mask[t] > 0:
        print(f"  {np.datetime_as_string(ds.time.values[t])}: {active_mask[t]} cells in MHW")

# Verify report.json
print("\n=== report.json ===")
with open('output/report.json', 'r') as f:
    report = json.load(f)
print(json.dumps(report, indent=2))
