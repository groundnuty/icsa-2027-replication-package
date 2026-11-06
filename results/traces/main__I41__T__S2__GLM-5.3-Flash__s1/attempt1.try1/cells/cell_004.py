import numpy as np, time, os

def worker_init():
    global FS, H5
    import fsspec, h5py
    FS = fsspec.filesystem('onedata')
    f = FS.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
    H5 = h5py.File(f, 'r')

def read_days(day_idxs):
    dset = H5['analysed_sst']
    out = np.empty((len(day_idxs), 60, 60), dtype=np.float32)
    for i, t in enumerate(day_idxs):
        out[i] = dset[t, 404:464, 559:619]
    return out

# serial timing
worker_init()
idxs = list(range(100, 140))
t0 = time.time(); arr = read_days(idxs); t1 = time.time()
print("serial 40 days: %.2f s -> %.3f s/day" % (t1-t0, (t1-t0)/40))
print("sample stats:", np.nanmean(arr), np.isfinite(arr).mean())

# multiprocessing timing
import multiprocessing as mp
N = 8
t0 = time.time()
with mp.Pool(N, initializer=worker_init) as pool:
    chunks = [list(range(1000+i*20, 1000+(i+1)*20)) for i in range(N)]
    res = pool.map(read_days, chunks)
t1 = time.time()
print("mp %d workers, 160 days total: %.2f s -> %.3f s/day" % (N, t1-t0, (t1-t0)/160))
print("shapes:", [r.shape for r in res[:2]])
