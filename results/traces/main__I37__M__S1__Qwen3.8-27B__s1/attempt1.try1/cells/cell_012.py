import os, pickle, time, numpy as np, h5py
from multiprocessing import Pool

base = "/data/icsa2027_data_20261101T090944Z/s1z"
EXT_SHAPE = (4028, 3600)
TGT_SHAPE = (92, 3600)
LAT_SL = slice(330, 390); LON_SL = slice(551, 611)

def make_mmaps():
    p_ext = '/tmp/mhw/sst_ext.npy'
    p_tgt = '/tmp/mhw/sst_tgt.npy'
    if not os.path.exists(p_ext):
        m = np.lib.format.open_memmap(p_ext, mode='w+', dtype=np.float32, shape=EXT_SHAPE)
        m.flush(); del m
    if not os.path.exists(p_tgt):
        m = np.lib.format.open_memmap(p_tgt, mode='w+', dtype=np.float32, shape=TGT_SHAPE)
        m.flush(); del m
    return p_ext, p_tgt

make_mmaps()
with open('/tmp/mhw/dates.pkl','rb') as fh:
    D = pickle.load(fh)
ext_paths = [f"{base}/sst_{s.replace('-','')}.nc" for s in D['ext']]
tgt_paths = [f"{base}/sst_{s.replace('-','')}.nc" for s in D['tgt']]

def work_ext(args):
    i, path = args
    mm = np.memmap('/tmp/mhw/sst_ext.npy', dtype=np.float32, shape=EXT_SHAPE, mode='r+')
    with h5py.File(path, 'r') as f:
        mm[i] = f['analysed_sst'][0, LAT_SL, LON_SL]
    mm.flush()
    return i

def work_tgt(args):
    i, path = args
    mm = np.memmap('/tmp/mhw/sst_tgt.npy', dtype=np.float32, shape=TGT_SHAPE, mode='r+')
    with h5py.File(path, 'r') as f:
        mm[i] = f['analysed_sst'][0, LAT_SL, LON_SL]
    mm.flush()
    return i

CHUNK = 500
jobs_ext = list(zip(range(4028), ext_paths))
jobs_tgt = list(zip(range(92), tgt_paths))

t0 = time.time()
with Pool(8) as pool:
    done = pool.map(work_ext, jobs_ext[:CHUNK], chunksize=16)
print(f"ext rows 0..{len(done)} loaded in {time.time()-t0:.1f}s ({len(done)/(time.time()-t0)*1000:.0f} files/s)")
