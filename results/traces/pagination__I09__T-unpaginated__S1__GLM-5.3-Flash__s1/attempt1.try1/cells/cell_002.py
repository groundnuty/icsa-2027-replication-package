import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
with fs.open(f'{base}/sst_20220601.nc','rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(ds)
    print(ds.lat.values[:5], ds.lat.values[-5:])
    print(ds.lon.values[:5], ds.lon.values[-5:])
    print(ds.time.values)
    v = list(ds.data_vars)
    print(v)
