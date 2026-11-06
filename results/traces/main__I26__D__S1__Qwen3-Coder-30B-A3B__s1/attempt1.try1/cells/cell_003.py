import xarray as xr
import fsspec
import numpy as np

# First, let's download and examine one file to understand the structure
fs = fsspec.filesystem('onedata')
remote_path = '/icsa2027_data_20261101T090944Z/s1z/sst_19820101.nc'
local_path = '/work/sst_19820101.nc'

fs.get(remote_path, local_path)

# Open with xarray
ds = xr.open_dataset(local_path, engine='h5netcdf')
print("Dataset dimensions:", dict(ds.dims))
print("Dataset variables:", list(ds.data_vars.keys()))

# Check the SST data specifically
if 'analysed_sst' in ds.data_vars:
    print("\nAnalysed SST variable details:")
    sst_var = ds['analysed_sst']
    print("Shape:", sst_var.shape)
    print("Dimensions:", sst_var.dims)
    print("Coordinates:")
    for coord in ds.coords:
        print(f"  {coord}: shape={ds.coords[coord].shape}, values range: {ds.coords[coord].min().values} to {ds.coords[coord].max().values}")
    
    # Show some sample data
    print("\nSample SST data (first few values):")
    print(sst_var.isel(time=0, latitude=0, longitude=0).values)
    print("Sample latitudes:", ds.latitude.values[:5])
    print("Sample longitudes:", ds.longitude.values[:5])

ds.close()