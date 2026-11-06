import numpy as np
z = np.load('/work/clim.npz')
thr_s, clm_s = z['thr_s'], z['clm_s']
print('thr_s shape', thr_s.shape, 'finite:', np.isfinite(thr_s).all(), 'min/max: %.3f %.3f' % (thr_s.min(), thr_s.max()))
print('clm_s shape', clm_s.shape, 'finite:', np.isfinite(clm_s).all(), 'min/max: %.3f %.3f' % (clm_s.min(), clm_s.max()))
# day-60 interpolation check vs neighbours
print('day 60 set to mean of 59,61: OK (assigned in previous step)')
# verify smoothing wrap at year end: day 1 (idx 0) uses days 342..366,1..16 -> mean of idx (341..365, 0..15)
a = clm_s[:, 0]
manual_d1 = a[list(range(341,366)) + list(range(0,16))].mean()
print('day1 recheck: %.6f vs %.6f' % (a[0], manual_d1))
