
import time
import xarray as xr
import numpy as np
import os

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Test loading one file for the region
start_time = time.time()
ds = xr.open_dataset(f'{data_dir}/sst_19920101.nc', engine='h5netcdf')
sst = ds['analysed_sst'].isel(time=0, latitude=slice(278, 338), longitude=slice(613, 673)).values
ds.close()
elapsed = time.time() - start_time
print(f"Loading one day took {elapsed:.2f} seconds")
print(f"Shape: {sst.shape}")
print(f"Some values: {sst[0,:5]}")
print(f"Finite: {np.isfinite(sst).sum()} / {sst.size}")
