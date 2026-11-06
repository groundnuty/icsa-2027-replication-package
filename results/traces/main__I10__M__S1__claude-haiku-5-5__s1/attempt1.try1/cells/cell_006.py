import os, numpy as np, xarray as xr, datetime as dt, time
from concurrent.futures import ThreadPoolExecutor
D='/data/icsa2027_data_20261101T090944Z/s1z'
os.makedirs('/tmp/w',exist_ok=True)
start=dt.date(1991,12,27); end=dt.date(2005,8,31)
dates=[]; d=start
while d<=end: dates.append(d); d+=dt.timedelta(1)
ref=xr.open_dataset(D+'/sst_20050615.nc',engine='h5netcdf')
la=np.arange(60); 
lat=ref.latitude.values; lon=ref.longitude.values
la=np.where((lat>=55.67)&(lat<=56.87))[0]; lo=np.where((lon>=16.45)&(lon<=17.65))[0]
ref.close()
def load(d):
    p=f"{D}/sst_{d:%Y%m%d}.nc"
    with xr.open_dataset(p,engine='h5netcdf') as x:
        assert x.time.values[0].astype('datetime64[D]')==np.datetime64(d)
        return x.analysed_sst.isel(time=0,latitude=la,longitude=lo).values.astype(np.float64)
t=time.time()
with ThreadPoolExecutor(16) as ex: arrs=list(ex.map(load,dates))
S=np.stack(arrs); print(S.shape, time.time()-t)
np.savez('/tmp/w/sst.npz',S=S,dates=np.array([str(x) for x in dates]),lat=lat[la],lon=lon[lo])