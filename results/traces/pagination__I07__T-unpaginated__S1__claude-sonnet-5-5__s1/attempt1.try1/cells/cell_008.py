import fsspec,re,xarray as xr,pandas as pd,numpy as np,pickle
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
fl=sorted(fs.find('icsa2027_data_20261101T090944Z/s1z'))
idx={re.search(r'sst_(\d{8})',f).group(1):f for f in fl}
have=pd.to_datetime(list(idx),format='%Y%m%d')
m=pd.date_range('1982-01-01','2023-12-31').difference(have);print(len(idx),len(m),m[:10])
def load(day):
    f=idx[day.strftime('%Y%m%d')]
    for t in range(4):
        try:
            with xr.open_dataset(fs.open(f,'rb'),engine='h5netcdf') as d:
                return d.analysed_sst.sel(latitude=slice(54.449,55.651),longitude=slice(16.049,17.251)).isel(time=0).load()
        except Exception as e: err=e
    raise err
days=[d for d in list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2021-06-01','2021-08-31')) if d.strftime('%Y%m%d') in idx]
print(len(days))
with ThreadPoolExecutor(16) as ex: arrs=list(ex.map(load,days))
print(arrs[0].shape,arrs[0].latitude.values[[0,-1]],arrs[0].longitude.values[[0,-1]],np.nanmean(arrs[0]))
pickle.dump((days,[a.values for a in arrs],arrs[0].latitude.values,arrs[0].longitude.values),open('/tmp/d.pkl','wb'))