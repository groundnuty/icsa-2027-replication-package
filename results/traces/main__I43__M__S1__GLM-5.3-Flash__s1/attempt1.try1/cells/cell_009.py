import h5py, numpy as np, time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

DIR='/data/icsa2027_data_20261101T090944Z/s1z'
ILAT=slice(438,498); ILON=slice(487,547)

def load(fn):
    with h5py.File(f'{DIR}/sst_{fn}.nc','r') as f:
        return f['analysed_sst'][0, ILAT, ILON]

# test: verify filename date == time value for a sample
import datetime as dt
for fn in ['19820101','20170601','20231231','20000229']:
    with h5py.File(f'{DIR}/sst_{fn}.nc','r') as f:
        t = f['time'][:][0]
        units = f['time'].attrs['units']
    assert units == b'seconds since 1981-01-01', units
    d = dt.datetime(1981,1,1) + dt.timedelta(seconds=int(t))
    assert d.strftime('%Y%m%d') == fn, (fn, d)
print('filename<->time consistency OK (incl. 2000-02-29 leap day present)')

d0, d1 = date(1991,12,27), date(2003,1,5)
ndates = (d1-d0).days + 1
print('baseline-load range days:', ndates)

fns = [(d0+timedelta(days=i)).strftime('%Y%m%d') for i in range(120)]
t0=time.time()
with ThreadPoolExecutor(8) as ex:
    arrs = list(ex.map(load, fns))
print('120 files, 8 threads:', round(time.time()-t0,2), 's')
t0=time.time()
with ThreadPoolExecutor(16) as ex:
    arrs = list(ex.map(load, fns))
print('120 files, 16 threads:', round(time.time()-t0,2), 's')
arr = np.stack(arrs)
print(arr.shape, arr.dtype, 'nan frac', np.isnan(arr).mean())
