
import xarray as xr
import numpy as np

ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')

# Check the variable attributes
print(ds['analysed_sst'].attrs)
print("\nDtype:", ds['analysed_sst'].dtype)

# Look at some sample data in our region
lat_vals = ds.latitude.values
lon_vals = ds.longitude.values
lat_indices = np.where((lat_vals >= 63.31) & (lat_vals <= 64.51))[0]
lon_indices = np.where((lon_vals >= 21.31) & (lon_vals <= 22.51))[0]

# Get a small sample of data from the region for a few days
sample = ds['analysed_sst'].isel(time=slice(0,5), latitude=slice(lat_indices[0], lat_indices[-1]+1), longitude=slice(lon_indices[0], lon_indices[-1]+1))
print("\nSample shape:", sample.shape)
print("Sample values (first few):")
print(sample.values[:, :3, :3])
