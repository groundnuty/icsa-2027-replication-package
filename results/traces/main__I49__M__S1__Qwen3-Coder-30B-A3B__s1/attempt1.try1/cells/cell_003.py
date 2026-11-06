import xarray as xr
import numpy as np

# Load a sample file to understand the structure
sample_file = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20231231.nc"
try:
    ds = xr.open_dataset(sample_file, engine="h5netcdf")
    print("Dataset coordinates and variables:")
    print(ds.coords)
    print("\nVariables:")
    print(ds.data_vars)
    print("\nLatitudes range:", ds['lat'].min().values, "to", ds['lat'].max().values)
    print("Longitudes range:", ds['lon'].min().values, "to", ds['lon'].max().values)
    ds.close()
except Exception as e:
    print(f"Error opening file: {e}")