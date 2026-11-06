
import xarray as xr
import numpy as np
import json

# Verify NetCDF
ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("NetCDF contents:")
print(ds)
print("\nVariable dtype:", ds['mhw'].dtype)
print("Variable shape:", ds['mhw'].shape)
print("Unique values:", np.unique(ds['mhw'].values))
print("Time range:", ds.time.values[0], "to", ds.time.values[-1])
print("Lat range:", ds.lat.values[0], "to", ds.lat.values[-1])
print("Lon range:", ds.lon.values[0], "to", ds.lon.values[-1])
print("Total 1s:", ds['mhw'].sum().values)
ds.close()

# Verify report
with open('output/report.json') as f:
    report = json.load(f)
print("\nReport:")
print(json.dumps(report, indent=2))
