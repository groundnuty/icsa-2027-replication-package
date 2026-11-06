import numpy as np
# sanity check: what does NaN fraction look like per doy? All NaN for any doy?
thr = np.load("/work/thr_raw.npy"); clim = np.load("/work/clim_raw.npy")
nan_any = np.isnan(thr).any(axis=(1,2))
print("doys with any NaN threshold:", np.where(nan_any)[0]+1)
nan_all = np.isnan(thr).all(axis=(1,2))
print("doys with ALL NaN:", np.where(nan_all)[0]+1)
# cell-wise: any cell that is NaN for some doy?
print("cells with NaN threshold anywhere:", np.isnan(thr).any(axis=0).sum())
# per-cell land fraction
clim_nan_frac = np.isnan(clim).mean(axis=0)
print("NaN frac per cell: min/max:", clim_nan_frac.min(), clim_nan_frac.max())
import matplotlib
print("matplotlib available")
