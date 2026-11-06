
import numpy as np
import xarray as xr

# Check SST values in the dataset
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Look at some values for a specific region point
sst_point = ds.analysed_sst.sel(latitude=58.0, longitude=11.0, time=slice('2004-08-01','2004-08-10'))
print("SST values at (58.0, 11.0) in Aug 2004:")
print(sst_point.values)

# Check units in attribute
print("\nSST attrs:")
print(ds.analysed_sst.attrs)
