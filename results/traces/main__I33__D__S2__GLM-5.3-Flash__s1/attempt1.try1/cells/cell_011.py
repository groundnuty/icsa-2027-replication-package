import numpy as np
from scipy.ndimage import uniform_filter1d
clim_sm = np.load('/work/clim_sm.npy'); thr_sm = np.load('/work/thr_sm.npy')
land = np.isnan(clim_sm[0])
print('land cells (NaN on doy1):', land.sum())
print('all land NaN all year:', np.isnan(clim_sm[:, land]).all(), np.isnan(thr_sm[:, land]).all())
print('any sea-cell NaNs in clim_sm/thr_sm:', np.isnan(clim_sm[:, ~land]).any(), np.isnan(thr_sm[:, ~land]).any())
# scipy cross-check on sea cells only
i_s, j_s = np.where(~land)
sel = (i_s % 7 == 0) & (j_s % 7 == 0)
cells = list(zip(i_s[sel], j_s[sel]))[:40]
for name, arr in [('clim', clim_sm), ('thr', thr_sm)]:
    ref = np.stack([arr[:, i, j] for i, j in cells], axis=1)
    s2 = np.stack([uniform_filter1d(arr[:, i, j], size=31, mode='wrap') for i, j in cells], axis=1)
    print(name, 'scipy wrap max abs diff:', np.abs(ref - s2).max())
# also compare vs a manual loop on one cell
i, j = cells[0]
x = clim_sm[:, i, j].copy()
raw = np.load('/work/clim_raw.npy')[:, i, j]
man = np.array([np.nanmean(raw[(np.arange(d-15, d+16)) % 366]) for d in range(1, 367)])
print('manual loop max abs diff:', np.abs(x - man).max())
print('sample clim_sm sea cell doy153/244/1:', x[152], x[243], x[0])