
import xarray as xr
import json
import numpy as np

# Read back the output
ds_out = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("mhw_mask.nc:")
print(ds_out)
print("\nmhw variable:")
print(ds_out['mhw'])
print("\nmhw values sum:", ds_out['mhw'].sum().values)
print("Time values:", ds_out['time'].values[:3], "...", ds_out['time'].values[-3:])
print("Lat values:", ds_out['lat'].values[:3], "...", ds_out['lat'].values[-3:])
print("Lon values:", ds_out['lon'].values[:3], "...", ds_out['lon'].values[-3:])
print("mhw dtype:", ds_out['mhw'].dtype)

with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nreport.json:")
print(json.dumps(report, indent=2))
