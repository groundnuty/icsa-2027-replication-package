import xarray as xr
import numpy as np

# Load a sample file to understand the structure
sample_file = "/data/icsa2027_data_20261101T090944Z/s1z/sst_20231231.nc"
try:
    ds = xr.open_dataset(sample_file, engine="h5netcdf")
    print("Dataset coordinates:")
    print(ds.coords)
    print("\nDataset variables:")
    print(ds.data_vars)
    print("\nSST variable shape:", ds['sst'].shape if 'sst' in ds else 'Not found')
    if 'sst' in ds:
        print("SST variable dims:", ds['sst'].dims)
        print("SST variable attrs:", ds['sst'].attrs)
    ds.close()
except Exception as e:
    print(f"Error opening file: {e}")