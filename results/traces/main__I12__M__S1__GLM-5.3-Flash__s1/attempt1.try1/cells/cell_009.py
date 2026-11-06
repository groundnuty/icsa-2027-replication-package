import os, time, numpy as np, h5py, multiprocessing as mp
DIR = '/data/icsa2027_data_20261101T090944Z/s1z'
files = sorted(os.listdir(DIR))

def worker(args):
    names, = args
    out = np.empty((len(names), 60, 60), dtype='float32')
    for i, name in enumerate(names):
        with h5py.File(os.path.join(DIR, name), 'r') as f:
            out[i] = f['analysed_sst'][0, 130:190, 78:138]
    return out

chunks = [files[i::16] for i in range(16)]
t0 = time.time()
with mp.Pool(16) as pool:
    res = pool.map(worker, [(c,) for c in chunks])
data = np.empty((len(files), 60, 60), dtype='float32')
for i, r in enumerate(res):
    data[i::16] = r
dt = time.time() - t0
print(f'{len(files)} files in {dt:.1f}s; finite frac {np.isfinite(data).mean():.4f}')
print('overall min/max:', np.nanmin(data).round(3), np.nanmax(data).round(3))
