import os, time, h5py, numpy as np
from concurrent.futures import ProcessPoolExecutor
print("cpus:", os.cpu_count())
d = "/data/icsa2027_data_20261101T090944Z/s1z"
i0,i1,j0,j1 = 196,256,485,545
def work(s):
    with h5py.File(f"{d}/sst_{s}.nc","r") as f:
        return s, f["analysed_sst"][0, i0:i1, j0:j1][:].astype(np.float64)
import datetime as dt
def rng(a,b):
    t=a
    while t<=b:
        yield t.strftime("%Y%m%d")
        t+=dt.timedelta(days=1)
sample = list(rng(dt.date(1992,1,1), dt.date(1992,3,31)))
t0=time.time()
with ProcessPoolExecutor(max_workers=8) as ex:
    res = list(ex.map(work, sample, chunksize=8))
t1=time.time()
print(f"{len(sample)} files in {t1-t0:.1f}s -> {len(sample)/(t1-t0):.1f} files/s")
print("ext total estimate min:", 4121/(len(sample)/(t1-t0))/60)
