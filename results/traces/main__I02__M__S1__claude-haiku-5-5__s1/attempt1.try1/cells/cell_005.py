import os,re,datetime as dt
import xarray as xr, numpy as np
from concurrent.futures import ThreadPoolExecutor
d='/data/icsa2027_data_20261101T090944Z/s1z'
ds=xr.open_dataset(d+'/sst_19820101.nc',engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
la=np.where((lat>=54.17-1e-6)&(lat<=55.37+1e-6))[0]; lo=np.where((lon>=13.25-1e-6)&(lon<=14.45+1e-6))[0]
print(len(la),len(lo), lat[la[[0,-1]]], lon[lo[[0,-1]]])
print(np.diff(lat[la])[:3], np.diff(lon[lo])[:3])
ds.close()
def dates_needed():
    out=[]
    s=dt.date(1991,12,27)
    while s<=dt.date(2003,1,5): out.append(s); s+=dt.timedelta(1)
    s=dt.date(2004,6,1)
    while s<=dt.date(2004,8,31): out.append(s); s+=dt.timedelta(1)
    return out
need=dates_needed(); print(len(need))
def load(day):
    p=f"{d}/sst_{day:%Y%m%d}.nc"
    with xr.open_dataset(p,engine='h5netcdf') as x:
        a=x.analysed_sst.isel(time=0,latitude=slice(la[0],la[-1]+1),longitude=slice(lo[0],lo[-1]+1)).values.astype(np.float64)
    return a
with ThreadPoolExecutor(16) as ex: arrs=list(ex.map(load,need))
A=np.stack(arrs); print(A.shape, np.isnan(A).mean())
np.savez('/tmp/sub.npz',A=A,days=np.array([str(x) for x in need]),lat=lat[la],lon=lon[lo])