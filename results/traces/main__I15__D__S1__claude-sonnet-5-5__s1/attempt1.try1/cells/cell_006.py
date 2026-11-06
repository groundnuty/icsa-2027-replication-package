import fsspec,os,pandas as pd,xarray as xr,numpy as np
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
P='icsa2027_data_20261101T090944Z/s1z/'
os.makedirs('/work/d',exist_ok=True)
days=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2019-06-01','2019-08-31'))
def get(t):
    s=t.strftime('%Y%m%d'); out=f'/work/d/{s}.npy'
    if os.path.exists(out): return s,'ok'
    try:
        loc=f'/work/d/{s}.nc'
        fs.get(P+f'sst_{s}.nc',loc)
        a=xr.open_dataset(loc,engine='h5netcdf')
        b=a.sel(latitude=slice(56.12,57.34),longitude=slice(17.70,18.92))
        np.save(out,b.analysed_sst.values[0].astype('float64'))
        if s=='20190601':
            np.save('/work/lat.npy',b.latitude.values);np.save('/work/lon.npy',b.longitude.values)
        a.close();os.remove(loc);return s,'ok'
    except Exception as e: return s,repr(e)[:80]
with ThreadPoolExecutor(16) as ex: r=list(ex.map(get,days))
bad=[x for x in r if x[1]!='ok'];print(len(r),len(bad),bad[:5])