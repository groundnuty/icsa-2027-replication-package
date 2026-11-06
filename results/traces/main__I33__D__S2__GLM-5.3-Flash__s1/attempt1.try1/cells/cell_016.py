import numpy as np
clim_raw = np.load('/work/clim_raw.npy'); thr_raw = np.load('/work/thr_raw.npy')
clim_sm = np.load('/work/clim_sm.npy');  thr_sm = np.load('/work/thr_sm.npy')
land = np.isnan(clim_sm[0]); sea = ~land

# CORRECT manual check: element i (doy i+1) -> window 0-based i-15..i+15
def man_smooth(raw2d):  # raw2d: (366, ncells)
    out = np.empty_like(raw2d)
    for i in range(366):
        out[i] = np.nanmean(raw2d[(np.arange(i-15, i+16)) % 366], axis=0)
    return out

idx = np.where(sea)
sel = [k for k in range(len(idx[0])) if idx[0][k] % 15 == 0 and idx[1][k] % 15 == 0][:12]
for nm, raw, sm in [('clim', clim_raw, clim_sm), ('thr', thr_raw, thr_sm)]:
    cells = np.stack([raw[:, idx[0][k], idx[1][k]] for k in sel], axis=1)
    m = man_smooth(cells)
    ref = np.stack([sm[:, idx[0][k], idx[1][k]] for k in sel], axis=1)
    print(nm, 'manual-vs-func max abs diff:', np.nanmax(np.abs(m - ref)))

# scipy check aligned element-wise
from scipy.ndimage import uniform_filter1d
for nm, sm in [('clim', clim_sm), ('thr', thr_sm)]:
    cells = np.stack([sm[:, idx[0][k], idx[1][k]] for k in sel], axis=1)
    s2 = np.stack([uniform_filter1d(cells[:, c], size=31, mode='wrap') for c in range(len(sel))], axis=1)
    print(nm, 'scipy-vs-func max abs diff:', np.nanmax(np.abs(cells - s2)))
print('day-to-day max jump (sea, clim):', np.abs(np.diff(clim_sm[:, sea], axis=0)).max())
print('day-to-day max jump (sea, thr):', np.abs(np.diff(thr_sm[:, sea], axis=0)).max())
print('clim_sm doy153 @30,30 %.4f, thr_sm doy153 @30,30 %.4f' % (clim_sm[152,30,30], thr_sm[152,30,30]))