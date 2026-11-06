import os,glob,numpy as np,pandas as pd,xarray as xr
from concurrent.futures import ThreadPoolExecutor
base='/data/icsa2027_data_20261101T090944Z/s1z/sst_%s.nc'
def ld(day):
    f=base%day.strftime('%Y%m%d')
    if not os.path.exists(f): return None
    x=xr.open_dataset(f,engine='h5netcdf')
    x=x.sel(latitude=slice(58.685,59.895),longitude=slice(18.685,19.895))
    return x.analysed_sst.values[0].astype('float64'),x.latitude.values,x.longitude.values
days=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2010-06-01','2010-08-31'))
with ThreadPoolExecutor(16) as ex: res=list(ex.map(ld,days))
miss=[d for d,r in zip(days,res) if r is None];print(len(miss),miss[:5])
r0=[r for r in res if r][0];print(r0[0].shape,r0[1],r0[2],np.nanmean(r0[0]))
import pickle;pickle.dump((days,res),open('/tmp/c.pkl','wb'))