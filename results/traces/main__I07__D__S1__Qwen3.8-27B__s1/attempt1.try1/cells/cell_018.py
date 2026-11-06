import numpy as np
S_base = np.load('/work/S_base.npy'); S_tgt = np.load('/work/S_tgt.npy')
M = np.load('/work/M.npy')
thr_s = np.load('/work/thr_s.npy'); clim_s = np.load('/work/clim_s.npy')
lat_vals = np.load('/work/lat_vals.npy'); lon_vals = np.load('/work/lon_vals.npy')

fin_tgt = np.isfinite(S_tgt)
sea = fin_tgt.all(axis=0).reshape(-1)  # (3600,)
NC = 3600
print("sea cells:", sea.sum())
print("sea thr_s all finite:", np.isfinite(thr_s[:, sea]).all())
print("sea clim_s all finite:", np.isfinite(clim_s[:, sea]).all())
print("land thr_s all NaN:", np.isnan(thr_s[:, ~sea]).all())
print("sea thr_s range (K):", thr_s[:, sea].min(), thr_s[:, sea].max())
print("sea clim_s range (K):", clim_s[:, sea].min(), clim_s[:, sea].max())

# manual hazen check for one sea cell, doy 153 (June 1)
c = int(np.argmax(sea))  # first sea cell (row-major)
d = 152  # 0-based for doy 153
idx = np.where(M[d])[0]
pool = S_base[idx, c//60, c%60]
pool_sorted = np.sort(pool)
h = (len(pool)+1)*0.9  # hazen
lo = int(np.floor(h)); 
manual = pool_sorted[lo-1] + (h-lo)*(pool_sorted[lo]-pool_sorted[lo-1])
print("manual hazen p90:", manual, "numpy thr pre-smooth check on same cell:")
# recompute unsmoothed for this cell
import numpy as np
flat = S_base.reshape(S_base.shape[0], NC)
thr_one = np.nanpercentile(flat[idx], 90, method='hazen')
print("numpy cell:", thr_one[c], "manual:", manual, "match:", np.isclose(thr_one[c], manual))
