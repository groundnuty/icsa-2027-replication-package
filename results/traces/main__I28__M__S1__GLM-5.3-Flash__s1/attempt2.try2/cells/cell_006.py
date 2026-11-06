import numpy as np, h5py, time, os
from multiprocessing import Pool
base = "/data/icsa2027_data_20261101T090944Z/s1z"
import datetime as dt
files = [f"sst_{(dt.date(1995,1,1)+dt.timedelta(days=i)).strftime('%Y%m%d')}.nc" for i in range(48)]

def rd(fn):
    with h5py.File(os.path.join(base, fn), "r") as f:
        a = f["analysed_sst"][0, 218:278, 601:661]
    return np.isfinite(a).sum()

for nw in (1, 8, 16):
    t0=time.time()
    with Pool(nw) as pool:
        res = pool.map(rd, files)
    el=time.time()-t0
    print(f"workers={nw}: 48 files in {el:.2f}s -> {el/48*1000:.0f} ms/file, est 5862 files: {el/48*5862/60:.1f} min")
