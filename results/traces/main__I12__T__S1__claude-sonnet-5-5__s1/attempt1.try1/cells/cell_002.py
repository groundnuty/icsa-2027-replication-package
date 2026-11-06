import xarray as xr, numpy as np, pandas as pd
names=set(x.split('/')[-1] if isinstance(x,str) else x['name'] for x in fs.ls(p))
print(len(names))
want=pd.date_range('1991-12-27','2009-08-31')
miss=[d for d in want if f"sst_{d:%Y%m%d}.nc" not in names]
print(len(miss),miss[:20])
f=fs.open(p+'/sst_20090601.nc','rb');ds=xr.open_dataset(f,engine='h5netcdf');print(ds)
print(ds.lat.values[:3] if 'lat' in ds else '')