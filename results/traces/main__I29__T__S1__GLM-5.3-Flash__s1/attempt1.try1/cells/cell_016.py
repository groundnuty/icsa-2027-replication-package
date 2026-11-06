import fsspec, h5py, numpy as np, time, datetime
from concurrent.futures import ThreadPoolExecutor
fs = fsspec.filesystem('onedata')
base='icsa2027_data_20261101T090944Z/s1z/'

start = datetime.date(1982,1,1); end = datetime.date(2019,12,31)
dates = [start+datetime.timedelta(days=k) for k in range((end-start).days+1)]
paths = [base+'sst_%04d%02d%02d.nc'%(d.year,d.month,d.day) for d in dates]

def reader(args):
    idx, p = args
    f = fs.open(p,'rb')
    with h5py.File(f,'r') as h:
        arr = h['analysed_sst'][0, 218:278, 601:661]
    f.close()
    return idx, np.ascontiguousarray(arr)

# test with 20 files and 8 threads
t0=time.time()
sub = [(i,paths[i]) for i in range(0,20)]
res = {}
with ThreadPoolExecutor(max_workers=8) as ex:
    for idx, arr in ex.map(reader, sub):
        res[idx]=arr
t1=time.time()
print('20 files, 8 threads:', t1-t0)
print('shape', res[0].shape, res[0].dtype)
