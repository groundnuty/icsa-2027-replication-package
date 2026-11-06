
import pandas as pd
import numpy as np
import fsspec
import xarray as xr

fs = fsspec.filesystem('onedata')
data_path = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'

with fs.open(data_path, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print("Dataset attributes:")
    for k, v in ds.attrs.items():
        print(f"  {k}: {v}")
    
    print("\nData variable attributes:")
    for k, v in ds['analysed_sst'].attrs.items():
        print(f"  {k}: {v}")
    
    print(f"\nData var dtype: {ds['analysed_sst'].dtype}")
