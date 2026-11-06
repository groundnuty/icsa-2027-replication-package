import xarray as xr, numpy as np, os, glob
d='/data/icsa2027_data_20261101T090944Z/s1z'
ds=xr.open_dataset(f'{d}/sst_19820101.nc',engine='h5netcdf')
print(ds)
for v in ds.variables: print(v, ds[v].attrs)
files=sorted(os.listdir(d)); print(files[:2], files[-3:])
import re
names=set(files)
print([f for f in files if f.startswith('sst_1991') or f.startswith('sst_2003')][:3])