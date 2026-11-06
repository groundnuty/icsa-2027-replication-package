import os,re,datetime as dt, numpy as np, xarray as xr
d='/data/icsa2027_data_20261101T090944Z/s1z'
ds=xr.open_dataset(f'{d}/sst_19820101.nc',engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=57.57-1e-6)&(lat<=58.77+1e-6))[0]; lo=np.where((lon>=10.25-1e-6)&(lon<=11.45+1e-6))[0]
print(lat[la][[0,-1]], len(la), lon[lo][[0,-1]], len(lo), np.diff(lat[la])[:3], np.diff(lon[lo])[:3])
ds.close()
# dates needed
alld=[]
x=dt.date(1991,12,27)
while x<=dt.date(2016,8,31):
    alld.append(x); x+=dt.timedelta(1)
# load subset
import time
t0=time.time()
arr={}
for x in alld:
    f=f'{d}/sst_{x.strftime("%Y%m%d")}.nc'
    with xr.open_dataset(f,engine='h5netcdf') as o:
        v=o.analysed_sst.isel(time=0,latitude=la,longitude=lo).values.astype(np.float64)
        arr[x]=v
    if len(arr)%1000==0: print(len(arr), time.time()-t0, flush=True)
print(time.time()-t0)
A=np.stack([arr[x] for x in alld]); print(A.shape, np.nanmin(A), np.nanmax(A))
np.savez('/tmp/sub.npz',A=A,dates=np.array([str(x) for x in alld]),lat=lat[la],lon=lon[lo])