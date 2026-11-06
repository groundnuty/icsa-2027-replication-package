import fsspec, os, numpy as np, xarray as xr, pandas as pd, time
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
dates=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2004-06-01','2004-08-31'))
os.makedirs('/work/d',exist_ok=True)
def get(d):
    s=d.strftime('%Y%m%d'); loc=f'/work/d/sst_{s}.nc'
    if not os.path.exists(loc):
        fs.get(f'icsa2027_data_20261101T090944Z/s1z/sst_{s}.nc',loc)
    with xr.open_dataset(loc,engine='h5netcdf') as ds:
        lat=ds.latitude.values; lon=ds.longitude.values
        il=np.where((lat>=54.13-1e-4)&(lat<=55.33+1e-4))[0]
        jl=np.where((lon>=14.67-1e-4)&(lon<=15.87+1e-4))[0]
        v=ds.analysed_sst.isel(latitude=il,longitude=jl).values.astype(np.float64)
        return v, lat[il], lon[jl], str(ds.time.values[0])[:10]
t=time.time()
with ThreadPoolExecutor(8) as ex:
    res=list(ex.map(get,dates))
print(time.time()-t, len(res))
print(res[0][1].min(),res[0][1].max(),res[0][2].min(),res[0][2].max(), res[0][0].shape)
print(all(r[3]==d.strftime('%Y-%m-%d') for r,d in zip(res,dates)))