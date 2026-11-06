import fsspec, io, time, numpy as np, h5py
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'
import datetime as dt
d0 = dt.date(1992,6,1)
dates = [(d0+dt.timedelta(days=i)).strftime('%Y%m%d') for i in range(48)]
paths = [f'{base}/sst_{d}.nc' for d in dates]

# Strategy 1: fs.cat batches of 16, then h5py decode (sequential decode)
t0=time.time()
tot_bytes=0
for i in range(0, 48, 16):
    data = fs.cat(paths[i:i+16])
    for p, b in data.items():
        f = h5py.File(io.BytesIO(b),'r')
        arr = f['analysed_sst'][0, 217:277, 421:481]
        f.close()
        tot_bytes += len(b)
t1=time.time()
print('batched cat+decode 48 files:', round(t1-t0,2), 's')

# Strategy 2: ThreadPoolExecutor(8), each: fs.cat one path + h5py decode
def load(p):
    b = fs.cat(p)[p]
    f = h5py.File(io.BytesIO(b),'r')
    arr = f['analysed_sst'][0, 217:277, 421:481]
    f.close()
    return arr
t2=time.time()
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(load, paths))
t3=time.time()
print('threaded 48 files:', round(t3-t2,2), 's')
