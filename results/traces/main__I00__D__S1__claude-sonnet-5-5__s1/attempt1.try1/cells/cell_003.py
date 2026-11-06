import fsspec,pandas as pd,os,xarray as xr,numpy as np
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
names=set(os.path.basename(f) for f in fs.ls(p,detail=False))
print(len(names),min(names),max(names))
need=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2004-06-01','2004-08-31'))
miss=[d for d in need if f"sst_{d:%Y%m%d}.nc" not in names];print(len(need),miss[:20],len(miss))
os.makedirs('/work/d',exist_ok=True)
fs.get(f"{p}/sst_20040601.nc",'/work/d/a.nc')
d=xr.open_dataset('/work/d/a.nc',engine='h5netcdf');print(d)