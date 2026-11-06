import os, time, h5py, numpy as np
print('cpus:', os.cpu_count())
d = '/data/icsa2027_data_20261101T090944Z/s1z'
# timing test: 12 sequential reads
t0 = time.time()
for date in ['20030810','20030811','20030812','20030813','20030814','20030815','20030816','20030817','20030818','20030819','20030820','20030821']:
    with h5py.File(f'{d}/sst_{date}.nc','r') as f:
        a = f['analysed_sst'][0, 196:256, 485:545]
        tm = f['time'][:]
t1 = time.time()
print('12 reads in', t1-t0, 's ->', (t1-t0)/12, 's/file')
print('time vals:', tm)
