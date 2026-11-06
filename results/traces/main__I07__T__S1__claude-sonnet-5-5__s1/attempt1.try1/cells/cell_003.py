import fsspec,xarray as xr,re,numpy as np,pandas as pd
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
fl=sorted(fs.find(p));print(len(fl),fl[0],fl[-1])
d=pd.to_datetime([re.search(r'(\d{8})',f).group(1) for f in fl],format='%Y%m%d')
print(d.is_unique);full=pd.date_range(d.min(),d.max());print(len(full),full.difference(d)[:50])
x=xr.open_dataset(fs.open(fl[0],'rb'),engine='h5netcdf');print(x)