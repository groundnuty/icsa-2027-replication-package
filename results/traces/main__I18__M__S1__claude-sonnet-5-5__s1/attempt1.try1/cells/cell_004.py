import os,xarray as xr,numpy as np,pandas as pd
d='/data/icsa2027_data_20261101T090944Z/s1z'
fs=sorted(os.listdir(d));print(fs[0],fs[-1])
ds=xr.open_dataset(d+'/sst_20100601.nc',engine='h5netcdf');print(ds)
S=set(fs)
dates=pd.date_range('1991-12-27','2003-01-05');miss=[x for x in dates if f"sst_{x:%Y%m%d}.nc" not in S];print(len(miss),miss[:10])
print([x for x in pd.date_range('2010-06-01','2010-08-31') if f"sst_{x:%Y%m%d}.nc" not in S])