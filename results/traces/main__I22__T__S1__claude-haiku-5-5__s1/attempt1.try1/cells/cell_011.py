
import fsspec, datetime as dt, time, xarray as xr, numpy as np, os
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
D='icsa2027_data_20261101T090944Z/s1z'
start=dt.date(1991,12,27); end=dt.date(2004,8,31)
allds=[start+dt.timedelta(i) for i in range((end-start).days+1)]
def grab(d):
    out=f"/tmp/sub/{d:%Y%m%d}.npy"
    if os.path.exists(out): return
    with fs.open(f"{D}/sst_{d:%Y%m%d}.nc",'rb') as f:
        ds=xr.open_dataset(f,engine='h5netcdf')
        lat=ds.latitude.values; lon=ds.longitude.values
        il=np.where((lat>=57.41)&(lat<=58.61))[0]; jl=np.where((lon>=18.69)&(lon<=19.89))[0]
        a=ds.analysed_sst.isel(time=0,latitude=il,longitude=jl).values.astype(np.float32)
        ds.close()
    np.save(out,a)
t=time.time()
todo=[d for d in allds if not os.path.exists(f"/tmp/sub/{d:%Y%m%d}.npy")]
print('todo',len(todo))
with ThreadPoolExecutor(16) as ex:
    list(ex.map(grab,todo[:1800]))
print(time.time()-t, len(os.listdir('/tmp/sub')))
