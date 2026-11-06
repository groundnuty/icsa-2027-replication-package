import os, pickle, time, numpy as np, h5py
from multiprocessing import Pool

for p in ('/tmp/mhw/sst_ext.npy', '/tmp/mhw/sst_tgt.npy'):
    if os.path.exists(p): os.remove(p)

EXT_SHAPE = (4028, 60, 60)
TGT_SHAPE = (92, 60, 60)
np.lib.format.open_memmap('/tmp/mhw/sst_ext.npy', mode='w+', dtype=np.float32, shape=EXT_SHAPE)
np.lib.format.open_memmap('/tmp/mhw/sst_tgt.npy', mode='w+', dtype=np.float32, shape=TGT_SHAPE)

base = "/data/icsa2027_data_20261101T090944Z/s1z"
with open('/tmp/mhw/dates.pkl','rb') as fh:
    D = pickle.load(fh)
ext_paths = [f"{base}/sst_{s.replace('-','')}.nc" for s in D['ext']]
tgt_paths = [f"{base}/sst_{s.replace('-','')}.nc" for s in D['tgt']]

def work_ext(args):
    i, path = args
    mm = np.memmap('/tmp/mhw/sst_ext.npy', dtype=np.float32, shape=EXT_SHAPE, mode='r+')
    with h5py.File(path, 'r') as f:
        mm[i] = f['analysed_sst'][0, 330:390, 551:611]
    mm.flush()
    return i

def work_tgt(args):
    i, path = args
    mm = np.memmap('/tmp/mhw/sst_tgt.npy', dtype=np.float32, shape=TGT_SHAPE, mode='r+')
    with h5py.File(path, 'r') as f:
        mm[i] = f['analysed_sst'][0, 330:390, 551:611]
    mm.flush()
    return i

CHUNK = 500
jobs_ext = list(zip(range(4028), ext_paths))
jobs_tgt = list(zip(range(92), tgt_paths))

t0 = time.time()
with Pool(8) as pool:
    done = pool.map(work_ext, jobs_ext[:CHUNK], chunksize=16)
    done_t = pool.map(work_tgt, jobs_tgt, chunksize=16)
print(f"ext rows {len(done)} + tgt rows {len(done_t)} loaded in {time.time()-t0:.1f}s ({len(done)/(time.time()-t0)*1000:.0f} files/s)")
import pickle
with open('/tmp/mhw/state.pkl','wb') as fh:
    pickle.dump({'ext_loaded': len(done), 'tgt_loaded': len(done_t)}, fh)
