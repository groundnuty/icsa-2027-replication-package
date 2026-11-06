import xarray as xr, numpy as np
ds = xr.open_dataset('/work/s2z/sst_s2.nc', engine='h5netcdf')
print(ds)
print()
for c in ds.coords:
    try:
        print(c, ds[c].values[:3], '...', ds[c].values[-3:], ds[c].dtype, ds[c].shape)
    except Exception as e:
        print(c, e)
print()
for v in ds.data_vars:
    print(v, ds[v].dims, ds[v].dtype, ds[v].attrs)