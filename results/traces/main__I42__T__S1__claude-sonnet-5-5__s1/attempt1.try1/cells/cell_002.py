import xarray as xr,numpy as np,pandas as pd
fl=fs.ls(p,detail=False);print(len(fl),fl[-1])
names=set(x.split('/')[-1] for x in fl)
d=pd.date_range('1991-12-27','2003-01-05').append(pd.date_range('2012-06-01','2012-08-31'))
miss=[x for x in d if f"sst_{x:%Y%m%d}.nc" not in names];print(len(miss),miss[:20])
ds=xr.open_dataset(fs.open(p+'/sst_20120601.nc','rb'),engine='h5netcdf');print(ds)