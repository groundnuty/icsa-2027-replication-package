
import fsspec
import xarray as xr
import numpy as np
import datetime
import time

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Test reading one file
start = time.time()
f = fs.open(f'{base}/sst_19920101.nc', 'rb')
ds = xr.open_dataset(f, engine='h5netcdf')
sst_region = ds.analysed_sst.values[0, 330:390, 551:611]
print(f"Time to read one file: {time.time() - start:.2f}s")
print(f"Shape: {sst_region.shape}")
print(f"Some values: {sst_region[0,:5]}")
ds.close()
f.close()
