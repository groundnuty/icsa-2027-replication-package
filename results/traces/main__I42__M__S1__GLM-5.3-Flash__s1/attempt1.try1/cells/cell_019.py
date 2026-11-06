import numpy as np
thr = np.load("/work/thr_raw.npy"); clim = np.load("/work/clim_raw.npy")
# Which doys are NaN for sea cells?
cell_allnan = np.isnan(thr).all(axis=0)  # (60,60)
sea_thr = thr[:, ~cell_allnan]  # (366, nsea)
nan_doy = np.isnan(sea_thr).any(axis=1)
print("doys NaN for some sea cell:", np.where(nan_doy)[0]+1)
print("count:", nan_doy.sum())
# is it the same set for clim?
sea_clim = clim[:, ~cell_allnan]
print("clim same:", np.array_equal(np.isnan(sea_clim).any(axis=1), nan_doy))
# For a specific sea cell, which doys are NaN?
c = sea_thr[:, 0]
print("cell0 NaN doys:", np.where(np.isnan(c))[0]+1)
c2 = sea_thr[:, 100]
print("cell100 NaN doys:", np.where(np.isnan(c2))[0]+1)
