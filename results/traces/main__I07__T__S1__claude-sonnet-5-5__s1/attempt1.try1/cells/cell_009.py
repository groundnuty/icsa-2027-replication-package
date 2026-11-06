import fsspec,xarray as xr,numpy as np,pandas as pd,time,os
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
dates=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2021-06-01','2021-08-31'))
def get(t):
    f=f"{p}/sst_{t:%Y%m%d}.nc"
    err=None
    for k in range(5):
        try:
            with fs.open(f,'rb') as fh:
                x=xr.open_dataset(fh,engine='h5netcdf')
                la=x.latitude.values;lo=x.longitude.values
                m1=(la>=54.45-1e-4)&(la<=55.65+1e-4);m2=(lo>=16.05-1e-4)&(lo<=17.25+1e-4)
                v=x.analysed_sst.isel(time=0,latitude=m1,longitude=m2).values.astype('float64')
                return v,la[m1],lo[m2]
        except Exception as e: err=e;time.sleep(1)
    raise err
t0=time.time()
with ThreadPoolExecutor(24) as ex: r=list(ex.map(get,dates))
A=np.stack([a[0] for a in r]);os.makedirs('output',exist_ok=True)
np.savez('output/cache.npz',A=A,lat=r[0][1],lon=r[0][2],dates=np.array([f"{t:%Y-%m-%d}" for t in dates]))
print(time.time()-t0,A.shape,np.isnan(A).mean())