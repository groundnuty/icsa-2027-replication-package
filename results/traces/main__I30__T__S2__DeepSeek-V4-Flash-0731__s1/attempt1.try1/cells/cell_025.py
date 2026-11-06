
import xarray as xr
import json
import numpy as np

# Verify NetCDF
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("NetCDF contents:")
print(ds)
print("\nmhw dtype:", ds['mhw'].dtype)
print("mhw shape:", ds['mhw'].shape)
print("mhw sum:", ds['mhw'].sum().values)
print("time:", ds['time'].values[0], "to", ds['time'].values[-1])
print("lat:", ds['latitude'].values[0], "to", ds['latitude'].values[-1])
print("lon:", ds['longitude'].values[0], "to", ds['longitude'].values[-1])
ds.close()

# Verify report
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport:")
print(json.dumps(report, indent=2))
