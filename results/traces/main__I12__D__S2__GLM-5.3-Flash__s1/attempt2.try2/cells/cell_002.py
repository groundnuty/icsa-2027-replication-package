import xarray as xr, numpy as np
p = '/work/s2z/sst_s2.nc'
ds = xr.open_dataset(p, engine='h5netcdf')
print(ds)
print('\n-- attrs --')
print(dict(ds.attrs))