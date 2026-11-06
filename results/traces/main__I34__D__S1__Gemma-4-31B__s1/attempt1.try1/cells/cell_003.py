import fsspec
import xarray as xr
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'

# Inspect one file to see coordinates and variable name
sample_file_remote = f'{path}/sst_19820101.nc'
sample_file_local = '/work/sst_19820101.nc'
fs.get(sample_file_remote, sample_file_local)

with xr.open_dataset(sample_file_local, engine='h5netcdf') as ds:
    print(ds)
