import fsspec, traceback, os
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
allfiles = fs.ls(base)
print("total files:", len(allfiles))
first = allfiles[0]; last = allfiles[-1]
print("first:", first, "last:", last)

import xarray as xr
with fs.open(first, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(ds)
