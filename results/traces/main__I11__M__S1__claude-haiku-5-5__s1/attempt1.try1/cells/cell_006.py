
import os, time, numpy as np, xarray as xr, pandas as pd
from concurrent.futures import ThreadPoolExecutor
d='/data/icsa2027_data_20261101T090944Z/s1z'
need=pd.date_range('1991-12-27','2003-01-05').append(pd.date_range('2021-06-01','2021-08-31'))
need=pd.DatetimeIndex(sorted(set(need)))
ref=xr.open_dataset(d+'/sst_19820101.nc',engine='h5netcdf')
lat=ref.latitude.values.astype(np.float64); lon=ref.longitude.values.astype(np.float64)
li=np.where((lat>=55.67-1e-6)&(lat<=56.87+1e-6))[0]; lo=np.where((lon>=16.45-1e-6)&(lon<=17.65+1e-6))[0]
ref.close()
def load(t):
    p=f"{d}/sst_{t:%Y%m%d}.nc"
    with xr.open_dataset(p,engine='h5netcdf') as x:
        a=x.analysed_sst.isel(time=0).values[np.ix_(li,lo)].astype(np.float32)
    return a
t0=time.time()
with ThreadPoolExecutor(16) as ex: arrs=list(ex.map(load,need))
print(time.time()-t0, len(arrs))
S=np.stack(arrs)  # float32, (ndays, 60, 60)
os.makedirs('/tmp/w',exist_ok=True)
np.savez('/tmp/w/sub.npz',S=S,dates=need.values.astype('datetime64[D]'),lat=lat[li],lon=lon[lo])
print(S.shape, np.isnan(S).sum())
