script = r'''
import fsspec, os, numpy as np, xarray as xr, datetime as dt
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
os.makedirs('/work/cache',exist_ok=True)
# date list: 1991-12-27 .. 2003-01-05 and 2021-06-01 .. 2021-08-31
days=[]
d=dt.date(1991,12,27)
while d<=dt.date(2003,1,5): days.append(d); d+=dt.timedelta(1)
d=dt.date(2021,6,1)
while d<=dt.date(2021,8,31): days.append(d); d+=dt.timedelta(1)
# grid indices from a reference file
fs.get(base+'sst_20210601.nc','/work/ref.nc')
r=xr.open_dataset('/work/ref.nc',engine='h5netcdf')
lat=r.latitude.values.astype(float); lon=r.longitude.values.astype(float)
ilat=np.where((lat>=54.39-1e-6)&(lat<=55.59+1e-6))[0]
ilon=np.where((lon>=18.25-1e-6)&(lon<=19.45+1e-6))[0]
print('lat idx',ilat[0],ilat[-1],len(ilat),'lon idx',ilon[0],ilon[-1],len(ilon))
print('lat vals',lat[ilat[0]],lat[ilat[-1]],'lon vals',lon[ilon[0]],lon[ilon[-1]])
np.savez('/work/grid.npz',lat=lat[ilat],lon=lon[ilon],ilat=ilat,ilon=ilon)
def get(day):
    s=day.strftime('%Y%m%d')
    out=f'/work/cache/{s}.npy'
    if os.path.exists(out): return
    loc=f'/work/cache/{s}.nc'
    fs.get(base+f'sst_{s}.nc',loc)
    with xr.open_dataset(loc,engine='h5netcdf') as ds:
        v=ds.analysed_sst.isel(time=0).values[ilat[0]:ilat[-1]+1, ilon[0]:ilon[-1]+1].astype(np.float32)
        t=ds.time.values[0]
    np.save(out,v)
    os.remove(loc)
with ThreadPoolExecutor(16) as ex:
    list(ex.map(get,days))
print('done',len(days))
'''
open('/work/fetch.py','w').write(script)
import subprocess
p=subprocess.run(['python','/work/fetch.py'],capture_output=True,text=True,timeout=3000)
print(p.stdout[-3000:], p.stderr[-3000:])