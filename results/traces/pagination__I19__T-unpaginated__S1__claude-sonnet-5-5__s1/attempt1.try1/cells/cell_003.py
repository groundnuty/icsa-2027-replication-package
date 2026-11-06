import fsspec,xarray as xr,numpy as np,pandas as pd
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
names=set(x.split('/')[-1] for x in fs.ls(p,detail=False))
d=pd.date_range('1991-12-27','2003-01-05')
miss=[x for x in d if f'sst_{x:%Y%m%d}.nc' not in names]
t=pd.date_range('2014-06-01','2014-08-31')
print(len(miss),miss[:10],[x for x in t if f'sst_{x:%Y%m%d}.nc' not in names])
ds=xr.open_dataset(fs.open(p+'/sst_20140601.nc','rb'),engine='h5netcdf');print(ds)