import xarray as xr, numpy as np
ds = xr.open_dataset('/work/sst_s2.nc', engine='h5netcdf')
print(ds)
print('---')
print('time dtype', ds.time.dtype, ds.time.values[0], ds.time.values[-1], ds.time.size)
for c in ds.coords:
    try:
        print(c, ds[c].dtype, ds[c].shape, ds[c].values[:3], ds[c].values[-3:])
    except Exception as e:
        print(c, 'err', e)
print('---vars')
for v in ds.data_vars:
    print(v, ds[v].dtype, ds[v].shape)
