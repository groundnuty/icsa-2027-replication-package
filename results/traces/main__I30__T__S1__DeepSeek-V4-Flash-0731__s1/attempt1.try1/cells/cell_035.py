
import xarray as xr
import numpy as np

ds = xr.open_dataset('output/mhw_mask.nc', engine='h5netcdf')
print("Time values:", ds['time'].values)
print("Lat values:", ds['lat'].values)
print("Lon values:", ds['lon'].values)
