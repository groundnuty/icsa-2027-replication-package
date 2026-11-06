import xarray as xr,re
L=fs.ls('icsa2027_data_20261101T090944Z/s1z')
names=sorted(L); print(len(names),names[0],names[-1])
ds=set(re.findall(r'(\d{8})',n)[-1] for n in names)
import pandas as pd
need=pd.date_range('1991-12-27','2003-01-05').strftime('%Y%m%d').tolist()+pd.date_range('2012-06-01','2012-08-31').strftime('%Y%m%d').tolist()
miss=[d for d in need if d not in ds];print(len(miss),miss[:50])
print([n for n in names if not re.search(r'sst_\d{8}\.nc$',n)])
fs.get(names[0],'/work/a.nc');print(xr.open_dataset('/work/a.nc',engine='h5netcdf'))