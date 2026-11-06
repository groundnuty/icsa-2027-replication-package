import numpy as np, warnings
warnings.filterwarnings('ignore')
thr = np.load('/work/thr_raw.npy'); clim = np.load('/work/clim_raw.npy')
thr_s = np.load('/work/thr_s.npy'); clim_s = np.load('/work/clim_s.npy')
T = np.load('/work/target_sst.npy'); sea = np.isfinite(T).all(axis=0)

ok = True
for j in [0, 1, 59, 152, 243, 365]:
    idxs = [(j-15+k) % 366 for k in range(31)]
    ok &= np.allclose(thr_s[j], thr[idxs].mean(axis=0), equal_nan=True)
    ok &= np.allclose(clim_s[j], clim[idxs].mean(axis=0), equal_nan=True)
print('smooth31 vs brute force (6 days, all cells, equal_nan):', bool(ok))
# sea-cell-only double check with exact float ops
j=152
idxs=[(j-15+k)%366 for k in range(31)]
d = np.abs(thr_s[j][sea] - thr[idxs][:,sea].mean(axis=0)).max()
print('max abs diff (day153, sea cells):', d)
# day366 window
chk366 = np.concatenate([thr[350:], thr[:15]]).mean(axis=0)
print('day366 == mean(days351..366,1..15):', np.allclose(thr_s[365][sea], chk366[sea], equal_nan=True),
      'maxdiff sea:', np.abs(thr_s[365][sea]-chk366[sea]).max())
# clim range and thr vs clim sanity on sea cells
print('clim_s sea range:', np.nanmin(clim_s[:,sea]), np.nanmax(clim_s[:,sea]))
print('thr_s sea range:', np.nanmin(thr_s[:,sea]), np.nanmax(thr_s[:,sea]))
frac = (thr_s[:,sea] < clim_s[:,sea]).mean()
print('fraction of (day,sea-cell) where thr<clim:', round(float(frac),4))
