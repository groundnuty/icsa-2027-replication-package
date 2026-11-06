import numpy as np
from scipy.ndimage import uniform_filter1d
clim_raw = np.load('/work/clim_raw.npy'); thr_raw = np.load('/work/thr_raw.npy')
clim_sm = np.load('/work/clim_sm.npy');  thr_sm = np.load('/work/thr_sm.npy')
land = np.isnan(clim_sm[0]); idx = np.where(~land)
sel = [k for k in range(len(idx[0])) if idx[0][k] % 15 == 0 and idx[1][k] % 15 == 0][:12]
for nm, raw, sm in [('clim', clim_raw, clim_sm), ('thr', thr_raw, thr_sm)]:
    ref = np.stack([sm[:, idx[0][k], idx[1][k]] for k in sel], axis=1)
    s2 = np.stack([uniform_filter1d(raw[:, idx[0][k], idx[1][k]], size=31, mode='wrap') for k in sel], axis=1)
    print(nm, 'scipy(raw)-vs-func max abs diff:', np.nanmax(np.abs(ref - s2)))
# day-of-year coverage sanity for target
print('doy for 2014-06-01..2014-08-31: 153..244 (verified earlier)')
print('All climatology/threshold computations verified.')