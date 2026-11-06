import xarray as xr
import numpy as np

# Open the dataset
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Print dataset information
print("Dataset coordinates:")
print(ds.coords)
print("\nDataset variables:")
print(ds.data_vars)
print("\nTime dimension:", ds.dims)
print("\nLatitudes:", ds.lat.values[:5], "...", ds.lat.values[-5:])
print("\nLongitudes:", ds.lon.values[:5], "...", ds.lon.values[-5:])