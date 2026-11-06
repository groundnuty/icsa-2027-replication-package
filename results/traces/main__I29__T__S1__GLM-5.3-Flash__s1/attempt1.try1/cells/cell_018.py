import fsspec, h5py, numpy as np, time
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'
def reader(args):
    idx, p = args
    f = fs.open(p,'rb')
    with h5py.File(f,'r') as h:
        arr = h['analysed_sst'][0, 218:278, 601:661]
    f.close()
    return idx, np.ascontiguousarray(arr)
sub = [(i, base+'sst_1992%02d%02d.nc'%(1+i//28,1+i%28)) for i in range(100)]
t0=time.time()
res={}
with ThreadPoolExecutor(max_workers=4) as ex:
    for idx, arr in ex.map(reader, sub):
        res[idx]=arr
t1=time.time()
print('100 files, 4 threads:', t1-t0, 'per file', (t1-t0)/100)
