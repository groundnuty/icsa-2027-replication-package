code='''
import fsspec,pandas as pd,numpy as np,xarray as xr,os,time
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata');p='icsa2027_data_20261101T090944Z/s1z'
def get(dt):
    s=dt.strftime('%Y%m%d');fn=f'cache/{s}.npy'
    if os.path.exists(fn):return s,True
    for a in range(4):
        try:
            with fs.open(f'{p}/sst_{s}.nc','rb') as f:
                d=xr.open_dataset(f,engine='h5netcdf')
                d=d.sel(latitude=slice(56.62,57.84),longitude=slice(20.22,21.44))
                np.save(fn,d.analysed_sst.values[0])
            return s,True
        except Exception as e: err=e
    return s,str(err)
ds=list(pd.date_range('1991-12-27','2003-01-05'))+list(pd.date_range('2010-06-01','2010-08-31'))
t=time.time()
with ThreadPoolExecutor(16) as ex: r=list(ex.map(get,ds))
print(time.time()-t,[x for x in r if x[1]!=True][:3],len(os.listdir('cache')))
'''
open('dl.py','w').write(code)
import subprocess
print(subprocess.run(['python','dl.py'],capture_output=True,text=True))