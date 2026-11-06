
import xarray as xr
import numpy as np
import json

# Load the output
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
mhw = ds.mhw.values  # (time, lat, lon)
times = ds.time.values
ds.close()

# Compute active days
active = np.any(mhw > 0, axis=(1, 2))
print("Active days:")
for i, a in enumerate(active):
    if a:
        print(f"  {times[i]}: active")
    else:
        print(f"  {times[i]}: NOT active")

# Check events from report
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nEvents from report:")
for ev in report['events']:
    print(f"  {ev['onset']} to {ev['end']}")
