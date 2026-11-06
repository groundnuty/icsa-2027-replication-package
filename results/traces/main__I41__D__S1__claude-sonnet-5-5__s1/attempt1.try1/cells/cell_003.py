import fsspec,re,os
import pandas as pd, xarray as xr
fs=fsspec.filesystem('onedata')
fl=fs.ls('icsa2027_data_20261101T090944Z/s1z',detail=False)
ds=sorted(re.search(r'(\d{8})',f).group(1) for f in fl if re.search(r'\d{8}',f))
print(len(fl),len(ds),ds[0],ds[-1])
al=pd.date_range('1991-12-27','2003-01-05').strftime('%Y%m%d')
tg=pd.date_range('2021-06-01','2021-08-31').strftime('%Y%m%d')
S=set(ds);print([d for d in al if d not in S][:20],[d for d in tg if d not in S])
print([f for f in fl if not re.search(r'sst_\d{8}\.nc',f)])
os.makedirs('/work',exist_ok=True)
fs.get(fl[0],'/work/a.nc')
print(xr.open_dataset('/work/a.nc',engine='h5netcdf'))