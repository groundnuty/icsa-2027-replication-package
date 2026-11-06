import numpy as np, datetime as dt, os
from concurrent.futures import ThreadPoolExecutor
os.makedirs('work',exist_ok=True); os.makedirs('output',exist_ok=True)
def daterange(a,b):
    d=a
    while d<=b:
        yield d; d+=dt.timedelta(days=1)
dates=list(daterange(dt.date(1991,12,27),dt.date(2003,1,5)))+list(daterange(dt.date(2012,6,1),dt.date(2012,8,31)))
def load(d):
    fn=P+f"sst_{d:%Y%m%d}.nc"
    with fs.open(fn,'rb') as f:
        x=xarray.open_dataset(f,engine='h5netcdf')
        lat=x.latitude.values; lon=x.longitude.values
        im=np.where((lat>=54.45)&(lat<=55.65))[0]; jm=np.where((lon>=16.05)&(lon<=17.25))[0]
        v=x.analysed_sst.values[0][np.ix_(im,jm)].astype(np.float64)
        x.close()
    return v, lat[im], lon[jm]
t=time.time()
with ThreadPoolExecutor(16) as ex:
    res=list(ex.map(load,dates))
print(time.time()-t, len(res))
lat=res[0][1]; lon=res[0][2]
assert all(np.array_equal(r[1],lat) and np.array_equal(r[2],lon) for r in res)
arr=np.stack([r[0] for r in res])
np.savez('work/sub.npz',sst=arr,dates=np.array([str(d) for d in dates]),lat=lat,lon=lon)
print(arr.shape, lat[[0,-1]], lon[[0,-1]], np.isnan(arr).sum())