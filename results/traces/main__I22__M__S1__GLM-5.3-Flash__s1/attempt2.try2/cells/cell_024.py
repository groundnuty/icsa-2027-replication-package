import os, time, numpy as np
from concurrent.futures import ThreadPoolExecutor
import h5py
d = '/data/icsa2027_data_20261101T090944Z/s1z'
def read_sub(datestr):
    with h5py.File(f'{d}/sst_{datestr}.nc', 'r') as f:
        return f['analysed_sst'][0, 196:256, 485:545]
# test higher concurrency: 48 files with 24 threads
dates = [f'200308{dd:02d}' for dd in range(1, 32)] + [f'200309{dd:02d}' for dd in range(1, 18)]
t0 = time.time()
with ThreadPoolExecutor(max_workers=24) as ex:
    res = list(ex.map(read_sub, dates))
t1 = time.time()
n = len(dates)
print(f'{n} files, 24 threads: {t1-t0:.2f} s -> {(t1-t0)/n*1000:.0f} ms/file, {n*2.63/(t1-t0):.1f} MB/s')
t0 = time.time()
res2 = [read_sub(x) for x in dates]
t1 = time.time()
print(f'{n} files sequential: {t1-t0:.2f} s -> {(t1-t0)/n*1000:.0f} ms/file, {n*2.63/(t1-t0):.1f} MB/s')
print('identical results:', all(np.array_equal(a, b) for a, b in zip(res, res2)))
