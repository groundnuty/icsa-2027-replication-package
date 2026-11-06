import fsspec, xarray as xr, numpy as np, pandas as pd, os
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
def rd(d):
    p=f'icsa2027_data_20261101T090944Z/s1z/sst_{d}.nc'
    with fs.open(p,'rb') as f:
        ds=xr.open_dataset(f,engine='h5netcdf').load()
    la=ds.latitude.values; lo=ds.longitude.values
    il=np.where((la>=54.81-1e-4)&(la<=56.01+1e-4))[0]; jl=np.where((lo>=19.61-1e-4)&(lo<=20.81+1e-4))[0]
    sub=ds.analysed_sst.isel(time=0, latitude=il, longitude=jl).values.astype(np.float64)
    return sub, la[il], lo[jl], str(ds.time.values[0])[:10]
dates = list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2007-06-01','2007-08-31'))
ds_str=[d.strftime('%Y%m%d') for d in dates]
with ThreadPoolExecutor(8) as ex:
    res=list(ex.map(rd, ds_str))
arr=np.stack([r[0] for r in res]); la=res[0][1]; lo=res[0][2]
tdates=[r[3] for r in res]
assert tdates==[d.strftime('%Y-%m-%d') for d in dates]
np.savez('/tmp/x/cache.npz', arr=arr, la=la, lo=lo, dates=np.array(tdates))
print(arr.shape, la, lo, np.isnan(arr).sum())
