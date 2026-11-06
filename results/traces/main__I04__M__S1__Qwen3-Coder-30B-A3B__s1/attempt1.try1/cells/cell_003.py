import xarray as xr
import numpy as np

# Try to open one of the SST files to understand the structure
file_path = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20231231.nc"
try:
    ds = xr.open_dataset(file_path, engine="h5netcdf")
    print("Dataset structure:")
    print(ds)
    print("\nVariables:")
    for var in ds.data_vars:
        print(f"  {var}: {ds[var].dims}")
    print("\nCoordinates:")
    for coord in ds.coords:
        print(f"  {coord}: {ds[coord].dims}")
    ds.close()
except Exception as e:
    print(f"Error opening file: {e}")