import fsspec, time
import numpy as np
import h5py
fs = fsspec.filesystem('onedata')
f = fs.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
t0 = time.time()
with h5py.File(f, 'r') as h:
    var = h['analysed_sst']
    print("open time:", time.time()-t0)
    t1 = time.time()
    n = 0
    acc = 0.0
    for i in range(30):
        d = var[i]  # one day, full grid
        acc += float(np.nanmean(d[300:320, 480:500]))
        n += 1
    dt = time.time() - t1
    print("30 chunks in", dt, "s ->", dt/n*1000, "ms/chunk, approx", 3.79e9/(n/(dt)) / 3.79e9 * 1, )
    print("est total time for 4120 chunks: min", 4120*dt/30/60, "max (with overhead)")
    print("sample mean ok:", np.isfinite(acc))
