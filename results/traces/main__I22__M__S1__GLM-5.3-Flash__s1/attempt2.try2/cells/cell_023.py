import os, time, numpy as np
from concurrent.futures import ThreadPoolExecutor
import h5py
print('pool_window.json exists from earlier call:', os.path.exists('/work/work/pool_window.json'))
d = '/data/icsa2027_data_20261101T090944Z/s1z'
# benchmark: parallel read of 16 files with threads
def read_sub(datestr):
    with h5py.File(f'{d}/sst_{datestr}.nc', 'r') as f:
        return f['analysed_sst'][0, 196:256, 485:545]
t0 = time.time()
with ThreadPoolExecutor(max_workers=16) as ex:
    res = list(ex.map(read_sub, [f'200307{dd:02d}' for dd in range(1, 17)]))
t1 = time.time()
print('16 files via 16 threads:', round(t1-t0, 2), 's')
t0 = time.time()
for dd in range(1, 9):
    read_sub(f'200307{dd:02d}')
t1 = time.time()
print('8 files sequential:', round(t1-t0, 2), 's ->', round((t1-t0)/8, 3), 's/file')
