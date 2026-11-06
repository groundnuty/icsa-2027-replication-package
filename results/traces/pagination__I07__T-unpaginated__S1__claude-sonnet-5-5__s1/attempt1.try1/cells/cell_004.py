import numpy as np, os
from concurrent.futures import ThreadPoolExecutor
idx={d:f for d,f in zip(alld,fl)}
def load(day):
    f=idx[day]
    for t in range(4):
        try:
            with xr.open_dataset(fs.open(f,'rb'),engine='h5netcdf') as d:
                a=d.analysed_sst.sel(latitude=slice(54.449,55.651),longitude=slice(16.049,17.251)).isel(time=0).load()
                return a
        except Exception as e: err=e
    raise err
days=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2021-06-01','2021-08-31'))
with ThreadPoolExecutor(16) as ex: arrs=list(ex.map(load,days))
print(arrs[0].shape,arrs[0].latitude.values[[0,-1]],arrs[0].longitude.values[[0,-1]],np.nanmean(arrs[0]))
import pickle;pickle.dump((days,[a.values for a in arrs],arrs[0].latitude.values,arrs[0].longitude.values),open('/tmp/d.pkl','wb'))