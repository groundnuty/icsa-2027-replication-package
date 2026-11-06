
import xarray as xr
import numpy as np
from datetime import date, timedelta
import os, time

data_dir = '/data/icsa2027_data_20261101T090944Z/s1z'

# Test loading one file and getting the region
ds = xr.open_dataset(f'{data_dir}/sst_19920101.nc', engine='h5netcdf')
print(ds.analysed_sst.shape)
region = ds.analysed_sst.values[0, 350:410, 413:473]
print(region.shape)
print("NaN count:", np.isnan(region).sum())
print("Non-NaN count:", np.sum(~np.isnan(region)))
ds.close()
