import xarray as xr
import numpy as np
import json

# Verify output files
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc:")
print(f"  shape: {ds_out['mhw'].shape}")
print(f"  dtype: {ds_out['mhw'].dtype}")
print(f"  unique values: {np.unique(ds_out['mhw'].values)}")
print(f"  sum: {ds_out['mhw'].values.sum()}")
print(f"  time: {ds_out['time'].values[0]} to {ds_out['time'].values[-1]}")
print(f"  lat: {ds_out['lat'].values[0]} to {ds_out['lat'].values[-1]}, count={len(ds_out['lat'])}")
print(f"  lon: {ds_out['lon'].values[0]} to {ds_out['lon'].values[-1]}, count={len(ds_out['lon'])}")

# Check per-day active pattern
mhw = ds_out['mhw'].values
daily_active = mhw.sum(axis=(1,2))
print("\nDays with active cells:")
for t in range(len(ds_out['time'])):
    if daily_active[t] > 0:
        date_str = str(ds_out['time'].values[t])[:10]
        print(f"  {date_str}: {daily_active[t]} active cells")

with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport:")
print(json.dumps(report, indent=2))
