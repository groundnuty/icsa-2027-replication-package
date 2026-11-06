
import sys, numpy as np
sys.path.insert(0,'/work/mhw')
sea = np.load('/work/mhw/sea.npy')
thr = np.load('/work/mhw/thr_raw.npy')
thr_s = np.load('/work/mhw/thr_s.npy')
clim_s = np.load('/work/mhw/clim_s.npy')

ns = sea.sum()
print('sea cells:', ns)
print('sea cells with NaN in thr (incl d60):', int((np.isnan(thr[:, sea]).any(axis=1)).sum()))
print('sea cells with NaN in thr_s:', int(np.isnan(thr_s[:, sea]).any(axis=1).sum()))
print('sea cells with NaN in clim_s:', int(np.isnan(clim_s[:, sea]).any(axis=1).sum()))
print('thr_s sea range:', round(float(thr_s[:, sea].min()),3), round(float(thr_s[:, sea].max()),3))
# sample: mean threshold for summer doys 153-244 across sea cells
print('mean thr_s over sea cells, doys 153-244:', round(float(thr_s[:, sea][:, 152:244].mean()),4), 'K')
print('mean clim_s over sea cells, doys 153-244:', round(float(clim_s[:, sea][:, 152:244].mean()),4), 'K')
# spot check one cell, one day: recompute manually
ext, tgt, done = None, None, None
import common
ext, tgt, done = common.load_state()
import pickle, datetime as dt
with open('/work/mhw/idx.pkl','rb') as f: idx = pickle.load(f)
doy_ext = np.load('/work/mhw/doy_ext.npy')
i_cell = int(np.flatnonzero(sea)[0])
d = 153
X = ext[idx[d], i_cell].astype(np.float64)
print('manual cell', i_cell, 'd', d, 'pool size', X.size, 'finite', np.isfinite(X).sum())
q = np.nanquantile(X, 0.9, method='hazen')
m = np.nanmean(X)
print('manual q:', q, 'm:', m, '| stored thr:', thr[i_cell, d-1], 'clim check via raw?')
print('match:', np.isclose(q, thr[i_cell, d-1]))
