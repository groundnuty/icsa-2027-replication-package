
import sys, numpy as np, pickle, warnings, time
sys.path.insert(0,'/work/mhw')
import common

ext, tgt, done = common.load_state()
with open('/work/mhw/idx.pkl','rb') as f: idx = pickle.load(f)

n_cells = 3600
thr  = np.full((n_cells, 366), np.nan)
clim = np.full((n_cells, 366), np.nan)
S = ext.astype(np.float64)  # 4028 x 3600
t0 = time.time()
with warnings.catch_warnings():
    warnings.simplefilter('ignore', RuntimeWarning)
    for d in range(1, 367):
        if d == 60: continue
        X = S[:, idx[d]]            # (3600, 121)
        thr[:, d-1]  = np.nanquantile(X, 0.9, method='hazen', axis=1)
        clim[:, d-1] = np.nanmean(X, axis=1)
print('pools done in', round(time.time()-t0,1), 's')
print('any NaN in thr (d!=60):', np.isnan(thr).sum(axis=1).max(), 'cells w/ any NaN:', (np.isnan(thr).sum(axis=1)>0).sum())
# day 60 fill
thr[:, 59]  = (thr[:, 58] + thr[:, 60]) / 2.0
clim[:, 59] = (clim[:, 58] + clim[:, 60]) / 2.0
print('day60 filled; NaNs now:', np.isnan(thr).sum(), np.isnan(clim).sum())

# smooth: circular centred 31-day mean
off = np.arange(-15, 16)
si = (np.arange(366)[:, None] + off[None, :]) % 366
t1 = time.time()
thr_s  = thr[:, si].mean(axis=2)
clim_s = clim[:, si].mean(axis=2)
print('smoothed in', round(time.time()-t1,1), 's')
print('thr_s range:', thr_s.min(), thr_s.max())
np.save('/work/mhw/thr_s.npy', thr_s)
np.save('/work/mhw/clim_s.npy', clim_s)
np.save('/work/mhw/thr_raw.npy', thr)
print('saved')
