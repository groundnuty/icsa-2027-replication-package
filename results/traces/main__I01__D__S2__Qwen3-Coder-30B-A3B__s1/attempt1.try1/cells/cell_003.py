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
print("\nLatitude values (first 5):", ds.latitude.values[:5])
print("\nLongitude values (first 5):", ds.longitude.values[:5])

# Check what variables are available
print("\nAvailable variables:")
for var in ds.data_vars:
    print(f"  {var}: {ds[var].dims}")