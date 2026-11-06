import xarray as xr,re
L=fs.ls('icsa2027_data_20261101T090944Z/s1z')
names=sorted(L); print(len(names),names[0],names[-1])
ds={re.findall(r'(\d{8})',n)[0] for n in names}
import pandas as pd
need=set(pd.date_range('1991-12-27','2003-01-05').strftime('%Y%m%d'))|set(pd.date_range('2013-06-01','2013-08-31').strftime('%Y%m%d'))
print(len(need-ds),sorted(need-ds)[:20]); print([n for n in names if not n.endswith('.nc')][:5])
fs.get(names[0],'/work/a.nc')
d=xr.open_dataset('/work/a.nc',engine='h5netcdf');print(d)