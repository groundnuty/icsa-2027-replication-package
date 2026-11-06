import h5py, numpy as np, time
from concurrent.futures import ThreadPoolExecutor
DIR='/data/icsa2027_data_20261101T090944Z/s1z'
fns = [f'1992{str(m+1).zfill(2)}01' for m in range(12)]
def load_region(fn):
    with h5py.File(f'{DIR}/sst_{fn}.nc','r') as f:
        return f['analysed_sst'][0, 438:498, 487:547]
def load_full(fn):
    with h5py.File(f'{DIR}/sst_{fn}.nc','r') as f:
        return f['analysed_sst'][0]
t0=time.time()
with ThreadPoolExecutor(16) as ex: A=list(ex.map(load_region, fns))
print('region reads, 12 files:', round(time.time()-t0,2))
t0=time.time()
with ThreadPoolExecutor(16) as ex: B=list(ex.map(load_full, fns))
print('full-grid reads, 12 files:', round(time.time()-t0,2))
# decode-then-subset timing (whole grid into numpy, then subset)
def load_full_decode(fn):
    with h5py.File(f'{DIR}/sst_{fn}.nc','r') as f:
        a = f['analysed_sst'][0].astype('float32')
    return a[438:498, 487:547]
t0=time.time()
with ThreadPoolExecutor(16) as ex: C=list(ex.map(load_full_decode, fns))
print('full-decode subset, 12 files:', round(time.time()-t0,2))
print('region==full-decode-subset:', np.array_equal(np.nan_to_num(A[0],nan=-1), np.nan_to_num(C[0],nan=-1)))
