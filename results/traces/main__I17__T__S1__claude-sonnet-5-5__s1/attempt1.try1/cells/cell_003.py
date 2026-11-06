import fsspec,xarray as xr,numpy as np,pandas as pd
fs=fsspec.filesystem('onedata');p='icsa2027_data_20261101T090944Z/s1z'
fl=fs.find(p);print(len(fl),fl[-1])
names=[f.split('/')[-1] for f in fl]
print([n for n in names if not n.startswith('sst_')])
d=xr.open_dataset(fs.open(p+'/sst_20100601.nc','rb'),engine='h5netcdf');print(d)
dates=set(n[4:12] for n in names if n.startswith('sst_'))
rng=pd.date_range('1991-12-27','2010-08-31').strftime('%Y%m%d')
print([x for x in rng if x not in dates][:50])