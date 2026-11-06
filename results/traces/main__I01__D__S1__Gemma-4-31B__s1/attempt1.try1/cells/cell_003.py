import fsspec
import xarray as xr
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

fs = fsspec.filesystem('onedata')
path = 'icsa2027_data_20261101T090944Z/s1z'
files = fs.ls(path)

# Filter files to only include those starting with sst_ and ending with .nc
sst_files = sorted([f for f in files if f.startswith(f'{path}/sst_') and f.endswith('.nc')])

# Test one file
test_file_remote = sst_files[0]
test_file_local = f'/work/{os.path.basename(test_file_remote)}'
fs.get(test_file_remote, test_file_local)
ds = xr.open_dataset(test_file_local, engine="h5netcdf")
print(ds)
ds.close()
