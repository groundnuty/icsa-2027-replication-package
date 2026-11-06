import fsspec, os, xarray as xr, numpy as np, datetime as dt, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
days=[]
d=dt.date(1991,12,27)
while d<=dt.date(2012,8,31):
    days.append(d); d+=dt.timedelta(1)
ds=xr.open_dataset(base and '/work/s/t.nc',engine='h5netcdf')
lat=ds.latitude.values.astype(float); lon=ds.longitude.values.astype(float)
la=np.where((lat>=57.33-1e-4)&(lat<=58.53+1e-4))[0]; lo=np.where((lon>=9.03-1e-4)&(lon<=10.23+1e-4))[0]
np.savez('/work/s/coords.npz', lat=lat[la], lon=lon[lo])
def proc(day):
    out=f'/work/s/sub/{day:%Y%m%d}.npz'
    if os.path.exists(out): return 1
    fn=f'/work/s/raw_{day:%Y%m%d}.nc'
    fs.get(base+f'sst_{day:%Y%m%d}.nc', fn)
    with xr.open_dataset(fn,engine='h5netcdf') as x:
        v=x.analysed_sst.isel(time=0).values[la[0]:la[-1]+1, lo[0]:lo[-1]+1].astype(np.float64)
        np.savez(out, sst=v)
    os.remove(fn)
    return 1
t0=time.time()
with ThreadPoolExecutor(16) as ex:
    res=list(ex.map(proc, days))
print(len(res), len(os.listdir('/work/s/sub')), time.time()-t0)