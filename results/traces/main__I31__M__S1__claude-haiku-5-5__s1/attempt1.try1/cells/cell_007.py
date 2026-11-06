script=r'''
import xarray as xr, numpy as np, pandas as pd
P='/data/icsa2027_data_20261101T090944Z/s1z/'
d=xr.open_dataset(P+'sst_19820101.nc',engine='h5netcdf')
lat=d.latitude.values; lon=d.longitude.values
li=np.where((lat>=58.69-1e-6)&(lat<=59.89+1e-6))[0]; lo=np.where((lon>=18.69-1e-6)&(lon<=19.89+1e-6))[0]
dates=pd.date_range('1991-12-27','2003-01-05').tolist()+pd.date_range('2017-06-01','2017-08-31').tolist()
out={}
for dt in dates:
    f=P+'sst_%s.nc'%dt.strftime('%Y%m%d')
    with xr.open_dataset(f,engine='h5netcdf') as x:
        out[dt.strftime('%Y-%m-%d')]=x.analysed_sst.values[0,li[0]:li[-1]+1,lo[0]:lo[-1]+1].astype(np.float64)
        if dt==dates[0]:
            la=x.latitude.values[li]; lo_=x.longitude.values[lo]
keys=sorted(out)
np.savez('/tmp/cache.npz',sst=np.stack([out[k] for k in keys]),dates=np.array(keys),lat=la,lon=lo_)
print('done',len(keys))
'''
open('/tmp/extract.py','w').write(script)
import subprocess
p=subprocess.Popen('nohup python /tmp/extract.py > /tmp/extract.log 2>&1 &',shell=True)
print('started')