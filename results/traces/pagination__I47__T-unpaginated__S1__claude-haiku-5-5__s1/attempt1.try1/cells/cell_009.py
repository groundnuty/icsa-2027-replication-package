import fsspec, xarray as xr, numpy as np, pandas as pd, os, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
d='icsa2027_data_20261101T090944Z/s1z/'
days = list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2019-06-01','2019-08-31'))
la=np.arange(2,62); lo=np.arange(2,62)  # placeholder, recomputed below
def load_sub(day):
    p=d+f"sst_{day:%Y%m%d}.nc"
    with fs.open(p,'rb') as f:
        ds=xr.open_dataset(f,engine='h5netcdf')
        return ds
ds0=load_sub(days[0])
lat=ds0.latitude.values; lon=ds0.longitude.values
la=np.where((lat>=64.39-1e-4)&(lat<=65.59+1e-4))[0]
lo=np.where((lon>=23.41-1e-4)&(lon<=24.61+1e-4))[0]
def load_sub2(day):
    p=d+f"sst_{day:%Y%m%d}.nc"
    with fs.open(p,'rb') as f:
        ds=xr.open_dataset(f,engine='h5netcdf')
        return ds.analysed_sst.isel(time=0,latitude=slice(la[0],la[-1]+1),longitude=slice(lo[0],lo[-1]+1)).values.astype(np.float64)
t=time.time()
with ThreadPoolExecutor(16) as ex:
    arrs=list(ex.map(load_sub2,days))
print(time.time()-t, len(arrs))
A=np.stack(arrs)
os.makedirs('/tmp',exist_ok=True)
np.savez('/tmp/sst_cache.npz',A=A,days=np.array([str(x.date()) for x in days]),lat=lat[la],lon=lon[lo])
print(A.shape, np.isnan(A).mean(), lat[la][[0,-1]], lon[lo][[0,-1]])
