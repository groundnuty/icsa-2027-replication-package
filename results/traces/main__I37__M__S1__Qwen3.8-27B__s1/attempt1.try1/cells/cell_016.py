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

start, end = 3000, 4028
t0 = time.time()
with Pool(8) as pool:
    done = pool.map(work_ext, list(zip(range(start, end), ext_paths[start:end])), chunksize=16)
with open('/tmp/mhw/state.pkl','wb') as fh:
    pickle.dump({'ext_loaded': end, 'tgt_loaded': 92}, fh)
print(f"loaded rows {start}..{end} in {time.time()-t0:.1f}s")

# quick sanity: no completely-NaN rows where we'd expect data; check ranges
ext = np.memmap('/tmp/mhw/sst_ext.npy', dtype=np.float32, shape=EXT_SHAPE)
tgt = np.memmap('/tmp/mhw/sst_tgt.npy', dtype=np.float32, shape=(92,60,60))
ext = np.array(ext, dtype=np.float64); tgt = np.array(tgt, dtype=np.float64)
print("ext finite frac:", np.isfinite(ext).mean(), "tgt finite frac:", np.isfinite(tgt).mean())
print("ext range:", np.nanmin(ext), np.nanmax(ext))
print("tgt range:", np.nanmin(tgt), np.nanmax(tgt))
np.save('/tmp/mhw/ext_check.npy', None)
