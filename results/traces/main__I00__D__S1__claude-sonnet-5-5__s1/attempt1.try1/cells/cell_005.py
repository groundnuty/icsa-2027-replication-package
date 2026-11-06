import fsspec,pandas as pd,os,xarray as xr,numpy as np
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
r=fs.ls(p,detail=False);print(len(r))
try:
    print(len(fs.find(p)))
except Exception as e:print(e)
names=set(os.path.basename(f) for f in fs.find(p))
need=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2004-06-01','2004-08-31'))
miss=[d for d in need if f"sst_{d:%Y%m%d}.nc" not in names];print(len(names),len(miss),miss[:5])