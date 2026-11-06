
import xarray as xr
import json
import numpy as np

# Verify the NetCDF file
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("Dataset:")
print(ds)
print("\nVariable mhw dtype:", ds['mhw'].dtype)
print("Shape:", ds['mhw'].shape)
print("Time coords:", ds['time'].values[0], "to", ds['time'].values[-1])
print("Lat range:", ds['lat'].values[0], "to", ds['lat'].values[-1])
print("Lon range:", ds['lon'].values[0], "to", ds['lon'].values[-1])
print("Unique values:", np.unique(ds['mhw'].values))
print("Sum:", ds['mhw'].values.sum())
ds.close()

# Verify the report
with open('output/report.json', 'r') as f:
    report = json.load(f)
print("\nReport:")
print(json.dumps(report, indent=2))
