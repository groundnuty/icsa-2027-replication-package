import fsspec, h5py, numpy as np, time
fs = fsspec.filesystem('onedata')
base = 'icsa2027_data_20261101T090944Z/s1z'

def load(d):
    with fs.open(f'{base}/sst_{d}.nc','rb') as f:
        with h5py.File(f,'r') as h:
            return h

with fs.open(f'{base}/sst_19920101.nc','rb') as f:
    with h5py.File(f,'r') as h:
        def show(name, obj):
            if isinstance(obj, h5py.Dataset):
                print(name, obj.shape, obj.dtype)
        h.visititems(show)

t0=time.time()
import concurrent.futures as cf
dates = ['19920101','19920615','19961231','20000601','20021231','20220601','20220831']
def read_region(d, i0,i1,j0,j1):
    with fs.open(f'{base}/sst_{d}.nc','rb') as f:
        with h5py.File(f,'r') as h:
            return d, h['analysed_sst'][0, i0:i1+1, j0:j1+1].astype(np.float64)

i0,i1,j0,j1 = 66,125,531,590
with cf.ThreadPoolExecutor(16) as ex:
    res = list(ex.map(lambda d: read_region(d,i0,i1,j0,j1), dates))
print('7 files parallel secs:', time.time()-t0)
for d,v in res:
    print(d, v.shape, np.isfinite(v).mean().round(3), v.dtype)
