
import fsspec
import xarray as xr
import numpy as np

fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

# Check a file from 1992 and 2004
for f in ['sst_19920101.nc', 'sst_20040601.nc']:
    path = f'{base}/{f}'
    with fs.open(path, 'rb') as fh:
        ds = xr.open_dataset(fh, engine='h5netcdf')
        print(f)
        print(ds)
        print()
