import xarray as xr
import numpy as np

# Let's examine a sample file to understand the structure
sample_file = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20230601.nc"
try:
    ds = xr.open_dataset(sample_file, engine="h5netcdf")
    print("Dataset structure:")
    print(ds)
    print("\nCoordinates:")
    print(ds.coords)
    print("\nVariables:")
    print(ds.data_vars)
    ds.close()
except Exception as e:
    print(f"Error opening file: {e}")