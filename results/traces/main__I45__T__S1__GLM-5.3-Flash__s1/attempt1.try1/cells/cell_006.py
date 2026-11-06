import fsspec, h5py, numpy as np, time, os
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z'
i0,i1,j0,j1 = 491,550,616,675

# check time units + decode
with fs.open(f'{base}/sst_20090615.nc','rb') as f:
    with h5py.File(f,'r') as hf:
        print('time attrs:', dict(hf['time'].attrs))
        print('time value:', hf['time'][0])

def read_one(ds_):
    with fs.open(f'{base}/sst_{ds_}.nc','rb') as f:
        with h5py.File(f,'r') as hf:
            sub = hf['analysed_sst'][0, i0:i1+1, j0:j1+1]
            t = int(hf['time'][0])
    return sub, t

dates = [f'2009-06-{d:02d}' for d in range(1,16)]
t0=time.time()
for d in dates:
    sub,t = read_one(d.replace('-',''))
print('sequential 15 files:', round(time.time()-t0,2),'s')

from concurrent.futures import ThreadPoolExecutor
dates2 = ['2009-07-'+f'{d:02d}' for d in range(1,21)]
t0=time.time()
with ThreadPoolExecutor(8) as ex:
    res = list(ex.map(lambda ds_: read_one(ds_.replace('-','')), dates2))
print('threaded(8) 20 files:', round(time.time()-t0,2),'s')
subs = np.stack([r[0] for r in res]); ts = np.array([r[1] for r in res])
print('shape', subs.shape, 'finite frac', np.isfinite(subs).mean())
import pandas as pd
print('decoded times ok:', all(pd.Timestamp(t, unit='s').strftime('%Y%m%d')==ds_.replace('-','') for t,ds_ in zip(ts,dates2)))
