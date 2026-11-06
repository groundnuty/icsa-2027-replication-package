import fsspec,xarray as xr,re,pandas as pd
fs=fsspec.filesystem('onedata')
need=pd.date_range('1991-12-27','2003-01-05').strftime('%Y%m%d').tolist()+pd.date_range('2012-06-01','2012-08-31').strftime('%Y%m%d').tolist()
names=sorted(fs.find('icsa2027_data_20261101T090944Z/s1z'));print(len(names),names[-1])
ds=set(re.findall(r'(\d{8})',n)[-1] for n in names)
miss=[d for d in need if d not in ds];print(len(miss),miss[:50])