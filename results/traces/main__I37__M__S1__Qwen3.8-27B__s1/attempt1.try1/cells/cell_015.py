import os, pickle, time, numpy as np, h5py
from multiprocessing import Pool

EXT_SHAPE = (4028, 60, 60)
base = "/data/icsa2027_data_20261101T090944Z/s1z"
with open('/tmp/mhw/dates.pkl','rb') as fh:
    D = pickle.load(fh)
ext_paths = [f"{base}/sst_{s.replace('-','')}.nc" for s in D['ext']]

def work_ext(args):
    i, path = args
    mm = np.memmap('/tmp/mhw/sst_ext.npy', dtype=np.float32, shape=EXT_SHAPE, mode='r+')
    with h5py.File(path, 'r') as f:
        mm[i] = f['analysed_sst'][0, 330:390, 551:611]
    mm.flush()
    return i

start, end = 1500, 3000
t0 = time.time()
with Pool(16) as pool:
    done = pool.map(work_ext, list(zip(range(start, end), ext_paths[start:end])), chunksize=32)
with open('/tmp/mhw/state.pkl','wb') as fh:
    pickle.dump({'ext_loaded': end, 'tgt_loaded': 92}, fh)
print(f"loaded rows {start}..{end} in {time.time()-t0:.1f}s ({(end-start)/(time.time()-t0):.0f} files/s)")
