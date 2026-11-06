import numpy as np
thr = np.load("/work/thr_raw.npy"); clim = np.load("/work/clim_raw.npy")
# Which cells are fully NaN (land)?
cell_allnan_thr = np.isnan(thr).all(axis=0)
cell_allnan_clim = np.isnan(clim).all(axis=0)
print("all-NaN thr cells:", cell_allnan_thr.sum(), " all-NaN clim cells:", cell_allnan_clim.sum())
# cells with SOME NaN
some_nan = np.isnan(thr).any(axis=0) & ~cell_allnan_thr
print("sea cells with some NaN thr:", some_nan.sum())
print("land cells:", cell_allnan_thr.sum(), "of", 60*60)
# NaN frac distribution
site_g = np.isnan(clim).mean(axis=0)
vals = site_g[~cell_allnan_clim]
print("sea cells NaN frac: min %.4f max %.4f mean %.4f" % (vals.min(), vals.max(), vals.mean()))
# how many sea cells have any NaN at all
print("sea cells with >=1 NaN:", (np.isnan(thr).any(axis=0) & ~cell_allnan_thr).sum())
# Histogram-ish: frac>0.0027 only?
print("unique-ish fracs (rounded 3dp):", np.unique(np.round(vals,3))[:10])
