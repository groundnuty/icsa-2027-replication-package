
import sys, numpy as np
sys.path.insert(0,'/work/mhw')
sea = np.load('/work/mhw/sea.npy')
thr = np.load('/work/mhw/thr_raw.npy')
thr_s = np.load('/work/mhw/thr_s.npy')
clim_s = np.load('/work/mhw/clim_s.npy')

ns = sea.sum()
print('sea cells:', ns)
print('sea cells with NaN in thr (incl d60):', int(np.isnan(thr[sea, :]).any(axis=1).sum()))
print('sea cells with NaN in thr_s:', int(np.isnan(thr_s[sea, :]).any(axis=1).sum()))
print('sea cells with NaN in clim_s:', int(np.isnan(clim_s[sea, :]).any(axis=1).sum()))
print('thr_s sea range:', round(float(thr_s[sea, :].min()),3), round(float(thr_s[sea, :].max()),3))
print('mean thr_s over sea cells, doys 153-244:', round(float(thr_s[sea, :][:, 152:244].mean()),4), 'K')
print('mean clim_s over sea cells, doys 153-244:', round(float(clim_s[sea, :][:, 152:244].mean()),4), 'K')

import common, pickle
ext, tgt, done = common.load_state()
with open('/work/mhw/idx.pkl','rb') as f: idx = pickle.load(f)
i_cell = int(np.flatnonzero(sea)[0])
for d in (153, 200, 61):
    X = ext[idx[d], i_cell].astype(np.float64)
    q = np.nanquantile(X, 0.9, method='hazen'); m = np.nanmean(X)
    print(f'cell {i_cell} d {d}: pool {X.size} finite {np.isfinite(X).sum()} q_manual {q:.6f} vs stored {thr[i_cell, d-1]:.6f} match {np.isclose(q, thr[i_cell, d-1])} clim_manual {m:.6f}')
