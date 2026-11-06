import h5py, numpy as np, time, os
from concurrent.futures import ProcessPoolExecutor

base = "/data/icsa2027_data_20261101T090944Z/s1z"

def read_slice(path, i0, i1, j0, j1):
    with h5py.File(path, "r") as f:
        return f["analysed_sst"][0, i0:i1, j0:j1]

def read_pair(args):
    path, i0, i1, j0, j1 = args
    with h5py.File(path, "r") as f:
        return f["analysed_sst"][0, i0:i1, j0:j1]

files = [f"{base}/sst_199206{k:02d}.nc" for k in range(1, 31)]
args = [(f, 435, 495, 485, 545) for f in files]

t0 = time.time()
with ProcessPoolExecutor(max_workers=4) as ex:
    res = list(ex.map(read_pair, args))
t1 = time.time()
print("30 files, 4 procs:", round(t1-t0, 2), "s")
res = np.stack(res)
print("shape", res.shape, "NaN frac", np.isnan(res).mean())

t0 = time.time()
for f in files:
    read_slice(f, 435, 495, 485, 545)
t1 = time.time()
print("30 files, serial:", round(t1-t0, 2), "s")
print("cpus:", os.cpu_count())
