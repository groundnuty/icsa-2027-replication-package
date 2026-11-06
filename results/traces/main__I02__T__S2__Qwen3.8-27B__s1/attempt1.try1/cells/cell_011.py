import numpy as np, pickle
z = np.load('work/sst.npz')
SB = z['SB']
with open('work/pool_idx.pkl','rb') as fh: pool_idx = pickle.load(fh)
n_cells = 3600
SBf = SB.reshape(4028, n_cells)
z2 = np.load('work/thr.npz')
thr, clim, thr_s, clim_s, sea = z2['thr'], z2['clim'], z2['thr_s'], z2['clim_s'], z2['sea']

def ref_pool(dd, c):
    return [float(v) for v in SBf[pool_idx[dd], c] if np.isfinite(v)]

fails = 0
cells = list(range(0, n_cells, 97)) + [0, 123, 1800, 3599]
for c in cells:
    for dd in [1, 2, 59, 61, 62, 100, 153, 200, 244, 300, 365, 366]:
        vals = ref_pool(dd, c)
        exp_q = np.quantile(vals, 0.9, method='hazen') if vals else np.nan
        exp_m = float(np.mean(vals)) if vals else np.nan
        if not ((np.isnan(exp_q) and np.isnan(thr[c, dd-1])) or abs(thr[c, dd-1] - exp_q) < 1e-9):
            fails += 1; print("MISMATCH thr", c, dd, thr[c, dd-1], exp_q)
        if not ((np.isnan(exp_m) and np.isnan(clim[c, dd-1])) or abs(clim[c, dd-1] - exp_m) < 1e-9):
            fails += 1; print("MISMATCH clim", c, dd)
    for dd in [1, 2, 45, 60, 61, 153, 366]:
        idxs = [(dd - 1 + k) % 366 for k in range(-15, 16)]
        exp_t = float(np.mean(thr[c, idxs]))
        exp_c = float(np.mean(clim[c, idxs]))
        if not ((np.isnan(exp_t) and np.isnan(thr_s[c, dd-1])) or abs(thr_s[c, dd-1] - exp_t) < 1e-9):
            fails += 1; print("MISMATCH thr_s", c, dd, thr_s[c, dd-1], exp_t)
        if not ((np.isnan(exp_c) and np.isnan(clim_s[c, dd-1])) or abs(clim_s[c, dd-1] - exp_c) < 1e-9):
            fails += 1; print("MISMATCH clim_s", c, dd)
print("cross-check fails:", fails)
