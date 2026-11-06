import xarray as xr, numpy as np, os, glob
d='/data/icsa2027_data_20261101T090944Z/s1z'
ds=xr.open_dataset(f'{d}/sst_19820101.nc', engine='h5netcdf')
print(ds)
print(ds.attrs)
for v in ds.variables: print(v, ds[v].attrs, ds[v].dtype)
print(sorted(os.listdir(d))[-3:])