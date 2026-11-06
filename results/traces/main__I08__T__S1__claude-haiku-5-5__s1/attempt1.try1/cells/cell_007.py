import fsspec, xarray as xr, numpy as np, datetime, os, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
la=slice(311,371); 
def getday(ds_date):
    n=base+f"sst_{ds_date:%Y%m%d}.nc"
    with fs.open(n,'rb') as f:
        ds=xr.open_dataset(f,engine='h5netcdf')
        ds=ds.isel(latitude=slice(None),longitude=slice(None))
        return ds
# determine indices robustly from first file
with fs.open(base+'sst_20070601.nc','rb') as f:
    d0=xr.open_dataset(f,engine='h5netcdf').load()
lat=d0.latitude.values; lon=d0.longitude.values
li=np.where((lat>=54.81)&(lat<=56.01))[0]; oi=np.where((lon>=19.61)&(lon<=20.81))[0]
print(li[0],li[-1],oi[0],oi[-1], len(li), len(oi))
def load_one(day):
    n=base+f"sst_{day:%Y%m%d}.nc"
    with fs.open(n,'rb') as f:
        ds=xr.open_dataset(f,engine='h5netcdf').load()
    t=ds.time.values[0]
    assert str(t)[:10]==day.isoformat(), (n,t)
    arr=ds.analysed_sst.values[0][np.ix_(li,oi)].astype(np.float64)
    return arr
days=[]
d=datetime.date(1991,12,27)
while d<=datetime.date(2003,1,5): days.append(d); d+=datetime.timedelta(1)
tgt=[]
d=datetime.date(2007,6,1)
while d<=datetime.date(2007,8,31): tgt.append(d); d+=datetime.timedelta(1)
alld=days+tgt
t0=time.time()
with ThreadPoolExecutor(16) as ex:
    arrs=list(ex.map(load_one, alld))
print('elapsed',time.time()-t0, len(arrs))
A=np.stack(arrs)
np.savez('/tmp/sst_region.npz', sst=A.astype(np.float32), dates=np.array([x.isoformat() for x in alld]), lat=lat[li], lon=lon[oi])
print(A.shape, np.isnan(A).sum())