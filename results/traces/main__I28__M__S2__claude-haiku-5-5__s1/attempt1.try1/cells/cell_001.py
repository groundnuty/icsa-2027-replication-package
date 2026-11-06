
import xarray as xr, numpy as np, os
p='/data/icsa2027_data_20261101T090944Z/s2z/sst_s2.nc'
ds=xr.open_dataset(p,engine='h5netcdf')
print(ds)
for v in ds.variables: print(v, ds[v].dtype, ds[v].attrs)
