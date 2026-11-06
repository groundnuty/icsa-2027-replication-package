import re,os
fl=fs.ls('icsa2027_data_20261101T090944Z/s1z')
names=sorted(os.path.basename(f) for f in fl)
print(len(names),names[0],names[-1])
ds=set(re.findall(r'\d{8}',n)[0] for n in names if re.search(r'\d{8}',n))
print([n for n in names if not re.fullmatch(r'sst_\d{8}\.nc',n)])
import pandas as pd
need=pd.date_range('1991-12-27','2003-01-05').strftime('%Y%m%d')
need=list(need)+list(pd.date_range('2009-06-01','2009-08-31').strftime('%Y%m%d'))
print([d for d in need if d not in ds][:50])
os.makedirs('/work/d',exist_ok=True)
fs.get('icsa2027_data_20261101T090944Z/s1z/sst_20090601.nc','/work/d/a.nc')
import xarray as xr
x=xr.open_dataset('/work/d/a.nc',engine='h5netcdf');print(x)