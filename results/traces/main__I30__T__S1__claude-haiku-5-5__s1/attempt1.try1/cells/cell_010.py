
import fsspec, time, datetime as dt, xarray as xr, numpy as np
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
B='icsa2027_data_20261101T090944Z/s1z/sst_%s.nc'
days=[dt.date(1991,12,27)+dt.timedelta(i) for i in range((dt.date(2003,1,5)-dt.date(1991,12,27)).days+1)]
days+= [dt.date(2010,6,1)+dt.timedelta(i) for i in range(92)]
def get(d):
    with fs.open(B%d.strftime('%Y%m%d'),'rb') as f:
        ds=xr.open_dataset(f,engine='h5netcdf')
        lat=ds.latitude.values; lon=ds.longitude.values
        la=np.where((lat>=58.69)&(lat<=59.89))[0]; lo=np.where((lon>=18.69)&(lon<=19.89))[0]
        s=ds.analysed_sst.isel(latitude=slice(la[0],la[-1]+1),longitude=slice(lo[0],lo[-1]+1)).values.astype(np.float64)
        return s, lat[la], lon[lo]
t=time.time()
with ThreadPoolExecutor(16) as ex:
    res=list(ex.map(get,days))
print(time.time()-t, len(res))
sst=np.stack([r[0] for r in res]); lat=res[0][1]; lon=res[0][2]
print(sst.shape, all(np.array_equal(r[1],lat) and np.array_equal(r[2],lon) for r in res))
np.savez('/tmp/sst.npz', sst=sst, lat=lat, lon=lon, days=np.array([d.strftime('%Y%m%d') for d in days]))
