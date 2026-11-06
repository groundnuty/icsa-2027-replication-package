import os, time, numpy as np, h5py, multiprocessing as mp, datetime as dt
DIR = '/data/icsa2027_data_20261101T090944Z/s1z'
files = sorted(os.listdir(DIR))
fdates = {f: dt.date(int(f[4:8]), int(f[8:10]), int(f[10:12])) for f in files}

d0 = dt.date(1991,12,27); d1 = dt.date(2003,1,5)
t0d = dt.date(2009,6,1); t1d = dt.date(2009,8,31)
need = [f for f,d in fdates.items() if (d0 <= d <= d1) or (t0d <= d <= t1d)]
need.sort()
print('needed files:', len(need))

def worker(args):
    names, = args
    out = np.empty((len(names), 60, 60), dtype='float32')
    for i, name in enumerate(names):
        with h5py.File(os.path.join(DIR, name), 'r') as f:
            out[i] = f['analysed_sst'][0, 130:190, 78:138]
    return out

chunks = [need[i::16] for i in range(16)]
t0 = time.time()
with mp.Pool(16) as pool:
    res = pool.map(worker, [(c,) for c in chunks])
data = np.empty((len(need), 60, 60), dtype='float32')
for i, r in enumerate(res):
    data[i::16] = r
print(f'loaded in {time.time()-t0:.1f}s', data.shape)

dates = np.array([fdates[f] for f in need], dtype='datetime64[D]')
np.save('/tmp/dates.npy', dates)
np.save('/tmp/sst_needed.npy', data)
print('saved. finite frac:', np.isfinite(data).mean().round(4))
