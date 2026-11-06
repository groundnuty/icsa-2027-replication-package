import h5py, numpy as np, time
from concurrent.futures import ThreadPoolExecutor
y0, y1, x0, x1 = 32, 92, 284, 344
def read(pth):
    with h5py.File(pth,'r') as f:
        return f['analysed_sst'][0, y0:y1, x0:x1]
base='/data/icsa2027_data_20261101T090944Z/s1z/sst_%04d%02d%02d.nc'
paths=[]
import datetime as dt
d=dt.date(1992,6,1)
for i in range(40):
    paths.append(base%(d.year,d.month,d.day)); d+=dt.timedelta(days=1)
t0=time.time(); a=read(paths[0]); print('first read', time.time()-t0)
t0=time.time()
for p in paths: read(p)
print('seq per-file', (time.time()-t0)/40)
t0=time.time()
for p in paths: read(p)
print('seq again per-file', (time.time()-t0)/40)
t0=time.time()
with ThreadPoolExecutor(8) as ex:
    list(ex.map(read, paths))
print('threads8 per-file', (time.time()-t0)/40)
# check time coord of a file
import xarray as xr
for p in [paths[0], '/data/icsa2027_data_20261101T090944Z/s1z/sst_20021231.nc']:
    ds=xr.open_dataset(p, engine='h5netcdf')
    print(p.split('/')[-1], ds.time.values, ds.analysed_sst.shape)
    ds.close()
