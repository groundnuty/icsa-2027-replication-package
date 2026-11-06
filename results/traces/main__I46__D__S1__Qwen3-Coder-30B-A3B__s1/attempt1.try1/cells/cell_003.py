import xarray as xr
import numpy as np
import fsspec
import os

# Create output directory
os.makedirs('output', exist_ok=True)

# Download a sample file to examine structure
fs = fsspec.filesystem('onedata')
sample_file = '/icsa2027_data_20261101T090944Z/s1z/sst_20130601.nc'
fs.get(sample_file, 'sst_20130601.nc')

# Open and examine the sample file
ds = xr.open_dataset('sst_20130601.nc', engine='h5netcdf')
print("Sample file dimensions:", ds.dims)
print("Sample file variables:", list(ds.data_vars.keys()))
print("Coordinates:", list(ds.coords.keys()))
print("SST shape:", ds['analysed_sst'].shape)
print("Latitude range:", ds['latitude'].min().values, "to", ds['latitude'].max().values)
print("Longitude range:", ds['longitude'].min().values, "to", ds['longitude'].max().values)
print("First few latitudes:", ds['latitude'][:5].values)
print("First few longitudes:", ds['longitude'][:5].values)