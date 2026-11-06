import os, numpy as np, datetime as dt, time
from concurrent.futures import ProcessPoolExecutor
import h5py
D='/data/icsa2027_data_20261101T090944Z/s1z'

def rd(fn):
    with h5py.File(os.path.join(D,fn),'r') as f:
        return fn, f['analysed_sst'][0,34:94,213:273].astype(np.float32)

def make_range(a,b):
    out=[]
    d=a
    while d<=b:
        out.append(f'sst_{d:%Y%m%d}.nc'); d+=dt.timedelta(days=1)
    return out

bfiles=make_range(dt.date(1991,12,27), dt.date(2003,1,5))
tfiles=make_range(dt.date(2004,6,1), dt.date(2004,8,31))
print("baseline files:", len(bfiles), "missing:", sum(1 for f in bfiles if not os.path.exists(os.path.join(D,f))))
print("target files:", len(tfiles), "missing:", sum(1 for f in tfiles if not os.path.exists(os.path.join(D,f))))

t0=time.time()
with ProcessPoolExecutor(max_workers=24) as ex:
    bres=list(ex.map(rd, bfiles, chunksize=4))
    tres=list(ex.map(rd, tfiles, chunksize=4))
print(f"read in {time.time()-t0:.1f}s")
bdata=np.stack([a for _,a in bres])
tdata=np.stack([a for _,a in tres])
print("baseline:", bdata.shape, "finite:", np.isfinite(bdata).mean())
print("target:", tdata.shape, "finite:", np.isfinite(tdata).mean())
sea=np.isfinite(tdata).all(axis=0)
print("sea cells:", sea.sum(), "of", sea.size)
np.save('/tmp/baseline.npy', bdata)
np.save('/tmp/target.npy', tdata)
with open('/tmp/meta.txt','w') as fh:
    fh.write('\n'.join(bfiles)+'\n')
print("saved")
