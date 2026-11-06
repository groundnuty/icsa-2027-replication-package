import xarray as xr
import numpy as np

# Let's look at one file to understand the structure
file_path = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20231231.nc"
ds = xr.open_dataset(file_path, engine="h5netcdf")
print("Dataset coordinates:")
print(ds.coords)
print("\nDataset variables:")
print(ds.data_vars)
print("\nVariable names:")
for var in ds.data_vars:
    print(f"  {var}")

# Check the actual variable names for lat/lon
print("\nCoordinate variable names:")
for coord in ds.coords:
    print(f"  {coord}: {ds.coords[coord]}")

# Check the SST variable
if 'analysed_sst' in ds.data_vars:
    sst_var = ds['analysed_sst']
    print(f"\nAnalysed SST shape: {sst_var.shape}")
    print(f"Analysed SST dims: {sst_var.dims}")
    print(f"Analysed SST first few values:\n{sst_var.isel(time=0).values[0:5, 0:5]}")
    
    # Check coordinate ranges
    print(f"\nLatitude range: {ds.latitude.min().values} to {ds.latitude.max().values}")
    print(f"Longitude range: {ds.longitude.min().values} to {ds.longitude.max().values}")