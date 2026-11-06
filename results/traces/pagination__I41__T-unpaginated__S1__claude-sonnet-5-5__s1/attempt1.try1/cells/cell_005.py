code=r'''
import fsspec, xarray as xr, numpy as np, pandas as pd, pickle
from concurrent.futures import ThreadPoolExecutor
fs=fsspec.filesystem('onedata')
p='icsa2027_data_20261101T090944Z/s1z'
need=pd.date_range('1991-12-27','2003-01-05').append(pd.date_range('2021-06-01','2021-08-31'))
def load(d):
    for t in range(5):
        try:
            with xr.open_dataset(fs.open(f"{p}/sst_{d:%Y%m%d}.nc",'rb'),engine='h5netcdf') as x:
                la=x.latitude.values; lo=x.longitude.values
                i=np.where((la>=61.57-1e-4)&(la<=62.77+1e-4))[0]; j=np.where((lo>=20.17-1e-4)&(lo<=21.37+1e-4))[0]
                v=x.analysed_sst.values[0][i[0]:i[-1]+1,j[0]:j[-1]+1].astype('float64')
                return v,la[i[0]:i[-1]+1],lo[j[0]:j[-1]+1]
        except Exception as e: err=e
    raise err
with ThreadPoolExecutor(16) as ex: res=list(ex.map(load,need))
la,lo=res[0][1],res[0][2]
assert all((r[1]==la).all() and (r[2]==lo).all() for r in res)
data=np.stack([r[0] for r in res])
pickle.dump((need,data,la,lo),open('/tmp/c.pkl','wb'))
print(data.shape,la,lo,np.nanmin(data),np.nanmax(data))
'''
open('/tmp/l.py','w').write(code)
import subprocess
r=subprocess.run(['python','/tmp/l.py'],capture_output=True,text=True);print(r.stdout[-3000:],r.stderr[-2000:])