import fsspec, xarray as xr, numpy as np, pandas as pd, os, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
d='icsa2027_data_20261101T090944Z/s1z/'
days = list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2019-06-01','2019-08-31'))
def load(day):
    p=d+f"sst_{day:%Y%m%d}.nc"
    with fs.open(p,'rb') as f:
        ds=xr.open_dataset(f,engine='h5netcdf')
        ds=ds.load()
    return ds
t=time.time()
ds0=load(days[0])
lat=ds0.latitude.values; lon=ds0.longitude.values
la=np.where((lat>=64.39-1e-4)&(lat<=65.59+1e-4))[0]
lo=np.where((lon>=23.41-1e-4)&(lon<=24.61+1e-4))[0]
print(len(la),len(lo), lat[la[0]],lat[la[-1]],lon[lo[0]],lon[lo[-1]], time.time()-t)
