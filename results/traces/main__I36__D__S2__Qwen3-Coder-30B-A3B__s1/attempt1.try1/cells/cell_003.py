import fsspec
import xarray as xr
import numpy as np
import os

# Download the file
remote_path = '/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
local_path = '/work/sst_s2.nc'

# Check if file already exists
if not os.path.exists(local_path):
    fs = fsspec.filesystem('onedata')
    fs.get(remote_path, local_path)
    print("File downloaded successfully")
else:
    print("File already exists locally")

# Open with xarray to examine structure
try:
    ds = xr.open_dataset(local_path, engine="h5netcdf")
    print("Dataset structure:")
    print(ds)
    
    # Print coordinates
    print("\nCoordinates:")
    for coord in ds.coords:
        print(f"{coord}: {ds[coord].values[:5] if len(ds[coord].values) > 5 else ds[coord].values}")
        
    # Print variables
    print("\nVariables:")
    for var in ds.data_vars:
        print(f"{var}: {ds[var].dims}")
        
    # Check SST variable specifically
    if 'sst' in ds.data_vars:
        sst_var = ds['sst']
        print(f"\nSST variable shape: {sst_var.shape}")
        print(f"SST variable dims: {sst_var.dims}")
        print(f"SST variable units: {sst_var.attrs.get('units', 'Unknown')}")
        
        # Show some sample data
        print(f"Sample SST data (first few values): {sst_var.isel(time=0, lat=0, lon=0).values}")
        
except Exception as e:
    print(f"Error opening dataset: {e}")
    import traceback
    traceback.print_exc()