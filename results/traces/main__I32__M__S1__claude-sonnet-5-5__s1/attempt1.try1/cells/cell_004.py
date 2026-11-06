import xarray as xr, numpy as np, pandas as pd, os
from concurrent.futures import ThreadPoolExecutor
d='/data/icsa2027_data_20261101T090944Z/s1z'
dates=pd.date_range('1991-12-27','2003-01-05').append(pd.date_range('2005-06-01','2005-08-31'))
miss=[x for x in dates if not os.path.exists(f'{d}/sst_{x:%Y%m%d}.nc')];print(len(miss),miss[:10])
def ld(x):
    p=f'{d}/sst_{x:%Y%m%d}.nc'
    if not os.path.exists(p):return None
    with xr.open_dataset(p,engine='h5netcdf') as s:
        s=s.sel(latitude=slice(59.04,60.26),longitude=slice(21.24,22.46))
        return s.analysed_sst.values[0].astype('float64'),s.latitude.values,s.longitude.values
with ThreadPoolExecutor(16) as ex: R=list(ex.map(ld,dates))
ok=[r for r in R if r][0];print(ok[0].shape,ok[1][[0,-1]],ok[2][[0,-1]])
import pickle;pickle.dump((dates,R),open('/tmp/r.pkl','wb'))