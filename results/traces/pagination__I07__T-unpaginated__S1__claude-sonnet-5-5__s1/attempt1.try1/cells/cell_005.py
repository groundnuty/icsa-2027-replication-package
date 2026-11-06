import fsspec,re,xarray as xr,pandas as pd,numpy as np,pickle
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
fl=sorted(fs.find(p))
alld=pd.to_datetime([re.search(r'(\d{8})',f).group(1) for f in fl],format='%Y%m%d')
idx=dict(zip(alld,fl))
def load(day):
    f=idx[pd.Timestamp(day)]
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
pickle.dump((days,[a.values for a in arrs],arrs[0].latitude.values,arrs[0].longitude.values),open('/tmp/d.pkl','wb'))