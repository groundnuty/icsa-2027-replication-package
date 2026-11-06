import fsspec, xarray as xr, numpy as np
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
with fs.open(f'{base}/sst_20210615.nc', 'rb') as f:
    ds = xr.open_dataset(f, engine='h5netcdf')
    print(ds)
    print()
    for v in ds.variables:
        print(v, ds[v].dtype, ds[v].shape, dict(ds[v].attrs))
    print()
    print('global attrs:', dict(ds.attrs))