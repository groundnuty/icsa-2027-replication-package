import fsspec, xarray as xr, numpy as np, time, os, datetime as dt
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
B='icsa2027_data_20261101T090944Z/s1z/'
def load(day):
    p=B+f"sst_{day.strftime('%Y%m%d')}.nc"
    with fs.open(p,'rb') as f:
        d=xr.open_dataset(f,engine='h5netcdf')
        la=d.latitude.values; lo=d.longitude.values
        ilat=np.where((la>=57.83-1e-6)&(la<=59.03+1e-6))[0]; ilon=np.where((lo>=17.41-1e-6)&(lo<=18.61+1e-6))[0]
        v=d.analysed_sst.isel(latitude=ilat,longitude=ilon).values.astype(np.float64)
        d.close()
    return day, v, la[ilat], lo[ilon]
t0=time.time()
r=[load(dt.date(2008,6,1)+dt.timedelta(i)) for i in range(4)]
print(time.time()-t0, r[0][1].shape, r[0][2][[0,-1]], r[0][3][[0,-1]])