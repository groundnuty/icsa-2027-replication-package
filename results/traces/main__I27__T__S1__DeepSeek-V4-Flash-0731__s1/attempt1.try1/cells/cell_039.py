
import xarray as xr
import fsspec
import numpy as np
import pandas as pd

fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')

# Check attribute for units
print(ds.analysed_sst.attrs)
print("\nFull dataset attrs:")
for k, v in ds.attrs.items():
    print(f"  {k}: {v}")
