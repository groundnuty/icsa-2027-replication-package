
import fsspec, xarray as xr, numpy as np, time, os, datetime as dt
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z/'
ilat=np.arange(0,0); 
ds=xr.open_dataset(fs.open(P+'sst_19820101.nc','rb'),engine='h5netcdf')
lat=ds.latitude.values; lon=ds.longitude.values
ilat=np.where((lat>=58.69-1e-6)&(lat<=59.89+1e-6))[0]; ilon=np.where((lon>=18.69-1e-6)&(lon<=19.89+1e-6))[0]
dates=[dt.date(1991,12,27)+dt.timedelta(days=i) for i in range((dt.date(2003,1,5)-dt.date(1991,12,27)).days+1)]
dates+=[dt.date(2017,6,1)+dt.timedelta(days=i) for i in range(92)]
def load(d):
    name=P+f"sst_{d:%Y%m%d}.nc"
    x=xr.open_dataset(fs.open(name,'rb'),engine='h5netcdf')
    a=x['analysed_sst'].isel(latitude=ilat,longitude=ilon).values[0].astype(np.float64)
    tt=x.time.values[0]
    x.close()
    return a, str(tt)[:10]
t=time.time()
with ThreadPoolExecutor(16) as ex: res=list(ex.map(load,dates))
print(time.time()-t)
arr=np.stack([r[0] for r in res]); tstr=[r[1] for r in res]
print(arr.shape, all(s==d.isoformat() for s,d in zip(tstr,dates)))
os.makedirs('work',exist_ok=True)
np.savez('work/sst.npz', sst=arr, dates=np.array([d.isoformat() for d in dates]), lat=lat[ilat], lon=lon[ilon])
