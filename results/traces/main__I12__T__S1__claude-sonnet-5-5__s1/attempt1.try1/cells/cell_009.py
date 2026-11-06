import fsspec,xarray as xr,numpy as np,pandas as pd,time
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
def get(d):
    err=None
    for k in range(4):
        try:
            with fs.open(f'{p}/sst_{d:%Y%m%d}.nc','rb') as f:
                x=xr.open_dataset(f,engine='h5netcdf')
                x=x.sel(latitude=slice(56.09-1e-4,57.29+1e-4),longitude=slice(10.55-1e-4,11.75+1e-4)).load()
            return x
        except FileNotFoundError: return None
        except Exception as e: err=e
    return ('err',str(err))
dates=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2009-06-01','2009-08-31'))
t=time.time()
with ThreadPoolExecutor(16) as ex: res=list(ex.map(get,dates))
print(time.time()-t)
bad=[(d,r) for d,r in zip(dates,res) if r is None or isinstance(r,tuple)]
print(len(bad),bad[:5])
ok=[(d,r.analysed_sst.values[0]) for d,r in zip(dates,res) if r is not None and not isinstance(r,tuple)]
last=[r for r in res if r is not None and not isinstance(r,tuple)][-1]
np.savez('/tmp/d.npz',t=np.array([d.value for d,_ in ok]),a=np.stack([a for _,a in ok]),lat=last.latitude.values,lon=last.longitude.values)