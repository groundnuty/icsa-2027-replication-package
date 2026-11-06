import fsspec,xarray as xr,pandas as pd,numpy as np,os,time
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
B='icsa2027_data_20261101T090944Z/s1z/'
dates=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2012-06-01','2012-08-31'))
os.makedirs('/work/c',exist_ok=True)
def get(d):
    out=f'/work/c/{d:%Y%m%d}.npz'
    if os.path.exists(out): return 'ok'
    for t in range(3):
        try:
            tmp=f'/work/t_{d:%Y%m%d}.nc'
            fs.get(B+f'sst_{d:%Y%m%d}.nc',tmp)
            x=xr.open_dataset(tmp,engine='h5netcdf')
            x=x.sel(latitude=slice(54.449,55.651),longitude=slice(16.049,17.251))
            np.savez(out,v=x.analysed_sst.values[0].astype('float64'),la=x.latitude.values,lo=x.longitude.values)
            x.close();os.remove(tmp);return 'ok'
        except Exception as e: err=str(e)
    return d.strftime('%Y%m%d')+err[:80]
t=time.time()
with ThreadPoolExecutor(16) as ex: r=list(ex.map(get,dates))
print(time.time()-t,[x for x in r if x!='ok'][:10])