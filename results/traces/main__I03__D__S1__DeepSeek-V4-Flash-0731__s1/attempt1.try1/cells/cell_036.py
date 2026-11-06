
import os

# Check files exist
for f in ['output/mhw_mask.nc', 'output/report.json']:
    if os.path.exists(f):
        size = os.path.getsize(f)
        print(f"{f}: EXISTS ({size} bytes)")
    else:
        print(f"{f}: MISSING!")

# Read report
import json
with open('output/report.json') as f:
    report = json.load(f)
print(f"\nReport events: {len(report['events'])}")
for ev in report['events']:
    print(f"  {ev['onset']} to {ev['end']}")

# Read NetCDF
import xarray as xr
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print(f"\nmhw_mask.nc: shape={ds['mhw'].shape}, dtype={ds['mhw'].dtype}")
print(f"  Time: {ds.time.values[0]} to {ds.time.values[-1]}")
print(f"  Lat: {ds.lat.values[0]} to {ds.lat.values[-1]}")
print(f"  Lon: {ds.lon.values[0]} to {ds.lon.values[-1]}")
