import h5py, numpy as np, time, os
from concurrent.futures import ProcessPoolExecutor

base = "/data/icsa2027_data_20261101T090944Z/s1z"

def read_pair(args):
    path, i0, i1, j0, j1 = args
    with h5py.File(path, "r") as f:
        return f["analysed_sst"][0, i0:i1, j0:j1]

# full baseline window files
files = [f"{base}/sst_{y}{m:02d}{d:02d}.nc" for y in [1991,2003] for m,d in [(12,27),(1,5)]]
# rough: all 1991-12-27..2003-01-05 = 4028 files
import datetime as dtm
d = dtm.date(1991,12,27); end = dtm.date(2003,1,5)
files = []
while d <= end:
    files.append(f"{base}/sst_{d:%Y%m%d}.nc"); d += dtm.timedelta(days=1)
print(len(files), "files")
args = [(f, 435, 495, 485, 545) for f in files]
t0 = time.time()
with ProcessPoolExecutor(max_workers=16) as ex:
    chunks = list(ex.map(read_pair, args, chunksize=8))
t1 = time.time()
print("read all baseline-window files, 16 procs:", round(t1-t0,1), "s")
arr = np.stack(chunks)  # (4028, 60, 60) float32
print(arr.shape, arr.dtype, "NaN frac:", np.isnan(arr).mean())
np.save("/work/baseline_region_f32.npy", arr)
print("saved npy; size MB:", os.path.getsize("/work/baseline_region_f32.npy")/1e6)
