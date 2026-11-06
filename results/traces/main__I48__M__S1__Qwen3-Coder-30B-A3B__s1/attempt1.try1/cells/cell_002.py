import xarray as xr
import numpy as np

# Let's look at one file to understand the structure
file_path = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20231231.nc"
ds = xr.open_dataset(file_path, engine="h5netcdf")
print("Dataset coordinates:")
print(ds.coords)
print("\nDataset variables:")
print(ds.data_vars)
print("\nSST variable details:")
if 'sst' in ds.data_vars:
    print(ds.sst)
print("\nLat/lon ranges:")
print(f"Latitude range: {ds.lat.min().values} to {ds.lat.max().values}")
print(f"Longitude range: {ds.lon.min().values} to {ds.lon.max().values}")