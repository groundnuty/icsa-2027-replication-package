import fsspec, xarray as xr, numpy as np, datetime as dt, os
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z/'
with fs.open(P+'sst_20100601.nc','rb') as f:
    d=xr.open_dataset(f,engine='h5netcdf').load()
lat=d.latitude.values; lon=d.longitude.values
ilat=np.where((lat>=57.13-1e-4)&(lat<=58.33+1e-4))[0]; ilon=np.where((lon>=22.79-1e-4)&(lon<=23.99+1e-4))[0]
start=dt.date(1991,12,27); end=dt.date(2003,1,5)
days=[start+dt.timedelta(i) for i in range((end-start).days+1)]
tstart=dt.date(2010,6,1); tend=dt.date(2010,8,31)
tdays=[tstart+dt.timedelta(i) for i in range((tend-tstart).days+1)]
alld=days+tdays
def get(date):
    s=date.strftime('%Y%m%d')
    with fs.open(P+f'sst_{s}.nc','rb') as f:
        x=xr.open_dataset(f,engine='h5netcdf')
        v=x.analysed_sst.values[0][np.ix_(ilat,ilon)].astype(np.float64)
        x.close()
    return v
with ThreadPoolExecutor(16) as ex:
    res=list(ex.map(get,alld))
arr=np.stack(res)
print(arr.shape, np.isnan(arr).mean())
np.savez('/tmp/sst_region.npz', arr=arr, days=np.array([x.isoformat() for x in alld]), lat=lat[ilat], lon=lon[ilon])
print(np.nanmin(arr), np.nanmax(arr))