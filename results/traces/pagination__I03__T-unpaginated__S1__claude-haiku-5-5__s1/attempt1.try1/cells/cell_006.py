
import fsspec, xarray as xr, time, numpy as np, os
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z/'
dates = np.arange(np.datetime64('1991-12-27'), np.datetime64('2003-01-06'))
tdates = np.arange(np.datetime64('2014-06-01'), np.datetime64('2014-09-01'))
alld = np.concatenate([dates, tdates])
def rd(d):
    s=str(d).replace('-','')
    with fs.open(P+f'sst_{s}.nc','rb') as f:
        ds=xr.open_dataset(f,engine='h5netcdf').load()
    v=ds.analysed_sst.values[0].astype(np.float64)
    lat=ds.latitude.values; lon=ds.longitude.values
    ri=np.where((lat>=54.17)&(lat<=55.37))[0]; ci=np.where((lon>=13.25)&(lon<=14.45))[0]
    return v[np.ix_(ri,ci)], lat[ri], lon[ci], str(ds.time.values[0])[:10]
t=time.time()
with ThreadPoolExecutor(12) as ex:
    res=list(ex.map(rd, alld))
print('read',time.time()-t, len(res))
sst=np.stack([r[0] for r in res])
lat=res[0][1]; lon=res[0][2]
# verify date alignment
bad=[(str(d),r[3]) for d,r in zip(alld,res) if str(d)!=r[3]]
print('mismatch',len(bad), bad[:3])
np.savez('/tmp/sst.npz', sst=sst, lat=lat, lon=lon, dates=alld.astype(str))
print(sst.shape, lat[[0,-1]], lon[[0,-1]], np.isnan(sst).sum())
