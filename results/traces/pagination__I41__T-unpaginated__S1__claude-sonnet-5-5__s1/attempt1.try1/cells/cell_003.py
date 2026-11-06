import fsspec
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
import xarray as xr, numpy as np, pandas as pd
names=set(x.split('/')[-1] for x in fs.ls(p,detail=False))
need=pd.date_range('1991-12-27','2003-01-05').append(pd.date_range('2021-06-01','2021-08-31'))
miss=[d for d in need if f"sst_{d:%Y%m%d}.nc" not in names]
print(len(miss),miss[:20], [n for n in names if not n.startswith('sst_')][:5])
ds=xr.open_dataset(fs.open(p+'/sst_20210601.nc','rb'),engine='h5netcdf')
print(ds)