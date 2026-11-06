import fsspec,xarray as xr,os,pandas as pd,numpy as np
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z/'
os.makedirs('/work/d',exist_ok=True)
days=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2007-06-01','2007-08-31'))
def get(t):
    n=f"sst_{t:%Y%m%d}.nc"; out=f'/work/d/{n}'
    if os.path.exists(out+'.npy'): return t,'ok'
    try:
        fs.get(P+n,out)
        ds=xr.open_dataset(out,engine='h5netcdf')
        s=ds.analysed_sst.sel(latitude=slice(59.92,61.14),longitude=slice(18.68,19.90)).load()
        np.save(out+'.npy',s.values[0]); 
        np.save('/work/lat.npy',s.latitude.values);np.save('/work/lon.npy',s.longitude.values)
        ds.close(); os.remove(out); return t,'ok'
    except Exception as e: return t,repr(e)[:80]
with ThreadPoolExecutor(16) as ex: res=list(ex.map(get,days))
bad=[r for r in res if r[1]!='ok'];print(len(bad),bad[:5])