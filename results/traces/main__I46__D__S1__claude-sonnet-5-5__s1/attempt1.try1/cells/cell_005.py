import fsspec,xarray as xr,re,pandas as pd
fs=fsspec.filesystem('onedata')
D='icsa2027_data_20261101T090944Z/s1z'
r=fs.find(D);print(len(r))
need=set(pd.date_range('1991-12-27','2003-01-05').strftime('%Y%m%d'))|set(pd.date_range('2013-06-01','2013-08-31').strftime('%Y%m%d'))
ds={re.findall(r'(\d{8})',n)[0] for n in r}
print(len(need-ds),sorted(need-ds)[:10],min(ds),max(ds))