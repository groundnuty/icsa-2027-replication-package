import os, pickle, numpy as np, datetime as dt
from concurrent.futures import ProcessPoolExecutor
import h5py
D='/data/icsa2027_data_20261101T090944Z/s1z'

def rd(fn):
    with h5py.File(os.path.join(D,fn),'r') as f:
        return fn, f['analysed_sst'][0,34:94,213:273].astype(np.float32)

files=[]
d=dt.date(1991,12,27); end=dt.date(2003,1,5)
while d<=end:
    files.append(f'sst_{d:%Y%m%d}.nc'); d+=dt.timedelta(days=1)

t0=time.time()
res={}
with ProcessPoolExecutor(max_workers=24) as ex:
    for fn,a in ex.map(rd, files, chunksize=4):
        res[fn]=a
print(f"read {len(res)} files in {time.time()-t0:.1f}s")
data=np.stack([res[f] for f in files])  # (T,60,60) float32
print(data.shape, data.dtype, "finite frac:", np.isfinite(data).mean())
# sea-cell definition: finite on EVERY target day. Verify with a target read.
tfiles=[]
d=dt.date(2004,6,1); end=dt.date(2004,8,31)
while d<=end:
    tfiles.append(f'sst_{d:%Y%m%d}.nc'); d+=dt.timedelta(days=1)
print("target files:", len(tfiles), "missing:", sum(1 for f in tfiles if not os.path.exists(os.path.join(D,f))))
def rdt(fn):
    with h5py.File(os.path.join(D,fn),'r') as f:
        return fn, f['analysed_sst'][0,34:94,213:273].astype(np.float32)
tdata=np.stack([rdt(f)[1] for f in tfiles])
print("target:", tdata.shape, "finite frac:", np.isfinite(tdata).mean())
cells_finite_every_target_day=np.isfinite(tdata).all(axis=0)
print("sea cells:", cells_finite_every_target_day.sum(), "of", cells_finite_every_target_day.size)

with open('/tmp/pool.npy','wb') as fh:
    np.save(fh, data)
with open('/tmp/target.npy','wb') as fh:
    np.save(fh, tdata)
print("saved")
