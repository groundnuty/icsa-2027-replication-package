import numpy as np
from concurrent.futures import ThreadPoolExecutor
def load(s):
    for _ in range(4):
        try:
            with xr.open_dataset(fs.open(f'{p}/sst_{s}.nc','rb'),engine='h5netcdf') as d:
                a=d.analysed_sst.sel(latitude=slice(57.85-1e-4,59.05+1e-4),longitude=slice(21.01-1e-4,22.21+1e-4)).load()
                return a
        except Exception as e: err=e
    raise err
a=load('20130601');print(a.shape,a.latitude.values,a.longitude.values,a.dtype,float(a.max()))
dates=list(pd.date_range('1991-12-27','2003-01-05').strftime('%Y%m%d'))+list(pd.date_range('2013-06-01','2013-08-31').strftime('%Y%m%d'))
with ThreadPoolExecutor(16) as ex: arrs=list(ex.map(load,dates))
print(len(arrs))