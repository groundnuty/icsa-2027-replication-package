import fsspec,xarray as xr,re,pandas as pd
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
names=sorted(x.split('/')[-1] for x in fs.ls(p,detail=False))
ds=set(n[4:12] for n in names)
need=pd.date_range('1991-12-27','2003-01-05').strftime('%Y%m%d')
print([d for d in need if d not in ds][:50], len(names), names[0],names[-1],[n for n in names if not re.fullmatch(r'sst_\d{8}\.nc',n)])
tg=pd.date_range('2014-06-01','2014-08-31').strftime('%Y%m%d');print([d for d in tg if d not in ds])
d=xr.open_dataset(fs.open(p+'/sst_20140601.nc','rb'),engine='h5netcdf');print(d)