import numpy as np, os, time, datetime as dt
print(os.path.getsize('/tmp/baseline.npy'), os.path.getsize('/tmp/target.npy'))
bdata=np.load('/tmp/baseline.npy', mmap_mode='r')
tdata=np.load('/tmp/target.npy')
print(bdata.shape, tdata.shape)
sea=np.isfinite(tdata).all(axis=0)
print("sea cells:", sea.sum())
# check per-day finite pattern constant
fin=np.isfinite(tdata)
print("per-day finite counts unique:", np.unique(fin.sum(axis=(1,2))))
# land cells same across baseline?
finb=np.isfinite(np.asarray(bdata[:400]))
percell=finb.all(axis=0)
print("cells finite on first 400 baseline days:", percell.sum())
print("same set as sea cells:", np.array_equal(percell, sea))
# check a few individual baseline days for any-cell NaN differences
any_nan_per_day=(~finb).sum(axis=(1,2))
print("unique nan counts in first 400 baseline days:", np.unique(any_nan_per_day))
# timing test of nanquantile on one pool
vals=np.asarray(bdata[:121]).astype(np.float64)
t0=time.time()
q=np.nanquantile(vals, 0.9, axis=0, method='hazen')
t1=time.time()
print(f"nanquantile (121,60,60): {t1-t0:.3f}s -> est 365 days: {365*(t1-t0):.0f}s")
m=np.nanmean(vals, axis=0)
print("q sample:", q[40,40], "mean sample:", m[40,40])
