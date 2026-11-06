import fsspec,xarray as xr,re
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
fl=fs.find(p)
print(len(fl),fl[-1])
ds=xr.open_dataset(fs.open(fl[0],'rb'),engine='h5netcdf')
print(ds)
print([f for f in fl if not re.search(r'sst_\d{8}\.nc$',f)])
ds=[f[-11:-3] for f in fl]
import pandas as pd
d=pd.to_datetime(ds,format='%Y%m%d')
full=pd.date_range(d.min(),d.max())
print(d.min(),d.max(),len(full)-len(d), full.difference(d)[:50])