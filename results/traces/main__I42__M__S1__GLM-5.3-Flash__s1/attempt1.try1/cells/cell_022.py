import numpy as np
thr_s = np.load("/work/thr_smooth.npy")
land = ~np.isfinite(thr_s).all(axis=0)
print("non-finite cells:", land.sum())
se = thr_s[:, ~land]
nf = ~np.isfinite(se)
print("doys with any non-finite:", np.where(nf.any(axis=1))[0]+1)
print("cells with any non-finite:", nf.any(axis=0).sum())
