import xarray as xr, numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print('---')
for v in ds.variables:
    try:
        print(v, ds[v].dtype, ds[v].shape, dict(ds[v].attrs))
    except Exception as e:
        print(v, 'ERR', e)