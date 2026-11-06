import os, time, hashlib, pickle, numpy as np, h5py
from multiprocessing import Pool

base = "/data/icsa2027_data_20261101T090944Z/s1z"
os.makedirs('/work/chk', exist_ok=True)

def daterange(a, b):
    import datetime as dt
    d, out = a, []
    while d <= b:
        out.append(d); d += dt.timedelta(days=1)
    return out
ext_dates = daterange(__import__('datetime').date(1991,12,27), __import__('datetime').date(2003,1,5))
tgt_dates = daterange(__import__('datetime').date(2012,6,1), __import__('datetime').date(2012,8,31))
ext_paths = [f"{base}/sst_{s.strftime('%Y%m%d')}.nc" for s in ext_dates]
tgt_paths = [f"{base}/sst_{s.strftime('%Y%m%d')}.nc" for s in tgt_dates]
print("jobs:", len(ext_paths), len(tgt_paths))

def work(job):
    which, i, path = job
    with h5py.File(path, 'r') as f:
        b = f['analysed_sst'][0, 330:390, 551:611]
    return which, i, b

# resume state
state = {'ext_done': 0, 'tgt_done': 0}
sp = '/work/chk/state.json'
if os.path.exists(sp):
    import json
    state = json.load(open(sp))
    ext = np.load('/work/chk/ext.npy')
    tgt = np.load('/work/chk/tgt.npy')
    print("resuming at", state)
else:
    ext = np.zeros((4028, 60, 60), np.float32)
    tgt = np.zeros((92, 60, 60), np.float32)

jobs = [('e', i, ext_paths[i]) for i in range(state['ext_done'], 4028)] + \
       [('t', i, tgt_paths[i]) for i in range(state['tgt_done'], 92)]
print("remaining jobs:", len(jobs))

t0 = time.time(); n = 0
with Pool(8) as pool:
    for which, i, b in pool.imap_unordered(work, jobs, chunksize=8):
        (ext if which == 'e' else tgt)[i] = b
        n += 1
        if n % 400 == 0:
            np.save('/work/chk/ext.npy', ext); np.save('/work/chk/tgt.npy', tgt)
            import json
            json.dump({'ext_done': int((ext != 0).any(axis=(1,2)).sum() if False else state['ext_done'] + (1 if which=='e' else 0))}, open('/work/chk/state.json','w'))
            print(f"  {n}/{len(jobs)} ({n/(time.time()-t0):.0f}/s) elapsed {time.time()-t0:.0f}s", flush=True)

# final checkpoint
np.save('/work/chk/ext.npy', ext); np.save('/work/chk/tgt.npy', tgt)
import json
json.dump({'ext_done': 4028, 'tgt_done': 92}, open('/work/chk/state.json','w'))
print("load done in", time.time()-t0)
he = hashlib.sha256(np.ascontiguousarray(ext).tobytes()).hexdigest()
ht = hashlib.sha256(np.ascontiguousarray(tgt).tobytes()).hexdigest()
print("ext sha256:", he)
print("tgt sha256:", ht)
with open('/work/chk/hashes.txt','w') as f:
    f.write(he + "  ext\n" + ht + "  tgt\n")
print("finite ext:", np.isfinite(ext).mean(), "finite tgt:", np.isfinite(tgt).mean())
