import numpy as np, h5py, fsspec, multiprocessing as mp, time, os, datetime as dt

def worker_init():
    global FS, H5
    import fsspec, h5py
    FS = fsspec.filesystem('onedata')
    f = FS.open('icsa2027_data_20261101T090944Z/s2z/sst_s2.nc', 'rb')
    H5 = h5py.File(f, 'r')

def read_days(day_idxs):
    dset = H5['analysed_sst']
    out = np.empty((len(day_idxs), 60, 60), dtype=np.float32)
    for i, t in enumerate(day_idxs):
        out[i] = dset[t, 404:464, 559:619]
    return out

# ---- build date index maps ----
d0 = dt.date(1982, 1, 1)
def idx_of(date): return (date - d0).days

# baseline extended window: 1991-12-27 .. 2003-01-05
b_lo, b_hi = dt.date(1991,12,27), dt.date(2003,1,5)
bidx = np.arange(idx_of(b_lo), idx_of(b_hi)+1)
bdates = [b_lo + dt.timedelta(days=int(k)) for k in range(len(bidx))]
print("baseline ext: n =", len(bidx), bdates[0], bdates[-1])

# target: 2021-06-01..2021-08-31
t_lo, t_hi = dt.date(2021,6,1), dt.date(2021,8,31)
tidx = np.arange(idx_of(t_lo), idx_of(t_hi)+1)
tdates = [t_lo + dt.timedelta(days=int(k)) for k in range(len(tidx))]
print("target: n =", len(tidx), tdates[0], tdates[-1])

t0 = time.time()
with mp.Pool(8, initializer=worker_init) as pool:
    bslices = [bidx[i:i+250] for i in range(0, len(bidx), 250)]
    tslices = [tidx[i:i+92] for i in range(0, len(tidx), 92)]
    bres = pool.map(read_days, bslices)
    tres = pool.map(read_days, tslices)
B = np.concatenate(bres, axis=0)  # (nbase, 60, 60) float32
T = np.concatenate(tres, axis=0)  # (92, 60, 60) float32
print("read time: %.1f s" % (time.time()-t0), "| B:", B.shape, "| T:", T.shape)
print("B finite frac:", np.isfinite(B).mean(), "| T finite frac:", np.isfinite(T).mean())

os.makedirs('work', exist_ok=True)
np.save('work/B.npy', B)
np.save('work/T.npy', T)
# save date arrays
np.save('work/bdays.npy', np.array([(b - dt.date(1970,1,1)).days for b in bdates], dtype=np.int64))
np.save('work/tdays.npy', np.array([(x - dt.date(1970,1,1)).days for x in tdates], dtype=np.int64))
print("saved.")
# quick sanity: per-cell finite counts in target
fin_all = np.isfinite(T).all(axis=0)
print("sea cells (finite all target days):", fin_all.sum(), "of", fin_all.size)
