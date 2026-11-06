import xarray as xr, fsspec, numpy as np
fs = fsspec.filesystem('onedata')
p2 = 'icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
with fs.open(p2, 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(ds)
    print('---- attrs ----')
    print(ds.attrs)
