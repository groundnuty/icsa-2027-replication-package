import fsspec
import xarray as xr
import numpy as np
import pandas as pd
import os

# Clean up /work
for f in os.listdir('/work'):
    os.remove(os.path.join('/work', f))

fs = fsspec.filesystem('onedata')
remote_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

try:
    # Use fs.open to create a file-like object
    with fs.open(remote_path, 'rb') as f:
        # Use engine="h5netcdf" which supports file-like objects
        ds = xr.open_dataset(f, engine="h5netcdf")
        print("Dataset opened successfully!")
        print(ds)
        # Test a small slice
        test_slice = ds.analysed_sst.isel(time=0, latitude=0, longitude=0).values
        print(f"Test value: {test_slice}")
        ds.close()
except Exception as e:
    print(f"Failed to open dataset: {e}")
