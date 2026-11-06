import time, numpy as np, h5py, os
from concurrent.futures import ProcessPoolExecutor
D='/data/icsa2027_data_20261101T090944Z/s1z'
import datetime as dt
# baseline needed: 1991-12-27 .. 2003-01-05
files=[]
d=dt.date(1991,12,27); end=dt.date(2003,1,5)
while d<=end:
    files.append(f'sst_{d:%Y%m%d}.nc'); d+=dt.timedelta(days=1)
print("baseline files:", len(files), files[0], files[-1])
missing=[f for f in files if not os.path.exists(os.path.join(D,f))]
print("missing:", len(missing))

def rd(fn):
    with h5py.File(os.path.join(D,fn),'r') as f:
        a=f['analysed_sst'][0,34:94,213:273].astype(np.float32)
    return fn, a

t0=time.time()
res={}
with ProcessPoolExecutor(max_workers=16) as ex:
    for fn,a in ex.map(rd, files[:400], chunksize=8):
        res[fn]=a
t1=time.time()
print(f"400 files in {t1-t0:.1f}s -> rate {400/(t1-t0):.1f} files/s; est full {len(files)} files: {len(files)*((t1-t0)/400):.0f}s")
arr=np.stack([res[f] for f in files[:400]])
print(arr.shape, np.isfinite(arr).mean())
